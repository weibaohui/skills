#!/usr/bin/env python3
"""
FDE 资产中心管理与检索脚本
复用已存储的登录信息，支持查看平台科研资产全局统计、分页按需检索资产、查看资产交付物详情与文件附件。

用法:
  python3 manage_assets.py stats
  python3 manage_assets.py search [--keyword <关键词>] [--type <SOLUTION|SKILL|PRACTICE>] [--page 1] [--size 10]
  python3 manage_assets.py detail --id <资产ID>
"""

import argparse
import json
import sys
from fde_common import make_request, get_request_id

def show_stats():
    print("[*] 正在拉取资产中心全局指标与统计...")
    stats_res = make_request("GET", "/fde/moss/web/asset/v1/api/v1/assets/statistics")
    count_res = make_request("GET", "/fde/moss/web/asset/v1/api/v1/assets/count-summary")

    if stats_res.get("error") or count_res.get("error"):
        print("[x] 获取统计信息失败！")
        sys.exit(1)

    s = stats_res.get("data", {})
    c = count_res.get("data", {})

    print("\n" + "=" * 55)
    print("【FDE 科研资产中心全景概览】")
    print("=" * 55)
    print(f" 平台总科研资产数: {s.get('totalAssets', 0)} 个")
    print(f" 当前可见资产数:   {c.get('visibleCount', 0)} 个")
    print(f" 累计文件下载量:   {s.get('totalDownload', 0)} 次")
    print(f" 近30天活跃浏览量: {s.get('view30d', 0)} 次")
    print("=" * 55 + "\n")

def search_assets(keyword: str, asset_type: str, page: int, size: int):
    print(f"[*] 正在检索资产 (关键词: '{keyword or '全部'}', 分类: '{asset_type or '全部'}')...")
    payload = {
        "head": {"requestId": get_request_id()},
        "data": {
            "page": page,
            "size": size
        }
    }
    if keyword:
        payload["data"]["assetName"] = keyword
    if asset_type:
        payload["data"]["assetType"] = asset_type

    res = make_request("POST", "/fde/moss/web/asset/v1/api/v1/assets/page", data=payload)
    if res.get("error"):
        print(f"[x] 检索失败: {res.get('message')}")
        sys.exit(1)

    data = res.get("data", {})
    total = data.get("total", 0)
    items = data.get("list", [])

    print(f"\n【资产检索结果】(总数: {total} 个，展示第 {page} 页 {len(items)} 条)")
    print("-" * 80)
    print(f"{'资产ID':<22} | {'类型':<10} | {'资产编号':<18} | {'资产名称'}")
    print("-" * 80)
    for a in items:
        aid = a.get("assetId", "")
        atype = a.get("assetType", "")
        ano = a.get("assetNo", "")
        aname = a.get("assetName", "")
        print(f"{aid:<22} | {atype:<10} | {ano:<18} | {aname}")
    print("-" * 80 + "\n")

def show_detail(asset_id: str):
    print(f"[*] 正在获取资产 ID={asset_id} 的详情信息...")
    res = make_request("GET", "/fde/moss/web/asset/v1/api/v1/assets/detail", params={"assetId": asset_id})

    if res.get("error"):
        print(f"[x] 获取资产详情失败: {res.get('message')}")
        sys.exit(1)

    d = res.get("data", {})
    files = d.get("files", [])

    print("\n" + "=" * 65)
    print(f"【资产详情】: {d.get('assetName')}")
    print("=" * 65)
    print(f" 资产编号:   {d.get('assetNo')}")
    print(f" 资产类别:   {d.get('assetType')} | 状态: {d.get('assetStatus')}")
    print(f" 研发部门:   {d.get('deptName')}")
    print(f" 创建人员:   {d.get('creatorName')} ({d.get('creatorAccount')})")
    print(f" 业务优势:   {d.get('businessAdvantage') or '无'}")
    print(f" 技术架构:   {d.get('technicalArchitecture') or '无'}")
    print("-" * 65)
    print(f"挂载交付文件清单 (共 {len(files)} 个):")
    for f in files:
        # 平台返回的 fileSize 可能是字符串（如 "108"）也可能是数字，统一转 float
        try:
            size = float(f.get("fileSize", 0) or 0)
        except (TypeError, ValueError):
            size = 0.0
        fsize_kb = round(size / 1024, 2)
        print(f"  * [{f.get('fileType') or f.get('fileCategory', '')}] {f.get('fileName')} ({fsize_kb} KB)")
    print("=" * 65 + "\n")

def main():
    parser = argparse.ArgumentParser(description="FDE 资产中心管理工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    subparsers.add_parser("stats", help="查看资产中心全局指标统计")

    search_p = subparsers.add_parser("search", help="检索科研资产")
    search_p.add_argument("--keyword", type=str, default="", help="搜索关键词")
    search_p.add_argument("--type", type=str, choices=["SOLUTION", "SKILL", "PRACTICE", ""], default="", help="资产类别")
    search_p.add_argument("--page", type=int, default=1, help="页码")
    search_p.add_argument("--size", type=int, default=10, help="每页条数")

    detail_p = subparsers.add_parser("detail", help="获取指定资产详情")
    detail_p.add_argument("--id", type=str, required=True, help="资产 ID")

    args = parser.parse_args()

    if args.command == "stats":
        show_stats()
    elif args.command == "search":
        search_assets(args.keyword, args.type, args.page, args.size)
    elif args.command == "detail":
        show_detail(args.id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
