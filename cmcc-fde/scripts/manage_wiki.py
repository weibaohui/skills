#!/usr/bin/env python3
"""
FDE 知识库 (Wiki) 深度管理脚本
基于平台知识库 (fde-wiki-web) 原生网关接口，全面支持：
- 知识库空间 (Spaces) 列表与检索
- 知识库文档目录树 (Tree) 查看
- 文档内容与结构化正文在线读取 (原生支持 ProseMirror 结构正文还原)
- 文档导出与下载 (支持 Word .docx, PDF, Markdown .md, HTML 及附件源文件直下)
- 本地文档上传与导入 (支持 Markdown/文本原生页面化导入，及 Office/PDF 附件式挂载)
- 在线创建知识库文档页面
- 批量删除知识库文档
"""

import argparse
import json
import os
import ssl
import sys
import uuid
import urllib.request
import urllib.error
from fde_common import make_request, load_auth_config

# 证书链含国内 CA（SHECA 等），macOS Python 默认 CA 包不含，优先用 certifi
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

try:
    import brotli
except ImportError:
    brotli = None

WIKI_TENANT = "CMCC"

def _get_wiki_headers():
    return {
        "x-wiki-tenant-id": WIKI_TENANT,
        "x-auth-module": "PLATFORM"
    }

def list_spaces():
    print("[*] 正在拉取知识库空间 (Spaces) 列表...")
    res = make_request("GET", "/fde-wiki/api/wiki/spaces", custom_headers=_get_wiki_headers())
    if res.get("error"):
        print(f"[x] 拉取空间失败: {res.get('message')}")
        sys.exit(1)

    items = res.get("data", {}).get("items", [])
    print(f"\n【知识库空间列表】(共 {len(items)} 个空间)")
    print("-" * 85)
    print(f"{'空间ID':<8} | {'空间唯一标识 (Key)':<22} | {'空间名称'}")
    print("-" * 85)
    for s in items:
        sid = s.get("id", "")
        key = s.get("key", "")
        name = s.get("name", "")
        print(f"{sid:<8} | {key:<22} | {name}")
    print("-" * 85)
    print("提示: 可使用 'tree --space-id <空间ID>' 查看空间内的文档目录。\n")

def list_tree(space_id: int, parent_id: int = None):
    url = f"/fde-wiki/api/wiki/spaces/{space_id}/tree"
    if parent_id is not None:
        url += f"?parent={parent_id}"
        print(f"[*] 正在拉取空间 ID={space_id} 中文件夹 [{parent_id}] 下的文档...")
    else:
        print(f"[*] 正在拉取空间 ID={space_id} 的文档目录树...")
    res = make_request("GET", url, custom_headers=_get_wiki_headers())
    if res.get("error"):
        print(f"[x] 拉取文档目录失败: {res.get('message')}")
        sys.exit(1)

    raw_data = res.get("data", [])
    if isinstance(raw_data, dict):
        data = raw_data.get("tree", [])
    elif isinstance(raw_data, list):
        data = raw_data
    else:
        data = []
    scope = f"文件夹 {parent_id}" if parent_id is not None else "全部"
    print(f"\n【知识库文档清单】(空间 ID={space_id}，范围: {scope}，共 {len(data)} 个节点)")
    print("-" * 85)
    print(f"{'文档ID':<8} | {'类型':<10} | {'创建者':<22} | {'文档标题'}")
    print("-" * 85)
    for d in data:
        did = d.get("id", "")
        ctype = d.get("contentType", "")
        creator = d.get("creatorName", "")
        title = d.get("title", "未命名文档")
        icon = "📁 " if ctype == "folder" else "📄 "
        print(f"{did:<8} | {ctype:<10} | {creator:<22} | {icon}{title}")
    print("-" * 85)
    print("提示: 可使用 'download --doc-id <文档ID>' 导出下载，或 'read --space-id <空间ID> --doc-id <文档ID>' 在线读取。\n")

def _extract_prosemirror_text(node):
    """递归提取 ProseMirror 文档中的纯文本段落"""
    if not isinstance(node, dict):
        return ""
    texts = []
    node_type = node.get("type")
    if node_type == "text":
        return node.get("text", "")
    elif node_type in ("heading", "paragraph"):
        child_text = "".join(_extract_prosemirror_text(c) for c in node.get("content", []))
        if node_type == "heading":
            level = node.get("attrs", {}).get("level", 1)
            return f"\n{'#' * level} {child_text}\n"
        return child_text + "\n"
    elif node_type == "bulletList":
        return "\n" + "".join(f"- {_extract_prosemirror_text(c).strip()}\n" for c in node.get("content", []))
    elif node_type == "orderedList":
        return "\n" + "".join(f"1. {_extract_prosemirror_text(c).strip()}\n" for c in node.get("content", []))
    elif node_type in ("codeBlock", "code_block"):
        lang = node.get("attrs", {}).get("language", "")
        child_text = "".join(_extract_prosemirror_text(c) for c in node.get("content", []))
        return f"\n```{lang}\n{child_text}\n```\n"
    
    for c in node.get("content", []):
        t = _extract_prosemirror_text(c)
        if t:
            texts.append(t)
    return "".join(texts)

def read_document(space_id: int, doc_id: int):
    print(f"[*] 正在读取空间 [{space_id}] 下的文档 [{doc_id}]...")
    res = make_request("GET", f"/fde-wiki/api/wiki/spaces/{space_id}/pages/{doc_id}", custom_headers=_get_wiki_headers())
    if res.get("error"):
        print(f"[x] 读取文档基础信息失败: {res.get('message')}")
        sys.exit(1)

    d = res.get("data", {})
    title = d.get("title", "")
    ctype = d.get("contentType", "")
    created_at = d.get("createdAt", "").replace("T", " ").split(".")[0]
    updated_at = d.get("updatedAt", "").replace("T", " ").split(".")[0]
    creator = d.get("creatorName", "")

    print("\n" + "=" * 70)
    print(f"【知识库文档详情】: {title}")
    print("=" * 70)
    print(f" 文档 ID:   {doc_id} (空间 ID: {space_id})")
    print(f" 文档类型: {ctype}")
    print(f" 创建人员: {creator} | 创建时间: {created_at}")
    print(f" 更新时间: {updated_at}")
    print("-" * 70)

    # 1. 尝试从 /pages/{doc_id}/content 提取结构化富文本
    c_res = make_request("GET", f"/fde-wiki/api/wiki/pages/{doc_id}/content", custom_headers=_get_wiki_headers())
    doc_node = c_res.get("data", {}).get("default")
    if doc_node and isinstance(doc_node, dict):
        parsed_text = _extract_prosemirror_text(doc_node).strip()
        if parsed_text:
            print("【文档正文内容】:")
            print(parsed_text)
            print("=" * 70 + "\n")
            return

    # 2. 检查是否有附件元数据
    comp_res = make_request("GET", f"/fde-wiki/api/wiki/spaces/{space_id}/pages/{doc_id}/component", custom_headers=_get_wiki_headers())
    content_raw = comp_res.get("data", {}).get("content", "")
    if content_raw:
        try:
            content_json = json.loads(content_raw)
            if isinstance(content_json, dict) and "fetchUrl" in content_json:
                print(f"[附件型文档] 静态源: {content_json.get('fetchUrl')} (文件名: {content_json.get('fileName')}, 大小: {content_json.get('size')} bytes)")
                print(f"提示: 可使用 'download --doc-id {doc_id}' 直接下载该附件源文件。")
                print("=" * 70 + "\n")
                return
        except Exception:
            pass

    # 3. 兜底获取 previewText
    prev = make_request("GET", f"/fde-wiki/api/wiki/spaces/{space_id}/pages/{doc_id}/previewText", custom_headers=_get_wiki_headers())
    text_data = prev.get("data")
    if text_data:
        print("【文档预览文字】:")
        print(text_data)
    else:
        print("[i] 当前文档暂无文字正文或为二进制附件，可使用 'download' 命令导出/下载。")
    print("=" * 70 + "\n")

def download_document(doc_id: int, exp_format: str = "word", output_path: str = None, space_id: int = None):
    exp_format = exp_format.lower()
    if exp_format not in ["word", "pdf", "markdown", "html"]:
        exp_format = "word"

    auth = load_auth_config()
    print(f"[*] 正在请求将知识库文档 ID={doc_id} 导出为 [{exp_format}] 格式...")

    # 1. 尝试直接查看是否为上传的源文件附件
    if space_id:
        p_res = make_request("GET", f"/fde-wiki/api/wiki/spaces/{space_id}/pages/{doc_id}/component", custom_headers=_get_wiki_headers())
        content_raw = p_res.get("data", {}).get("content", "")
        if content_raw and "fetchUrl" in content_raw:
            try:
                c_json = json.loads(content_raw)
                fetch_url = c_json.get("fetchUrl")
                if fetch_url:
                    static_url = f"https://sti.chinamobile.com/fde-wiki/wiki-static/{fetch_url}"
                    fname = output_path or c_json.get("fileName") or f"doc_{doc_id}.{c_json.get('ext', 'bin').lstrip('.')}"
                    print(f"[*] 检测到文档内嵌源文件，正在直接从静态存储加速下载: {c_json.get('fileName')}...")
                    req = urllib.request.Request(static_url, headers={
                        "User-Agent": "Mozilla/5.0",
                        "Cookie": auth.get("cookie", ""),
                        "Data-Auth-Appid": "FDE",
                        "Data-Auth-Domain": "portal",
                        "Data-Auth-Enterpriseid": auth.get("enterpriseId", "ENT_999999"),
                        "x-wiki-tenant-id": WIKI_TENANT,
                        "x-auth-module": "PLATFORM"
                    })
                    with urllib.request.urlopen(req, context=_SSL_CTX) as resp:
                        with open(fname, "wb") as f:
                            f.write(resp.read())
                    print(f"\n[✓] 源文件下载成功！已保存至: {os.path.abspath(fname)}\n")
                    return
            except Exception:
                pass

    # 2. 调用转换导出服务
    export_url = f"https://sti.chinamobile.com/fde-wiki/api/wiki-convert/pages/{doc_id}/doc_export?tenant={WIKI_TENANT}&type={exp_format}"
    req = urllib.request.Request(export_url, headers={
        "User-Agent": "Mozilla/5.0",
        "Cookie": auth.get("cookie", ""),
        "Data-Auth-Appid": "FDE",
        "Data-Auth-Domain": "portal",
        "Data-Auth-Enterpriseid": auth.get("enterpriseId", "ENT_999999"),
        "x-wiki-tenant-id": WIKI_TENANT,
        "x-auth-module": "PLATFORM"
    })

    ext_map = {"word": "docx", "pdf": "pdf", "markdown": "md", "html": "html"}
    ext = ext_map.get(exp_format, "docx")
    save_file = output_path or f"wiki_doc_{doc_id}.{ext}"

    try:
        with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
            raw = resp.read()
            # 校验并解压 brotli / gzip
            try:
                if brotli:
                    data = brotli.decompress(raw)
                else:
                    data = raw
            except Exception:
                data = raw

            # 校验是否返回错误 json
            if data.startswith(b'{"code":'):
                try:
                    err = json.loads(data.decode("utf-8"))
                    print(f"[x] 导出失败: {err.get('message', '未知错误')}")
                    return
                except Exception:
                    pass

            with open(save_file, "wb") as f:
                f.write(data)

            print("\n" + "=" * 60)
            print(f"【✓】知识库文档导出并下载成功！")
            print("=" * 60)
            print(f" 文档 ID:   {doc_id}")
            print(f" 导出格式: {exp_format.upper()} (.{ext})")
            print(f" 文件大小: {len(data)} 字节")
            print(f" 本地路径: {os.path.abspath(save_file)}")
            print("=" * 60 + "\n")
    except urllib.error.HTTPError as e:
        print(f"[x] HTTP {e.code} 下载失败: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"[x] 下载异常: {e}")

def create_document(space_id: int, title: str, content_text: str = "", parent_id: int = 0):
    print(f"[*] 正在空间 ID={space_id} 下在线创建文档: 《{title}》...")
    # 构造标准 ProseMirror 节点
    paragraphs = []
    lines = content_text.split("\n") if content_text else [""]
    for line in lines:
        if line.startswith("# "):
            paragraphs.append({
                "type": "heading",
                "attrs": {"level": 1},
                "content": [{"type": "text", "text": line[2:]}]
            })
        elif line.startswith("## "):
            paragraphs.append({
                "type": "heading",
                "attrs": {"level": 2},
                "content": [{"type": "text", "text": line[3:]}]
            })
        elif line.startswith("### "):
            paragraphs.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": line[4:]}]
            })
        elif line.strip():
            paragraphs.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": line}]
            })
        else:
            paragraphs.append({"type": "paragraph"})

    pm_content = {
        "default": {
            "type": "doc",
            "content": paragraphs
        }
    }

    payload = {
        "contentType": "text",
        "title": title,
        "content": json.dumps(pm_content, ensure_ascii=False),
        "description": "",
        "locale": "zh",
        "isPrivate": False,
        "isPublished": False,
        "spaceId": space_id,
        "publishEndDate": "",
        "publishStartDate": "",
        "scriptCss": "",
        "scriptJs": "",
        "tags": []
    }
    if parent_id and parent_id > 0:
        payload["parent"] = parent_id

    res = make_request("POST", f"/fde-wiki/api/wiki/spaces/{space_id}/pages", data=payload, custom_headers=_get_wiki_headers())
    if res.get("error") or res.get("code") != 0:
        print(f"[x] 创建文档失败: {res}")
        sys.exit(1)

    page = res.get("data", {})
    pid = page.get("id")
    print("\n" + "=" * 60)
    print("【✓】知识库文档在线创建成功！")
    print("=" * 60)
    print(f" 新建文档 ID: {pid}")
    print(f" 文档标题:   {title}")
    print(f" 空间 ID:     {space_id}")
    print(f" 访问路径:   {page.get('path')}")
    print("=" * 60 + "\n")
    return pid

def upload_import_file(space_id: int, file_path: str, title: str = None, parent_id: int = 0):
    if not os.path.exists(file_path):
        print(f"[x] 本地文件不存在: {file_path}")
        sys.exit(1)

    fname = os.path.basename(file_path)
    ext = os.path.splitext(fname)[1].lower()
    doc_title = title or os.path.splitext(fname)[0]

    print(f"[*] 准备将本地文件 [{fname}] 导入到知识库空间 [{space_id}]...")

    # 如果是 Markdown 或普通文本文件，直接解析并作为在线知识库原生页面导入
    if ext in [".md", ".markdown", ".txt"]:
        print(f"[*] 检测到文本/Markdown 文件，正在解析为知识库原生结构化文档页面...")
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return create_document(space_id, doc_title, content, parent_id)

    # 其它文件（如 docx, pdf 等）使用平台的通用 doc_import 上传转换通道
    auth = load_auth_config()
    print(f"[*] 正在调用平台转换导入接口上传 [{fname}]...")
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    with open(file_path, "rb") as f:
        file_bytes = f.read()

    fields = {
        "tenant": WIKI_TENANT,
        "spaceId": str(space_id),
        "type": "word" if ext in [".doc", ".docx"] else "upload",
        "depth": "1"
    }

    body = b""
    for k, v in fields.items():
        body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8")

    body += (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{fname}"\r\n'
        f'Content-Type: application/octet-stream\r\n\r\n'
    ).encode("utf-8") + file_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    import_url = f"https://sti.chinamobile.com/fde-wiki/api/wiki-convert/pages/{parent_id}/doc_import"
    req = urllib.request.Request(
        import_url,
        data=body,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Cookie": auth.get("cookie", ""),
            "Data-Auth-Appid": "FDE",
            "Data-Auth-Domain": "portal",
            "Data-Auth-Enterpriseid": auth.get("enterpriseId", "ENT_999999"),
            "x-wiki-tenant-id": WIKI_TENANT,
            "x-auth-module": "PLATFORM",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60, context=_SSL_CTX) as resp:
            text = resp.read().decode("utf-8")
            res = json.loads(text)
            if res.get("code") == 0:
                print("\n" + "=" * 60)
                print("【✓】知识库文档上传导入成功！")
                print("=" * 60)
                print(f" 文件名:   {fname}")
                print(f" 文件大小: {len(file_bytes)} 字节")
                print(f" 空间 ID:  {space_id}")
                print(f" 状态反馈: {res.get('message', '导入成功')}")
                print("=" * 60 + "\n")
            else:
                print(f"[x] 上传失败: {res}")
    except urllib.error.HTTPError as e:
        print(f"[x] HTTP {e.code} 上传失败: {e.read().decode('utf-8', errors='ignore')}")
    except Exception as e:
        print(f"[x] 上传异常: {e}")

def delete_documents(space_id: int, doc_ids: list):
    print(f"[*] 正在从空间 ID={space_id} 批量删除文档: {doc_ids}...")
    res = make_request("DELETE", f"/fde-wiki/api/wiki/spaces/{space_id}/pages/batch", data={"pageIds": doc_ids}, custom_headers=_get_wiki_headers())
    if res.get("code") != 0:
        print(f"[x] 删除文档失败: {res}")
        return
    # 接口返回逐项结果，外层 code=0 不代表每项都删掉了（如 6010 无权限）
    ok, failed = [], []
    for item in res.get("data") or []:
        (ok if item.get("success") else failed).append((item.get("pageId"), item.get("message") or ""))
    if ok:
        print(f"[✓] 成功删除 {len(ok)} 个: {[p for p, _ in ok]}")
    if failed:
        print(f"[x] 删除失败 {len(failed)} 个: " + ", ".join(f"{p}({m})" for p, m in failed))

def main():
    parser = argparse.ArgumentParser(description="FDE 知识库 (Wiki) 深度管理脚本")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. spaces
    subparsers.add_parser("spaces", help="列出所有可访问的知识库空间")

    # 2. tree
    p_tree = subparsers.add_parser("tree", help="查看指定空间的文档目录树")
    p_tree.add_argument("--space-id", "-s", type=int, required=True, help="知识库空间 ID (如 88, 87)")
    p_tree.add_argument("--parent", type=int, default=None, help="可选：父文件夹 ID，展开该文件夹下的子文档")

    # 3. read
    p_read = subparsers.add_parser("read", help="在线读取文档详情与正文内容")
    p_read.add_argument("--space-id", "-s", type=int, required=True, help="知识库空间 ID")
    p_read.add_argument("--doc-id", "-d", type=int, required=True, help="文档 ID")

    # 4. download
    p_down = subparsers.add_parser("download", help="导出并下载文档")
    p_down.add_argument("--doc-id", "-d", type=int, required=True, help="文档 ID")
    p_down.add_argument("--format", "-f", choices=["word", "pdf", "markdown", "html"], default="word", help="导出格式: word (默认), pdf, markdown, html")
    p_down.add_argument("--output", "-o", help="保存的本地文件路径")
    p_down.add_argument("--space-id", "-s", type=int, help="空间 ID (用于附件型文档加速直链下载)")

    # 5. create
    p_create = subparsers.add_parser("create", help="在指定空间在线创建文档页面")
    p_create.add_argument("--space-id", "-s", type=int, required=True, help="知识库空间 ID")
    p_create.add_argument("--title", "-t", required=True, help="文档标题")
    p_create.add_argument("--content", "-c", default="", help="文档初始文本内容")
    p_create.add_argument("--parent-id", "-p", type=int, default=0, help="父文档 ID (可选)")

    # 6. upload
    p_up = subparsers.add_parser("upload", help="将本地文档上传导入至知识库空间")
    p_up.add_argument("--space-id", "-s", type=int, required=True, help="知识库空间 ID")
    p_up.add_argument("--file", "-f", required=True, help="本地文件路径 (如 .md, .docx, .txt)")
    p_up.add_argument("--title", "-t", help="指定文档标题 (可选，默认使用文件名)")
    p_up.add_argument("--parent-id", "-p", type=int, default=0, help="父文档 ID (可选)")

    # 7. delete
    p_del = subparsers.add_parser("delete", help="批量删除知识库文档")
    p_del.add_argument("--space-id", "-s", type=int, required=True, help="知识库空间 ID")
    p_del.add_argument("--doc-ids", "-d", required=True, help="待删除的文档 ID 列表，逗号分隔 (如: 1750,1751)")

    args = parser.parse_args()

    if args.command == "spaces":
        list_spaces()
    elif args.command == "tree":
        list_tree(args.space_id, args.parent)
    elif args.command == "read":
        read_document(args.space_id, args.doc_id)
    elif args.command == "download":
        download_document(args.doc_id, args.format, args.output, args.space_id)
    elif args.command == "create":
        create_document(args.space_id, args.title, args.content, args.parent_id)
    elif args.command == "upload":
        upload_import_file(args.space_id, args.file, args.title, args.parent_id)
    elif args.command == "delete":
        ids = [int(i.strip()) for i in args.doc_ids.split(",") if i.strip()]
        delete_documents(args.space_id, ids)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
