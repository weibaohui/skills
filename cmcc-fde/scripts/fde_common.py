"""
中国移动“灵畿”科研平台 (FDE) 核心公共工具库
提供跨脚本统一的配置加载、网络请求、会话校验与数据解压缩支持
"""

import base64
import gzip
import json
import os
import sys
import ssl
import time
from typing import Any, Dict, Optional
import urllib.request
import urllib.error

BASE_URL = "https://sti.chinamobile.com"

def get_auth_file_paths():
    """获取所有鉴权文件搜索路径，按优先级排列"""
    paths = []
    if os.environ.get("FDE_AUTH_PATH"):
        paths.append(os.environ["FDE_AUTH_PATH"])
    
    # 1. 当前工作目录下的 fde_auth.json
    paths.append(os.path.join(os.getcwd(), "fde_auth.json"))
    
    # 2. 脚本所在技能目录下的 config/fde_auth.json
    script_dir = os.path.dirname(os.path.abspath(__file__))
    skill_config = os.path.join(os.path.dirname(script_dir), "config", "fde_auth.json")
    paths.append(skill_config)

    # 3. 用户全局主目录 ~/.fde/fde_auth.json
    home_config = os.path.expanduser("~/.fde/fde_auth.json")
    paths.append(home_config)
    
    return paths

def load_auth_config() -> Dict[str, Any]:
    """读取已存储的登录会话与鉴权配置"""
    for p in get_auth_file_paths():
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("cookie"):
                        return data
            except Exception:
                pass
    return {}

def save_auth_config(data: Dict[str, Any], target_path: Optional[str] = None):
    """保存或更新登录会话与鉴权配置（同步写入技能配置与全局配置）"""
    save_targets = []
    if target_path:
        save_targets.append(target_path)
    else:
        # 同时写入当前工作区、技能内置目录以及全局 ~/.fde
        save_targets.append(os.path.join(os.getcwd(), "fde_auth.json"))
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_targets.append(os.path.join(os.path.dirname(script_dir), "config", "fde_auth.json"))
        save_targets.append(os.path.expanduser("~/.fde/fde_auth.json"))

    for path in save_targets:
        try:
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            existing = {}
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}
            existing.update(data)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[!] 警告: 保存鉴权文件至 {path} 失败: {e}", file=sys.stderr)

def get_request_id() -> str:
    return f"{int(time.time() * 1000)}{int(time.time() * 100) % 1000}"

def get_moss_headers() -> Dict[str, str]:
    """
    从凭证中提取浏览器侧的 MOSS 鉴权头。
    优先使用采集时保存的完整 fde_http_header；若只有 moss_token 则单独构造 MOSS-TOKEN。
    返回空 dict 表示凭证中无 MOSS-TOKEN（保持向后兼容，仅用 Cookie 亦可工作）。
    """
    auth = load_auth_config()
    headers: Dict[str, str] = {}
    fh = auth.get("fde_http_header") or {}
    if isinstance(fh, dict) and fh:
        # 仅透传平台鉴权相关的头，忽略浏览器无关字段
        for key in ("Data-Auth-Domain", "Data-Auth-Appid", "Data-Auth-Enterpriseid",
                    "MOSS-TOKEN", "x-auth-module", "x-auth-moduleid"):
            if fh.get(key):
                headers[key] = fh[key]
    if not headers.get("MOSS-TOKEN"):
        token_key = auth.get("token_key", "MOSS-TOKEN") or "MOSS-TOKEN"
        moss_token = auth.get("moss_token", "")
        if moss_token:
            headers[token_key] = moss_token
    return headers


def make_request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    custom_headers: Optional[Dict[str, str]] = None,
    timeout: int = 15
) -> Dict[str, Any]:
    """底层统一下发 HTTP 请求并处理 Gzip 解压缩"""
    auth = load_auth_config()
    cookie = auth.get("cookie", "")
    enterprise_id = auth.get("enterpriseId", "ENT_999999")
    private_token = auth.get("private_token", "")

    url = BASE_URL + path
    if params:
        query_parts = []
        for k, v in params.items():
            if v is not None:
                query_parts.append(f"{k}={urllib.request.quote(str(v))}")
        if query_parts:
            url += ("&" if "?" in url else "?") + "&".join(query_parts)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Data-Auth-Appid": "FDE",
        "Data-Auth-Domain": "portal",
        "Data-Auth-Enterpriseid": enterprise_id,
        "Origin": BASE_URL,
        "X-Requested-With": "XMLHttpRequest",
    }

    if cookie:
        headers["Cookie"] = cookie
    if private_token:
        headers["Private-Token"] = private_token
    # 自动附带浏览器侧 MOSS 鉴权头（MOSS-TOKEN 等），不存在时不添加，保持兼容
    headers.update(get_moss_headers())
    if custom_headers:
        headers.update(custom_headers)

    req_body = None
    if data is not None:
        req_body = json.dumps(data).encode("utf-8")

    req = urllib.request.Request(url, data=req_body, headers=headers, method=method.upper())

    # 证书链含 SHECA 等国内 CA，macOS Python 默认包不含其根证书，优先用 certifi 的 CA 包
    ssl_ctx = None
    try:
        import certifi
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ssl_ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx) as resp:
            raw = resp.read()
            text = ""
            try:
                text = gzip.decompress(raw).decode("utf-8")
            except Exception:
                try:
                    import brotli
                    text = brotli.decompress(raw).decode("utf-8")
                except Exception:
                    text = raw.decode("utf-8", errors="ignore")
            try:
                return json.loads(text)
            except Exception:
                return {"raw_text": text, "status_code": resp.status}
    except urllib.error.HTTPError as e:
        raw = e.read()
        err_text = ""
        try:
            err_text = gzip.decompress(raw).decode("utf-8")
        except Exception:
            try:
                import brotli
                err_text = brotli.decompress(raw).decode("utf-8")
            except Exception:
                err_text = raw.decode("utf-8", errors="ignore")
        return {"error": True, "http_status": e.code, "message": err_text}
    except Exception as e:
        return {"error": True, "message": str(e)}

def get_req_session_token() -> str:
    """
    获取需求子系统 (Proxima/Parse) 的 X-Parse-Session-Token。

    该 token 本质是「用户企业身份信息 JSON 的 base64 编码」。
    优先读取凭证中已缓存的 req_session_token / sessionToken；
    若无缓存，则自动从 auth 中的当前登录用户信息精确构造并回写缓存。
    """
    auth = load_auth_config()
    cached = auth.get("req_session_token") or auth.get("sessionToken", "")
    if cached:
        return cached

    user_id = auth.get("userId", "")
    if not user_id:
        return ""

    ent_id = auth.get("enterpriseId", "ENT_999999")
    euser_id = auth.get("euserId", "")
    ent_name = auth.get("enterpriseName") or auth.get("tenantName") or ""
    email = auth.get("email", "")
    emp_no = auth.get("employeeNo") or auth.get("username") or auth.get("deputyAccountNumber") or ""
    name = auth.get("name", "")

    payload = {
        "createTime": None,
        "email": email,
        "employeeNo": emp_no,
        "enterpriseCode": ent_id.replace("ENT_", "") if ent_id else "999999",
        "enterpriseId": ent_id,
        "enterpriseName": ent_name,
        "euserId": euser_id,
        "euserType": int(auth.get("euserType", 0) or 0),
        "loginStatus": int(auth.get("loginStatus", 1) or 1),
        "name": name,
        "staffCode": auth.get("staffCode"),
        "userId": user_id,
        "deputyAccountNumber": emp_no,
        "username": emp_no,
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    token = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    save_auth_config({"req_session_token": token, "sessionToken": token})
    return token


def get_auth_ticket() -> str:
    """
    通用单点登录 Ticket 获取接口 (跨子模块 SSO 动态换取凭证)
    各子系统 (需求、流水线、测试等) 均可通过该 Ticket 进行一次性免密鉴权与换 Token
    """
    h = get_moss_headers()
    h["Data-Auth-Appid"] = ""
    h["Data-Auth-Domain"] = ""
    res = make_request("GET", "/fde/moss/web/auth/v1/user/get-auth-ticket", custom_headers=h)
    if res.get("data") and res.get("head", {}).get("respStatus") == "00":
        return str(res.get("data"))
    return ""

