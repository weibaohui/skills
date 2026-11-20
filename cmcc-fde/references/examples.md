# FDE 技能调用示例与样例数据

本文档汇总 [SKILL.md](../SKILL.md) 中各脚本的典型调用示例与真实输出样例，供 AI 执行技能时参考。底层网关规范见 [api_reference.md](./api_reference.md)。

> 所有示例中的 `<ID>`、空间码、Token 等占位符请替换为真实值。Token/凭证属于敏感信息，输出时须脱敏。

---

## 1. 登录与凭证采集

### 1.1 交互式一键采集（小白首选）

```bash
python3 scripts/fetch_browser_auth.py interactive
```

流程：脚本拉起系统 Chrome → **仅打开唯一登录页** `https://sti.chinamobile.com/fde/micrologin/#/login` → 人工短信登录 → 终端回车 → 自动采集 Cookie / MOSS-TOKEN 并写入 `~/.fde/fde_auth.json`（唯一存储点）。

样例输出（Token 已脱敏）：

```text
[*] 正在打开 FDE 统一登录页: https://sti.chinamobile.com/fde/micrologin/#/login
[✓] 已打开: https://sti.chinamobile.com/fde/micrologin/#/login
[约束] 本脚本只弹出登录页，不会打开其它子系统页面。
>>> 登录成功后按回车继续采集（Ctrl+C 取消）...
[✓] Cookie / MOSS-TOKEN / 刷新令牌等凭证已写入 fde_auth.json（~/.fde）。
【✓】浏览器全量凭证自动采集完成，FDE 全套技能均已激活就绪！
 MOSS_SESSION : 8f3a2c1d...（512 字符）
 MOSS-TOKEN   : eyJhbGciOiJIUzI1Ni...（1204 字符）
```

### 1.2 分步操作

```bash
python3 scripts/fetch_browser_auth.py open    # 仅打开登录页
python3 scripts/fetch_browser_auth.py fetch   # 登录后采集凭证
python3 scripts/fetch_browser_auth.py status  # 检查当前登录态（不写文件）
python3 scripts/auth_login.py --check         # 校验本地凭证是否有效
```

---

## 2. 代码仓库与令牌

```bash
python3 scripts/manage_token.py create --name AI-Token          # 签发永久 Private Token
python3 scripts/manage_repos.py list --page 1 --size 20         # 仓库列表
python3 scripts/manage_repos.py branches --path 64              # 分支列表
python3 scripts/manage_repos.py tree --path 64 --ref master     # 在线目录树
python3 scripts/manage_repos.py read --path 64 --file README.md # 在线读源码
python3 scripts/manage_repos.py clone-info --path 64            # 免密克隆命令
```

克隆命令样例（用户名 = SSO 账号，`@` 编码为 `%40`；Git 入口为 `/fde/code/`）：

```bash
git clone https://weibaohui%40hq.cmcc:<private_token>@sti.chinamobile.com/fde/code/<full_path>.git
```

---

## 3. 需求与缺陷管理

```bash
# 空间
python3 scripts/manage_spaces.py list                                   # 空间列表（spaceId/spaceCode）
python3 scripts/manage_spaces.py set --code G2026000S                   # 设默认空间

# 需求：增删改查 + 状态 + 任意字段编辑
python3 scripts/manage_demands.py list --space G2026000S
python3 scripts/manage_demands.py create --space G2026000S --title "新增性能监控模块"
python3 scripts/manage_demands.py update-status --space G2026000S --id <ID> --status 开发
python3 scripts/manage_demands.py update --space G2026000S --id <ID> \
  --set "优先级=P1" --set "负责人=张三" --set "描述=优化首屏加载"
python3 scripts/manage_demands.py delete --space G2026000S --id <ID>

# 缺陷：命令与需求一致，类型固化为缺陷
python3 scripts/manage_bugs.py list --space G2026000S
python3 scripts/manage_bugs.py create --space G2026000S --title "登录页按钮错位"
```

`update` 读回核对样例（每字段写后读回校验，防网关假成功）：

```text
[*] 更新字段: 优先级=P1, 负责人=张三, 描述=优化首屏加载
[✓] 优先级: 写后核对一致
[✓] 负责人: 写后核对一致
[✓] 描述: 写后核对一致
```

---

## 4. 知识库 / 资产 / 智能体

```bash
python3 scripts/manage_wiki.py spaces                                    # 知识库空间列表
python3 scripts/manage_wiki.py tree --space-id 87 --parent <目录ID>       # 深层目录树
python3 scripts/manage_wiki.py read --doc-id 1749                         # 读取正文
python3 scripts/manage_wiki.py download --doc-id 1749 --format pdf        # 导出 PDF
python3 scripts/manage_wiki.py upload --space-id 87 --file doc.md         # 上传文件

python3 scripts/manage_assets.py stats                                    # 资产统计
python3 scripts/manage_assets.py search --keyword 智能                    # 资产检索

python3 scripts/manage_agent.py list                                      # 智能体列表
python3 scripts/manage_agent.py run --agent-id "quick-qa" --prompt "分析报告"  # 派发任务
```

---

## 5. 端到端工作流样例

完整的「登录 → 查空间 → 管理需求 → 导出报告」流程见可执行模板：

- [templates/workflow.sh](../templates/workflow.sh) — 标准操作流程模板
- [templates/report.sh](../templates/report.sh) — 报告生成模板
