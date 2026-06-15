---
name: design-patterns
description: "软件设计模式完整知识库 — 基于 GoF 23 种经典 + 10 种并发模式 + 11 种企业/分布式模式 + 11 种现代云原生模式 + 11 种反模式。识别代码坏味道、选择合适设计模式、给出安全重构方案。Keywords: design pattern, refactor, code smell, singleton, factory, observer, strategy, decorator, adapter, facade, proxy, command, iterator, state, template method, visitor, builder, prototype, abstract factory, composite, flyweight, bridge, mediator, memento, interpreter, chain of responsibility, repository, dependency injection, cqrs, event sourcing, saga, circuit breaker, bulkhead, god object, spaghetti, golden hammer, premature optimization, copy paste, big ball of mud, magic numbers, hard coding, 设计模式, 重构, 代码坏味道, 提炼函数, 搬移函数, 封装, 简化条件, 多态, 继承, 卫语句, 委托, 代码整洁, 重构名录, SRP, OCP, LSP, ISP, DIP, SOLID, DRY, KISS, YAGNI. Triggers on: 重构这段代码, 用什么模式, 这是什么坏味道, 怎么改进, 提取函数, 拆分大类, 消除重复, 替换条件, 引入接口, 设计模式, refactor this, what pattern, code smell, how to improve, extract function, split class, remove duplication, replace conditional, introduce interface, apply pattern"
version: "1.0.0"
license: MIT
metadata:
  author: hermes
  tags: [design-patterns, refactoring, gof, solid, code-quality, code-review, anti-patterns, 设计模式, 重构, 代码质量]
  docs-url: github.com/weibaohui/skills
---

# Design Patterns Skill

Unified design patterns reference based on **GoF 23 + 并发 10 + 企业 7 + 现代 11 + 反模式 11 = 62 种模式**。

> **与 `code-refactor` skill 互补**：
> - `code-refactor` 偏"70+ 重构手法 + 24 种坏味道 + Clean Code 规则"
> - 本 skill 偏"62 种设计模式选择 + SOLID + 反模式警告"
> - 两个一起加载效果最佳

---

## PART 1: 核心设计原则

### SOLID 原则

| 原则 | 规则 | 违反征兆 |
|------|------|----------|
| **SRP** 单一职责 | 一个类只有一个改变的原因 | 类有 30+ 方法 / 字段 > 10 个 |
| **OCP** 开闭 | 对扩展开放，对修改关闭 | 加新功能要改老代码 / Switch on type |
| **LSP** 里氏替换 | 子类可替换父类 | 子类抛 UnsupportedException |
| **ISP** 接口隔离 | 多个小接口优于一个大接口 | 客户端被迫依赖不用方法 |
| **DIP** 依赖倒置 | 依赖抽象，不依赖具体 | `new ConcreteClass()` 散落各处 |

### 其它关键原则

- **DRY**（Don't Repeat Yourself）：重复是万恶之源
- **KISS**（Keep It Simple, Stupid）：简单胜于复杂
- **YAGNI**（You Aren't Gonna Need It）：不为未来写代码
- **LoD**（Law of Demeter）：只跟朋友说话，不跟陌生人聊天
  - 违反：`a.getB().getC().getD()`（train wreck）
- **CQS**（Command-Query Separation）：函数要么做事，要么回答，不同时做
- **CQS 变体**：Prefer immutability; use side-effect-free functions
- **Composite over Inheritance**：组合优于继承
- **Program to Interface, not Implementation**：面向接口编程

### 重构安全四原则

1. **测试先行**：没有测试不重构
2. **小步前进**：一次只改一处
3. **频繁验证**：改完跑测试
4. **小步提交**：git commit 每步可回退

**Rule of Three**：重复出现 3 次才动手重构。

---

## PART 2: GoF 23 种经典设计模式（1994）

### 2.1 创建型（Creational）— 5 种

> **核心问题**：如何灵活地创建对象，解耦对象的创建与使用

#### 1. Singleton（单例模式）

**问题**：一个类只能有一个实例，并提供全局访问点

**解决方案**：
- 私有构造方法
- 静态方法返回唯一实例
- 双重检查锁定保证线程安全

**代码骨架（Java）**：
```java
public class Singleton {
    private static volatile Singleton instance;
    private Singleton() {}
    public static Singleton getInstance() {
        if (instance == null) {
            synchronized (Singleton.class) {
                if (instance == null) {
                    instance = new Singleton();
                }
            }
        }
        return instance;
    }
}
```

**好处**：节省内存、避免重复创建、全局访问点

**什么时候用**：
- ✅ 配置管理器、日志器、数据库连接池、线程池、缓存
- ❌ 不要用于有状态的对象（违反 SRP、难测试）

**反模式警告**：单例 = 全局变量 = 测试困难，慎用！

---

#### 2. Factory Method（工厂方法模式）

**问题**：创建对象时不想指定具体类，但要让子类决定实例化哪个类

**代码骨架（Java）**：
```java
abstract class Creator {
    public abstract Product factoryMethod();
    public void doSomething() {
        Product p = factoryMethod();
        p.use();
    }
}
class ConcreteCreatorA extends Creator {
    public Product factoryMethod() { return new ProductA(); }
}
```

**好处**：解耦创建和使用、易于扩展、符合 OCP

**什么时候用**：
- ✅ 不知道该用对象的确切类型
- ✅ 类将创建对象的职责委托给子类
- ✅ 框架需要标准化创建流程

---

#### 3. Abstract Factory（抽象工厂模式）

**问题**：创建**一系列相关或相互依赖的对象**（如 UI 主题、跨平台 UI 组件），而不指定具体类

**代码骨架（Java）**：
```java
interface GUIFactory {
    Button createButton();
    Checkbox createCheckbox();
}
class WinFactory implements GUIFactory {
    public Button createButton() { return new WinButton(); }
    public Checkbox createCheckbox() { return new WinCheckbox(); }
}
class MacFactory implements GUIFactory {
    public Button createButton() { return new MacButton(); }
    public Checkbox createCheckbox() { return new MacCheckbox(); }
}
```

**好处**：保证系列产品的一致性、切换产品族方便、符合 OCP

**什么时候用**：
- ✅ UI 跨平台（Windows/Mac/Linux 主题）
- ✅ 数据库访问层（MySQL/PostgreSQL/Oracle 同一套 API）
- ✅ 测试 mock

---

#### 4. Builder（建造者模式）

**问题**：创建**复杂对象**（很多可选参数），构造函数参数太多

**代码骨架（Java）**：
```java
class UserBuilder {
    private String name = "";
    private int age = 0;
    private String email = "";
    public UserBuilder setName(String n) { this.name = n; return this; }
    public UserBuilder setAge(int a) { this.age = a; return this; }
    public UserBuilder setEmail(String e) { this.email = e; return this; }
    public User build() { return new User(name, age, email); }
}
User u = new UserBuilder().setName("Alice").setAge(30).build();
```

**好处**：避免参数爆炸、可读性强、可选参数处理优雅

**什么时候用**：
- ✅ 复杂对象（HTTP 请求、SQL 查询、配置对象）
- ✅ 多个可选参数
- ✅ 创建过程需要分步骤进行

---

#### 5. Prototype（原型模式）

**问题**：创建对象的成本很大（数据库查询、RPC），直接 new 浪费资源

**代码骨架（Java）**：
```java
class Sheep implements Cloneable {
    private String name;
    public Sheep(String name) { this.name = name; }
    @Override
    public Sheep clone() throws CloneNotSupportedException {
        return (Sheep) super.clone();
    }
}
```

**好处**：避免重复初始化的开销、简化创建流程

**什么时候用**：
- ✅ 创建对象成本高（DB、RPC、大对象图）
- ✅ 避免分层次的工厂类
- ⚠️ 注意：深拷贝 vs 浅拷贝

---

### 2.2 结构型（Structural）— 7 种

> **核心问题**：如何将类或对象组合成更大的结构

#### 6. Adapter（适配器模式）

**问题**：已有类的接口**与需求不匹配**，但不能修改原类（第三方库、老代码）

**两种形式**：
- **类适配器**（继承）
- **对象适配器**（组合）—— **更灵活，推荐**

**代码骨架（Java）**：
```java
interface Target { void request(); }
class Adaptee { void specificRequest() { /* 老接口 */ } }
class Adapter implements Target {
    private Adaptee adaptee;
    public Adapter(Adaptee a) { this.adaptee = a; }
    public void request() { adaptee.specificRequest(); }
}
```

**什么时候用**：
- ✅ 集成第三方库（API 风格不一致）
- ✅ 老系统迁移、跨平台兼容

---

#### 7. Bridge（桥接模式）

**问题**：类的**多个独立变化维度**，继承会导致类爆炸

**代码骨架**：
```java
interface Implementor { void operationImpl(); }
abstract class Abstraction {
    protected Implementor impl;
    public Abstraction(Implementor i) { this.impl = i; }
    public void operation() { impl.operationImpl(); }
}
```

**什么时候用**：
- ✅ 多维度变化（形状 + 颜色、平台 + 功能）
- ✅ 不希望继承导致类数量爆炸

---

#### 8. Composite（组合模式）

**问题**：表示**部分-整体的层次结构**（树形结构）

**代码骨架**：
```java
interface Component { void operation(); void add(Component c); }
class Leaf implements Component { public void operation() { /*...*/ } }
class Composite implements Component {
    private List<Component> children = new ArrayList<>();
    public void add(Component c) { children.add(c); }
    public void operation() { for (Component c : children) c.operation(); }
}
```

**什么时候用**：
- ✅ 文件系统、UI 树、组织架构、菜单
- ✅ 任何树形/递归结构

---

#### 9. Decorator（装饰器模式）

**问题**：动态地给对象**添加职责**，但不想用继承

**代码骨架**：
```java
interface Coffee { double cost(); String desc(); }
class SimpleCoffee implements Coffee {
    public double cost() { return 2.0; }
    public String desc() { return "Coffee"; }
}
class MilkDecorator extends CoffeeDecorator {
    public double cost() { return coffee.cost() + 0.5; }
    public String desc() { return coffee.desc() + " + Milk"; }
}
```

**什么时候用**：
- ✅ Java I/O 流（`BufferedReader(FileReader)`）
- ✅ Web 中间件（auth、logging、CORS 链）
- ✅ React 高阶组件（HOC）

---

#### 10. Facade（外观模式）

**问题**：复杂子系统有几十个类，客户端使用很麻烦

**代码骨架**：
```java
class ComputerFacade {
    private CPU cpu;
    private Memory memory;
    private Disk disk;
    public void start() {
        cpu.freeze();
        memory.load();
        disk.read();
        cpu.execute();
    }
}
```

**什么时候用**：
- ✅ 为复杂子系统提供简单接口
- ✅ 分层架构（Service 层就是 Facade）
- ✅ 第三方 SDK 包装

---

#### 11. Flyweight（享元模式）

**问题**：创建大量**相似对象**导致内存浪费

**代码骨架**：
```java
class TreeType {
    private String name;
    private Color color;
}
class TreeFactory {
    private static Map<String, TreeType> cache = new HashMap<>();
    public static TreeType getTreeType(String name, Color color) {
        String key = name + color;
        if (!cache.containsKey(key)) {
            cache.put(key, new TreeType(name, color));
        }
        return cache.get(key);
    }
}
```

**什么时候用**：
- ✅ 大量相似对象（粒子系统、字符、坐标点）
- ✅ 字符串常量池、Integer 缓存

---

#### 12. Proxy（代理模式）

**问题**：不想直接访问真实对象（控制访问、延迟加载、远程访问、保护）

**变体**：
- **虚拟代理**：延迟加载（大对象、图片）
- **保护代理**：权限控制
- **远程代理**：RPC、REST
- **智能引用**：引用计数、懒加载

**代码骨架**：
```java
interface Image { void display(); }
class ProxyImage implements Image {
    private RealImage real;
    private String filename;
    public ProxyImage(String f) { this.filename = f; }
    public void display() {
        if (real == null) real = new RealImage(filename);
        real.display();
    }
}
```

**什么时候用**：
- ✅ Spring AOP、数据库连接池
- ✅ RPC、Dubbo、gRPC 客户端
- ✅ 缓存代理、防火墙代理

---

### 2.3 行为型（Behavioral）— 11 种

> **核心问题**：如何处理类或对象之间的通信和职责分配

#### 13. Chain of Responsibility（责任链模式）

**问题**：多个对象都有机会处理请求，**不确定哪个会处理**

**代码骨架**：
```java
abstract class Handler {
    protected Handler next;
    public void handle(Request r) {
        if (canHandle(r)) doHandle(r);
        else if (next != null) next.handle(r);
    }
}
class AuthHandler extends Handler { /*...*/ }
class LogHandler extends Handler { /*...*/ }
```

**什么时候用**：
- ✅ Web 中间件链（auth → log → rate-limit → handler）
- ✅ 异常处理链、UI 事件冒泡

---

#### 14. Command（命令模式）

**问题**：将**请求封装为对象**，从而支持撤销、队列、日志、宏命令

**代码骨架**：
```java
interface Command { void execute(); void undo(); }
class LightOnCommand implements Command {
    private Light light;
    public LightOnCommand(Light l) { this.light = l; }
    public void execute() { light.on(); }
    public void undo() { light.off(); }
}
```

**什么时候用**：
- ✅ 文本编辑器的撤销/重做
- ✅ 数据库事务、任务队列
- ✅ GUI 按钮、菜单

---

#### 15. Interpreter（解释器模式）

**问题**：给定一种语言，定义它的**文法表示**，并定义一个解释器

**什么时候用**：
- ✅ SQL 解析、正则表达式、配置文件解析
- ✅ DSL（领域特定语言）
- ⚠️ 不推荐用于复杂文法（用 ANTLR 等 parser generator）

---

#### 16. Iterator（迭代器模式）

**问题**：提供一种**顺序访问聚合对象元素**的方法

**什么时候用**：
- ✅ Java `for-each`、Python `for x in list`、Rust `for x in vec`
- ✅ 集合框架（ArrayList、HashMap 都有 iterator）

---

#### 17. Mediator（中介者模式）

**问题**：多个对象之间**复杂引用关系**，导致网状结构

**什么时候用**：
- ✅ 聊天室、飞机控制系统
- ✅ GUI 对话框（组件互引用通过 Controller）
- ✅ 事件总线（Event Bus）

---

#### 18. Memento（备忘录模式）

**问题**：不破坏封装性的前提下，**捕获对象内部状态**，并在之后恢复

**代码骨架**：
```java
class EditorMemento { private String state; /*...*/ }
class Editor {
    private String text;
    public EditorMemento save() { return new EditorMemento(text); }
    public void restore(EditorMemento m) { this.text = m.getState(); }
}
class History {
    private Stack<EditorMemento> stack = new Stack<>();
    public void save(Editor e) { stack.push(e.save()); }
    public void undo(Editor e) { e.restore(stack.pop()); }
}
```

**什么时候用**：
- ✅ 编辑器撤销/重做
- ✅ 数据库事务回滚、游戏存档

---

#### 19. Observer（观察者模式）

**问题**：对象间**一对多依赖**，当一个对象状态变化，所有依赖者都收到通知

**代码骨架**：
```java
interface Observer { void update(String msg); }
class Subject {
    private List<Observer> observers = new ArrayList<>();
    public void attach(Observer o) { observers.add(o); }
    public void notify(String msg) { for (Observer o : observers) o.update(msg); }
}
```

**什么时候用**：
- ✅ 事件处理（DOM 事件、Vue/React 响应式）
- ✅ 消息队列（pub-sub）、MVC 中的 Model-View

**注意**：避免循环依赖；考虑线程安全。

---

#### 20. State（状态模式）

**问题**：对象**行为随状态变化**而变化，用大量 if-else 难维护

**代码骨架**：
```java
interface State { void handle(Context c); }
class ConcreteStateA implements State {
    public void handle(Context c) { c.setState(new ConcreteStateB()); }
}
class Context {
    private State state;
    public void request() { state.handle(this); }
}
```

**什么时候用**：
- ✅ 订单状态（待支付/已支付/已发货/已完成）
- ✅ TCP 连接状态、工作流引擎

---

#### 21. Strategy（策略模式）

**问题**：多种算法可互换，**避免硬编码**具体算法

**代码骨架**：
```java
interface PaymentStrategy { void pay(int amount); }
class CreditCardStrategy implements PaymentStrategy { /*...*/ }
class PayPalStrategy implements PaymentStrategy { /*...*/ }
class ShoppingCart {
    private PaymentStrategy strategy;
    public void setStrategy(PaymentStrategy s) { this.strategy = s; }
    public void checkout(int amount) { strategy.pay(amount); }
}
```

**什么时候用**：
- ✅ 排序算法选择、支付方式选择
- ✅ 压缩算法、加密算法

**典型应用**：**Replace Conditional with Polymorphism**（用多态取代条件）

---

#### 22. Template Method（模板方法模式）

**问题**：算法的**整体结构固定**，但某些步骤由子类实现

**代码骨架**：
```java
abstract class Game {
    public final void play() {  // 模板方法
        initialize();
        startPlay();
        endPlay();
    }
    abstract void initialize();
    abstract void startPlay();
    abstract void endPlay();
}
```

**什么时候用**：
- ✅ 框架（Spring 的 JdbcTemplate、HttpServlet）
- ✅ 测试框架（setUp/test/tearDown）

---

#### 23. Visitor（访问者模式）

**问题**：对复杂对象结构进行**多种操作**，避免污染元素类

**代码骨架**：
```java
interface Visitor {
    void visit(ConcreteElementA a);
    void visit(ConcreteElementB b);
}
interface Element { void accept(Visitor v); }
class ConcreteElementA implements Element {
    public void accept(Visitor v) { v.visit(this); }
}
```

**什么时候用**：
- ✅ 编译器 AST 遍历
- ✅ 文件系统操作（打印、统计、删除）
- ✅ XML/JSON 解析

**缺点**：难以增加新元素（所有 visitor 都要改）

---

## PART 3: 并发模式（POSA 2）

> 来自《Pattern-Oriented Software Architecture, Volume 2》

#### 24. Active Object（主动对象）

**问题**：方法调用和执行不在同一线程，要解耦

**解决方案**：对象有自己的执行线程，方法调用转消息入队

**什么时候用**：
- ✅ GUI 事件处理、异步 I/O
- ✅ Actor 模型（Erlang/Akka）

---

#### 25. Monitor Object（监视器对象）

**问题**：并发访问共享对象，需要线程安全

**解决方案**：synchronized 方法，同一时刻只一个线程

**什么时候用**：任何共享可变状态

---

#### 26. Balking（拒绝模式）

**问题**：对象状态不允许操作时，**静默返回**（不等待、不抛错）

**代码骨架**：
```java
class Printer {
    private boolean busy;
    public void print(String job) {
        if (busy) return;  // Balking
        busy = true;
        // 实际打印
        busy = false;
    }
}
```

**什么时候用**：
- ✅ 自动保存（已在保存中就跳过）
- ✅ 防止重复操作

---

#### 27. Double-Checked Locking（双重检查锁定）

**问题**：延迟初始化的线程安全单例

**什么时候用**：
- ✅ 单例模式的懒加载
- ⚠️ Java 5+ volatile 关键字必需

---

#### 28. Guarded Suspension（保护性悬挂）

**问题**：方法需要等待**某个条件成立**才能继续

**代码骨架**：
```java
synchronized void guardedMethod() {
    while (!conditionMet()) {
        wait();  // 释放锁并等待
    }
}
```

**什么时候用**：生产者-消费者、阻塞队列

---

#### 29. Immutable Object（不可变对象）

**问题**：共享对象需要绝对线程安全

**解决方案**：所有字段 final、无 setter、防御性拷贝

**什么时候用**：
- ✅ String、Integer、LocalDateTime
- ✅ 多线程共享数据、简化并发

---

#### 30. Lock Object（锁对象）

**问题**：需要比 synchronized 更灵活的锁

**什么时候用**：
- ✅ 需要 tryLock、可中断、公平性

---

#### 31. Read-Write Lock（读写锁）

**问题**：读多写少场景，普通锁性能差

**什么时候用**：缓存系统、配置中心

---

#### 32. Thread Pool（线程池）

**问题**：频繁创建/销毁线程开销大

**什么时候用**：几乎所有服务端程序

---

#### 33. Thread-Local Storage（线程局部存储）

**问题**：每个线程需要自己的独立变量副本

**代码骨架**：
```java
private static ThreadLocal<User> currentUser = ThreadLocal.withInitial(() -> null);
```

**什么时候用**：
- ✅ Web 请求上下文（Spring RequestContextHolder）
- ✅ 数据库连接、事务管理

---

## PART 4: 企业/分布式模式

> 来自 Sun J2EE BluePrints、Microsoft Patterns & Practices

#### 34. Repository（仓储模式）

**问题**：业务层和数据访问层耦合

**什么时候用**：
- ✅ DDD（领域驱动设计）
- ✅ 任何需要数据访问抽象的项目

---

#### 35. Unit of Work（工作单元）

**问题**：一组对象修改，要么全成功要么全失败

**什么时候用**：
- ✅ 数据库事务
- ✅ Hibernate Session、Entity Framework DbContext

---

#### 36. Identity Map（标识映射）

**问题**：同一对象在内存中只保留一份

**什么时候用**：ORM 框架

---

#### 37. Service Locator（服务定位器）

**问题**：组件需要访问各种服务

**什么时候用**：
- ✅ 简单项目
- ⚠️ 不推荐复杂项目（隐藏依赖，难测试），改用 DI

---

#### 38. Data Transfer Object（数据传输对象）

**问题**：远程调用频繁，每次传多个参数

**什么时候用**：RPC、REST API、跨进程通信

---

#### 39. Front Controller（前端控制器）

**问题**：所有请求都需统一预处理

**什么时候用**：
- ✅ Spring MVC DispatcherServlet
- ✅ Express.js Router

---

#### 40. Interceptor（拦截器）

**问题**：在方法执行前后插入通用逻辑

**什么时候用**：
- ✅ Spring Interceptor、Java Servlet Filter
- ✅ AOP 实现机制

---

## PART 5: 现代模式（云原生/微服务）

#### 41. Dependency Injection（依赖注入）

**问题**：组件之间依赖关系硬编码

**三种形式**：构造器注入（推荐）、Setter 注入、接口注入

**什么时候用**：
- ✅ Spring、Guice、Dagger
- ✅ NestJS、Angular

---

#### 42. Publish-Subscribe（发布订阅）

**问题**：发布者和订阅者解耦

**和 Observer 的区别**：
- Observer：直接引用，一对多同步
- Pub-Sub：通过 broker，多对多异步

**什么时候用**：
- ✅ Kafka、RabbitMQ、RocketMQ
- ✅ 微服务通信

---

#### 43. CQRS（Command Query Responsibility Segregation）

**问题**：读写模型不一致、读写性能差异大

**什么时候用**：
- ✅ 高并发读写分离
- ✅ 事件溯源系统

---

#### 44. Event Sourcing（事件溯源）

**问题**：传统数据库只存当前状态，丢失历史

**什么时候用**：
- ✅ 金融系统、审计要求高的系统
- ✅ 复杂业务状态变迁

---

#### 45. Saga（长事务）

**问题**：分布式事务，传统 2PC 性能差

**两种类型**：编排式（Orchestration）、编制式（Choreography）

**什么时候用**：
- ✅ 微服务分布式事务
- ✅ 跨服务业务流程

---

#### 46. Circuit Breaker（断路器）

**问题**：依赖服务故障，导致调用方雪崩

**什么时候用**：
- ✅ 微服务调用
- ✅ Hystrix、Resilience4j、Sentinel

---

#### 47. Bulkhead（舱壁模式）

**问题**：一个组件故障拖垮整个系统

**什么时候用**：
- ✅ 微服务容错
- ✅ Hystrix 线程池隔离

---

#### 48. Sidecar（边车模式）

**问题**：辅助功能（日志、监控、配置）每个服务都要实现

**什么时候用**：
- ✅ Service Mesh（Istio、Linkerd）
- ✅ Kubernetes Pod 设计

---

#### 49. Ambassador（大使模式）

**问题**：应用需要重试、熔断、TLS、监控等网络功能

**什么时候用**：
- ✅ 遗留系统接入现代协议
- ✅ 网络功能抽象

---

#### 50. Anti-Corruption Layer（防腐层）

**问题**：新旧系统集成，旧模型污染新系统

**什么时候用**：
- ✅ 遗留系统迁移
- ✅ DDD 限界上下文集成

---

#### 51. Strangler Fig（绞杀者模式）

**问题**：不能一次性重写遗留系统

**什么时候用**：
- ✅ 遗留系统现代化
- ✅ 大型系统重构

---

## PART 6: 反模式（Anti-patterns）

> 看到就立即警告

#### 52. God Object（上帝对象）

**症状**：类有 30+ 方法、多个模块都依赖它

**解决**：单一职责原则、拆分

---

#### 53. Spaghetti Code（意大利面代码）

**症状**：控制流混乱、回调地狱

**解决**：重构为清晰结构、用 async/await 替代回调

---

#### 54. Golden Hammer（黄金锤）

**症状**：在所有项目都用同一种技术

**解决**：工具匹配问题、学习多种方案

---

#### 55. Premature Optimization（过早优化）

**症状**：在没测量前就优化

**Donald Knuth**："过早优化是万恶之源"

**正确做法**：先写清晰代码、用 profiler 找瓶颈、只优化关键路径

---

#### 56. Copy-Paste Programming（复制粘贴编程）

**症状**：同样代码到处都有

**解决**：提取公共方法、DRY 原则

---

#### 57. Big Ball of Mud（大泥球）

**症状**：系统结构完全丧失

**解决**：重构（Strangler Fig）、引入架构（分层、模块化）

---

#### 58. Magic Numbers / Strings（魔数/魔字符串）

**症状**：代码中散落不明含义的字面量

**反例**：
```java
if (status == 3) {  // 3 是什么？
    // ...
}
```

**解决**：
```java
enum OrderStatus { PENDING, PAID, SHIPPED, COMPLETED }
if (status == OrderStatus.PAID) { /*...*/ }
```

---

#### 59. Hard Coding（硬编码）

**症状**：配置信息（URL、密钥、路径）写在代码里

**解决**：配置文件、环境变量、配置中心

---

#### 60. Analysis Paralysis（分析瘫痪）

**症状**：过度设计，花太多时间分析

**解决**：迭代式开发、YAGNI、最小可行产品

---

#### 61. Death by Planning（计划死）

**症状**：写代码前画了 50 张图，永远不写代码

**解决**：敏捷开发、文档够用即可、代码即文档

---

#### 62. Bikeshedding（自行车棚效应）

**症状**：在琐碎细节上花大量时间（如命名），而忽略关键决策

**解决**：设定时间盒、重要问题优先

---

## PART 7: 模式选择决策矩阵（速查）

### 按问题类型速查

| 问题 | 推荐模式 |
|------|----------|
| 对象创建复杂 | Factory Method / Abstract Factory / Builder |
| 对象只有一个实例 | Singleton（慎用）|
| 创建对象成本高 | Prototype |
| 接口不兼容 | Adapter |
| 多维度变化 | Bridge |
| 树形结构 | Composite |
| 动态加功能 | Decorator |
| 简化复杂子系统 | Facade |
| 大量相似对象 | Flyweight |
| 控制访问 | Proxy |
| 请求链处理 | Chain of Responsibility |
| 撤销/重做 | Command / Memento |
| 文法解析 | Interpreter |
| 顺序访问 | Iterator |
| 复杂对象通信 | Mediator |
| 状态变化 | State |
| 算法可替换 | Strategy |
| 步骤固定 | Template Method |
| 操作复杂结构 | Visitor |
| 一对多通知 | Observer |
| 线程安全 | Immutable / Monitor / Lock |
| 异步调用 | Active Object |
| 条件等待 | Guarded Suspension |
| 一致性保证 | Identity Map / Unit of Work |
| 微服务容错 | Circuit Breaker / Bulkhead |
| 分布式事务 | Saga |
| 读写分离 | CQRS |
| 事件流 | Event Sourcing |
| 渐进式迁移 | Strangler Fig |
| 跨系统兼容 | Anti-Corruption Layer |

### 按 SOLID 原则反查

| 原则 | 模式 |
|------|------|
| **SRP** 单一职责 | Facade / Repository |
| **OCP** 开闭 | Strategy / Decorator / Chain |
| **LSP** 里氏替换 | Template Method / Strategy |
| **DIP** 依赖倒置 | Dependency Injection / Bridge |
| **ISP** 接口隔离 | Adapter / Facade |
| **LoD** 迪米特 | Facade / Mediator |
| **DRY** | Template Method / Strategy |

---

## PART 8: 实战模板

### 重构输出标准格式

当用户给出代码问"怎么改"时，按以下模板输出：

```markdown
## 诊断
**坏味道**：[具体坏味道名]
**违反原则**：[SOLID 哪条]
**位置**：[文件:行号]

## 建议
**应用模式**：[模式名]
**理由**：[为什么这个模式解决该问题]
**风险**：[低/中/高] + 原因

## 实施
### Before
[原始代码片段]

### After
[重构后代码片段]

### 验证
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 行为不变（接口契约保持）
- [ ] 性能无显著下降
```

### 完整示例：Long Method → Extract Method

**Before**：
```python
def process_order(order):
    # 验证
    if not order.items: raise ValueError("empty")
    if order.total < 0: raise ValueError("negative")
    # 计算价格
    subtotal = sum(i.price * i.qty for i in order.items)
    tax = subtotal * 0.1
    discount = 0
    if order.customer.is_vip: discount = subtotal * 0.15
    total = subtotal + tax - discount
    # 保存
    order.total = total
    db.save(order)
    # 发邮件
    send_email(order.customer.email, "Order confirmed", ...)
    # 记录日志
    log.info(f"Order {order.id} processed")
```

**After**：
```python
def process_order(order):
    _validate(order)
    order.total = _calculate_total(order)
    _save(order)
    _notify_and_log(order)

def _validate(order):
    if not order.items: raise ValueError("empty")
    if order.total < 0: raise ValueError("negative")

def _calculate_total(order):
    subtotal = sum(i.price * i.qty for i in order.items)
    return subtotal * 1.1 - _get_discount(order, subtotal)

def _get_discount(order, subtotal):
    return subtotal * 0.15 if order.customer.is_vip else 0

def _save(order): db.save(order)
def _notify_and_log(order):
    send_email(order.customer.email, "Order confirmed", ...)
    log.info(f"Order {order.id} processed")
```

---

## QUICK DECISION MATRIX

| 你看到 | 应该用 |
|--------|--------|
| `if-elif-else` 按 type 字段 | **Strategy** + 多态 |
| 复杂构造函数 (> 3 个参数) | **Builder** |
| 类有 30+ 方法 | 拆类 + **Facade** |
| 重复代码 ≥ 3 处 | **Extract Method** + **Template Method** |
| 全局变量访问 | **Encapsulate Variable** + 考虑 DI |
| 长消息链 `a.b.c.d()` | **Hide Delegate** |
| 数据库访问散落 | **Repository** |
| 微服务间通信 | **Pub-Sub** + **Circuit Breaker** |
| 大量 `new ConcreteClass()` | **Factory** + **DI** |
| 共享可变状态并发 | **Immutable Object** / **Lock** |
| 一对多事件通知 | **Observer** |
| 算法步骤固定细节不同 | **Template Method** |
| 多维度变化 | **Bridge** |
| 操作树形结构 | **Composite** |
| 撤销/重做 | **Command** + **Memento** |

---

## 终极原则

> **"模式为问题而生，不为模式而模式"** — GoF

❌ **不要**为了用模式而用模式
❌ **不要**在简单问题上套复杂模式
✅ **优先**用语言/库的内置机制（Java 8+ Stream、Python itertools）
✅ **Keep It Simple, Stupid** (KISS)
✅ **You Ain't Gonna Need It** (YAGNI)

**终极判断**：重构后代码是否更**易读、易测、易改**？否则不要重构。

---

## 推荐阅读

1. **《设计模式：可复用面向对象软件的基础》** — GoF, 1994
2. **《Head First 设计模式》** — Freeman 等（入门首选）
3. **《Effective Java》** — Joshua Bloch
4. **《重构：改善既有代码的设计 2e》** — Martin Fowler
5. **《Clean Code》** — Robert C. Martin
6. **《微服务设计模式》** — Chris Richardson
7. **https://refactoring.guru/** — 最佳在线资源
