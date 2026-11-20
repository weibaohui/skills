#!/usr/bin/env python3
"""
FDE 研发空间管理脚本 (manage_spaces.py)
用于检索当前用户所属的研发空间，查看空间 ID 与编码，并支持多空间交互式选择与默认空间切换。

用法示例:
  # 列出当前用户所属的全部研发空间 (包含 spaceId, spaceCode, 名称, 角色)
  python3 manage_spaces.py list

  # 交互式选择要操作的研发空间 (输入序号即可切换并保存为默认空间)
  python3 manage_spaces.py select

  # 命令行直接设置默认空间 (通过空间编码或空间 ID)
  python3 manage_spaces.py set --code G2026000S

  # 查看当前已选中的默认空间
  python3 manage_spaces.py current
"""

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional
from fde_common import make_request, load_auth_config, save_auth_config, get_moss_headers

def fetch_spaces(page: int = 1, size: int = 50) -> List[Dict[str, Any]]:
    """调用平台底层接口获取当前用户拥有的所有研发空间"""
    h = get_moss_headers()
    h["x-auth-module"] = "PLATFORM"
    
    res = make_request(
        "GET",
        "/fde/moss/web/desktop/v1/api/v1/user/space/list",
        params={"pageNo": page, "pageSize": size},
        custom_headers=h
    )
    if res.get("error"):
        print(f"[x] 拉取研发空间列表失败: {res.get('message')}")
        sys.exit(1)

    return res.get("data", {}).get("list", [])

def get_current_space() -> Dict[str, str]:
    """读取当前配置中选中的默认空间"""
    auth = load_auth_config()
    code = auth.get("default_space_code", "")
    sid = auth.get("default_space_id", "")
    name = auth.get("default_space_name", "")
    if not code:
        fde_h = auth.get("fde_http_header", {})
        if fde_h.get("x-auth-module") == "SPACE":
            code = fde_h.get("x-auth-moduleid", "")
    return {"spaceCode": code, "spaceId": sid, "spaceName": name}

def list_spaces():
    """打印研发空间列表表格"""
    spaces = fetch_spaces()
    if not spaces:
        print("[!] 当前用户未加入或未创建任何研发空间。")
        return

    curr = get_current_space()
    curr_code = curr.get("spaceCode", "")

    print(f"\n【我的研发空间列表】(共 {len(spaces)} 个空间)")
    print("=" * 110)
    print(f" {'序号':<4} | {'空间编码 (Code)':<14} | {'空间唯一 ID (spaceId)':<24} | {'空间名称':<22} | {'负责人':<10} | {'当前状态'}")
    print("-" * 110)
    
    for idx, s in enumerate(spaces, start=1):
        code = s.get("spaceCode", "")
        sid = s.get("spaceId", "")
        name = s.get("spaceName", "")
        owner = s.get("ownerName", "")
        is_curr = (code == curr_code)
        mark = " [*当前默认]" if is_curr else ""
        state = "正常" if str(s.get("spaceState", "0")) == "0" else "已归档"
        status_text = f"{state}{mark}"
        print(f" [{idx:<2}] | {code:<14} | {sid:<24} | {name:<22} | {owner:<10} | {status_text}")
    print("=" * 110)
    if curr_code:
        print(f"提示: 当前默认空间为 [{curr_code}]。可通过 'manage_spaces.py select' 切换。\n")
    else:
        print("提示: 尚未选择默认空间，可通过 'manage_spaces.py select' 选择要操作的空间。\n")

def select_space():
    """交互式让用户选择研发空间"""
    spaces = fetch_spaces()
    if not spaces:
        print("[x] 未检测到任何可用的研发空间。")
        sys.exit(1)

    curr = get_current_space()
    curr_code = curr.get("spaceCode", "")

    print("\n请选择您要操作的研发空间：")
    print("-" * 80)
    for idx, s in enumerate(spaces, start=1):
        code = s.get("spaceCode", "")
        sid = s.get("spaceId", "")
        name = s.get("spaceName", "")
        owner = s.get("ownerName", "")
        is_curr = " (当前选中)" if code == curr_code else ""
        print(f"  [{idx}] {name} (编码: {code}, 空间ID: {sid}, 负责人: {owner}){is_curr}")
    print("-" * 80)

    while True:
        try:
            choice = input(f"请输入空间序号 [1-{len(spaces)}] (输入 q 取消): ").strip()
            if choice.lower() == 'q':
                print("[*] 已取消选择。")
                return
            if not choice.isdigit():
                print("请输入有效数字！")
                continue
            num = int(choice)
            if 1 <= num <= len(spaces):
                chosen = spaces[num - 1]
                set_default_space(
                    chosen.get("spaceCode", ""),
                    chosen.get("spaceId", ""),
                    chosen.get("spaceName", "")
                )
                break
            else:
                print(f"输入超出范围，请输入 1 到 {len(spaces)} 之间的数字。")
        except (KeyboardInterrupt, EOFError):
            print("\n[*] 已取消。")
            break

def set_default_space(space_code: str, space_id: str = "", space_name: str = ""):
    """持久化设置默认空间"""
    auth = load_auth_config()
    if not space_id or not space_name:
        # 从已有空间列表中补全
        spaces = fetch_spaces()
        for s in spaces:
            if s.get("spaceCode") == space_code or s.get("spaceId") == space_code:
                space_code = s.get("spaceCode", "")
                space_id = s.get("spaceId", "")
                space_name = s.get("spaceName", "")
                break

    if not space_code:
        print("[x] 未找到对应空间，设置失败！")
        sys.exit(1)

    # 更新 fde_http_header
    fde_h = auth.get("fde_http_header", {})
    fde_h["x-auth-module"] = "SPACE"
    fde_h["x-auth-moduleid"] = space_code

    payload = {
        "default_space_code": space_code,
        "default_space_id": space_id,
        "default_space_name": space_name,
        "fde_http_header": fde_h
    }
    save_auth_config(payload)

    print("\n" + "=" * 65)
    print("【✓】默认研发空间切换成功！已更新至本地配置。")
    print("=" * 65)
    print(f" 空间名称: {space_name or '(未指定)'}")
    print(f" 空间编码: {space_code}")
    print(f" 空间 ID:  {space_id or '(无)'}")
    print("=" * 65)
    print("提示: 后续执行需求管理等脚本时，将默认在该空间下操作。\n")

def show_current():
    curr = get_current_space()
    if not curr.get("spaceCode"):
        print("[!] 当前尚未设置默认研发空间。请运行: python3 manage_spaces.py select 进行选择。")
    else:
        print("\n【当前默认研发空间】")
        print(f" 空间名称: {curr.get('spaceName') or '(未缓存)'}")
        print(f" 空间编码: {curr.get('spaceCode')}")
        print(f" 空间 ID:  {curr.get('spaceId') or '(未缓存)'}\n")

def main():
    parser = argparse.ArgumentParser(description="FDE 研发空间管理工具 (ID获取、列表与多空间切换)")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # 1. list
    subparsers.add_parser("list", help="列出当前用户的所有研发空间")

    # 2. select
    subparsers.add_parser("select", help="交互式选择要操作的研发空间")

    # 3. set
    p_set = subparsers.add_parser("set", help="指定并设置默认研发空间")
    p_set.add_argument("--code", "-c", required=True, help="空间编码 (如 G2026000S) 或空间 ID")
    p_set.add_argument("--id", "-i", default="", help="空间 ID (可选)")
    p_set.add_argument("--name", "-n", default="", help="空间名称 (可选)")

    # 4. current
    subparsers.add_parser("current", help="查看当前生效的默认空间")

    args = parser.parse_args()

    if args.command == "list" or not args.command:
        list_spaces()
    elif args.command == "select":
        select_space()
    elif args.command == "set":
        set_default_space(args.code, args.id, args.name)
    elif args.command == "current":
        show_current()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
