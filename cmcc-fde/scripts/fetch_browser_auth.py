#!/usr/bin/env python3
"""
FDE 首次登录凭证自动采集脚本（浏览器 cookie + MOSS-TOKEN）

第一次使用本技能、本地没有 fde_auth.json 时，用本脚本从浏览器会话中
一次性采集所有鉴权凭证，包括：
  - MOSS_SESSION (httpOnly Cookie，主会话)
  - MOSS-TOKEN  (sessionStorage.fdeHttpHeader["MOSS-TOKEN"]，API 鉴权 JWT)
  - refreshToken / mossEncryptKey / openEncryptKey (会话刷新与加密密钥)
  - fdeHttpHeader (完整的鉴权请求头模板)
并自动调用 auth_login.py 校验身份、写入三处 fde_auth.json。

底层依赖 playwright-browser-use 技能（需已 npm install，daemon 会拉起系统 Chrome）。
登录为短信 + 图形验证码，需人工在浏览器窗口完成，本脚本只负责「打开页面、
等待人工登录、采集凭证」，不猜测/绕过任何凭据。

【唯一登录入口】本脚本只会打开 FDE 统一登录页：
  https://sti.chinamobile.com/fde/micrologin/#/login
不得改为 /moss/microhome 等其它地址（那是登录后的落地页，直接打开会导致登录态异常）。
凭证采集阶段也只从当前已登录页面读取 Cookie，不额外弹出需求/代码等子系统页面。

用法:
  # 1. 打开登录页（daemon 未启动会自动拉起），人工登录后保持窗口
  python3 fetch_browser_auth.py open

  # 2. 采集凭证（登录完成后执行；含等待轮询）
  python3 fetch_browser_auth.py fetch [--wait 120]

  # 一步到位：打开页面 -> 等你登录 -> 自动采集（交互式，适合人工值守）
  python3 fetch_browser_auth.py interactive

  # 仅查看浏览器当前登录态，不写文件
  python3 fetch_browser_auth.py status
"""

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Any, Dict, Optional

# 允许从环境变量覆盖 playwright-browser-use 技能目录
PW_SKILL_DIR = os.environ.get(
    "PW_BROWSER_SKILL_DIR",
    os.path.expanduser("~/.workbuddy/skills/playwright-browser-use"),
)
PW_CLI = os.path.join(PW_SKILL_DIR, "pw-browser.js")
NODE_MODULES = os.path.join(PW_SKILL_DIR, "node_modules")

# 【唯一登录入口】FDE 统一登录页。脚本只会打开这一个地址，切勿改成 microhome
# 或其它子系统页面（那些是登录成功后的落地页，不是登录页，直接打开会导致登录态异常）。
FDE_LOGIN_URL = "https://sti.chinamobile.com/fde/micrologin/#/login"
WORKBENCH_URL = "https://sti.chinamobile.com/fde/microportal/#/workbench"

# 采集脚本：在浏览器 sessionStorage 中定位 MOSS-TOKEN 等凭证
# 注意：run-code 在 daemon 沙箱中执行，page 已注入；DOM/storage 读写必须包进
# page.evaluate，且最外层必须显式 return，结果才会作为 result 字段返回。
EXTRACT_JS = r"""
const data = await page.evaluate(() => {
  const result = { moss_token: '', fde_http_header: {},
                   token_key: '', refresh_token: '', moss_encrypt_key: '',
                   open_encrypt_key: '', entry_source: '', domain: '' };
  try {
    const fh = sessionStorage.getItem('fdeHttpHeader');
    if (fh) {
      try {
        const h = JSON.parse(fh);
        result.fde_http_header = h;
        const tk = sessionStorage.getItem('tokenKey') || 'MOSS-TOKEN';
        result.token_key = tk;
        result.moss_token = h[tk] || h['MOSS-TOKEN'] || h['moss-token'] || h['Moss-Token'] || '';
      } catch (e) {}
    }
    result.refresh_token    = sessionStorage.getItem('refreshToken') || '';
    result.moss_encrypt_key = sessionStorage.getItem('mossEncryptKey') || '';
    result.open_encrypt_key = sessionStorage.getItem('openEncryptKey') || '';
    result.entry_source     = sessionStorage.getItem('curEntrySource') || '';
    const dom = sessionStorage.getItem('domain');
    if (dom) { try { result.domain = JSON.parse(dom); } catch (e) {} }
    const cei = sessionStorage.getItem('curEnterpriseInfo');
    if (cei) { try { result.enterprise_info = JSON.parse(cei); } catch (e) {} }
  } catch (e) {}
  return result;
});
return JSON.stringify(data);
"""


def _pw(*args: str, timeout: int = 30) -> Dict[str, Any]:
    """调用 playwright-browser-use CLI，返回解析后的 JSON dict。"""
    if not os.path.exists(PW_CLI):
        print(f"[x] 找不到 playwright-browser-use 技能: {PW_CLI}", file=sys.stderr)
        print("    请先安装该技能（search_and_install_skills / 设置中启用浏览器控制）。", file=sys.stderr)
        sys.exit(1)
    env = os.environ.copy()
    env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
    env["NODE_PATH"] = NODE_MODULES
    cmd = ["node", PW_CLI, *args]
    try:
        proc = subprocess.run(
            cmd, env=env, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": {"message": f"命令超时: {' '.join(args)}"}}
    out = proc.stdout.strip()
    # 容错：有些命令输出带前缀日志，截取首个 JSON 对象
    start = out.find("{")
    if start < 0:
        return {"ok": False, "error": {"message": out or proc.stderr.strip() or "无输出"}}
    try:
        return json.loads(out[start:])
    except json.JSONDecodeError:
        return {"ok": False, "error": {"message": out[start:start + 300]}}


def _daemon_alive() -> bool:
    r = _pw("init", timeout=10)
    return bool(r.get("ok"))


def _start_daemon() -> bool:
    """若 daemon 未运行则后台拉起。"""
    if _daemon_alive():
        return True
    print("[*] 浏览器 daemon 未运行，正在拉起系统 Chrome ...")
    env = os.environ.copy()
    env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
    env["NODE_PATH"] = NODE_MODULES
    try:
        subprocess.Popen(
            ["node", PW_CLI, "daemon"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        print(f"[x] 启动 daemon 失败: {e}", file=sys.stderr)
        return False
    # 等待就绪
    for _ in range(15):
        time.sleep(1)
        if _daemon_alive():
            print("[✓] 浏览器 daemon 已就绪。")
            return True
    print("[x] daemon 启动超时，请检查 Chrome 是否可用。", file=sys.stderr)
    return False


def cmd_open() -> None:
    """仅打开 FDE 统一登录页（唯一允许弹出的页面地址）。"""
    if not _start_daemon():
        sys.exit(1)
    print(f"[*] 正在打开 FDE 统一登录页: {FDE_LOGIN_URL}")
    r = _pw("open", FDE_LOGIN_URL, timeout=60)
    if not r.get("ok"):
        print(f"[x] 打开页面失败: {r.get('error')}", file=sys.stderr)
        sys.exit(1)
    print(f"[✓] 已打开: {r.get('afterUrl') or r.get('data', {}).get('afterUrl', '')}")
    print("[提示] 请在打开的 Chrome 窗口中完成登录（手机号 + 图形验证码 + 短信动态密码）。")
    print("       登录成功进入工作台后，运行: python3 fetch_browser_auth.py fetch")
    print(f"[约束] 本脚本只弹出登录页 {FDE_LOGIN_URL}，不会打开其它子系统页面。")


def _read_browser_creds() -> Optional[Dict[str, Any]]:
    """从浏览器读取 Cookie + sessionStorage 凭证，返回结构化 dict。"""
    # 1) Cookie
    # ponytail: 严禁按 name 去重——平台会在同域名下发两份同名 MOSS_SESSION
    # （sti.chinamobile.com 与 .sti.chinamobile.com 各一条，2026-11-20 实测），
    # 去重会把另一条弄丢，导致 fde-code 子系统 405「登录已失效」。
    ck = _pw("cookies", "list", "--json", timeout=20)
    cookies = ck.get("cookies", []) if isinstance(ck, dict) else []
    # 保留全部记录（含同名不同域），按浏览器实际顺序拼接，保证与页面请求头一致
    cookie_str = "; ".join(f"{c.get('name')}={c.get('value', '')}" for c in cookies)
    # 供展示/落库用的主会话值：优先取裸域那条（登录门户签发），取不到取最后一条
    moss_vals = [c.get("value", "") for c in cookies if c.get("name") == "MOSS_SESSION"]
    moss_session = moss_vals[0] if moss_vals else ""

    # 2) sessionStorage 里的 MOSS-TOKEN 等
    rc = _pw("run-code", EXTRACT_JS, timeout=20)
    payload_str = rc.get("result") if isinstance(rc, dict) else None
    if not payload_str:
        # 兼容不同返回字段名
        data = rc.get("data", {}) if isinstance(rc, dict) else {}
        payload_str = data.get("result") if isinstance(data, dict) else None
    try:
        s = json.loads(payload_str) if payload_str else {}
    except (json.JSONDecodeError, TypeError):
        s = {}

    moss_token = s.get("moss_token", "")
    return {
        "cookie": cookie_str,
        "MOSS_SESSION": moss_session,
        "moss_token": moss_token,
        "token_key": s.get("token_key", "MOSS-TOKEN"),
        "fde_http_header": s.get("fde_http_header", {}),
        "refresh_token": s.get("refresh_token", ""),
        "moss_encrypt_key": s.get("moss_encrypt_key", ""),
        "open_encrypt_key": s.get("open_encrypt_key", ""),
        "entry_source": s.get("entry_source", ""),
        "browser_domain": s.get("domain", {}),
        "enterprise_info": s.get("enterprise_info", {}),
    }


def _logged_in(creds: Dict[str, Any]) -> bool:
    return bool(creds.get("MOSS_SESSION")) and bool(creds.get("moss_token"))


def cmd_status() -> None:
    if not _daemon_alive():
        print("[!] 浏览器 daemon 未运行。")
        return
    creds = _read_browser_creds()
    snap = _pw("snap", "--json", timeout=20)
    url = ""
    if isinstance(snap, dict):
        data = snap.get("data", {})
        url = (data.get("url", "") if isinstance(data, dict) else "") or snap.get("url", "")
    print("=== 浏览器登录态 ===")
    print(f" 当前页面: {url or '(未知)'}")
    print(f" MOSS_SESSION: {'✓ 已获取' if creds['MOSS_SESSION'] else '✗ 无'}")
    print(f" MOSS-TOKEN : {'✓ 已获取' if creds['moss_token'] else '✗ 无'}")
    print(f" refreshToken: {'✓ 已获取' if creds['refresh_token'] else '✗ 无'}")
    print(f" 综合判断: {'已登录，可执行 fetch' if _logged_in(creds) else '未登录，请先 open 并登录'}")


def cmd_fetch(wait_seconds: int) -> None:
    """采集凭证 -> 写临时 JSON -> 调 auth_login.py 校验并持久化。"""
    if not _daemon_alive():
        print("[x] 浏览器 daemon 未运行，请先执行: python3 fetch_browser_auth.py open", file=sys.stderr)
        sys.exit(1)

    print(f"[*] 等待浏览器登录完成（最长 {wait_seconds} 秒）...")
    creds = None
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        creds = _read_browser_creds()
        if _logged_in(creds):
            break
        time.sleep(3)
    if not creds or not _logged_in(creds):
        print("[x] 超时未检测到完整登录凭证（需要 MOSS_SESSION + MOSS-TOKEN）。", file=sys.stderr)
        print("    请确认已在浏览器完成登录并进入工作台页面。", file=sys.stderr)
        sys.exit(1)

    print("[✓] 已检测到完整登录凭证。")

    # 组装要持久化的凭证：身份字段会在 auth_login.py 校验后补全
    save_payload = {
        "cookie": creds["cookie"],
        "MOSS_SESSION": creds["MOSS_SESSION"],
        "moss_token": creds["moss_token"],
        "token_key": creds["token_key"],
        "fde_http_header": creds["fde_http_header"],
        "refresh_token": creds["refresh_token"],
        "moss_encrypt_key": creds["moss_encrypt_key"],
        "open_encrypt_key": creds["open_encrypt_key"],
        "entry_source": creds["entry_source"],
    }
    if creds.get("enterprise_info"):
        ei = creds["enterprise_info"]
        for k in ["name", "email", "employeeNo", "username", "deputyAccountNumber", "enterpriseCode"]:
            if ei.get(k):
                save_payload[k] = ei[k]

    # 写入临时凭证文件（复用 fde_common.save_auth_config，合并写入三处）
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from fde_common import save_auth_config
    save_auth_config(save_payload)
    print("[✓] Cookie / MOSS-TOKEN / 刷新令牌等凭证已写入 fde_auth.json（三处）。")

    # 从当前已登录页面读取全部 Cookie（不额外打开任何子系统页面）。
    # 注意：需求子系统 sessionToken 已由 fde_common.get_req_session_token() 本地身份生成，
    # 不再依赖浏览器预热；此处仅顺带收集浏览器内已有的 sessionToken 作为冗余备份。
    print("[*] 正在从当前页面采集 Cookie 与子模块凭证（不弹出其它页面）...")
    try:
        sub_ck = _pw("cookies", "list", "--json", timeout=20)
        sub_cookies = sub_ck.get("cookies", []) if isinstance(sub_ck, dict) else []
        sub_map = {c.get("name"): c.get("value", "") for c in sub_cookies}
        session_token = sub_map.get("sessionToken", "")
        if session_token:
            save_auth_config({
                "sessionToken": session_token,
                "req_session_token": session_token,
                "cookie": "; ".join(f"{k}={v}" for k, v in sub_map.items())
            })
            print("[✓] 浏览器内 sessionToken 已采集并写入配置（冗余备份）。")
        else:
            print("[-] 当前页面无 sessionToken（需求 token 本地生成，不影响功能）。")
    except Exception as e:
        print(f"[-] 子模块凭证采集提示: {e} (不影响主功能)")

    # 调用 auth_login.py --check 校验身份并补全 enterpriseId/userId 等字段
    script_dir = os.path.dirname(os.path.abspath(__file__))
    login_script = os.path.join(script_dir, "auth_login.py")
    print("[*] 正在校验身份并补全企业/用户信息 ...")
    proc = subprocess.run([sys.executable, login_script, "--check"])
    if proc.returncode != 0:
        print("[x] 身份校验失败，凭证可能已过期，请重新 open 登录后 fetch。", file=sys.stderr)
        sys.exit(1)

    # 自动为用户生成永久有效 (permanent) 代码仓库 Private Token
    token_script = os.path.join(script_dir, "manage_token.py")
    if os.path.exists(token_script):
        print("[*] 正在自动生成全权限永久代码仓库 Private Token ...")
        subprocess.run([sys.executable, token_script, "create", "--name", "Auto-Permanent-Token"])

    # 打印脱敏摘要
    print("\n" + "=" * 55)
    print("【✓】浏览器全量凭证自动采集完成，FDE 全套技能均已激活就绪！")
    print("=" * 55)
    print(f" MOSS_SESSION : {creds['MOSS_SESSION'][:8]}...（{len(creds['MOSS_SESSION'])} 字符）")
    print(f" MOSS-TOKEN   : {creds['moss_token'][:16]}...（{len(creds['moss_token'])} 字符）")
    print(f" refreshToken : {'已保存' if creds['refresh_token'] else '无'}")
    print(f" fdeHttpHeader: {len(creds['fde_http_header'])} 个头字段已保存")
    print("=" * 55)


def cmd_interactive() -> None:
    """一步到位：打开页面 -> 等待人工登录确认 -> 采集。"""
    cmd_open()
    try:
        input("\n>>> 登录成功后按回车继续采集（Ctrl+C 取消）...")
    except (EOFError, KeyboardInterrupt):
        print("\n[!] 已取消。可稍后手动执行: python3 fetch_browser_auth.py fetch")
        return
    cmd_fetch(wait_seconds=60)


def main() -> None:
    parser = argparse.ArgumentParser(description="FDE 浏览器凭证自动采集（Cookie + MOSS-TOKEN）")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("open", help="打开 FDE 登录页（daemon 未启动会自动拉起）")

    fetch_p = sub.add_parser("fetch", help="采集浏览器凭证并写入 fde_auth.json")
    fetch_p.add_argument("--wait", type=int, default=120, help="等待登录完成的最长秒数（默认 120）")

    sub.add_parser("status", help="查看浏览器当前登录态，不写文件")
    sub.add_parser("interactive", help="打开页面并等待回车后自动采集")

    args = parser.parse_args()
    if args.command == "open":
        cmd_open()
    elif args.command == "fetch":
        cmd_fetch(args.wait)
    elif args.command == "status":
        cmd_status()
    elif args.command == "interactive":
        cmd_interactive()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
