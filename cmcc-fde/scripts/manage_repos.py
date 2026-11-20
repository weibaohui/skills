#!/usr/bin/env python3
"""
FDE 代码仓库深度管理脚本
基于企业代码子系统原生网关接口，全面支持：
- 仓库列表检索与元数据查询
- 分支清单与类型查看 (master, tags, feature branches)
- 文件目录树在线遍历 (无需 Git clone 即可在线浏览)
- 源码文件在线读取 (在线提取文件原始内容)
- 合并请求 (Pull Requests) 列表与状态追踪
- 仓库成员与权限列表查询
- Git HTTP 免密克隆命令生成
"""

import argparse
import json
import sys
from fde_common import make_request, load_auth_config

def resolve_repo_full_path(identifier: str) -> str:
    """根据仓库 ID 或 full_path 解析出标准 full_path"""
    if "/" in identifier:
        return identifier
    
    # 尝试作为数字 ID 查找
    auth = load_auth_config()
    enterprise_id = auth.get("enterpriseId", "ENT_999999")
    res = make_request(
        "GET",
        f"/fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/projects",
        params={"enterprise_global": "true", "per_page": 100},
        custom_headers={"x-auth-module": "PLATFORM"}
    )
    repos = res.get("data", [])
    for r in repos:
        if str(r.get("id")) == str(identifier):
            return r.get("full_path")
    return identifier

def list_repositories(page: int = 1, per_page: int = 20, search: str = ""):
    auth = load_auth_config()
    enterprise_id = auth.get("enterpriseId", "ENT_999999")
    print(f"[*] 正在拉取企业 [{enterprise_id}] 下的代码仓库列表...")

    params = {
        "enterprise_global": "true",
        "page": page,
        "per_page": per_page
    }
    if search:
        params["search"] = search

    res = make_request(
        "GET",
        f"/fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/projects",
        params=params,
        custom_headers={"x-auth-module": "PLATFORM"}
    )

    if res.get("error"):
        print(f"[x] 拉取代码仓库失败: {res.get('message')}")
        sys.exit(1)

    repos = res.get("data", [])
    print(f"\n【代码仓库清单】(第 {page} 页，当前展示 {len(repos)} 个)")
    print("-" * 88)
    print(f"{'ID':<6} | {'仓库名称':<18} | {'命名空间/代码组':<22} | {'完整路径'}")
    print("-" * 88)
    for r in repos:
        name = r.get("name", "")
        ns = r.get("namespace_name", "")
        full_path = r.get("full_path", "")
        print(f"{r.get('id'):<6} | {name:<18} | {ns:<22} | {full_path}")
    print("-" * 88)

    token = auth.get("private_token", "")
    if token:
        print(f"[i] 已加载可用 Private Token: {token[:8]}*** (可直接用于 Git 克隆与推送鉴权)\n")

def list_branches(target: str):
    full_path = resolve_repo_full_path(target)
    print(f"[*] 正在查询仓库 [{full_path}] 的分支列表...")
    base = f"/fde/moss/web/fde-code/api/code/api/{full_path}/-"

    # 1. 尝试获取完整分支信息
    res = make_request("GET", f"{base}/branches", params={"enterprise_global": "true"}, custom_headers={"x-auth-module": "PLATFORM"})
    
    branch_list = []
    if isinstance(res.get("data"), dict) and "list" in res["data"]:
        branch_list = res["data"]["list"]
    else:
        # 回退到 names 接口
        names_res = make_request("GET", f"{base}/branches/names", params={"enterprise_global": "true"}, custom_headers={"x-auth-module": "PLATFORM"})
        names = names_res.get("data", {}).get("branch", [])
        branch_list = [{"name": n, "branch_type_human_name": "常规分支"} for n in names]

    print(f"\n【分支列表】(共 {len(branch_list)} 个分支)")
    print("-" * 65)
    print(f"{'分支名称':<25} | {'类型':<15} | {'最新提交 Commit'}")
    print("-" * 65)
    for b in branch_list:
        bname = b.get("name", "")
        btype = b.get("branch_type_human_name", "常规分支")
        commit_id = b.get("commit", {}).get("short_id") if isinstance(b.get("commit"), dict) else "-"
        print(f"{bname:<25} | {btype:<15} | {commit_id}")
    print("-" * 65 + "\n")

def show_tree(target: str, ref: str = "master"):
    full_path = resolve_repo_full_path(target)
    print(f"[*] 正在获取仓库 [{full_path}] 分支 [{ref}] 的文件目录树...")
    base = f"/fde/moss/web/fde-code/api/code/api/{full_path}/-"

    res = make_request("GET", f"{base}/{ref}/trees", params={"enterprise_global": "true"}, custom_headers={"x-auth-module": "PLATFORM"})
    if res.get("error"):
        print(f"[x] 获取目录树失败: {res.get('message')}")
        sys.exit(1)

    tree_data = res.get("tree_data", {})
    files = tree_data.get("files", [])
    folders = tree_data.get("folders", [])

    print(f"\n【文件目录清单】(分支: {ref}，文件数: {len(files)}，目录数: {len(folders)})")
    print("-" * 70)
    for folder in folders:
        print(f" 📁 {folder.get('name')}/")
    for file in files:
        print(f" 📄 {file.get('name')}")
    print("-" * 70)
    print("提示: 可使用 'read --path <仓库> --file <文件名>' 直接查看文件源码。\n")

def read_file(target: str, file_path: str, ref: str = "master"):
    full_path = resolve_repo_full_path(target)
    print(f"[*] 正在读取仓库 [{full_path}] 分支 [{ref}] 下的文件 [{file_path}]...")
    base = f"/fde/moss/web/fde-code/api/code/api/{full_path}/-"

    res = make_request(
        "GET",
        f"{base}/{ref}/blobs",
        params={"enterprise_global": "true", "path": file_path},
        custom_headers={"x-auth-module": "PLATFORM"}
    )

    if res.get("error"):
        print(f"[x] 读取文件失败: {res.get('message')}")
        sys.exit(1)

    raw_content = res.get("raw_content", "")
    print("\n" + "=" * 70)
    print(f"【文件内容】: {file_path} (Ref: {ref})")
    print("=" * 70)
    print(raw_content)
    print("=" * 70 + "\n")

def list_pull_requests(target: str):
    full_path = resolve_repo_full_path(target)
    print(f"[*] 正在拉取仓库 [{full_path}] 的合并请求 (Pull Requests)...")
    base = f"/fde/moss/web/fde-code/api/code/api/{full_path}/-"

    res = make_request("GET", f"{base}/pull_requests", params={"enterprise_global": "true"}, custom_headers={"x-auth-module": "PLATFORM"})
    if res.get("error"):
        print(f"[x] 获取 PR 列表失败: {res.get('message')}")
        sys.exit(1)

    pr_list = res.get("data", {}).get("list", [])
    print(f"\n【合并请求 (PR) 列表】(共 {len(pr_list)} 个)")
    print("-" * 80)
    print(f"{'IID':<6} | {'状态':<10} | {'评审状态':<10} | {'标题':<25} | {'创建时间'}")
    print("-" * 80)
    for pr in pr_list:
        iid = pr.get("iid", pr.get("id"))
        state = pr.get("state", "")
        review = pr.get("review_state", "")
        title = pr.get("title", "")
        created = pr.get("created_at", "").split(".")[0].replace("T", " ")
        print(f"#{iid:<5} | {state:<10} | {review:<10} | {title:<25} | {created}")
    print("-" * 80 + "\n")

def list_members(target: str):
    full_path = resolve_repo_full_path(target)
    print(f"[*] 正在查询仓库 [{full_path}] 的成员与角色...")
    base = f"/fde/moss/web/fde-code/api/code/api/{full_path}/-"

    res = make_request("GET", f"{base}/members", params={"enterprise_global": "true"}, custom_headers={"x-auth-module": "PLATFORM"})
    if res.get("error"):
        print(f"[x] 获取成员失败: {res.get('message')}")
        sys.exit(1)

    members = res.get("data", [])
    print(f"\n【仓库协作成员清单】(共 {len(members)} 人)")
    print("-" * 75)
    print(f"{'姓名':<12} | {'账号/用户名':<24} | {'角色':<8} | {'权限级别'}")
    print("-" * 75)
    for m in members:
        name = m.get("member_name", "")
        uname = m.get("member_username", "")
        role = m.get("role_name", "")
        perm = m.get("permission", "")
        creator_tag = " (创建人)" if m.get("is_creator") else ""
        print(f"{name + creator_tag:<12} | {uname:<24} | {role:<8} | 级别 {perm}")
    print("-" * 75 + "\n")

def get_clone_info(target: str):
    full_path = resolve_repo_full_path(target)
    auth = load_auth_config()
    token = auth.get("private_token", "")

    http_url = f"https://sti.chinamobile.com/fde-code-web/{full_path}.git"
    auth_clone_cmd = f"git clone https://oauth2:{token}@{http_url.replace('https://', '')}" if token else f"git clone {http_url}"

    print("\n" + "=" * 65)
    print(f"【代码仓库克隆指南】: {full_path}")
    print("=" * 65)
    print("标准 HTTP 克隆地址:")
    print(f"  {http_url}")
    print("\n使用当前已配置 Token 一键免密克隆命令:")
    print(f"  {auth_clone_cmd}")
    print("=" * 65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="FDE 代码仓库深度管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list
    list_p = subparsers.add_parser("list", help="查看代码仓库列表")
    list_p.add_argument("--page", type=int, default=1, help="页码")
    list_p.add_argument("--size", type=int, default=20, help="每页数量")
    list_p.add_argument("--search", type=str, default="", help="搜索仓库关键词")

    # branches
    branch_p = subparsers.add_parser("branches", help="查看指定仓库的分支列表")
    branch_p.add_argument("--path", type=str, required=True, help="仓库完整路径或数字 ID (如 64)")

    # tree
    tree_p = subparsers.add_parser("tree", help="查看指定分支的文件目录树")
    tree_p.add_argument("--path", type=str, required=True, help="仓库完整路径或数字 ID")
    tree_p.add_argument("--ref", type=str, default="master", help="分支或标签名 (默认 master)")

    # read
    read_p = subparsers.add_parser("read", help="在线读取文件内容")
    read_p.add_argument("--path", type=str, required=True, help="仓库完整路径或数字 ID")
    read_p.add_argument("--file", type=str, required=True, help="文件相对路径 (如 README.md)")
    read_p.add_argument("--ref", type=str, default="master", help="分支或标签名 (默认 master)")

    # prs
    pr_p = subparsers.add_parser("prs", help="查看仓库合并请求 (Pull Requests)")
    pr_p.add_argument("--path", type=str, required=True, help="仓库完整路径或数字 ID")

    # members
    mem_p = subparsers.add_parser("members", help="查看仓库成员与角色")
    mem_p.add_argument("--path", type=str, required=True, help="仓库完整路径或数字 ID")

    # clone-info
    info_p = subparsers.add_parser("clone-info", help="查看仓库免密克隆命令")
    info_p.add_argument("--path", type=str, required=True, help="仓库完整路径或数字 ID")

    args = parser.parse_args()

    if args.command == "list":
        list_repositories(args.page, args.size, args.search)
    elif args.command == "branches":
        list_branches(args.path)
    elif args.command == "tree":
        show_tree(args.path, args.ref)
    elif args.command == "read":
        read_file(args.path, args.file, args.ref)
    elif args.command == "prs":
        list_pull_requests(args.path)
    elif args.command == "members":
        list_members(args.path)
    elif args.command == "clone-info":
        get_clone_info(args.path)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
