# skills · 代码设计与重构指北

> **两套互补知识体系：代码整洁与重构手法 + 62 种软件设计模式**

---

## 📦 这是什么

这是一个遵循 [Vercel Labs Skills](https://skills.sh) 规范的 skill 仓库，可通过 `npx skills` 安装。

### 当前包含的 skill

| 路径 | 安装命令 | 说明 |
|------|----------|------|
| `code-refactor/` | `npx skills add weibaohui/skills/code-refactor` | 代码重构与整洁之道（24 坏味道 + 70+ 重构手法 + Clean Code 规则）|
| `design-patterns/` | `npx skills add weibaohui/skills/design-patterns` | 62 种软件设计模式（GoF 23 + 并发 10 + 企业 7 + 现代 11 + 反模式 11）|

---

## 📖 来源

本知识库的内容由以下经典著作提炼、整合而成：

| 书名 | 作者 | 核心贡献 | 适用 skill |
|------|------|----------|------------|
| **《代码整洁之道》**<br>*Clean Code* | Robert C. Martin (Bob 大叔) | 命名规范、函数设计、注释原则、格式规范、错误处理、类设计、系统设计、并发编程、测试原则 | `code-refactor` |
| **《重构: 改善既有代码设计 第二版》**<br>*Refactoring 2e* | Martin Fowler | 24 种代码坏味道、70+ 重构手法、重构时机判断 | `code-refactor` |
| **《设计模式：可复用面向对象软件的基础》**<br>*Design Patterns (GoF)* | Erich Gamma 等 4 人 | 23 种经典模式（创建 5 + 结构 7 + 行为 11）| `design-patterns` |
| **《Pattern-Oriented Software Architecture, Vol 2》** | Buschmann 等 | 10 种并发模式（Active Object、Monitor、Balking、Thread Pool...）| `design-patterns` |
| **Cloud Native Patterns** | Cornelia Davis / Chris Richardson | 微服务容错（Circuit Breaker、Bulkhead、Saga、Sidecar...）| `design-patterns` |

> **skill 互补关系**：
> - `code-refactor` 教 **"怎么把代码改好"**（70+ 具体重构手法）
> - `design-patterns` 教 **"用什么模式设计代码"**（62 种模式选择）
> - 两个 skill 一起加载效果最佳

---

## 🚀 安装

```bash
# 安装 code-refactor skill（代码重构手法 + Clean Code）
npx skills add weibaohui/skills/code-refactor

# 安装 design-patterns skill（62 种设计模式）
npx skills add weibaohui/skills/design-patterns
```

> 前提：需要 Node.js 18+。更多用法见 [skills.sh](https://skills.sh)。

---

## 📁 目录结构

```
📁 skills
├── 📄 README.md
├── 📄 LICENSE
├── 📄 .gitignore
│
├── 📁 code-refactor/             ← 代码重构 skill
│   └── 📄 SKILL.md               ← 完整知识体系（核心文件）
│       │
│       ├── PART 1: PRINCIPLES        — 设计原则
│       ├── PART 2: CODE SMELLS       — 24 种代码坏味道
│       ├── PART 3: REFACTORING       — 70+ 重构手法
│       ├── PART 4: CODE QUALITY      — 代码质量规范
│       ├── PART 5: WHEN TO REFACTOR  — 重构时机决策
│       └── QUICK DECISION MATRIX     — 快速决策矩阵
│
└── 📁 design-patterns/           ← 设计模式 skill
    └── 📄 SKILL.md               ← 62 种模式知识库（核心文件）
        │
        ├── PART 1: 设计原则           — SOLID + KISS + YAGNI
        ├── PART 2: GoF 23 种          — 创建 5 + 结构 7 + 行为 11
        ├── PART 3: 并发模式 (POSA 2)  — 10 种（Active Object、Thread Pool...）
        ├── PART 4: 企业/分布式         — 7 种（Repository、Unit of Work...）
        ├── PART 5: 现代模式           — 11 种（DI、Pub-Sub、CQRS、Saga...）
        ├── PART 6: 反模式             — 11 种（God Object、Spaghetti...）
        ├── PART 7: 模式选择决策矩阵   — 按问题/原则速查
        ├── PART 8: 实战模板           — 重构输出标准格式 + 完整示例
        └── QUICK DECISION MATRIX     — 快速决策表
```

---

## 🎯 核心内容一览

### 设计原则 (PART 1)

| 原则 | 要点 |
|------|------|
| 简单设计四规则 | 通过全部测试 → 无重复 → 表达意图 → 最小化类和函数 |
| SOLID | SRP / OCP / LSP / ISP / DIP |
| 迪米特法则 | "只跟朋友说话，不跟陌生人聊天" |
| CQS | 函数要么做事，要么回答，不同时做 |
| 不可变性 | 优先不可变数据，万不得已再改变 |

### 代码坏味道 (PART 2) — 24 种

命名问题、重复代码、过长函数、过长参数列表、全局数据、可变数据、发散式变化、霰弹式修改、依恋情结、数据泥团、基本类型偏执、switch 语句、重复遍历、循环语句、冗赘元素、内幕交易、过大的类、异曲同工的类、纯数据类、被拒绝的遗赠、注释掉的代码...

### 重构手法 (PART 3) — 70+ 种

| 章节 | 核心手法 |
|------|----------|
| Ch6: 第一组 | 提炼函数、内联函数、提炼变量、内联变量、改变函数声明、封装变量、引入参数对象 |
| Ch7: 封装 | 封装记录、集合封装、基本类型取代对象、以查询取代临时变量、提炼类、内联类、隐藏委托、移除中间人 |
| Ch8: 搬移 | 搬移函数、搬移字段、搬移语句到函数/调用者、内联函数到调用者、以函数调用取代内联代码 |
| Ch9: 数据 | 拆分变量、字段改名、以查询取代派生变量、将引用对象改为值对象、将值对象改为引用对象 |
| Ch10: 条件 | 分解条件、合并条件/表达式、以卫语句取代嵌套条件、以多态取代条件、引入特例、引入断言 |
| Ch11: API | 分离查询与修改、参数化函数、移除标记参数、保持对象完整、以查询取代参数、移除设值函数、以工厂取代构造、以命令取代函数 |
| Ch12: 继承 | 函数/字段上移、构造函数体上移、函数/字段下移、以子类取代类型码、移除子类、提炼超类、折叠继承、以委托取代子类/超类 |

### 代码质量规则 (PART 4)

- **命名**: 名副其实、避免误导、有意义的区分、读得出来的名称、可搜索的名称、避免编码
- **函数**: 短小、只做一件事、每个函数一个抽象层级、避免 switch 重复、使用多态、参数宜少不宜多
- **注释**: 好注释提供信息（法律信息、警示、解释意图、TODO），坏注释包括冗余、误导、日志式、归属
- **错误处理**: 优先异常而非返回码、提供异常上下文、定义常规流程（Special Case Pattern）
- **测试**: TDD 三定律、单断言原则、FIRST 原则（快速、独立、可重复、自验证、及时）

### 重构时机 (PART 5)

| 场景 | 决策 |
|------|------|
| 添加新功能时 | ✅ 重构，让代码更容易理解 |
| 修复 Bug 时 | ✅ 重构，让 Bug 无处藏身 |
| Code Review 时 | ✅ 重构，在提交前改进 |
| 重写比重构快时 | ❌ 不重构 |
| 已到截止日期时 | ❌ 不重构 |

---

## 📚 推荐阅读

1. **Clean Code: A Handbook of Agile Software Craftsmanship** — Robert C. Martin, 2008
2. **Refactoring: Improving the Design of Existing Code (2nd Edition)** — Martin Fowler, 2018
3. **Design Patterns: Elements of Reusable Object-Oriented Software** — GoF, 1994
4. **Head First Design Patterns** — Eric Freeman 等
5. **Pattern-Oriented Software Architecture, Volume 2** — Buschmann 等
6. **Working Effectively with Legacy Code** — Michael Feathers
7. **Code Complete (2nd Edition)** — Steve McConnell
8. **Microservices Patterns** — Chris Richardson
9. **https://refactoring.guru/** — 最佳在线资源

---

## 📄 许可证

MIT License — 欢迎自由使用、分享、改进。

## 👤 维护者

- **weibaohui** — [GitHub](https://github.com/weibaohui)

---

> 🧭 无论你是刚入行的新手还是经验丰富的架构师，愿这份知识体系成为你代码重构路上的指南针。
