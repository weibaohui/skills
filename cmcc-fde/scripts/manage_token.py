#!/usr/bin/env python3
"""
FDE 代码仓库私人令牌 (Private Token) 管理脚本
仅需复用已保存的 Cookie 登录信息，支持创建永久 (permanent) 令牌、列表查看与删除。

用法:
  python3 manage_token.py list
  python3 manage_token.py create [--name <令牌名>] [--expires <到期日>]
  python3 manage_token.py delete --id <令牌ID>
"""

import argparse
import json
import sys
from fde_common import make_request, load_auth_config, save_auth_config

def list_tokens():
    auth = load_auth_config()
    enterprise_id = auth.get("enterpriseId", "ENT_999999")
    print(f"[*] 正在拉取企业 [{enterprise_id}] 下的个人令牌列表...")

    res = make_request(
        "GET",
        f"/fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/private_tokens",
        params={"enterprise_global": "true"},
        custom_headers={"x-auth-module": "PLATFORM"}
    )

    if res.get("error"):
        print(f"[x] 拉取失败: {res.get('message')}")
        sys.exit(1)

    tokens = res.get("data", [])
    print(f"\n【个人私人令牌列表】(共 {len(tokens)} 个)")
    print("-" * 75)
    print(f"{'ID':<6} | {'名称':<22} | {'过期状态':<15} | {'创建时间'}")
    print("-" * 75)
    for t in tokens:
        exp = t.get("expire_time", "")
        if exp == "permanent":
            exp_display = "永久有效 (permanent)"
        else:
            exp_display = exp.split("T")[0] if "T" in exp else exp
        
        created = t.get("created_at", "").split(".")[0].replace("T", " ")
        print(f"{t.get('id'):<6} | {t.get('name', ''):<22} | {exp_display:<15} | {created}")
    print("-" * 75)

    current_saved = auth.get("private_token")
    if current_saved:
        print(f"[i] 当前本地持久化使用的 Token: {current_saved}\n")

def create_token(name: str, expires_at: str, scopes_str: str):
    auth = load_auth_config()
    enterprise_id = auth.get("enterpriseId", "ENT_999999")
    
    # 解析 scopes
    # 默认包含全部能力: 1(clone), 2(push), 4(api), 5(api_ro), 6(users), 7(projects), 8(groups)
    try:
        scopes = [int(s.strip()) for s in scopes_str.split(",") if s.strip()]
    except Exception:
        scopes = [1, 2, 4, 5, 6, 7, 8]

    print(f"[*] 正在创建令牌: {name} (请求到期日: {expires_at})...")
    payload = {
        "name": name,
        "expires_at": expires_at,
        "scopes": scopes
    }

    res = make_request(
        "POST",
        f"/fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/private_tokens",
        params={"enterprise_global": "true"},
        data=payload,
        custom_headers={"x-auth-module": "PLATFORM"}
    )

    if res.get("error") or res.get("code") == 0:
        print(f"[x] 创建失败: {res}")
        sys.exit(1)

    token_val = res.get("token")
    token_id = res.get("id")
    exp_status = res.get("expire_time")
    
    print("\n" + "=" * 60)
    print("【✓】代码仓库全功能令牌创建成功！")
    print("=" * 60)
    print(f" 令牌 ID: {token_id}")
    print(f" 令牌名称: {name}")
    print(f" 有效期: {exp_status} ({'永久有效' if exp_status == 'permanent' else exp_status})")
    print(f" 权限范围: {len(scopes)} 项核心操作权限 (含 Git 推拉与 API 全权限)")
    print("-" * 60)
    print(f">>> Token 密匙: {token_val} <<<")
    print("=" * 60)

    # 自动保存到持久化配置
    save_auth_config({"private_token": token_val})
    print("[✓] 已自动更新至本地共享鉴权配置文件 (后续脚本可直接调用 Git 仓库)\n")

def delete_token(token_id: int):
    auth = load_auth_config()
    enterprise_id = auth.get("enterpriseId", "ENT_999999")
    print(f"[*] 正在删除令牌 ID={token_id}...")

    res = make_request(
        "DELETE",
        f"/fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/private_tokens/{token_id}",
        params={"enterprise_global": "true"},
        custom_headers={"x-auth-module": "PLATFORM"}
    )

    if res.get("error") or res.get("code") != 0:
        print(f"[x] 删除失败: {res}")
        sys.exit(1)

    print(f"[✓] 令牌 ID={token_id} 已成功删除！\n")

def main():
    parser = argparse.ArgumentParser(description="FDE 代码仓库私人令牌管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # list
    subparsers.add_parser("list", help="查看所有私人令牌列表")

    # create
    create_parser = subparsers.add_parser("create", help="新建全功能私人令牌")
    create_parser.add_argument("--name", type=str, default="AI-Permanent-Token", help="令牌名称")
    create_parser.add_argument("--expires", type=str, default="2046-12-31", help="到期日期 (默认 2046-12-31 触发系统永久有效 permanent)")
    create_parser.add_argument("--scopes", type=str, default="1,2,4,5,6,7,8", help="权限项逗号分隔 (默认全部)")

    # delete
    del_parser = subparsers.add_parser("delete", help="删除指定 ID 的私人令牌")
    del_parser.add_argument("--id", type=int, required=True, help="要删除的令牌 ID")

    args = parser.parse_args()

    if args.command == "list":
        list_tokens()
    elif args.command == "create":
        create_token(args.name, args.expires, args.scopes)
    elif args.command == "delete":
        delete_token(args.id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
