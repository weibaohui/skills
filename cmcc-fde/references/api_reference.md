# 中国移动“灵畿”科研平台 (FDE) 底层网关与 API 规范

## 1. 网关拓扑与关键鉴权 Header

所有 FDE 接口统一通过移动内部 MOSS 网关分发，主基准地址为 `https://sti.chinamobile.com`。

| Header 字段 | 说明 | 示例值 | 适用范围 |
| :--- | :--- | :--- | :--- |
| `Cookie` | 用户主身份凭据，包含 MOSS 会话 ID | `MOSS_SESSION=...` | 全局所有接口 |
| `Data-Auth-Appid` | 统一前端应用标识 | `FDE` | 全局所有接口 |
| `Data-Auth-Domain` | 接入域上下文 | `portal` | 全局所有接口 |
| `Data-Auth-Enterpriseid`| 当前租户/企业 UUID | `ENT_999999` | 资产中心、代码服务、桌面 |
| `x-auth-module` | 微前端模块路由标头 | `PLATFORM` | 代码仓库子系统必须 |
| `Private-Token` | 代码仓库私人访问令牌 | `NjI3OGJjMDE...` | Git 仓库读写、代码 API |

---

## 2. 核心端点映射表

### 2.1 登录与身份
- 前端登录入口: `https://sti.chinamobile.com/fde/micrologin/#/login`
- 工作台入口: `https://sti.chinamobile.com/fde/microportal/#/workbench`
- `POST /fde/moss/web/manage/v1/self/list-euser`: 查询当前登录用户企业与身份信息
- `GET /fde/moss/web/desktop/v1/api/v1/moss/tenant/list?type=1`: 查询用户租户列表

### 2.2 代码仓库与私人令牌 (Gitee Custom Engine)
- `GET /fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/private_tokens?enterprise_global=true`: 查询私人令牌列表
- `POST /fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/private_tokens?enterprise_global=true`: 创建私人令牌
  - Scopes: `[1, 2, 4, 5, 6, 7, 8]`
  - Expires: 设置为 `2046-12-31` 系统自动转换为 `permanent` (永久有效)
- `DELETE /fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/private_tokens/{id}?enterprise_global=true`: 删除私人令牌
- `GET /fde/moss/web/fde-code/api/code/api/enterprises/{enterprise_id}/projects?enterprise_global=true`: 企业代码仓库列表

### 2.3 资产中心 (Asset Center)
- `GET /fde/moss/web/asset/v1/api/v1/assets/statistics`: 资产全局统计指标
- `GET /fde/moss/web/asset/v1/api/v1/assets/count-summary`: 可见资产统计
- `POST /fde/moss/web/asset/v1/api/v1/assets/page`: 分页多维搜索资产
- `GET /fde/moss/web/asset/v1/api/v1/assets/detail?assetId={id}`: 资产单项完整档案与附件交付物清单

### 2.4 灵宝 AI 智能体体系 (FDE Agent)
- `GET /fde/moss/web/fde-agent/v1/agents`: 部署专业智能体清单
- `GET /fde/moss/web/fde-agent/v1/sessions`: 智能体历史会话
- `GET /fde/moss/web/fde-agent/v1/sessions/{id}/messages`: 会话上下文与卡片
- `POST /fde/moss/web/fde-agent/v1/runs`: 异步下发智能体生成任务

## 5. 知识库 (Wiki) 子系统路由与交互协议

- **子系统访问入口**：`https://sti.chinamobile.com/fde-wiki-web/`
- **核心网关前缀**：
  - API 网关：`/fde-wiki/api/wiki`
  - 格式转换与导出服务：`/fde-wiki/api/wiki-convert`
  - 静态源文件直连存储：`/fde-wiki/wiki-static/{fetchUrl}`
- **关键鉴权 Header 要求**：
  - `x-wiki-tenant-id`: `CMCC`（中国移动专属租户标识，必传）
  - `x-auth-module`: `PLATFORM`
  - `Cookie`: 会话 Cookie
- **核心端点清单**：
  - `GET /fde-wiki/api/wiki/spaces`: 知识库空间 (Spaces) 列表
  - `GET /fde-wiki/api/wiki/spaces/{spaceId}/tree`: 指定空间的完整文档目录树
  - `GET /fde-wiki/api/wiki/spaces/{spaceId}/pages/{pageId}`: 获取文档基础元数据
  - `GET /fde-wiki/api/wiki/pages/{pageId}/content`: 获取文档 ProseMirror 结构化完整正文
  - `GET /fde-wiki/api/wiki/spaces/{spaceId}/pages/{pageId}/component`: 获取组件与富文本正文
  - `GET /fde-wiki/api/wiki/api/wiki-convert/pages/{pageId}/doc_export?tenant=CMCC&type={word|pdf|markdown|html}`: 文档转换导出与下载
  - `POST /fde-wiki/api/wiki/spaces/{spaceId}/pages`: 在线新建文档页面 (body 需携带 ProseMirror 文档节点 JSON)
  - `POST /fde-wiki/api/wiki-convert/pages/{parentId}/doc_import`: Multipart 格式本地文档上传转换导入
  - `DELETE /fde-wiki/api/wiki/spaces/{spaceId}/pages/batch`: 批量删除文档 (body: `{"pageIds": [...]}`)

## 6. 研发空间与需求管理 (fde-req-web / Proxima Core) 接口协议

- **子系统访问入口**：`https://sti.chinamobile.com/fde/base/fde-req-web/`
- **空间看板入口**：`https://sti.chinamobile.com/fde/base/fde-req-web/#/workspace/boards/req?spaceCode={spaceCode}`
- **网关前缀**：
  - 研发空间接口：`/fde/moss/web/desktop/v1/api/v1/user/space`
  - 需求管理核心网关：`/fde/moss/web/fde-req/api/team/parse/api`
- **关键 Header 规范**：
  - `x-auth-module`: `SPACE`
  - `x-auth-moduleid`: `{spaceCode}`（如 `X2026000T`）
  - `X-Parse-Application-Id`: `proxima-core`
  - `X-Parse-Session-Token`: `sessionToken`
- **核心端点清单**：
  - `GET /fde/moss/web/desktop/v1/api/v1/user/space/list?pageNo=1&pageSize=10`: 获取当前用户参与/拥有的研发空间列表
  - `GET /fde/moss/web/fde-req/api/team/parse/api/v2/items?workspace={spaceCode}&limit=20`: 分页查询空间需求列表
  - `POST /fde/moss/web/fde-req/api/team/parse/api/v2/items`: 创建新需求/事项
  - `PUT /fde/moss/web/fde-req/api/team/parse/api/v2/items/{itemId}`: 更新需求/工作流状态流转
  - `DELETE /fde/moss/web/fde-req/api/team/parse/api/v2/items/{itemId}`: 删除需求


