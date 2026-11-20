#!/usr/bin/env python3
"""
FDE 灵宝原生 AI 智能体互动脚本
复用已存储的登录信息，支持列出平台原生智能体、拉取对话历史卡片与下发分析任务。

用法:
  python3 manage_agent.py list
  python3 manage_agent.py sessions [--page 1] [--size 10]
  python3 manage_agent.py messages --session-id <会话ID>
  python3 manage_agent.py run --agent-id <智能体ID> --prompt "<任务描述>"
"""

import argparse
import json
import sys
from fde_common import make_request

def list_agents():
    print("[*] 正在拉取平台部署的专业智能体列表...")
    res = make_request("GET", "/fde/moss/web/fde-agent/v1/agents")
    if res.get("error"):
        print(f"[x] 拉取失败: {res.get('message')}")
        sys.exit(1)

    agents = res.get("data", [])
    print(f"\n【平台已部署智能体】(共 {len(agents)} 个)")
    print("-" * 75)
    print(f"{'智能体ID':<22} | {'名称':<15} | {'职能描述'}")
    print("-" * 75)
    for ag in agents:
        aid = ag.get("id", "")
        name = ag.get("name", "")
        desc = ag.get("description", "").replace("\n", " ")
        print(f"{aid:<22} | {name:<15} | {desc}")
    print("-" * 75 + "\n")

def list_sessions(page: int, size: int):
    print(f"[*] 正在拉取智能体历史会话清单 (第 {page} 页)...")
    res = make_request("GET", "/fde/moss/web/fde-agent/v1/sessions", params={"page": page, "size": size})
    if res.get("error"):
        print(f"[x] 拉取会话失败: {res.get('message')}")
        sys.exit(1)

    data = res.get("data", {})
    items = data.get("items", [])
    total = data.get("total", len(items))

    print(f"\n【智能体历史会话】(总数: {total}，当前展示 {len(items)} 条)")
    print("-" * 75)
    print(f"{'会话ID':<34} | {'所属智能体':<18} | {'会话标题'}")
    print("-" * 75)
    for s in items:
        sid = s.get("id", "")
        ag = s.get("agentId", "")
        title = s.get("title", "")
        print(f"{sid:<34} | {ag:<18} | {title}")
    print("-" * 75 + "\n")

def show_messages(session_id: str):
    print(f"[*] 正在获取会话 [{session_id}] 的完整问答流与阶段卡片...")
    res = make_request("GET", f"/fde/moss/web/fde-agent/v1/sessions/{session_id}/messages", params={"page": 1, "size": 50})
    if res.get("error"):
        print(f"[x] 获取会话消息失败: {res.get('message')}")
        sys.exit(1)

    items = res.get("data", {}).get("items", [])
    print("\n" + "=" * 70)
    print(f"【会话完整历史记录】(共 {len(items)} 条对话)")
    print("=" * 70)
    for m in items:
        role = "【用户】" if m.get("role") == "user" else "【智能体 AI】"
        created = m.get("createdAt", "").replace("T", " ").split(".")[0]
        content = m.get("content", "").strip()
        print(f"\n{role}  时间: {created}")
        print("-" * 50)
        print(content)
    print("=" * 70 + "\n")

def run_agent(agent_id: str, prompt: str, session_id: str = ""):
    print(f"[*] 正在向智能体 [{agent_id}] 下发任务...")
    # 注意：网关要求的字段名是 input（字符串），不是 prompt；用错会报「参数不合法：input」
    payload = {
        "agentId": agent_id,
        "input": prompt,
        "sessionId": session_id or ""
    }
    res = make_request("POST", "/fde/moss/web/fde-agent/v1/runs", data=payload)
    if res.get("error"):
        print(f"[x] 下发任务失败: {res.get('message')}")
        sys.exit(1)

    print("\n[✓] 任务已成功派发至智能体执行器！返回数据:")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    print("")

def main():
    parser = argparse.ArgumentParser(description="FDE 灵宝智能体交互工具")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    subparsers.add_parser("list", help="查看所有可用专业智能体")

    sess_p = subparsers.add_parser("sessions", help="查看历史会话记录")
    sess_p.add_argument("--page", type=int, default=1, help="页码")
    sess_p.add_argument("--size", type=int, default=10, help="每页条数")

    msg_p = subparsers.add_parser("messages", help="查看会话消息历史")
    msg_p.add_argument("--session-id", type=str, required=True, help="会话 ID")

    run_p = subparsers.add_parser("run", help="向智能体派发任务")
    run_p.add_argument("--agent-id", type=str, required=True, help="智能体 ID")
    run_p.add_argument("--prompt", type=str, required=True, help="任务描述或提示词")
    run_p.add_argument("--session-id", type=str, default="", help="可选继续追问的会话 ID")

    args = parser.parse_args()

    if args.command == "list":
        list_agents()
    elif args.command == "sessions":
        list_sessions(args.page, args.size)
    elif args.command == "messages":
        show_messages(args.session_id)
    elif args.command == "run":
        run_agent(args.agent_id, args.prompt, args.session_id)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
