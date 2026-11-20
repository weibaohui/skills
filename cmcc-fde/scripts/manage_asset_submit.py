#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产中心：提交候选资产（支持 SKILL 等），含文件上传。
抓自 microportal 提交资产页（2026-11-20，POST /fde/moss/web/file/auth/v1/upload + /asset/v1/api/v1/assets/create）。

链路：
  1. 上传文件  POST /fde/moss/web/file/auth/v1/upload   multipart: file=<文件>, fileType=fde_asset_02
               返回 data.fileId（即 create 里 files[].storageKey/fileCode）
               ponytail: fileType 枚举只实测了 SKILL 的 zip 走 fde_asset_02；其他类型/文档类别若报错，
               从提交页 FormData.append 钩子里抓真实 fileType 再补。
  2. 创建资产  POST /fde/moss/web/asset/v1/api/v1/assets/create  JSON（结构见 build_payload）

用法：
  python3 manage_asset_submit.py upload --file pkg.zip
  python3 manage_asset_submit.py submit --name "xxx技能包" --type SKILL --version V1.0 \
      --one-liner "一句话简介" --file pkg.zip --space-code G2026000S \
      [--scope SPACE] [--desc 说明] [--ability tool_call] [--draft]
"""
import argparse
import json
import random
import string
import sys
import time
import uuid

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from fde_common import make_request, load_auth_config  # noqa: E402

UPLOAD_PATH = "/fde/moss/web/file/auth/v1/upload"
CREATE_PATH = "/fde/moss/web/asset/v1/api/v1/assets/create"
FILE_TYPE = "fde_asset_02"  # 资产主包（SKILL.md/ZIP）实测值

# —— 中文→slug 映射（2026-11-20 从创建页 Vue 组件 techOptions/industryOptions/sceneOptions/capabilityOptions 实测提取）——
# tagGroup: asset_use_technology / asset_belong_industry / asset_scene / asset_ability_type
TECH_OPTIONS = {
    "数字教育": "digital_edu", "教育云平台": "edu_cloud_platform", "公共服务": "public_service",
    "智慧运维": "intelligent_operation", "DeepSeek": "deepseek", "智能组网": "intelligent_network",
    "智算": "intelligent_compute", "安全": "security", "网络": "network", "机器人": "robot",
    "边缘计算": "edge_compute", "门户集成": "portal_integrate", "物联网": "iot", "大数据": "big_data",
    "无人机": "uav", "BC融合": "bc_fusion", "三业融合": "three_industry_fusion",
    "低空经济": "low_altitude_economy", "车路云": "car_road_cloud", "信创": "info_secure",
    "工业互联网": "industrial_internet", "数据要素": "data_element", "5G": "5g",
    "视频云": "video_cloud", "数字人": "digital_human",
}
INDUSTRY_OPTIONS = {
    "通用场景": "general_scene", "连锁商业": "chain_business", "互联网": "internet",
    "农业文宣": "agri_culture", "医卫": "medical_health", "制造": "manufacture",
    "能源": "energy", "教育": "education", "银行": "bank", "交通": "transportation",
    "证券保险": "securities_insurance", "融合": "fusion", "住建": "construction",
    "政务": "government", "党务": "party_affairs",
}
SCENE_OPTIONS = {
    "审计场景": "audit_scene", "巡视场景": "inspect_scene", "企宣场景": "corp_publicity_scene",
    "安全场景": "security_scene", "党建场景": "party_scene", "办公场景": "office_scene",
    "餐饮AI巡店": "catering_ai_inspect", "电商AIGC": "ecommerce_aigc", "零售AI巡店": "retail_ai_inspect",
    "AI客服": "ai_customer_service", "物联管理": "iot_manage", "语音/短彩信": "voice_sms",
}
ABILITY_OPTIONS = {
    "语义理解": "semantic_understand", "生成文本": "generate_text", "多媒体处理": "multimedia_process",
    "函数调用": "function_call", "校验审核": "verify_audit", "知识问答": "knowledge_qa",
    "流程编排": "process_orchestration", "工具调用": "tool_call", "图像能力": "image_ability",
    "文件解析": "file_parse", "数据查询分析": "data_query_analysis", "代码能力": "code_ability",
    "文本理解": "text_understand", "文本生成": "text_generate",
}
# 资产类型：SKILL/SOLUTION/PRACTICE（PRACTICE=最佳实践，列表实证；解决方案=SOLUTION 报文实证）
TYPE_OPTIONS = {"SKILL": "Skill", "SOLUTION": "解决方案", "PRACTICE": "最佳实践"}


def _request_id():
    """抓包格式：毫秒时间戳 + 大写字母数字混排（服务端疑似只要求唯一性）。"""
    rnd = "".join(random.choices(string.ascii_uppercase + string.digits, k=40))
    return f"{int(time.time() * 1000)}ASPT{rnd}"


def upload_file(file_path):
    """上传文件到文件服务，返回 data.fileId（后续作 storageKey）。"""
    import ssl
    import urllib.request
    import urllib.error
    import os
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    a = load_auth_config()
    filename = os.path.basename(file_path)
    data = open(file_path, "rb").read()
    b = "----WebKitFormBoundary" + uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
            f'Content-Type: application/zip\r\n\r\n').encode() + data + f"\r\n--{b}\r\n".encode()
    body += f'Content-Disposition: form-data; name="fileType"\r\n\r\n{FILE_TYPE}\r\n'.encode()
    body += f"--{b}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={b}",
        "User-Agent": "Mozilla/5.0", "Cookie": a.get("cookie", ""),
    }
    headers.update(a.get("fde_http_header", {}))
    req = urllib.request.Request("https://sti.chinamobile.com" + UPLOAD_PATH, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=600, context=ctx) as resp:
            res = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        res = json.loads(e.read().decode())
    if (res.get("head") or {}).get("respCode") != "000000":
        print(f"[x] 上传失败: {json.dumps(res, ensure_ascii=False)[:300]}")
        sys.exit(1)
    d = res["data"]
    print(f"[✓] 文件已上传: {d['fileName']} ({d['fileSize']}B) fileId={d['fileId'][:20]}…")
    return d


def _slug(label, table):
    """中文标签→tagValue slug；已是合法 slug 则原样返回。"""
    if label in table.values():
        return label
    if label not in table:
        raise SystemExit(f"[x] 未知枚举值: {label}，可选: {'、'.join(table)}")
    return table[label]


def build_payload(name, asset_type, version, one_liner, file_info, space_code,
                  scope="GLOBAL", desc="", ability="工具调用", tech=None, industry=None,
                  scene=None, advantage="", target_customer="", draft=False):
    """构造 assets/create 的完整 JSON（字段序与抓包一致）。"""
    a = load_auth_config()
    tags = []
    # ponytail: 实测 SOLUTION/PRACTICE 发布时 asset_ability_type 报「未知的标签组」，
    # 能力类型仅 SKILL 有效；如平台放开再补
    if asset_type == "SKILL":
        for lb in (ability and [ability] or []):
            tags.append({"tagGroup": "asset_ability_type", "tagValue": _slug(lb, ABILITY_OPTIONS)})
    for group, table, labels in (("asset_use_technology", TECH_OPTIONS, tech or []),
                                 ("asset_belong_industry", INDUSTRY_OPTIONS, industry or []),
                                 ("asset_scene", SCENE_OPTIONS, scene or [])):
        for lb in (labels or []):
            tags.append({"tagGroup": group, "tagValue": _slug(lb, table)})
    return {
        "head": {"requestId": _request_id()},
        "data": {
            "assetName": name,
            "assetType": asset_type,           # 实测 SKILL；解决方案/最佳实践待验证
            "versionNo": version,
            "oneLiner": one_liner,
            "assetDesc": desc,
            "openScope": scope,                # 实测 GLOBAL；其他取值 SPACE/ORG/PERSONAL 按页面语义推断
            "tags": tags,
            "files": [{
                "fileName": file_info["fileName"], "fileSize": file_info["fileSize"],
                "storageKey": file_info["fileId"], "fileCode": file_info["fileId"],
                "fileCategory": "MAIN", "bizType": "",
            }],
            "jointDev": 0,
            "advantageDesc": advantage, "targetCustomer": target_customer, "triggerCondition": "",
            "landingProvinces": [], "landingProjectCount": None, "landingProjectDesc": "",
            "units": [{                       # 资产提供单位：默认当前用户所属企业，联系人为空
                "unitType": "PROVIDER", "unitName": a.get("enterpriseName", ""),
                "unitCode": a.get("enterpriseId", "ENT_999999"),
                "contactEuserId": "", "contactName": "", "contactPhone": "", "contactEmail": "",
            }],
            "subSkills": [], "mcps": [],
            "saveDraft": draft,               # true=暂存 false=直接提交
            "spaceCode": space_code,
        },
    }


def submit(payload):
    r = make_request("POST", CREATE_PATH, data=payload)
    head = (r.get("head") or {})
    # create 成功返回 respCode="00"（注意 upload 才是 "000000"），data=资产ID
    if head.get("respCode") not in ("00", "000000") or not r.get("data"):
        print(f"[x] 创建失败: {json.dumps(r, ensure_ascii=False)[:400]}")
        sys.exit(1)
    print(f"[✓] 资产已提交: {payload['data']['assetName']} 资产ID={r['data']} saveDraft={payload['data']['saveDraft']}")
    return r


def main():
    p = argparse.ArgumentParser(description="资产中心提交候选资产（SKILL 等）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("upload", help="仅上传文件，返回 fileId")
    sp.add_argument("--file", required=True)

    sp = sub.add_parser("submit", help="上传文件并创建资产")
    sp.add_argument("--name", required=True, help="资产名称")
    sp.add_argument("--type", default="SKILL", choices=list(TYPE_OPTIONS), help="SKILL/SOLUTION(解决方案)/PRACTICE(最佳实践)")
    sp.add_argument("--version", default="V1.0")
    sp.add_argument("--one-liner", required=True, help="一句话简介（≤50字）")
    sp.add_argument("--file", required=True, help="主包文件（zip/md）")
    sp.add_argument("--space-code", required=True, help="归属空间编码，如 G2026000S")
    sp.add_argument("--scope", default="GLOBAL", choices=["GLOBAL", "ORG", "SPACE", "PERSONAL"])
    sp.add_argument("--desc", default="")
    sp.add_argument("--ability", default="工具调用", help="能力类型（Skill 用，中文或 slug）")
    sp.add_argument("--tech", default="", help="使用技术（解决方案/最佳实践必填，逗号分隔，中文）")
    sp.add_argument("--industry", default="", help="归属行业（解决方案/最佳实践必填，逗号分隔，中文）")
    sp.add_argument("--scene", default="", help="适用场景（选填，逗号分隔）")
    sp.add_argument("--advantage", default="", help="方案优势（选填）")
    sp.add_argument("--target-customer", default="", help="目标客户（选填）")
    sp.add_argument("--draft", action="store_true", help="只暂存不提交")

    args = p.parse_args()
    if args.cmd == "upload":
        upload_file(args.file)
    elif args.cmd == "submit":
        if args.type in ("SOLUTION", "PRACTICE") and (not args.tech or not args.industry):
            p.error("解决方案/最佳实践 必填 --tech 和 --industry")
        fi = upload_file(args.file)
        payload = build_payload(args.name, args.type, args.version, args.one_liner,
                                fi, args.space_code, scope=args.scope, desc=args.desc,
                                ability=args.ability,
                                tech=[t.strip() for t in args.tech.split(",") if t.strip()],
                                industry=[t.strip() for t in args.industry.split(",") if t.strip()],
                                scene=[t.strip() for t in args.scene.split(",") if t.strip()],
                                advantage=args.advantage, target_customer=args.target_customer,
                                draft=args.draft)
        submit(payload)


if __name__ == "__main__":
    main()
