---
name: cmcc-fde
display_name: 中国移动灵畿科研平台（FDE）自动化助手
display_name_en: CMCC Lingji FDE Platform Automation Assistant
description: >-
  中国移动“灵畿”科研平台 (FDE) 自动化工具集与流程指南。当用户提及 FDE、灵畿、中国移动科研平台、
  登录凭证/会话采集、代码仓库与永久令牌 (Private Token)、研发空间、敏捷需求/缺陷增删改查与字段编辑、
  知识库 Wiki 文档、科研资产、灵宝 AI 智能体等关键词时应使用本技能。
  提供统一登录会话初始化、代码仓库永久令牌管理、企业代码仓库免克隆在线检索与读取、
  知识库文档在线阅读/上传导入与多格式导出下载、科研资产中心检索与统计、灵宝 AI 原生智能体互动，
  以及研发空间与需求/缺陷全生命周期管理 (Item CRUD/状态流转/任意字段编辑)。
  内置小白用户全自动凭证采集（免 F12 抓包、本地生成子系统 Token 与自动签发永久代码令牌）与单点登录 Ticket 机制。
description_zh: >-
  一站式自动化中国移动“灵畿”科研平台 (FDE)：涵盖登录凭证采集、代码仓库与永久令牌、
  研发空间、需求与缺陷的增删改查及字段编辑、知识库文档、科研资产检索与灵宝 AI 智能体互动。
description_en: >-
  An all-in-one automation toolkit for CMCC Lingji FDE platform: credential collection, code repositories
  and permanent tokens, R&D spaces, full CRUD and field editing of demands and bugs, Wiki documents,
  research asset search, and Lingji AI agent interaction.
version: 2.0.2
author: "中国移动"
allowed-tools: Bash
examples_zh:
  - "帮我采集 FDE 登录凭证并签发永久代码令牌"
  - "列出 G2026000S 空间的需求，并把某条需求优先级改成 P1、负责人设为张三"
  - "在线读取代码仓库的目录树和源码，或把某篇知识库文档导出成 PDF"
examples_en:
  - "Collect FDE login credentials and issue a permanent code token"
  - "List demands in space G2026000S and update one to priority P1 with an assignee"
  - "Browse a repository tree online, or export a Wiki document to PDF"
---

# 中国移动“灵畿”科研平台 (FDE) 技能指南

本技能为中国移动“灵畿”科研平台（FDE）提供完整的 Python 命令行工具集与操作流程。所有脚本**高度复用同一个鉴权文件 (`fde_auth.json`)**，除可选的知识库 `brotli` 模块外，其余脚本仅需 Python 3 标准库即可直接运行。

> [!IMPORTANT]
> **小白用户零门槛（Zero-Friction）设计原则**：
> - **严禁要求非技术用户按 F12 抓包查找 Cookie、Token 或 Session Key**。
> - 首次使用时，只需执行 `python3 scripts/fetch_browser_auth.py interactive`，在弹出的 Chrome 窗口中完成一次手机号短信登录，脚本后台将**全自动**串联：
>   1. 自动抓取主平台 httpOnly `Cookie` 与 `MOSS-TOKEN` (JWT)；
>   2. 自动单点登录并静默预热需求子系统 (`fde-req-web`)，捕获专属 `sessionToken`；
>   3. 自动调用 MOSS 单点登录 Ticket 接口验证身份并补全企业与用户信息；
>   4. 自动突破前端 20 年限制，静默签发永久有效 (`permanent`) 的代码仓库 Private Token 并写入配置。
> - 一次登录，全套技能（代码、文档、需求、资产、智能体）永久/长期就绪。

---

## 平台常用入口与登录地址

> [!IMPORTANT]
> **⭐ 唯一正确的 FDE 登录页（本 skill 浏览器自动化的唯一弹出地址）**：
> **https://sti.chinamobile.com/fde/micrologin/#/login**
> - `fetch_browser_auth.py open / interactive` **只会打开这一个地址**，凭证采集阶段也只从当前页面读 Cookie，**不会弹出任何其它子系统页面**。
> - 下表中除登录页以外的地址都是**登录成功后的落地页/业务入口**，仅供人工浏览器访问或接口参考，**绝不可作为登录页直接弹出**（例如 `/moss/microhome/#/home` 曾因被误设为登录页导致登录态异常，已废弃修正）。

| 类别 | 地址 | 用途 |
| :--- | :--- | :--- |
| ⭐ **唯一登录页** | [https://sti.chinamobile.com/fde/micrologin/#/login](https://sti.chinamobile.com/fde/micrologin/#/login) | **本 skill 唯一弹出的页面**，人工完成短信/验证码登录 |
| 个人工作台（登录后） | [https://sti.chinamobile.com/fde/microportal/#/workbench](https://sti.chinamobile.com/fde/microportal/#/workbench) | 登录成功后的落地页，人工访问 |
| 研发空间列表（登录后） | [https://sti.chinamobile.com/fde/microportal/#/dev-space](https://sti.chinamobile.com/fde/microportal/#/dev-space) | 业务入口，人工访问 |
| 需求与看板（登录后） | [https://sti.chinamobile.com/fde/base/fde-req-web/#/workspace/boards/req](https://sti.chinamobile.com/fde/base/fde-req-web/#/workspace/boards/req) | 业务入口，人工访问 |
| 代码子系统（登录后） | [https://sti.chinamobile.com/fde/base/fde-code-web/](https://sti.chinamobile.com/fde/base/fde-code-web/) | 业务入口（网页 UI），人工访问 |
| 代码令牌管理页 | [https://sti.chinamobile.com/fde/base/fde-code-web/private_token](https://sti.chinamobile.com/fde/base/fde-code-web/private_token) | 业务入口，人工访问 |
| 知识库系统 | [https://sti.chinamobile.com/fde-wiki-web/](https://sti.chinamobile.com/fde-wiki-web/) | 业务入口，人工访问 |

---

## 快速导航与脚本清单

| 脚本文件 | 功能说明 | 核心命令示例 |
| :--- | :--- | :--- |
| [fetch_browser_auth.py](./scripts/fetch_browser_auth.py) | **【首选零门槛】浏览器全量凭证自动采集**：拉起 Chrome，用户手机验证码登录后，全自动捕获 Cookie、MOSS-TOKEN、需求专属 sessionToken 并自动签发永久代码令牌 | `python3 fetch_browser_auth.py interactive` |
| [auth_login.py](./scripts/auth_login.py) | **登录会话初始化与验证**：使用现有 Cookie/Token 校验企业与用户身份档案并持久化同步 | `python3 auth_login.py --check` |
| [manage_token.py](./scripts/manage_token.py) | **代码仓库私人令牌管理**：直接调用后台 API 突破前端日历限制，创建永久有效 (`permanent`) 的全权限 Token | `python3 manage_token.py create --name AI-Token` |
| [manage_spaces.py](./scripts/manage_spaces.py) | **研发空间深度管理**：列出当前用户所有空间（包含空间唯一 ID `spaceId`、空间编码 `spaceCode`、名称与角色），支持多空间交互式选择与默认空间持久化切换 | `python3 manage_spaces.py list`<br>`python3 manage_spaces.py select`<br>`python3 manage_spaces.py current` |
| [manage_demands.py](./scripts/manage_demands.py) | **敏捷需求深度管理**：需求清单、新建、状态流转、删除，以及任意详情字段编辑（`update --set`）。**所有子命令必须显式带 `--space <编码>`，无默认空间记忆**（不带即报错退出，2026-11-20 实测） | `python3 manage_demands.py list --space G2026000S`<br>`python3 manage_demands.py update --space G2026000S --id <ID> --set 优先级=P1` |
| [manage_bugs.py](./scripts/manage_bugs.py) | **敏捷缺陷深度管理**：与需求共用端点，固化缺陷类型；缺陷清单、新建、状态流转、删除、任意详情字段编辑。**同上，所有子命令必须显式带 `--space <编码>`** | `python3 manage_bugs.py list --space G2026000S`<br>`python3 manage_bugs.py update --space G2026000S --id <ID> --set 严重程度=3-一般错误` |
| [req_fields.py](./scripts/req_fields.py) | **字段转换公共模块**：`update --set` 的字段别名归一化、类型转换（UUID/数组/富文本/用户对象）与写入后读回验证，被上述两个脚本共用（不单独调用） | — |
| [manage_repos.py](./scripts/manage_repos.py) | **代码仓库深度操作**：新建仓库、浏览仓库、分支列表、免克隆直接在线遍历文件树与读取源码、合并请求 (PR) 追踪、成员权限与免密 Git 克隆 | `python3 manage_repos.py create --name xx --path xx`<br>`python3 manage_repos.py branches --path 64`<br>`python3 manage_repos.py read --path 64 --file README.md` |
| [manage_assets.py](./scripts/manage_assets.py) | **科研资产中心检索**：全景统计、科技方案/技能/实践资产分页搜索与详情归档查询 | `python3 manage_assets.py search --keyword 智能` |
| [manage_agent.py](./scripts/manage_agent.py) | **灵宝 AI 智能体协同**：查询可用智能体列表、历史会话问答追踪与异步派发任务 | `python3 manage_agent.py list`<br>`python3 manage_agent.py run --agent-id "quick-qa" --prompt "分析报告"` |
| [manage_wiki.py](./scripts/manage_wiki.py) | **知识库文档与空间管理**：空间列表、目录树深度展开、富文本正文在线还原读取、文档导出下载 (Word/PDF/MD/HTML)、本地文件上传导入、页面创建与删除 | `python3 manage_wiki.py spaces`<br>`python3 manage_wiki.py download --doc-id 1749 --format pdf`<br>`python3 manage_wiki.py upload --space-id 87 --file doc.md` |
| [manage_item_wiki.py](./scripts/manage_item_wiki.py) | **事项关联知识（任意文件上传）**：把本地文件（含 zip 等导入通道不支持的格式）上传到知识库选定目录并关联到需求/事项；`dirs` 列目录树供选择落点、支持查询/取消关联。上传 path 目录段按目录**标题**匹配（脚本自动解析），>5MB 自动分片 | `python3 manage_item_wiki.py dirs --space-key Lingjizhishi`<br>`python3 manage_item_wiki.py upload --space-key Lingjizhishi --parent-page-id 1742 --file pkg.zip --item-key G2026000S-34`<br>`python3 manage_item_wiki.py list --item-key G2026000S-34` |
| [manage_asset_submit.py](./scripts/manage_asset_submit.py) | **资产中心提交候选资产（Skill/解决方案/最佳实践）**：文件上传（fileId→storageKey）+ 创建资产全链路；三类型必填差异、中文标签自动转 slug、暂存模式；能力类型标签仅 SKILL 合法 | `python3 manage_asset_submit.py upload --file pkg.zip`<br>`python3 manage_asset_submit.py submit --name "xx技能包" --type SKILL --one-liner "一句话" --file pkg.zip --space-code G2026000S --scope SPACE` |

---

## 登录与能力手册

> 登录凭证初始化是唯一的线性前置步骤（能力一）；此后各「能力」章节相互独立、无先后顺序，按需使用。

### 第一步（唯一前置步骤）：初始化或刷新登录凭证

#### 方式 A（强烈推荐，适合所有用户与小白）：全自动浏览器凭证采集

当本地尚未配置凭据，或凭证过期时，**统一使用 [fetch_browser_auth.py](./scripts/fetch_browser_auth.py)** 进行一键采集。
底层基于系统 Chrome 与 `playwright-browser-use` 自动化工具，由人工仅负责一次短信/图形验证码输入，脚本全自动完成一切技术细节：

```bash
# 一步到位交互式采集（推荐）：
# 1. 自动启动系统 Chrome，只打开唯一登录页 micrologin/#/login
# 2. 提示用户输入手机号和验证码
# 3. 用户在终端按回车，脚本从当前页面采集全量凭证（不弹出其它页面）
python3 scripts/fetch_browser_auth.py interactive

# 也可以分步执行：
python3 scripts/fetch_browser_auth.py open   # 仅拉起并打开唯一登录页
python3 scripts/fetch_browser_auth.py fetch  # 登录后自动轮询抓取并采集凭证
python3 scripts/fetch_browser_auth.py status # 仅检查当前浏览器登录状态
```

> [!IMPORTANT]
> **浏览器弹出的页面地址纪律（务必遵守）**：
> - `fetch_browser_auth.py` **只弹出 `https://sti.chinamobile.com/fde/micrologin/#/login` 这一个登录页**，采集凭证时只从当前已登录页面读 Cookie。
> - **不会、也不应弹出** `/moss/microhome/#/home`（旧错误配置，已废弃）、`fde-req-web` 需求看板等任何其它页面——那些是登录后的业务落地页，直接打开会导致登录态异常。
> - 需求子系统 `sessionToken` 已由 `fde_common.get_req_session_token()` **本地身份生成**，无需浏览器预热导航。

> [!NOTE]
> **凭证采集与动态 Token 机制**：
> 1. 主平台工作台使用 `MOSS_SESSION` Cookie 与 `MOSS-TOKEN` JWT。
> 2. 需求子系统 `sessionToken` 为无签名身份 JSON，本地即可生成（`get_req_session_token`），不依赖浏览器抓包。
> 3. 脚本从登录后的当前页面读取全部 Cookie（含 sessionToken 冗余备份）写入 `fde_auth.json`。
> 4. 脚本会自动调用 `auth_login.py --check` 校验身份，并在代码系统自动签发一个 2046 年过期的永久代码 Token。普通用户完全不需要关心这些内部机制。

#### 方式 B：手动提供 Cookie（高级开发者或已有现有会话）

若开发者已有浏览器中登录的 Cookie 字符串：

```bash
# 传入 Cookie 验证并自动提取所属企业 (ENT_999999)、用户 ID 等信息
python3 scripts/auth_login.py --cookie "MOSS_SESSION=...; ..."

# 检查当前本地保存的会话状态
python3 scripts/auth_login.py --check
```

---

### 能力：一键创建全功能永久代码令牌 (`manage_token.py`)

底层代码系统限制前端日历只能选择到最近 20 年，但通过 [manage_token.py](./scripts/manage_token.py) 可以直接突破限制，自动创建一个系统识别为 **`permanent`（永久有效）** 的全权限代码令牌：

```bash
# 查看已有令牌列表
python3 scripts/manage_token.py list

# 创建永久全权限 Token (默认 2046-12-31，系统自动判定为 permanent)
python3 scripts/manage_token.py create --name "AI-Permanent-Token"

# 删除无用令牌
python3 scripts/manage_token.py delete --id <令牌ID>
```
> [!TIP]
> 创建成功后，脚本会自动把生成的 `private_token` 写回鉴权配置中，供后续代码仓库拉取与 Git 操作无缝复用。

---

### 能力：研发空间查看、选择与需求/缺陷管理 (`manage_spaces.py` / `manage_demands.py` / `manage_bugs.py`)

灵畿平台的敏捷协同由研发空间（Dev Space）与敏捷需求子系统（底层由 Proxima Core / Gitee Team 引擎驱动）承载。系统提供了专有的研发空间管理工具 [manage_spaces.py](./scripts/manage_spaces.py) 与敏捷需求工具 [manage_demands.py](./scripts/manage_demands.py)：

#### 1. 研发空间查看与多空间自主选择 (`manage_spaces.py`)
当用户属于多个研发空间时，**系统坚决不擅自使用第一个空间，必须由用户自主选择或指定**：

```bash
# 1. 表格列出当前用户拥有的所有研发空间（包含空间唯一 ID spaceId、空间编码 spaceCode、名称、负责人与状态）
python3 scripts/manage_spaces.py list

# 2. 交互式选择当前要操作的研发空间（输入序号即可切换并持久化保存为默认空间）
python3 scripts/manage_spaces.py select

# 3. 命令行直接指定并保存默认研发空间 (通过空间编码如 G2026000S 或空间 ID)
python3 scripts/manage_spaces.py set --code G2026000S

# 4. 查看当前生效的默认研发空间
python3 scripts/manage_spaces.py current
```

#### 2. 空间敏捷需求深度管理 (`manage_demands.py`)
在指定空间下进行工作项的增删改查。

**⚠️ 硬性纪律（实测确认，agent 执行前必须自查）**：`manage_demands.py` / `manage_bugs.py` 的所有子命令**不存在默认空间记忆**——不带 `--space` 一律报 `[x] 未指定空间` 直接退出（2026-11-20 回归实测）。SKILL 文档虽写有"默认空间"说法，实测该机制无效。执行每条命令前必须显式携带 `--space <spaceCode>`（先 `spaces` 子命令列出可用编码），不带就执行属违规操作。

```bash
# 0. 列出研发空间（编码 spaceCode 供后续 --space 使用）
python3 scripts/manage_demands.py spaces

# 1. 查询需求列表（必须显式带 --space，无默认空间）
python3 scripts/manage_demands.py list --space G2026000S

# 2. 创建新需求
python3 scripts/manage_demands.py create --space G2026000S --title "新增性能监控模块" --desc "支持秒级指标采集与可视化看板"

# 3. 更改需求状态（状态名在工作流节点中动态解析）
python3 scripts/manage_demands.py update-status --space G2026000S --id <需求ID> --status "开发"

# 4. 删除指定需求
python3 scripts/manage_demands.py delete --space G2026000S --id <需求ID>

# 5. 编辑任意详情字段（--set 字段=值，可多次；详见下方字段参考）
python3 scripts/manage_demands.py update --space G2026000S --id <需求ID> \
  --set "标题=新标题" --set "优先级=P1" --set "严重程度=1-产品不可用" \
  --set "描述=补充的描述内容" --set "负责人=周志君"
```

> [!NOTE]
> **凭据与真实网关端点（2026-11 重写版）**：
> - `manage_demands.py` 的 sessionToken 统一由 `fde_common.get_req_session_token()` **基于 `fde_auth.json` 中的本地身份字段生成**，无需任何浏览器抓包或预热操作。
> - 研发空间列表端点：`GET /fde/moss/web/desktop/v1/api/v1/user/space/list?pageNo=1&pageSize=50`（必须携带分页参数）。
> - 需求网关端点（实测确认）：
>   - 列表：`POST /fde/moss/web/fde-req/api/team/parse/api/search/hierarchy`（IQL 查询）
>   - 创建：`POST /fde/moss/web/fde-req/api/team/parse/api/v2/items`（workspace / itemType 为 Parse Pointer）
>   - 改状态：`PUT /fde/moss/web/fde-req/api/team/parse/api/v2/items/{id}`（status 为 Parse Pointer）
>   - 删除：`POST /fde/moss/web/fde-req/api/team/parse/functions/deleteItems`（Parse Cloud 函数，注意无第二层 `/api`）
> - 空间码、itemType、status 在运行期动态解析为内部 objectId，不写死任何 ID。

#### 3. 敏捷缺陷管理 (`manage_bugs.py`)
缺陷在底层就是 `itemType = 缺陷 (quexian)` 的工作项，与需求共用同一套网关端点。`manage_bugs.py` 复用需求脚本的已验证逻辑，固化缺陷类型并提供基本增删改查：

```bash
# 1. 查询缺陷列表（IQL 按类型过滤: 类型 = '缺陷'）
python3 scripts/manage_bugs.py list --space G2026000S

# 2. 新建缺陷（itemType 固定为 quexian，无需指定 --type）
python3 scripts/manage_bugs.py create --space G2026000S --title "登录页按钮错位" --desc "在移动端点击无响应"

# 3. 更改缺陷状态（缺陷工作流：新建/已确认/修复中/已修复/验证中/完成/取消）
python3 scripts/manage_bugs.py update-status --space G2026000S --id <缺陷ID> --status "已确认"

# 4. 删除指定缺陷
python3 scripts/manage_bugs.py delete --space G2026000S --id <缺陷ID>

# 5. 编辑任意详情字段（--set 字段=值，可多次；详见下方字段参考）
python3 scripts/manage_bugs.py update --space G2026000S --id <缺陷ID> \
  --set "标题=新标题" --set "优先级=P1" --set "严重程度=3-一般错误" \
  --set "描述=复现步骤见附件" --set "负责人=周志君"
```

> [!NOTE]
> - 缺陷列表 IQL 为 `(所属空间 = '空间名') and (类型 = '缺陷') order by 创建时间 desc`，经实测精确返回缺陷项（注意 `工作项类型` 字段名不存在，会报 IQL 错误，须用 `类型` 或 `itemType`）。
> - 缺陷有独立的状态工作流节点（新建 → 已确认 → 修复中 → 已修复 → 验证中 → 完成），`update-status` 会从 `workflows/item/{id}` 动态解析 statusId。

#### 4. 详情字段编辑（`update` 命令，两个脚本通用）

`manage_demands.py` 与 `manage_bugs.py` 均支持 `update --id <ID> --set 字段=值 --set 字段=值 ...`，一次可改任意多个字段，脚本自动把中文/别名转为网关字段并按类型转换，**写入后会读回逐项核对**（网关常返回成功但实际未落库）。

**可编辑字段参考**（中文名与英文名均可）：

| 字段（别名） | 值格式 | 示例 |
| :--- | :--- | :--- |
| 标题 name | 字符串 | `--set "标题=新标题"` |
| 优先级 priority | P0–P5（自动转 UUID） | `--set "优先级=P1"` |
| 严重程度 severity | 选项文字 | `--set "严重程度=3-一般错误"`（可选：1-产品不可用 / 2-主要功能错误 / 3-一般错误 / 4-轻微错误） |
| 描述 description / requirement | 纯文本（自动转富文本） | `--set "描述=补充内容"` |
| 复现步骤 StepReproduce | 纯文本 | `--set "复现步骤=打开页面点按钮"` |
| 验收标准 acceptanceCriteria | 纯文本 | `--set "验收标准='响应<1秒'"` |
| 责任人 assignee / 负责人 / 关注人 watchers | 姓名或账号，多个用逗号 | `--set "责任人=魏宝辉"` |
| 处理人 flowHandler | 姓名或账号，多个用逗号 | `--set "处理人=魏宝辉"`（注：`ItemHandler`/当前处理人为工作流系统字段，写入无效；界面"处理人"对应 `flowHandler`） |
| 标签 Tag | 标签名，多个用逗号 | `--set "标签=产品,客户关注"`（可选值见字段定义） |
| 迭代 sprint / 故事点 StoryPoint / 版本 version | 字符串 | `--set "迭代=2026-Sprint1"` |
| 计划开始/结束时间 PlanStartTime / PlanFinishTime | `YYYY-MM-DD`（自动转毫秒时间戳，口径为当天 00:00 UTC+8） | `--set "计划结束时间=2026-11-27"`（完成时限即设此字段） |

> [!IMPORTANT]
> - 字段转换规则由公共模块 `scripts/req_fields.py` 统一实现：只有 `name` 写在顶层，其余字段一律写入 `values`；选项/人员/标签字段会转成数组，描述类转成 Slate 富文本。
> - 人员解析会先从空间已有事项收集成员，再补充 `/users` 列表（网关忽略 `where` 过滤，且 `/users` 前若干条可能不含全部成员），因此传姓名须是空间内真实成员。
> - 未知字段会报错并提示可用字段，不会静默忽略。

---

### 能力：深度查询与操作代码仓库 (`manage_repos.py`)

使用 [manage_repos.py](./scripts/manage_repos.py) 浏览、检索以及直接读取企业代码仓库：

```bash
# 1. 分页列出企业下所有代码仓库
python3 scripts/manage_repos.py list --page 1 --size 20

# 2. 查询指定仓库的所有分支 (支持传入仓库 ID 或完整路径)
python3 scripts/manage_repos.py branches --path 64

# 3. 在线遍历指定分支的文件目录树 (无需 Git Clone)
python3 scripts/manage_repos.py tree --path 64 --ref master

# 4. 在线直接读取文件源码内容
python3 scripts/manage_repos.py read --path 64 --file hello_commit_test.py

# 5. 查询仓库合并请求 (Pull Requests) 与评审状态
python3 scripts/manage_repos.py prs --path 64

# 6. 查询协作开发人员与角色权限
python3 scripts/manage_repos.py members --path 64

# 7. 获取免密 Git HTTP 克隆命令
python3 scripts/manage_repos.py clone-info --path 64

# 8. 新建代码仓库（复刻 UI 新建代码仓库表单，2026-11-20 实测）
python3 scripts/manage_repos.py create --name "my-repo" --path "my-repo" --desc "简介"
python3 scripts/manage_repos.py create --name "open-repo" --path "open-repo" --public   # 企业内部开源
```

> [!NOTE]
> **代码仓库 Git 凭证说明**（2026-11-20 实测修正）：平台 Git HTTP 采用 Basic 认证 + Private Token，底层实为 Gitee 企业版：
> - **用户名 = `fde_auth.json` 中的 `username`（SSO 登录账号，如 `weibaohui@hq.cmcc`）**；实测 `oauth2` 也能通过（服务端只认 Token、不校验用户名），但脚本统一用 SSO 账号；`@` 已自动 URL 编码为 `%40`；
> - **密码 = `manage_token.py` 签发的 Private Token**；
> - **Git HTTP 入口路径为 `/fde/code/<full_path>.git`**（不是网页子系统入口 `/fde/base/fde-code-web/`），完整命令形如 `git clone https://weibaohui%40hq.cmcc:<private_token>@sti.chinamobile.com/fde/code/<full_path>.git`，由 `clone-info` 一键生成；
> - 实测凭证矩阵：正确用户名+Token → HTTP 200；错误密码 → 404 "Incorrect username or password"；无认证 → 401。

---

### 能力：资产中心全景统计与检索 (`manage_assets.py`)

使用 [manage_assets.py](./scripts/manage_assets.py) 检索平台沉淀的科技方案、技能与实践资产：

```bash
# 查看全局资产与下载统计
python3 scripts/manage_assets.py stats

# 按类别分页检索资产 (类别: SOLUTION / SKILL / PRACTICE)
python3 scripts/manage_assets.py search --keyword "网络" --type SOLUTION

# 查看资产完整档案、研发人与挂载交付物列表
python3 scripts/manage_assets.py detail --id <资产ID>
```

---

### 能力：调用原生“灵宝”AI 智能体 (`manage_agent.py`)

使用 [manage_agent.py](./scripts/manage_agent.py) 与移动“灵宝”AI 智能体协同：

```bash
# 查询已部署的专业智能体 (quick-qa, visit-strategist, opportunity-analyst)
python3 scripts/manage_agent.py list

# 查看最新历史会话列表
python3 scripts/manage_agent.py sessions --page 1 --size 10

# 查看指定会话的完整历史问答
python3 scripts/manage_agent.py messages --session-id <会话ID>

# 下发任务调用智能体 (异步派发，返回 status: CREATED 即表示成功)
python3 scripts/manage_agent.py run --agent-id "visit-strategist" --prompt "请分析某省移动大客户拜访方案"
```

---

### 能力：知识库 (Wiki) 深度管理与文档上传下载 (`manage_wiki.py`)

使用 [manage_wiki.py](./scripts/manage_wiki.py) 进行知识库空间检索、目录树查看、在线正文阅读、文档导出下载及本地文件上传导入：

> [!IMPORTANT]
> 知识库网关默认采用 Brotli 数据压缩，若未安装 `brotli` 模块可能导致文档列表静默为空。使用 Wiki 功能前请执行：`python3 -m pip install brotli`。

```bash
# 1. 列出所有可访问的知识库空间 (包含个人文档库与企业共享知识库)
python3 scripts/manage_wiki.py spaces

# 2. 查询指定空间下的完整文档目录树
python3 scripts/manage_wiki.py tree --space-id 88

# 2b. 展开某个文件夹查看其子文档 (如"操作手册"文件夹 ID=1742)
python3 scripts/manage_wiki.py tree --space-id 88 --parent 1742

# 3. 在线读取指定文档的元数据与还原后的结构化正文
python3 scripts/manage_wiki.py read --space-id 88 --doc-id 1749

# 4. 导出并下载知识库文档 (支持 word / pdf / markdown / html)
python3 scripts/manage_wiki.py download --doc-id 1749 --format pdf --output ./faq.pdf
python3 scripts/manage_wiki.py download --doc-id 1749 --format word --output ./faq.docx

# 5. 上传并导入本地文件至知识库空间 (支持 .md, .docx, .txt 等)
python3 scripts/manage_wiki.py upload --space-id 87 --file ./my_note.md --title "自动化指南"

# 6. 在指定空间在线创建原生富文本页面
python3 scripts/manage_wiki.py create --space-id 87 --title "新建在线页面" --content "初始页面段落内容"

# 7. 批量删除指定空间下的文档
python3 scripts/manage_wiki.py delete --space-id 87 --doc-ids 1750,1751
```

### 能力：事项关联知识——任意文件（含 zip）上传并关联到需求/缺陷 (`manage_item_wiki.py`)

使用 [manage_item_wiki.py](./scripts/manage_item_wiki.py)。这是需求页「上传知识」按钮的接口级复刻（plugin_zyd_item_associate_wiki 链路），**与 `manage_wiki.py upload` 的区别**：后者走 doc_import 转换通道（只支持 word/pdf 转 doc、md/txt 转页面），本脚本走 `doc-open-api/CMCC/{spaceKey}/files/upload` 原始文件通道 + webtrigger 关联，**任何格式都能传**（zip/py/xlsx 等均实测可行），且能直接挂到需求/缺陷单上。

> [!IMPORTANT]
> - **上传目录必须由用户选定，脚本不默认落任何目录**：不带 `--parent-page-id` 时自动列出空间目录树供选择（或用 `dirs` 子命令单独查看）。
> - **上传 path 的目录段按【目录标题】匹配**：脚本内部先把 `--parent-page-id` 解析成目录标题再拼 path（如 `/操作手册/xx.zip`）。直接传数字会被当成"名为该数字的文件夹"而在根目录新建错误文件夹（实测踩过：传 `/1742/x` 造出了名为 1742 的目录）。
> - 同目录同名文件重复上传报「文档已存在」（HTTP 400），这是服务端判重，先 `disassociate` 或换名。
> - >5MB 自动分片（totalChunks/chunkIndex/uploadId），与前端插件一致。
> - `token` 请求头的出处与再获取方法见 `manage_item_wiki.py` 内 `API_TOKEN` 上方的注释块（插件 bundle 兜底值，平台换配置需从页面控制台重新抓取；`fde_auth.json` 加 `open_api_token` 字段可覆盖）。

```bash
# 1. 查看空间目录树，选定上传落点（取目录的 id）
python3 scripts/manage_item_wiki.py dirs --space-key Lingjizhishi

# 2. 上传文件到选定目录，并自动关联到需求（--item-key 可省略则只上传不关联）
#    不带 --parent-page-id 时会列出目录树并退出，提示选择
python3 scripts/manage_item_wiki.py upload \
  --space-key Lingjizhishi --parent-page-id 1742 \
  --file ./cmcc-fde.zip --item-key G2026000S-34

# 3. 查询某个需求/缺陷已关联的知识清单（返回 objectId 供取消关联用）
python3 scripts/manage_item_wiki.py list --item-key G2026000S-34

# 4. 取消关联（ objectId 来自 list 输出；只解除关联，不删知识库文件）
python3 scripts/manage_item_wiki.py disassociate --object-id KCMHdtm6KF
```

实战案例：需求 G2026000S-34（wiki管理功能增强）的参考实现 `manage_item_wiki.py` 已传至 Lingjizhishi/操作手册（pageId=1764）并关联。

### 能力：资产中心提交候选资产（Skill 等）(`manage_asset_submit.py`)

入口：空间内 资产管理 → 提交资产（`/fde/microportal/#/asset-center/create?spaceCode=`）。脚本复刻其两个接口：

1. **文件上传** `POST /fde/moss/web/file/auth/v1/upload`：multipart `file=<文件>` + `fileType=fde_asset_02`（SKILL 主包实测值），返回 `data.fileId` 即创建报文里的 `storageKey/fileCode`。
2. **创建资产** `POST /fde/moss/web/asset/v1/api/v1/assets/create`：JSON 报文，`head.requestId`=毫秒时间戳+随机串；`data` 含 assetName / assetType(SKILL) / versionNo / oneLiner(≤50字) / openScope(GLOBAL|ORG|SPACE|PERSONAL，实测 GLOBAL) / tags[{tagGroup:"asset_ability_type",tagValue:"tool_call"}] / files[] / units[{unitType:"PROVIDER",unitCode:"ENT_999999"}] / saveDraft / spaceCode。**成功判定 respCode=="00"（upload 才是 "000000"）**，`data`=资产ID。

三种资产类型的填法差异（2026-11-20 全量实测，assetType 为 create 报文里的真实取值）：

| 类型 | assetType | 必填字段 | 文件标签 | 特有选填 |
| :--- | :--- | :--- | :--- | :--- |
| Skill | `SKILL` | 名称/版本/一句话简介/能力类型/开放范围/文件 | SKILL.md / ZIP 文件 | 触发条件、子技能、MCP 工具 |
| 解决方案 | `SOLUTION` | 名称/版本/一句话简介/**使用技术(多选)**/**归属行业(多选)**/开放范围/文件 | 方案包 / 文档 | 资产说明、方案优势、适用场景、落地省份/项目数量/金额/描述、目标客户、配套文件 |
| 最佳实践 | `PRACTICE` | 同解决方案 | 实践文档 / Playbook | 同解决方案 |

中文→tagValue 映射（从创建页 Vue 组件实测提取，脚本内建转换，`--tech/--industry/--scene/--ability` 均接受中文）：
- 能力类型 `asset_ability_type`：语义理解=semantic_understand、生成文本=generate_text、多媒体处理=multimedia_process、函数调用=function_call、校验审核=verify_audit、知识问答=knowledge_qa、流程编排=process_orchestration、工具调用=tool_call、图像能力=image_ability、文件解析=file_parse、数据查询分析=data_query_analysis、代码能力=code_ability、文本理解=text_understand、文本生成=text_generate
- 使用技术 `asset_use_technology`（25项）：数字教育=digital_edu、教育云平台=edu_cloud_platform、公共服务=public_service、智慧运维=intelligent_operation、DeepSeek=deepseek、智能组网=intelligent_network、智算=intelligent_compute、安全=security、网络=network、机器人=robot、边缘计算=edge_compute、门户集成=portal_integrate、物联网=iot、大数据=big_data、无人机=uav、BC融合=bc_fusion、三业融合=three_industry_fusion、低空经济=low_altitude_economy、车路云=car_road_cloud、信创=info_secure、工业互联网=industrial_internet、数据要素=data_element、5G=5g、视频云=video_cloud、数字人=digital_human
- 归属行业 `asset_belong_industry`（15项）：通用场景=general_scene、连锁商业=chain_business、互联网=internet、农业文宣=agri_culture、医卫=medical_health、制造=manufacture、能源=energy、教育=education、银行=bank、交通=transportation、证券保险=securities_insurance、融合=fusion、住建=construction、政务=government、党务=party_affairs
- 适用场景 `asset_scene`（选填，节选）：审计场景=audit_scene、巡视场景=inspect_scene、企宣场景=corp_publicity_scene、安全场景=security_scene、党建场景=party_scene、办公场景=office_scene、餐饮AI巡店=catering_ai_inspect、电商AIGC=ecommerce_aigc、零售AI巡店=retail_ai_inspect、AI客服=ai_customer_service、物联管理=iot_manage、语音/短彩信=voice_sms（完整清单在脚本 `SCENE_OPTIONS`）

```bash
# 解决方案（暂存验证）
python3 scripts/manage_asset_submit.py submit --name "xx解决方案" --type SOLUTION \
    --one-liner "一句话简介" --file pkg.zip --space-code G2026000S --scope SPACE \
    --tech "DeepSeek,大数据" --industry "通用场景" --draft
# 最佳实践（发布）
python3 scripts/manage_asset_submit.py submit --name "xx最佳实践" --type PRACTICE \
    --one-liner "一句话简介" --file playbook.pdf --space-code G2026000S --scope GLOBAL \
    --tech "智算" --industry "政务"
```

已知边界：三种类型均实测创建成功（SKILL/SOLUTION/PRACTICE 各有草稿实证）；首次提交走 assets/create，草稿再次保存走 assets/edit；`type/list-tree` 接口直调报 401（映射取自页面组件而非该接口）；**能力类型标签组（asset_ability_type）仅 SKILL 有效**——SOLUTION/PRACTICE 发布时带上会报 `COMMON-4001 未知的标签组`（草稿模式不校验，脚本已改为仅 SKILL 附带）。

### 能力：资产管理（状态、生命周期与清理）

资产管理入口：空间内 资产管理 列表页（`/fde/microportal/#/dev-space/workspace/<spaceCode>/asset-manage`）。

**资产状态**（`assets/detail` 的 `assetStatus` / 列表状态列）：

| assetStatus | UI 显示 | 含义 |
| :--- | :--- | :--- |
| 0 | 草稿 | 暂存未提交，仅创建人可见可编辑 |
| 1 | 已发布 | 提交成功即此状态，全开放范围内可见 |

**生命周期**：创建（assets/create，saveDraft=true→草稿 / false→直接发布）→ 草稿可在编辑页「继续编辑」后保存（assets/edit）→ 已发布为终态。**平台不提供删除能力**：

- 已发布资产行内操作仅「编辑 / 下载附件」；草稿行内仅「继续编辑」。
- `assets/delete`、`assets/offline` 接口均报 401「没有访问权限」（普通用户无此权限）。
- 清理测试资产需联系空间/平台管理员，报资产编号（AST-YYYY-NNNN）清单。

**管理常用操作**：

```bash
# 检索空间/全网资产（注意：keyword/size 筛选参数实测未生效，固定返回前 10 条，
# 精确过滤用 python 侧对结果二次过滤或按类型分页遍历）
python3 scripts/manage_assets.py search --keyword cmcc-fde
python3 scripts/manage_assets.py search --type PRACTICE

# 看单个资产状态/挂载文件/创建人（核对是否发布成功）
python3 scripts/manage_assets.py detail --id <资产ID>

# 全局浏览/下载统计
python3 scripts/manage_assets.py stats
```

**实测要点**：
- 发布成功核验：`detail` 读回 `assetStatus=1`，且列表页状态列「已发布」；仅看 create 返回 respCode=00 不够（草稿也返回成功）。
- 已发布资产内容可改：行内「编辑」或编辑页 `/asset-center/edit/<资产ID>` 可改名称/描述/标签并重新保存，但**不能**改回草稿或删除。
- 草稿与同名已发布资产互不影响（同空间可并存多个同名不同形态资产，靠资产编号区分）。
- 资产 ID（雪花长数字）与资产编号（AST-YYYY-NNNN）并存：接口用前者，页面/人工沟通用后者。

---

## 实测验证与已知坑位修复记录

本工具集已针对全部脚本与网关端点完成端到端实测验证，以下关键问题均已修复并在代码中内建防护：

| 模块 / 场景 | 问题描述 | 根本原因与官方修复策略 |
| :--- | :--- | :--- |
| **研发空间列表** (`manage_demands.py spaces`) | 请求报 422 `{"respCode":"COMMON-4001","respDesc":"must not be null"}` | 网关强制校验分页参数，必须显式携带 `?pageNo=1&pageSize=50`，脚本已内置默认分页 |
| **需求子系统鉴权** (`manage_demands.py list/create`) | 报 400 `{"code":1209,"error":"无效的 Gitee token，用户不存在"}` | 需求子系统 SessionToken 为无签名 base64 身份 JSON，改由 `fde_common.get_req_session_token()` 基于 `fde_auth.json` 本地身份字段生成，无需浏览器抓包 |
| **需求列表查询** (`manage_demands.py list`) | 用 `GET /v2/items` 返回 HTML 页面被误判为空列表 | 改用实测端点 `POST /team/parse/api/search/hierarchy` + IQL `(所属空间 = '空间名')`，从 `payload.items` 取真实数据 |
| **需求创建** (`manage_demands.py create`) | 报「空间不存在」/「Item type not found」 | `workspace`、`itemType`、`status` 必须传 Parse Pointer（`{__type,className,objectId}`）；空间与类型 ID 运行期动态解析 |
| **需求删除** (`manage_demands.py delete`) | `DELETE /v2/items/{id}` 假成功（数据未删） | 改用 Parse Cloud 函数 `POST /team/parse/functions/deleteItems`，body 传 `{"itemIds":[id]}`，删后复查列表确认 |
| **缺陷类型过滤** (`manage_bugs.py list`) | IQL 用 `工作项类型 = '缺陷'` 报 `IQL error: CustomField` | 正确字段名为 `类型` 或 `itemType`：`and (类型 = '缺陷')`；缺陷 itemType objectId 运行期从 `itemType/search` 解析（key=`quexian`） |
| **缺陷增删改查** (`manage_bugs.py`) | — | 与需求共用端点，仅固化 itemType=缺陷 + IQL 按类型过滤；端到端实测 create→改状态(已确认)→delete 全通过，删后回到原数量无残留 |
| **详情字段编辑** (`update --set`) | 网关返回成功但字段未落库；标签/优先级等报「数据格式错误」 | 实测规则：仅 `name` 写顶层，其余字段写入 `values`；优先级 P0-P5→UUID；标签 `[{"value":...}]`；严重程度为字符串数组；描述为 Slate 数组；人员按姓名解析为用户对象数组。`req_fields.py` 已内建转换 + 写后读回逐项核对，6 字段一次更新全通过 |
| **单点登录 Ticket** (`fde_common.py`) | 跨模块接口报 401/403 鉴权失败 | 实现了平台通用 Ticket 换取函数 `get_auth_ticket()`，调用时清空 `Data-Auth-Appid` 和 `Data-Auth-Domain` 即可返回有效一次性 SSO 凭据 |
| **资产详情** (`manage_assets.py detail`) | 报 `TypeError: unsupported operand type(s) for /: 'str' and 'int'` | 平台返回的 `fileSize` 为字符串形式（如 `"108"`），已改为 `float()` 安全转换并对类型做缺失回退 |
| **灵宝智能体任务** (`manage_agent.py run`) | 报「参数不合法：input」且派发失败 | 网关入参要求键名为 `input` 而非 `prompt`；该接口为异步任务，返回 `CREATED` 状态即表示下发成功 |
| **知识库目录树** (`manage_wiki.py tree`) | 无法获取目录内部嵌套文档 | 必须携带 `?parent=<目录ID>` 才能拉取深层节点，已新增 `--parent` 参数支持任意深度展开 |
| **知识库数据解压** (`fde_common.py`) | 响应报乱码或解码崩溃 | 知识库网关启用 Brotli 压缩，代码已升级同时支持 Brotli 与 Gzip 自动解压缩机制 |
| **代码令牌有效期** (`manage_token.py create`) | 前端 UI 最多只能选 20 年后 | 后端接口直接允许传入 2046 年等超长时间戳，平台数据库自动标记为 `permanent` 永久有效 |
| **解决方案/最佳实践发布** (`manage_asset_submit.py`) | create 报 `COMMON-4001 未知的标签组` | 能力类型标签组 `asset_ability_type` 仅 SKILL 合法；SOLUTION/PRACTICE 只带 使用技术/归属行业/适用场景；草稿(saveDraft=true)不校验标签组，发布(false)才触发 |
| **资产状态核验** (`manage_assets.py detail`) | create 返回 00 即当发布成功，实为草稿 | `assetStatus`=1 才是已发布（0=草稿）；发布类操作必须 detail 读回核验 |
| **新建代码仓库** (`manage_repos.py create`) | UI 表单提交报文抓包 | `POST /fde-code/api/code/api/enterprises/{ent}/inner_source/projects`，payload `{name,path,description,public,owner_id,license_name,ignore,readme,enterprise_branch_plan_id:0,namespace_id:0,tag_ids:[]}`；`owner_id` 是代码子系统数字 ID（非 userId），经 `/information` 接口取顶层 `user.id`（注意不在 data 里） |
| **代码子系统 405「登录已失效」** (`manage_repos.py` 全线) | projects/information 等报 405，资产/需求接口却正常 | 浏览器存在**多份同名 MOSS_SESSION**：登录门户签在 `sti.chinamobile.com`（path=/），代码子系统 fde-code-web 签在 `.sti.chinamobile.com`（域名点前缀），重新登录后仅部分刷新，旧值失效即 405；`fetch_browser_auth.py` 已修复按 name 去重丢 Cookie 的 bug（现保留全部同名记录按浏览器顺序拼接），遇 405 重新 fetch 即恢复 |

---

## 协议与底层参考

更详细的底层 MOSS 网关反向代理映射、权限头要求与微前端路由规则，参见文档：
- [API Reference 文档](./references/api_reference.md)
