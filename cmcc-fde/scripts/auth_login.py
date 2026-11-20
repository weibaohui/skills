#!/usr/bin/env python3
"""
FDE 登录与鉴权会话初始化脚本
平台登录页面: https://sti.chinamobile.com/fde/micrologin/#/login

使用提供的 Cookie (MOSS_SESSION) 验证连通性，自动解析企业、租户及用户身份，并持久化到本地与全局配置文件。

用法:
  python3 auth_login.py --cookie "MOSS_SESSION=...; ..."
  python3 auth_login.py --file cookie.txt
  python3 auth_login.py --check (检查当前存储的登录状态)
"""

import argparse
import json
import sys
from fde_common import make_request, save_auth_config, load_auth_config, get_request_id

def verify_and_save(cookie_str: str):
    print("[*] 正在验证 Cookie 会话有效性并拉取用户信息...")
    
    # 临时覆盖内存配置发起校验
    custom_headers = {"Cookie": cookie_str}
    
    # 1. 查询当前用户及企业列表
    user_resp = make_request(
        "POST",
        "/fde/moss/web/manage/v1/self/list-euser",
        data={"head": {"requestId": get_request_id()}, "data": {}},
        custom_headers=custom_headers
    )

    if user_resp.get("error") or user_resp.get("head", {}).get("respStatus") != "00":
        print(f"[x] 鉴权失败！接口返回: {user_resp}")
        print("[!] 请先在浏览器中打开 FDE 平台登录页面登录：")
        print("    https://sti.chinamobile.com/fde/micrologin/#/login")
        print("    登录成功后，按 F12 打开网络面板复制 Cookie (含 MOSS_SESSION) 并重新执行此脚本。")
        sys.exit(1)

    user_list = user_resp.get("data", [])
    if not user_list:
        print("[x] 未获取到有效企业用户列表！")
        sys.exit(1)

    user_info = user_list[0]
    enterprise_id = user_info.get("enterpriseId", "ENT_999999")
    enterprise_name = user_info.get("enterpriseName", "")
    user_id = user_info.get("userId", "")
    euser_id = user_info.get("euserId", "")
    login_status = user_info.get("loginStatus", 1)

    # 2. 查询租户信息
    tenant_resp = make_request(
        "GET",
        "/fde/moss/web/desktop/v1/api/v1/moss/tenant/list",
        params={"type": 1},
        custom_headers=custom_headers
    )
    tenants = tenant_resp.get("data", [])
    tenant_name = tenants[0].get("tenantName", "") if tenants else "默认租户"

    auth_payload = {
        "cookie": cookie_str,
        "enterpriseId": enterprise_id,
        "enterpriseName": enterprise_name,
        "userId": user_id,
        "euserId": euser_id,
        "tenantName": tenant_name,
        "loginStatus": login_status
    }

    # 持久化存储
    save_auth_config(auth_payload)

    print("\n" + "=" * 55)
    print("【✓】FDE 登录会话验证成功！已完成身份鉴权持久化。")
    print("=" * 55)
    print(f" 所属企业: {enterprise_name} ({enterprise_id})")
    print(f" 租户名称: {tenant_name}")
    print(f" 用户 ID: {user_id}")
    print(f" eUser ID: {euser_id}")
    print(f" 会话状态: 正常有效 (LoginStatus={login_status})")
    # 展示 MOSS-TOKEN 采集状态（若存在）
    try:
        from fde_common import load_auth_config as _load
        _saved = _load()
        _moss = _saved.get("moss_token", "")
        if _moss:
            print(f" MOSS-TOKEN: 已采集 ({_moss[:12]}...，{len(_moss)} 字符)")
    except Exception:
        pass
    print("=" * 55)
    print("提示: 后续执行技能脚本 (manage_token.py, manage_assets.py 等) 将自动复用此凭证。\n")

def check_current_status():
    auth = load_auth_config()
    if not auth.get("cookie"):
        print("[!] 当前尚未存储任何登录凭据！")
        print("    1. 请先在浏览器中访问 FDE 平台登录页完成登录：")
        print("       https://sti.chinamobile.com/fde/micrologin/#/login")
        print("    2. 获取 Cookie 后执行：python3 auth_login.py --cookie \"MOSS_SESSION=...\"")
        sys.exit(1)
    
    print("[*] 正在检查当前存储凭据的有效性...")
    verify_and_save(auth["cookie"])

def main():
    parser = argparse.ArgumentParser(description="FDE 登录与鉴权管理工具")
    parser.add_argument("--cookie", type=str, help="完整的浏览器 Cookie 字符串 (包含 MOSS_SESSION)")
    parser.add_argument("--file", type=str, help="包含 Cookie 字符串的本地文本文件路径")
    parser.add_argument("--check", action="store_true", help="校验已存储的会话凭据状态")

    args = parser.parse_args()

    if args.check:
        check_current_status()
        return

    cookie_val = ""
    if args.cookie:
        cookie_val = args.cookie.strip()
    elif args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            cookie_val = f.read().strip()
    else:
        # 尝试检查已有凭据
        existing = load_auth_config()
        if existing.get("cookie"):
            print("[*] 检测到已存在存储的凭据，正在验证...")
            verify_and_save(existing["cookie"])
            return
        else:
            parser.print_help()
            sys.exit(1)

    verify_and_save(cookie_val)

if __name__ == "__main__":
    main()
