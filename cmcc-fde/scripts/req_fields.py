#!/usr/bin/env python3
"""
需求子系统字段更新公共模块 (cmcc-fde)
供 manage_demands.py / manage_bugs.py 共用, 负责:
  1. 字段别名归一化 (中文名 / key 名)
  2. --set 字符串值 → 网关期望的类型 (UUID / 数组 / Slate 富文本 / 用户对象)
  3. 顶层字段 vs values 字段的写入位置区分
  4. 写入后读回验证 (PUT 常返回成功但未真正落库, 必须复查)

关键实测结论 (2026-11):
  - 顶层直接写: name, priority (status 由 update-status 处理)
  - values 前缀写: 其余全部字段
  - 选项/人员字段必须传数组, 富文本必须传 Slate 数组, 否则假成功
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from fde_common import make_request

REQ_API = "/fde/moss/web/fde-req/api/team/parse/api"

# 写入在顶层的字段 (实测: 只有 name; priority 虽可读在顶层, 但写入必须放 values)
TOP_FIELDS = {"name"}

# 优先级名称 → UUID (实测 P0-P5)
PRIORITY_UUID = {
    "p0": "8f7912a5-9176-4a79-a269-2269ac42b5a2",
    "p1": "af12151d-af82-407f-b0de-0b9985525cef",
    "p2": "ca8c3e43-3e7b-444d-8940-d0967d944921",
    "p3": "1a3e1092-7d70-42ee-ad38-0e8d953c4c23",
    "p4": "fef17446-412d-43c9-8cd6-b73deb999010",
    "p5": "805b0a86-12d5-49d3-b91f-420832e1d0a4",
}

# 富文本字段 (Slate 数组)
RICH_TEXT_FIELDS = {
    "requirement", "StepReproduce", "acceptanceCriteria",
    "content", "taskDescription", "reason", "Source",
}

# 人员字段 (用户对象数组), 支持按姓名/账号解析
USER_FIELDS = {
    "assignee", "watchers", "proposer", "participant",
    "verifier", "reporter", "flowHandler", "ItemHandler",
}

# 选项数组字段 (字符串数组, 如 ["3-一般错误"])
OPTION_ARRAY_FIELDS = {"Orderofeverity", "SecurityLevel", "version", "sprint"}

# 对象数组字段 ([{"value": "..."}], 如标签)
OBJECT_ARRAY_FIELDS = {"Tag"}

# 字段别名 → 网关 key
FIELD_ALIASES = {
    "标题": "name", "title": "name", "name": "name",
    "优先级": "priority", "priority": "priority",
    "严重程度": "Orderofeverity", "严重性": "Orderofeverity",
    "severity": "Orderofeverity", "orderofeverity": "Orderofeverity",
    "描述": "requirement", "需求描述": "requirement", "缺陷描述": "requirement",
    "description": "requirement", "requirement": "requirement",
    "复现步骤": "StepReproduce", "stepreproduce": "StepReproduce",
    "验收标准": "acceptanceCriteria", "acceptancecriteria": "acceptanceCriteria",
    "负责人": "assignee", "处理人": "assignee", "assignee": "assignee",
    "关注人": "watchers", "关注": "watchers", "watchers": "watchers",
    "提出人": "proposer", "proposer": "proposer",
    "验证者": "verifier", "verifier": "verifier",
    "报告人": "reporter", "reporter": "reporter",
    "标签": "Tag", "tag": "Tag",
    "迭代": "sprint", "sprint": "sprint",
    "故事点": "StoryPoint", "storypoint": "StoryPoint",
    "版本": "version", "version": "version",
    "计划开始时间": "PlanStartTime", "planstarttime": "PlanStartTime",
    "计划结束时间": "PlanFinishTime", "planfinishtime": "PlanFinishTime",
    "安全级别": "SecurityLevel", "securitylevel": "SecurityLevel",
}


def canonical_field(name: str) -> Optional[str]:
    """把别名/中文名归一化为网关字段 key。"""
    return FIELD_ALIASES.get(name) or FIELD_ALIASES.get(name.lower())


def _to_slate(text: str) -> List[Dict[str, Any]]:
    """纯文本 → Slate 段落数组; 若已是 JSON 数组则原样解析。"""
    stripped = text.strip()
    if stripped.startswith("["):
        try:
            parsed = json.loads(stripped)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
    return [{"type": "p", "children": [{"text": text}]}]


def _resolve_user(query: str, h: Dict[str, str], cache: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """按昵称/账号解析用户, 返回可直接写入的用户对象。"""
    q = query.strip()
    hits = [u for u in cache
            if q in (u.get("nickname") or "") or q.lower() in (u.get("username") or "").lower()]
    if not hits:
        return None
    u = hits[0]
    uid = u.get("objectId", "")
    return {
        "__type": "Pointer", "className": "_User", "objectId": uid,
        "objectId": uid, "value": uid,
        "username": u.get("username", ""), "nickname": u.get("nickname", ""),
        "enabled": u.get("enabled", True), "deleted": u.get("deleted", False),
        "label": "%s(%s)" % (u.get("nickname", ""), uid),
    }


def _split_multi(raw: str) -> List[str]:
    """按中英文逗号/分号拆分多值。"""
    for sep in ["，", ";", "；", ","]:
        if sep in raw:
            return [x.strip() for x in raw.split(sep) if x.strip()]
    return [raw.strip()] if raw.strip() else []


def _load_user_cache(h: Dict[str, str], space: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """
    汇总可按姓名/账号解析的用户来源:
      1. /users 全量列表
      2. 空间内已有工作项的用户字段 (assignee/proposer/creator 等) —
         网关忽略 where 条件, 且 /users 前 500 条可能不含某些真实成员,
         从已有事项收集能保证覆盖本空间实际可指派的人。
    """
    users: Dict[str, Dict[str, Any]] = {}
    try:
        res = make_request("GET", REQ_API + "/users", params={"limit": 500}, custom_headers=h)
        for u in res.get("results", []) or []:
            if u.get("objectId"):
                users[u["objectId"]] = u
    except Exception:
        pass
    if space:
        try:
            p = {
                "iql": "(所属空间 = '%s')" % (space["name"] or space["code"]),
                "size": 200, "from": 0, "extend": {}, "fields": [],
                "refererInfo": {"workspaceKey": space["code"]},
            }
            r = make_request("POST", REQ_API + "/search/hierarchy", data=p, custom_headers=h)
            for it in r.get("payload", {}).get("items", []):
                vals = it.get("values", {}) or {}
                candidates = []
                for key in ("assignee", "proposer", "watchers", "verifier", "reporter"):
                    v = vals.get(key)
                    if isinstance(v, list):
                        candidates += v
                for key in ("createdBy", "updatedBy"):
                    v = it.get(key)
                    if isinstance(v, list):
                        candidates += v
                    elif isinstance(v, dict):
                        candidates.append(v)
                for u in candidates:
                    if not isinstance(u, dict) or not u.get("objectId"):
                        continue
                    uid = u["objectId"]
                    if uid not in users:
                        users[uid] = {
                            "objectId": uid,
                            "username": u.get("username", uid),
                            "nickname": u.get("nickname", ""),
                            "enabled": u.get("enabled", True),
                            "deleted": u.get("deleted", False),
                        }
        except Exception:
            pass
    return list(users.values())


def convert_value(field: str, raw: str, h: Dict[str, str],
                  user_cache: Optional[List[Dict[str, Any]]] = None,
                  space: Optional[Dict[str, str]] = None) -> Tuple[str, Any, str]:
    """
    把 --set 的原始字符串值转换为 (写入位置, 值, 说明)。
    写入位置: 'top' 或 'values'。
    """
    note = ""
    # 优先级: P0-P5 → UUID
    if field == "priority":
        key = raw.strip().lower()
        val = PRIORITY_UUID.get(key, raw.strip())
        if key in PRIORITY_UUID:
            note = "%s→UUID" % raw.strip().upper()
        return "values", val, note

    # 标题: 顶层字符串
    if field == "name":
        return "top", raw, note

    # 人员字段: 解析为用户对象数组
    if field in USER_FIELDS:
        if user_cache is None:
            user_cache = _load_user_cache(h, space)
        users = []
        for q in _split_multi(raw):
            u = _resolve_user(q, h, user_cache)
            if u:
                users.append(u)
            else:
                note += " 未找到用户[%s]" % q
        if not users:
            raise ValueError("无法解析人员: %s (可用姓名或账号, 多个用逗号分隔)" % raw)
        return "values", users, note.strip()

    # 富文本字段
    if field in RICH_TEXT_FIELDS:
        return "values", _to_slate(raw), ("Slate富文本" if not raw.strip().startswith("[") else "Slate原样")

    # 对象数组字段 (标签等, 形如 [{"value":"产品"}])
    if field in OBJECT_ARRAY_FIELDS:
        if raw.strip().startswith("["):
            try:
                return "values", json.loads(raw.strip()), "JSON数组"
            except Exception:
                pass
        return "values", [{"value": x} for x in _split_multi(raw)], "对象数组"

    # 选项数组字段
    if field in OPTION_ARRAY_FIELDS:
        if raw.strip().startswith("["):
            try:
                return "values", json.loads(raw.strip()), "JSON数组"
            except Exception:
                pass
        return "values", _split_multi(raw), "字符串数组"

    # 其它字段: 尝试 JSON 解析, 否则按字符串 (写入 values)
    stripped = raw.strip()
    if stripped.startswith("[") or stripped.startswith("{") or stripped.lower() in ("true", "false", "null"):
        try:
            return "values", json.loads(stripped), "JSON"
        except Exception:
            pass
    return "values", raw, note


def build_payload(sets: List[str], h: Dict[str, str],
                  space: Optional[Dict[str, str]] = None) -> Tuple[Dict[str, Any], List[str]]:
    """
    解析多个 '字段=值' 字符串, 生成 PUT payload。
    返回 (payload, 说明列表)。字段放顶层与 values 分层合并。
    """
    payload: Dict[str, Any] = {}
    values: Dict[str, Any] = {}
    notes = []
    # 仅在需要解析人员字段时, 预先加载一次用户缓存
    user_cache = None
    for item in sets:
        key = item.split("=", 1)[0].strip()
        if canonical_field(key) in USER_FIELDS:
            user_cache = _load_user_cache(h, space)
            break
    for item in sets:
        if "=" not in item:
            raise ValueError("无效的 --set 格式: %s (应为 字段=值)" % item)
        key, raw = item.split("=", 1)
        field = canonical_field(key.strip())
        if not field:
            raise ValueError("未知字段: %s (支持的字段见 SKILL.md 或 req_fields.py 的 FIELD_ALIASES)" % key.strip())
        location, value, note = convert_value(field, raw, h, user_cache, space)
        if location == "top":
            payload[field] = value
        else:
            values[field] = value
        notes.append("  %s = %s%s" % (field, _brief(value), ("  [%s]" % note) if note else ""))
    if values:
        payload["values"] = values
    return payload, notes


def _brief(v: Any) -> str:
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 60 else s[:57] + "..."


def find_item(item_id: str, space: Dict[str, str], h: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """从空间查询中按 id 找回某个工作项 (无单条详情 GET 端点)。"""
    p = {
        "iql": "(所属空间 = '%s')" % (space["name"] or space["code"]),
        "size": 200, "from": 0, "extend": {},
        "fields": [], "refererInfo": {"workspaceKey": space["code"]},
    }
    res = make_request("POST", REQ_API + "/search/hierarchy", data=p, custom_headers=h)
    for it in res.get("payload", {}).get("items", []):
        if it.get("id") == item_id or it.get("objectId") == item_id:
            return it
    return None


def _slate_text(v: Any) -> str:
    """提取 Slate 数组中的纯文本, 用于宽松比对。"""
    out = []
    def walk(nodes):
        if isinstance(nodes, list):
            for n in nodes:
                if isinstance(n, dict):
                    if "text" in n:
                        out.append(str(n.get("text", "")))
                    walk(n.get("children"))
        elif isinstance(nodes, dict):
            walk(nodes.get("children"))
    walk(v)
    return "".join(out).strip()


def verify(item_id: str, payload: Dict[str, Any], space: Dict[str, str],
           h: Dict[str, str]) -> Tuple[bool, List[str]]:
    """
    写入后读回验证。返回 (是否全部通过, 每项核对结果)。
    """
    item = find_item(item_id, space, h)
    if not item:
        return False, ["  [x] 读回失败: 找不到该工作项"]
    results = []
    all_ok = True
    values = item.get("values", {}) or {}
    for field, expected in payload.items():
        if field == "values":
            for k, v in payload["values"].items():
                actual = values.get(k)
                ok = _match(actual, v)
                all_ok = all_ok and ok
                results.append("  %s %s: %s" % ("[✓]" if ok else "[x]", k,
                                                 _brief(actual) if actual is not None else "<空>"))
        else:
            actual = item.get(field)
            ok = _match(actual, expected)
            all_ok = all_ok and ok
            results.append("  %s %s: %s" % ("[✓]" if ok else "[x]", field, _brief(actual)))
    return all_ok, results


def _match(actual: Any, expected: Any) -> bool:
    """比对读回值与期望值, 富文本按纯文本宽松比对。"""
    if actual == expected:
        return True
    if isinstance(expected, list) and all(isinstance(x, dict) for x in expected):
        # 富文本或用户对象: 富文本比文本, 用户对象比 objectId 集合
        if expected and "text" in json.dumps(expected[0], ensure_ascii=False):
            return _slate_text(actual) == _slate_text(expected)
        if expected and "objectId" in expected[0]:
            aids = {x.get("objectId") for x in (actual or []) if isinstance(x, dict)}
            eids = {x.get("objectId") for x in expected}
            return aids == eids
    return False
