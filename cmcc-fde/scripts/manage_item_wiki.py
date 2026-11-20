#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事项关联知识：上传任意文件（含 zip）到知识库并关联到需求/事项，或查询/取消关联。

接口链路（抓自 FDE 需求页「上传知识」插件 plugin_zyd_item_associate_wiki 4.40.6）：
  1. 上传  POST https://sti.chinamobile.com/fde-wiki/doc-open-api/CMCC/{spaceKey}/files/upload
           multipart: file, path=/{parentPageId}/{filename}   （>5MB 需分片+totalChunks/chunkIndex/uploadId）
           headers: token=<OPEN_API_TOKEN 默认 482733936f2e45eaba0cc5768e5541eb1>, uuid=<随机>
           返回: {id, hash, contentType(如 upload), ...}；同名重传报「文档已存在」
  2. 关联  POST .../webtriggers/webtrigger-associate-item-wiki
           {itemAssociateWiki:{spaceKey,contentType,hash,pageId,pageTitle,itemKey,isDeleted:false,versionId:null},
            tenant:"ENT_999999", sessionToken:<base64用户信息>, username}
  3. 查询  webtrigger-get-item-associate-wiki {itemKey, baseLineItemId:null, tenant, sessionToken, username}
  4. 取消  webtrigger-disassociate-item-wiki {objectId, sessionToken}
"""
import argparse
import base64
import json
import mimetypes
import sys
import uuid

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fde_common import make_request, load_auth_config  # noqa: E402

# open-api token 出处与再获取方法（2026-11-20 抓取自线上插件 bundle）：
#   文件: https://sti.chinamobile.com/fde-req/apps/static/plugin_zyd_item_associate_wiki/production/<版本号>/client-side/main/js/433.*.min.js
#   代码原文: apiToken: context?.env?.OPEN_API_TOKEN ?? "482733936f2e45eaba0cc5768e5541eb1"
#   该 JS 必须**在已登录的页面上下文里 fetch** 才拿得到（直接 curl 空响应）——
#   到需求页 (https://sti.chinamobile.com/fde/base/fde-req-web/item/<id>) 控制台执行:
#     fetch('/fde-req/apps/static/plugin_zyd_item_associate_wiki/production/4.40.6-alpha.6/client-side/main/js/433.eaee6c92ed16bbefe3a0.min.js').then(r=>r.text()).then(t=>console.log(t.match(/apiToken:[^,]+/)))
#   版本号变化时，从需求页加载的插件 chunk 网络请求里看当前版本目录，再 grep "apiToken:"。
API_TOKEN = "482733936f2e45eaba0cc5768e5541eb1"  # ponytail: 来自插件 bundle 的兜底字面量(env.OPEN_API_TOKEN ?? 此值)，实测当前可用但平台换配置即失效；可在 fde_auth.json 加 open_api_token 覆盖
CHUNK_SIZE = 5 * 1024 * 1024  # ponytail: 与插件一致的 5MB 分片，未实测服务端阈值
WEBTRIGGER_BASE = "/fde/moss/web/fde-req/apps/api/v1/ENT_999999/apps/plugin_zyd_item_associate_wiki/environments/production/webtriggers/"


def _session_token(auth=None):
    """构造 webtrigger 鉴权用的 sessionToken（用户信息 JSON 的 base64）。"""
    a = auth or load_auth_config()
    # username 必须是真实 SSO 账号(deputyAccountNumber)，employeeNo 在新版凭证中是哈希值，
    # 填入会报 1209 "无效的 Gitee token，用户不存在"(2026-11-20 实测修复，同 fde_common.get_req_session_token)
    sso_account = a.get("deputyAccountNumber") or a.get("username") or a.get("employeeNo", "")
    info = {
        "createTime": None, "email": a.get("email", ""), "employeeNo": a.get("employeeNo", ""),
        "enterpriseCode": a.get("enterpriseCode", ""), "enterpriseId": a.get("enterpriseId", ""),
        "enterpriseName": a.get("enterpriseName", ""), "euserId": a.get("euserId", ""),
        "euserType": 0, "loginStatus": 1, "name": a.get("name", ""), "staffCode": None,
        "userId": a.get("userId", ""), "deputyAccountNumber": sso_account,
        "username": sso_account,
    }
    return base64.b64encode(json.dumps(info, ensure_ascii=False).encode()).decode()


def _sso_account():
    """webtrigger 请求体用的 username：真实 SSO 账号（employeeNo 为哈希值不可用）。"""
    a = load_auth_config()
    return a.get("deputyAccountNumber") or a.get("username") or a.get("employeeNo", "")


def _upload_one_chunk(space_key, file_path, path, filename, upload_id=None, chunk_bytes=None,
                      total_chunks=1, chunk_index=0):
    """单次（或单分片）上传。返回响应 data dict。"""
    import ssl
    import urllib.request
    import urllib.error
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    a = load_auth_config()
    data = chunk_bytes if chunk_bytes is not None else open(file_path, "rb").read()
    b = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f'Content-Type: {mimetypes.guess_type(filename)[0] or "application/octet-stream"}\r\n\r\n').encode()
    body += data + f"\r\n--{b}\r\n".encode()
    body += f'Content-Disposition: form-data; name="path"\r\n\r\n{path}\r\n'.encode()
    if total_chunks > 1:
        body += (f'Content-Disposition: form-data; name="totalChunks"\r\n\r\n{total_chunks}\r\n').encode()
        body += (f'Content-Disposition: form-data; name="chunkIndex"\r\n\r\n{chunk_index}\r\n').encode()
    if upload_id:
        body += (f'Content-Disposition: form-data; name="uploadId"\r\n\r\n{upload_id}\r\n').encode()
    body += f"--{b}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={b}",
        "token": a.get("open_api_token", API_TOKEN), "uuid": uuid.uuid4().hex,
        "User-Agent": "Mozilla/5.0", "Cookie": a.get("cookie", ""),
    }
    headers.update(a.get("fde_http_header", {}))
    url = f"https://sti.chinamobile.com/fde-wiki/doc-open-api/CMCC/{space_key}/files/upload"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600, context=ctx) as resp:
            res = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        res = json.loads(e.read().decode())
    return res


def _resolve_dir_title(space_id, parent_page_id):
    """查目录页标题：上传 path 的目录段是按【标题】匹配的，传数字会被当成同名文件夹。"""
    r = make_request("POST", WEBTRIGGER_BASE + "page-tree-data",
                     data={"spaceId": space_id, "params": {"parent": None, "fillTitle": True}})
    for n in ((r.get("data") or {}).get("data") or {}).get("tree") or []:
        if n.get("id") == parent_page_id:
            return n.get("title")
    print(f"[x] 目录 id={parent_page_id} 不在该空间根目录，先用 dirs 命令确认")
    sys.exit(1)


def upload_file(space_key, space_id, file_path, parent_page_id):
    """上传文件到 space_key 的 parent_page_id 目录下，返回响应 data（含 id/hash/contentType）。"""
    import os
    filename = os.path.basename(file_path)
    dir_title = _resolve_dir_title(space_id, parent_page_id)
    path = f"/{dir_title}/{filename}"
    size = os.path.getsize(file_path)
    total = max(1, (size + CHUNK_SIZE - 1) // CHUNK_SIZE)
    upload_id, res = None, None
    with open(file_path, "rb") as f:
        for i in range(total):
            chunk = f.read(CHUNK_SIZE)
            res = _upload_one_chunk(space_key, file_path, path, filename,
                                    upload_id=upload_id, chunk_bytes=chunk,
                                    total_chunks=total, chunk_index=i)
            if res.get("code") != 0:
                print(f"[x] 上传失败: {res.get('message')}")
                sys.exit(1)
            upload_id = (res.get("data") or {}).get("uploadId")
    print(f"[✓] 上传成功: {filename} -> space {space_key} / {parent_page_id}")
    return res["data"]


def associate(space_key, page_id, title, content_type, hash_, item_key):
    """把知识库文件/页面关联到事项 itemKey，返回关联记录（含 objectId）。"""
    body = {
        "itemAssociateWiki": {
            "spaceKey": space_key, "contentType": content_type, "hash": hash_,
            "pageId": page_id, "pageTitle": title, "itemKey": item_key,
            "isDeleted": False, "versionId": None,
        },
        "tenant": "ENT_999999", "sessionToken": _session_token(),
        "username": _sso_account(),
    }
    r = make_request("POST", WEBTRIGGER_BASE + "webtrigger-associate-item-wiki", data=body)
    d = r.get("data") or {}
    if not d.get("objectId"):
        print(f"[x] 关联失败: {json.dumps(r, ensure_ascii=False)[:300]}")
        sys.exit(1)
    print(f"[✓] 已关联 {title} (pageId={page_id}) -> {item_key} (objectId={d['objectId']})")
    return d


def _resolve_space_id(space_key, space_id=None):
    """spaceKey → 数字 spaceId（page-tree-data 与上传目录解析都按数字 ID 查）。"""
    if space_id:
        return space_id
    wiki_headers = {"x-wiki-tenant-id": "CMCC", "x-auth-module": "PLATFORM"}
    res = make_request("GET", "/fde-wiki/api/wiki/spaces", custom_headers=wiki_headers)
    for s in ((res.get("data") or {}).get("items") or []):
        if s.get("key") == space_key:
            return s.get("id")
    print(f"[x] 找不到空间 {space_key} 的数字 spaceId，请先用 `manage_wiki.py spaces` 查询后加 --space-id")
    sys.exit(1)


def list_dirs(space_key, space_id):
    """列出空间下可选的目录（文件夹/页面节点），供上传前选择落点。"""
    sid = _resolve_space_id(space_key, space_id)
    r = make_request("POST", WEBTRIGGER_BASE + "page-tree-data",
                     data={"spaceId": sid, "params": {"parent": None, "fillTitle": True}})
    nodes = ((r.get("data") or {}).get("data") or {}).get("tree") or []
    if not nodes:
        print("（该空间未返回任何节点）")
        return []
    print(f"【空间 {space_key} (spaceId={sid}) 目录树】——从中选择上传目标目录（取 id 作 --parent-page-id）：")
    def walk(items, depth):
        for n in items:
            leaf = "📄" if n.get("isLeaf") else "📁"
            print(f"  {'  '*depth}{leaf} id={n.get('id')}  {n.get('title')}  [{n.get('contentType')}]")
            walk(n.get("children") or [], depth + 1)
    # 树可能平铺（无 children），按 path 缩进展示
    if any(n.get("children") for n in nodes):
        walk(nodes, 0)
    else:
        for n in sorted(nodes, key=lambda x: (x.get("path") or "", x.get("sort_key") or "")):
            d = max(0, len((n.get("path") or "").split("/")) - 2)
            leaf = "📄" if n.get("isLeaf") else "📁"
            print(f"  {'  '*d}{leaf} id={n.get('id')}  {n.get('title')}  [{n.get('contentType')}]")
    return nodes


def list_assoc(item_key):
    r = make_request("POST", WEBTRIGGER_BASE + "webtrigger-get-item-associate-wiki", data={
        "itemKey": item_key, "baseLineItemId": None, "tenant": "ENT_999999",
        "sessionToken": _session_token(), "username": _sso_account(),
    })
    items = r.get("data") or []
    print(f"【{item_key} 关联知识】(共 {len(items)} 条)")
    for it in items:
        print(f"  {it.get('objectId')} | {it.get('pageTitle')} | pageId={it.get('pageId')} | space={it.get('spaceKey')}")
    return items


def disassociate(object_id):
    r = make_request("POST", WEBTRIGGER_BASE + "webtrigger-disassociate-item-wiki", data={
        "objectId": object_id, "sessionToken": _session_token()})
    if r.get("success"):
        print(f"[✓] 已取消关联: {object_id}")
    else:
        print(f"[x] 取消失败: {json.dumps(r, ensure_ascii=False)[:300]}")


def main():
    p = argparse.ArgumentParser(description="事项关联知识（上传文件到知识库并关联需求）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("upload", help="上传文件到知识库并关联到事项")
    sp.add_argument("--space-key", required=True, help="知识库空间唯一标识，如 Lingjizhishi")
    sp.add_argument("--parent-page-id", type=int, help="目标目录页面 ID（path 形如 /<该ID>/）；不传则列出目录树供选择")
    sp.add_argument("--space-id", type=int, help="空间的数字 ID（仅 dirs 命令需要；manage_wiki.py spaces 可查）")
    sp.add_argument("--file", help="本地文件路径")
    sp.add_argument("--item-key", help="事项 key（如 G2026000S-33），传入则自动关联")

    sp = sub.add_parser("dirs", help="列出空间目录树，供选择上传落点")
    sp.add_argument("--space-key", required=True)
    sp.add_argument("--space-id", type=int)

    sp = sub.add_parser("list", help="查询事项已关联的知识")
    sp.add_argument("--item-key", required=True)

    sp = sub.add_parser("disassociate", help="取消关联")
    sp.add_argument("--object-id", required=True)

    args = p.parse_args()
    if args.cmd == "dirs":
        list_dirs(args.space_key, args.space_id)
    elif args.cmd == "upload":
        if not args.file:
            p.error("upload 需要 --file")
        if args.parent_page_id is None:
            # 不带目标目录时：列出目录树，让用户选择，而不是默认传到某个目录
            nodes = list_dirs(args.space_key, getattr(args, "space_id", None))
            # 未指定目录 = 必须问用户，不默认落任何目录
            try:
                choice = input("\n请输入上传目标目录的 id（见上方目录树）: ").strip()
            except EOFError:
                # 非交互环境（agent 调用）：停下来向用户展示目录树并要求明确指定
                print("\n[!] 未指定上传目录。请从上方目录树中选定目录后，"
                      "带 --parent-page-id <目录id> 重新执行。")
                sys.exit(2)
            if not choice.isdigit():
                print(f"[x] 目录 id 须为数字，收到: {choice}")
                sys.exit(2)
            args.parent_page_id = int(choice)
        sid = _resolve_space_id(args.space_key, getattr(args, "space_id", None))
        d = upload_file(args.space_key, sid, args.file, args.parent_page_id)
        if args.item_key:
            associate(args.space_key, d.get("pageId") or d.get("id"),
                      d.get("title") or args.file.rsplit("/", 1)[-1],
                      d.get("contentType") or "upload", d.get("hash"), args.item_key)
    elif args.cmd == "list":
        list_assoc(args.item_key)
    elif args.cmd == "disassociate":
        disassociate(args.object_id)


if __name__ == "__main__":
    main()
