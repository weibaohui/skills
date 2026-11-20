#!/usr/bin/env python3
"""
FDE 研发空间与缺陷管理工具 (cmcc-fde)
缺陷在底层是 itemType = 缺陷 (quexian) 的工作项, 与需求共用同一套网关端点。
本脚本在 manage_demands.py 已验证逻辑基础上, 固化缺陷类型并支持:
- 研发空间列表 (spaces)
- 缺陷列表 (list, IQL 按类型过滤 + 分页)
- 新建缺陷 (create)
- 缺陷状态流转 (update-status, 动态解析缺陷工作流节点)
- 缺陷删除 (delete)

实现要点:
  1. sessionToken 由 fde_common.get_req_session_token() 基于本地身份生成, 无浏览器依赖。
  2. 真实网关端点:
       - list   : POST /team/parse/api/search/hierarchy  (IQL: 类型 = '缺陷')
       - create : POST /team/parse/api/v2/items           (itemType 固定为 quexian)
       - update : PUT  /team/parse/api/v2/items/{id}      (status Pointer)
       - delete : POST /team/parse/functions/deleteItems  (Parse Cloud 函数)
  3. 空间码、缺陷类型、状态名称在运行期动态解析为内部 objectId, 不写死任何 ID。

用法示例:
  python3 manage_bugs.py spaces
  python3 manage_bugs.py list --space G2026000S
  python3 manage_bugs.py create --space G2026000S --title "登录页按钮错位"
  python3 manage_bugs.py update-status --space G2026000S --id <ID> --status 已确认
  python3 manage_bugs.py delete --space G2026000S --id <ID>
"""

import argparse
import json
from typing import Any, Dict, List, Optional

from fde_common import (
    make_request,
    load_auth_config,
    get_moss_headers,
    get_req_session_token,
)
from req_fields import build_payload, verify

# 需求子系统网关前缀
REQ_API = "/fde/moss/web/fde-req/api/team/parse/api"   # /search, /v2/items ...
SPACE_LIST = "/fde/moss/web/desktop/v1/api/v1/user/space/list"

# 缺陷类型: 名称 / key, objectId 运行期动态解析
BUG_TYPE_NAME = "缺陷"
BUG_TYPE_KEYS = ("quexian", "bug", "缺陷")


# ---------- 通用工具 ----------

def _ptr(object_id: str, class_name: str) -> Dict[str, str]:
    """构造 Parse Pointer"""
    return {"__type": "Pointer", "className": class_name, "objectId": object_id}


def _headers(space_code: str) -> Dict[str, str]:
    """需求子系统统一鉴权头（token 由本地身份生成）"""
    auth = load_auth_config()
    token = get_req_session_token()
    h = get_moss_headers()
    h["x-auth-module"] = "SPACE"
    h["x-auth-moduleid"] = space_code
    h["X-Parse-Application-Id"] = auth.get("enterpriseId", "ENT_999999")
    h["X-Parse-Session-Token"] = token
    h["x-parse-session-token"] = token
    return h


def _is_error(res: Any) -> bool:
    return isinstance(res, dict) and bool(res.get("error"))


def _err_msg(res: Dict[str, Any]) -> str:
    msg = res.get("message", "")
    try:
        j = json.loads(msg)
        return j.get("error") or j.get("desc") or msg
    except Exception:
        return str(msg)


# ---------- 空间解析 ----------

def _fetch_spaces() -> List[Dict[str, Any]]:
    h = get_moss_headers()
    h["x-auth-module"] = "PLATFORM"
    res = make_request("GET", SPACE_LIST,
                       params={"pageNo": 1, "pageSize": 50}, custom_headers=h)
    if _is_error(res):
        return []
    return res.get("data", {}).get("list", []) or []


def _resolve_space(space_code: Optional[str]) -> Dict[str, str]:
    """返回 {'code','name','objectId'}。未指定时用 default_space_code。"""
    auth = load_auth_config()
    code = space_code or auth.get("default_space_code", "")
    spaces = _fetch_spaces()
    for s in spaces:
        if s.get("spaceCode") == code:
            return {
                "code": code,
                "name": s.get("spaceName", ""),
                "objectId": s.get("spaceId", ""),
            }
    return {"code": code, "name": "", "objectId": ""}


def _workspace_object_id(space: Dict[str, str], h: Dict[str, str]) -> str:
    """解析工作区内部 objectId (形如 xNwFNHVjqK)。"""
    p = {
        "iql": "(所属空间 = '%s')" % (space["name"] or space["code"]),
        "size": 1, "from": 0, "extend": {},
        "fields": ["id", "workspace"],
        "refererInfo": {"workspaceKey": space["code"]},
    }
    res = make_request("POST", REQ_API + "/search/hierarchy", data=p, custom_headers=h)
    try:
        items = res.get("payload", {}).get("items", [])
        if items:
            return items[0].get("workspace", {}).get("objectId", "")
    except Exception:
        pass
    return ""


# ---------- 缺陷类型 / 状态解析 ----------

def _bug_type_object_id(ws_id: str, h: Dict[str, str]) -> str:
    """解析缺陷 itemType 的 objectId (优先 quexian, 再按 name/key 兜底)。"""
    res = make_request("GET", REQ_API + "/itemType/search",
                       params={"workspace": ws_id}, custom_headers=h)
    types = res.get("payload", []) if isinstance(res, dict) else []
    # 优先 key = quexian
    for t in types:
        if str(t.get("key", "")).lower() == "quexian":
            return t.get("objectId", "")
    # 再按 name=缺陷 / key=bug 兜底
    for t in types:
        if t.get("name") == BUG_TYPE_NAME or str(t.get("key", "")).lower() in ("bug", "缺陷"):
            return t.get("objectId", "")
    return ""


def _status_object_id(name: str, item_id: str, h: Dict[str, str]) -> str:
    """把状态名（如 '已确认'）解析为该缺陷工作流节点的 statusId。"""
    res = make_request("GET", REQ_API + "/workflows/item/" + item_id, custom_headers=h)
    if isinstance(res, dict):
        for node in res.get("nodes", []):
            if node.get("name") == name or node.get("key") == name:
                return node.get("statusId", "")
    return ""


# ---------- 命令实现 ----------

def cmd_spaces(args):
    spaces = _fetch_spaces()
    print(f"\n【研发空间列表】(共 {len(spaces)} 个)")
    print("-" * 100)
    print(f"{'空间编码':<14} | {'空间ID':<24} | {'空间名称':<20} | {'负责人'}")
    print("-" * 100)
    for s in spaces:
        print(f"{s.get('spaceCode',''):<14} | {s.get('spaceId',''):<24} | "
              f"{s.get('spaceName',''):<20} | {s.get('ownerName','')}")
    print("-" * 100 + "\n")


def cmd_list(args):
    space = _resolve_space(args.space)
    if not space["code"]:
        print("[x] 未指定空间。请用 --space 指定或用 manage_spaces.py 设置默认空间。")
        return
    print(f"[*] 查询空间 [{space['code']}] {space['name']} 的缺陷...")
    h = _headers(space["code"])
    iql = "(所属空间 = '%s') and (类型 = '%s') order by 创建时间 desc" % (
        space["name"] or space["code"], BUG_TYPE_NAME)
    payload = {
        "iql": iql,
        "size": args.size, "from": (args.page - 1) * args.size,
        "extend": {},
        "fields": ["id", "key", "name", "status", "itemType", "assignee", "createdAt"],
        "refererInfo": {"workspaceKey": space["code"]},
    }
    res = make_request("POST", REQ_API + "/search/hierarchy", data=payload, custom_headers=h)
    if _is_error(res):
        print(f"[x] 查询失败: {_err_msg(res)}")
        return
    pl = res.get("payload", {})
    items = pl.get("items", [])
    total = pl.get("totalCount", len(items))
    print(f"\n【空间 {space['code']} 缺陷清单】(共 {total} 条, 本页 {len(items)} 条)")
    print("-" * 100)
    print(f"{'ID':<12} | {'Key':<16} | {'标题':<32} | {'状态':<10}")
    print("-" * 100)
    for it in items:
        iid = it.get("id", "")
        key = it.get("key", "")
        name = (it.get("name", "") or "")[:30]
        st = (it.get("status", {}) or {}).get("name", "")
        print(f"{iid:<12} | {key:<16} | {name:<32} | {st:<10}")
    print("-" * 100 + "\n")


def cmd_create(args):
    space = _resolve_space(args.space)
    if not space["code"]:
        print("[x] 未指定空间。")
        return
    h = _headers(space["code"])
    ws_id = _workspace_object_id(space, h)
    if not ws_id:
        print("[x] 无法解析工作区内部 ID(该空间可能暂无任何工作项)。")
        return
    bug_type_id = _bug_type_object_id(ws_id, h)
    if not bug_type_id:
        print("[x] 无法解析缺陷类型 (quexian) 的 objectId。")
        return
    payload = {
        "name": args.title,
        "description": args.desc,
        "workspace": _ptr(ws_id, "Workspace"),
        "itemType": _ptr(bug_type_id, "ItemType"),
    }
    print(f"[*] 在空间 [{space['code']}] 创建缺陷: 《{args.title}》...")
    res = make_request("POST", REQ_API + "/v2/items", data=payload, custom_headers=h)
    if _is_error(res):
        print(f"[x] 创建失败: {_err_msg(res)}")
        return
    iid = res.get("objectId", "")
    print("\n" + "=" * 60)
    print("【✓】缺陷创建成功")
    print("=" * 60)
    print(f"  ID:    {iid}")
    print(f"  Key:   {res.get('key','')}")
    print(f"  标题:  {res.get('name','')}")
    print(f"  空间:  {space['code']}")
    print("=" * 60 + "\n")


def cmd_update_status(args):
    space = _resolve_space(args.space)
    if not space["code"]:
        print("[x] 未指定空间。")
        return
    h = _headers(space["code"])
    st_id = _status_object_id(args.status, args.id, h)
    if not st_id:
        print(f"[x] 无法解析状态 [{args.status}],请检查状态名或缺陷 ID。")
        return
    payload = {"status": _ptr(st_id, "Status")}
    print(f"[*] 将缺陷 [{args.id}] 状态改为 [{args.status}] ...")
    res = make_request("PUT", REQ_API + "/v2/items/" + args.id,
                       data=payload, custom_headers=h)
    if _is_error(res):
        print(f"[x] 更新失败: {_err_msg(res)}")
        return
    print(f"[✓] 缺陷 [{args.id}] 状态已更新为 [{args.status}]\n")


def cmd_delete(args):
    space = _resolve_space(args.space)
    if not space["code"]:
        print("[x] 未指定空间。")
        return
    h = _headers(space["code"])
    # Cloud 函数端点路径特殊：/team/parse/functions (无第二个 api)
    fn_url = "/fde/moss/web/fde-req/api/team/parse/functions/deleteItems"
    print(f"[*] 删除缺陷 [{args.id}] ...")
    res = make_request("POST", fn_url, data={"itemIds": [args.id]}, custom_headers=h)
    if _is_error(res):
        print(f"[x] 删除失败: {_err_msg(res)}")
        return
    if isinstance(res, dict) and "DOCTYPE" in str(res.get("raw_text", "")):
        print("[x] 删除失败: 网关返回异常页面")
        return
    print(f"[✓] 缺陷 [{args.id}] 已删除\n")


def cmd_update(args):
    """通用字段编辑：--set 字段=值（可多次），自动区分顶层/values 并转换类型。"""
    space = _resolve_space(args.space)
    if not space["code"]:
        print("[x] 未指定空间。")
        return
    h = _headers(space["code"])
    try:
        payload, notes = build_payload(args.set, h, space)
    except ValueError as e:
        print(f"[x] {e}")
        return
    print(f"[*] 更新缺陷 [{args.id}] 的字段:")
    print("\n".join(notes))
    res = make_request("PUT", REQ_API + "/v2/items/" + args.id, data=payload, custom_headers=h)
    if _is_error(res):
        print(f"[x] 更新失败: {_err_msg(res)}")
        return
    ok, checks = verify(args.id, payload, space, h)
    print("\n" + "=" * 60)
    print("【✓】更新请求已提交" if ok else "【!】更新已提交, 但读回核对有差异")
    print("=" * 60)
    print("\n".join(checks))
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="FDE 研发空间与缺陷管理工具")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("spaces", help="列出研发空间")
    p.set_defaults(func=cmd_spaces)

    p = sub.add_parser("list", help="查询缺陷列表")
    p.add_argument("--space", "-s", default=None)
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--size", type=int, default=20)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("create", help="创建缺陷")
    p.add_argument("--space", "-s", default=None)
    p.add_argument("--title", "-t", required=True)
    p.add_argument("--desc", "-d", default="")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("update-status", help="更新状态")
    p.add_argument("--space", "-s", default=None)
    p.add_argument("--id", "-i", required=True)
    p.add_argument("--status", required=True)
    p.set_defaults(func=cmd_update_status)

    p = sub.add_parser("delete", help="删除缺陷")
    p.add_argument("--space", "-s", default=None)
    p.add_argument("--id", "-i", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("update", help="编辑任意字段 (--set 字段=值, 可多次)")
    p.add_argument("--space", "-s", default=None)
    p.add_argument("--id", "-i", required=True)
    p.add_argument("--set", dest="set", action="append", required=True, metavar="字段=值",
                   help="如: --set 优先级=P1 --set 描述=文本 --set 负责人=张三 (可重复)")
    p.set_defaults(func=cmd_update)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
