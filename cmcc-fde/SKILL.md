---
name: cmcc-fde
description: >-
  中国移动“灵畿”科研底座平台 (FDE) 自动化工具集与流程指南。
  支持统一登录会话初始化、代码仓库永久令牌 (Private Token) 管理、企业代码仓库免克隆在线检索与读取、
  知识库 (Wiki) 文档在线阅读/上传导入与多格式导出下载、科研资产中心检索与统计、“灵宝”AI原生智能体互动，
  以及研发空间与需求管理 (Item CRUD/状态流转)。
  内置小白用户全自动凭证采集（免F12抓包、自动预热采集子系统Token与自动签发永久代码令牌）与单点登录 Ticket 机制。
---

# 中国移动“灵畿”科研底座平台 (FDE) 技能指南

本技能为中国移动“灵畿”科研底座平台（FDE / MOSS）提供完整的 Python 命令行工具集与操作流程。所有脚本**高度复用同一个鉴权文件 (`fde_auth.json`)**，除可选的知识库 `brotli` 模块外，其余脚本仅需 Python 3 标准库即可直接运行。

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

- **统一登录页面**：[https://sti.chinamobile.com/fde/micrologin/#/login](https://sti.chinamobile.com/fde/micrologin/#/login)
- **个人工作台入口**：[https://sti.chinamobile.com/fde/microportal/#/workbench](https://sti.chinamobile.com/fde/microportal/#/workbench)
- **研发空间列表入口**：[https://sti.chinamobile.com/fde/microportal/#/dev-space](https://sti.chinamobile.com/fde/microportal/#/dev-space)
- **需求与看板系统入口**：[https://sti.chinamobile.com/fde/base/fde-req-web/#/workspace/boards/req](https://sti.chinamobile.com/fde/base/fde-req-web/#/workspace/boards/req)
- **代码子系统入口**：[https://sti.chinamobile.com/fde/base/fde-code-web/](https://sti.chinamobile.com/fde/base/fde-code-web/)
- **代码令牌管理页**：[https://sti.chinamobile.com/fde/base/fde-code-web/private_token](https://sti.chinamobile.com/fde/base/fde-code-web/private_token)
- **知识库系统入口**：[https://sti.chinamobile.com/fde-wiki-web/](https://sti.chinamobile.com/fde-wiki-web/)

---

## 快速导航与脚本清单

| 脚本文件 | 功能说明 | 核心命令示例 |
| :--- | :--- | :--- |
| [fetch_browser_auth.py](./scripts/fetch_browser_auth.py) | **【首选零门槛】浏览器全量凭证自动采集**：拉起 Chrome，用户手机验证码登录后，全自动捕获 Cookie、MOSS-TOKEN、需求专属 sessionToken 并自动签发永久代码令牌 | `python3 fetch_browser_auth.py interactive` |
| [auth_login.py](./scripts/auth_login.py) | **登录会话初始化与验证**：使用现有 Cookie/Token 校验企业与用户身份档案并持久化同步 | `python3 auth_login.py --check` |
| [manage_token.py](./scripts/manage_token.py) | **代码仓库私人令牌管理**：直接调用后台 API 突破前端日历限制，创建永久有效 (`permanent`) 的全权限 Token | `python3 manage_token.py create --name AI-Token` |
| [manage_spaces.py](./scripts/manage_spaces.py) | **研发空间深度管理**：列出当前用户所有空间（包含空间唯一 ID `spaceId`、空间编码 `spaceCode`、名称与角色），支持多空间交互式选择与默认空间持久化切换 | `python3 manage_spaces.py list`<br>`python3 manage_spaces.py select`<br>`python3 manage_spaces.py current` |
| [manage_demands.py](./scripts/manage_demands.py) | **敏捷需求深度管理**：需求清单、新建、状态流转、删除，以及任意详情字段编辑（`update --set`） | `python3 manage_demands.py list`<br>`python3 manage_demands.py update --id <ID> --set 优先级=P1` |
| [manage_bugs.py](./scripts/manage_bugs.py) | **敏捷缺陷深度管理**：与需求共用端点，固化缺陷类型；缺陷清单、新建、状态流转、删除、任意详情字段编辑 | `python3 manage_bugs.py list`<br>`python3 manage_bugs.py update --id <ID> --set 严重程度=3-一般错误` |
| [req_fields.py](./scripts/req_fields.py) | **字段转换公共模块**：`update --set` 的字段别名归一化、类型转换（UUID/数组/富文本/用户对象）与写入后读回验证，被上述两个脚本共用（不单独调用） | — |
| [manage_repos.py](./scripts/manage_repos.py) | **代码仓库深度操作**：浏览仓库、分支列表、免克隆直接在线遍历文件树与读取源码、合并请求 (PR) 追踪、成员权限与免密 Git 克隆 | `python3 manage_repos.py branches --path 64`<br>`python3 manage_repos.py read --path 64 --file README.md` |
| [manage_assets.py](./scripts/manage_assets.py) | **科研资产中心检索**：全景统计、科技方案/技能/实践资产分页搜索与详情归档查询 | `python3 manage_assets.py search --keyword 智能` |
| [manage_agent.py](./scripts/manage_agent.py) | **灵宝 AI 智能体协同**：查询可用智能体列表、历史会话问答追踪与异步派发任务 | `python3 manage_agent.py list`<br>`python3 manage_agent.py run --agent-id "quick-qa" --prompt "分析报告"` |
| [manage_wiki.py](./scripts/manage_wiki.py) | **知识库文档与空间管理**：空间列表、目录树深度展开、富文本正文在线还原读取、文档导出下载 (Word/PDF/MD/HTML)、本地文件上传导入、页面创建与删除 | `python3 manage_wiki.py spaces`<br>`python3 manage_wiki.py download --doc-id 1749 --format pdf`<br>`python3 manage_wiki.py upload --space-id 87 --file doc.md` |

---

## 工作流与操作步骤

### 第一步：初始化或刷新登录凭证

#### 方式 A（强烈推荐，适合所有用户与小白）：全自动浏览器凭证采集

当本地尚未配置凭据，或凭证过期时，**统一使用 [fetch_browser_auth.py](./scripts/fetch_browser_auth.py)** 进行一键采集。
底层基于系统 Chrome 与 `playwright-browser-use` 自动化工具，由人工仅负责一次短信/图形验证码输入，脚本全自动完成一切技术细节：

```bash
# 一步到位交互式采集（推荐）：
# 1. 自动启动系统 Chrome 打开登录页
# 2. 提示用户输入手机号和验证码
# 3. 用户在终端按回车，脚本自动预热各子系统并采集全量凭证
python3 scripts/fetch_browser_auth.py interactive

# 也可以分步执行：
python3 scripts/fetch_browser_auth.py open   # 仅拉起并打开页面
python3 scripts/fetch_browser_auth.py fetch  # 登录后自动轮询抓取并预热子系统
python3 scripts/fetch_browser_auth.py status # 仅检查当前浏览器登录状态
```

> [!NOTE]
> **自动预热与动态 Token 采集机制**：
> 1. 主平台工作台使用 `MOSS_SESSION` Cookie 与 `MOSS-TOKEN` JWT。
> 2. 需求子系统（Proxima Core）采用微前端隔离架构，拥有独立的会话凭证 `sessionToken`。
> 3. `fetch_browser_auth.py` 在主平台登录成功后，会自动导航至 `fde-req-web` 需求看板页完成静默预热，并自动提取注入到浏览器中的 `sessionToken` 保存至 `fde_auth.json`。
> 4. 同时，脚本会自动调用平台通用单点登录 Ticket 接口（`GET /fde/moss/web/auth/v1/user/get-auth-ticket`）并在代码系统自动签发一个 2046 年过期的永久代码 Token。普通用户完全不需要关心这些内部机制。

#### 方式 B：手动提供 Cookie（高级开发者或已有现有会话）

若开发者已有浏览器中登录的 Cookie 字符串：

```bash
# 传入 Cookie 验证并自动提取所属企业 (ENT_999999)、用户 ID 等信息
python3 scripts/auth_login.py --cookie "MOSS_SESSION=...; ..."

# 检查当前本地保存的会话状态
python3 scripts/auth_login.py --check
```

---

### 第二步：一键创建全功能永久代码令牌 (Private Token)

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

### 第三步：研发空间查看、选择与需求管理

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
在指定空间或当前默认空间下进行工作项的增删改查：

```bash
# 0. 列出研发空间（编码 spaceCode 供后续 --space 使用）
python3 scripts/manage_demands.py spaces

# 1. 查询需求列表 (未带 --space 时使用默认空间，可用 manage_spaces.py 设置)
python3 scripts/manage_demands.py list
# 也可以显式指定空间编码：
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
| 负责人 assignee / 关注人 watchers | 姓名或账号，多个用逗号 | `--set "负责人=周志君,张三"` |
| 标签 Tag | 标签名，多个用逗号 | `--set "标签=产品,客户关注"`（可选值见字段定义） |
| 迭代 sprint / 故事点 StoryPoint / 版本 version | 字符串 | `--set "迭代=2026-Sprint1"` |
| 计划开始/结束时间 | 时间戳或字符串 | `--set "计划开始时间=..."` |

> [!IMPORTANT]
> - 字段转换规则由公共模块 `scripts/req_fields.py` 统一实现：只有 `name` 写在顶层，其余字段一律写入 `values`；选项/人员/标签字段会转成数组，描述类转成 Slate 富文本。
> - 人员解析会先从空间已有事项收集成员，再补充 `/users` 列表（网关忽略 `where` 过滤，且 `/users` 前若干条可能不含全部成员），因此传姓名须是空间内真实成员。
> - 未知字段会报错并提示可用字段，不会静默忽略。

---

### 第四步：深度查询与操作代码仓库

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
```

---

### 第五步：资产中心全景统计与检索

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

### 第六步：调用原生“灵宝”AI 智能体

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

### 第七步：知识库 (Wiki) 深度管理与文档上传下载

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

---

## 协议与底层参考

更详细的底层 MOSS 网关反向代理映射、权限头要求与微前端路由规则，参见文档：
- [API Reference 文档](./references/api_reference.md)
