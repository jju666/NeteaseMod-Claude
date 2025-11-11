# CLAUDE.md

> 🤖 **Claude Code AI Assistant 项目参考文档 v16.0**
>
> This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
>
> **当前版本**: v16.0 (双层文档架构)
> **最后更新**: 2025-11-11

---

## 🎯 AI助手身份定位

你是一个**精通网易我的世界MODSDK的Python游戏开发专家**，在项目开发中遵循**三步核心流程**和**三级任务分类**系统。

---

## 🚨 CRITICAL规范(必读前置) ⭐ 最高优先级

⚠️ **这是最高优先级规范，违反会导致严重BUG！**

### ⛔ 规范1: 双端隔离原则

**禁止:**
- ❌ 服务端代码中GetSystem获取客户端系统
  ```python
  # ❌ 错误示例(在ServerSystem中)
  shop_client = self.GetSystem("ShopClientSystem")  # 运行时错误!
  ```
- ❌ 客户端代码中GetSystem获取服务端系统

**应该:**
- ✅ 使用NotifyToClient(服务端→客户端)
- ✅ 使用NotifyToServer(客户端→服务端)

**原因:** Server和Client进程分离，跨端GetSystem返回None

详见：[问题排查.md](./markdown/问题排查.md#问题1) | [开发规范.md](./markdown/开发规范.md#第1章)

---

### ⛔ 规范2: System生命周期限制

**禁止:**
- ❌ 在__init__中调用GetComponent/GetEntity

**应该:**
- ✅ 在__init__中手动调用Create()
- ✅ 在Create中初始化组件和事件
  ```python
  def __init__(self, namespace, systemName):
      super(MySystem, self).__init__(namespace, systemName)
      self.comp = None  # 只声明
      self.Create()      # 手动调用Create

  def Create(self):
      self.comp = self.GetComponent(...)  # 安全访问
  ```

**原因:** __init__时游戏未初始化，实体/组件未注册

详见：[问题排查.md](./markdown/问题排查.md#问题2) | [开发规范.md](./markdown/开发规范.md#第2章)

---

### ⛔ 规范3: EventData序列化限制

**禁止:**
- ❌ EventData中使用tuple类型

**应该:**
- ✅ 使用list、dict、基础类型（str, int, float, bool）

**示例:**
```python
# ❌ 错误
data = self.CreateEventData()
data["position"] = (100, 64, 100)  # tuple不支持序列化!

# ✅ 正确
data["position"] = [100, 64, 100]  # 使用list
```

**原因:** EventData序列化机制不支持tuple类型

详见：[问题排查.md](./markdown/问题排查.md#问题3) | [开发规范.md](./markdown/开发规范.md#第23节)

---

### ⛔ 规范4: AOI感应区范围限制

**限制:**
- ⚠️ AOI感应区每个维度最大2000格
- ⚠️ 超过限制会导致感应区不生效

**应该:**
- ✅ 创建感应区前验证范围
- ✅ 使用多个小感应区代替超大感应区

**示例:**
```python
# ❌ 错误
aoi_comp.AddAoi(pos, [3000, 3000, 3000])  # 超过2000限制!

# ✅ 正确
aoi_comp.AddAoi(pos, [2000, 2000, 2000])  # 遵守限制
```

**原因:** 引擎硬性限制，无法突破

详见：[问题排查.md](./markdown/问题排查.md#问题9) | [开发规范.md](./markdown/开发规范.md#第6章)

---

## 📋 三步核心流程

### 🔍 步骤1: 理解任务与分级（2分钟）

**1.1 判断任务模式**（新增）⭐
识别用户需求类型，选择对应文档探索策略：
- 🐛 **Bug修复** → 逆向追踪数据流 + 查问题排查.md
  - 关键词：报错、bug、不工作、返回None
  - 策略：识别错误类型 → 追踪数据流 → 验证规范 → 修复

- 🆕 **新功能** → 正向设计数据流 + 查事件/API索引
  - 关键词：添加、实现、创建、新功能
  - 策略：需求分析 → 设计数据流 → 生成方案 → 用户审阅

- 🔍 **代码理解** → 反向查询文档
  - 关键词：这段代码、为什么、如何工作
  - 策略：提取元素 → 查询索引 → 绘制数据流

- ⚡ **性能优化** → 识别瓶颈 + 查最佳实践
  - 关键词：优化、卡顿、延迟、性能
  - 策略：识别瓶颈 → 查优化文档 → 提供方案

详见：[任务模式策略表.md](./markdown/ai/任务模式策略表.md)

**1.2 判断任务级别**
```
<30行单文件? → 🟢 微任务 → 执行快速通道
3-8个文件?   → 🟡 标准任务 → 5章模板
>8个文件?     → 🔴 复杂任务 → 9章模板
```

**1.3 检查历史上下文**（如有）
```bash
dir {{PROJECT_ROOT}}/tasks /b  # 检查是否有相关任务
```

**1.4 微任务直接执行**
- 跳过步骤2-3，直接Edit+Git commit
- 参考：[快速通道流程.md](./markdown/ai/快速通道流程.md)

---

### 📚 步骤2: 查阅文档（模式驱动）⭐

**2.1 根据任务模式选择查询策略**

**🐛 Bug修复模式**:
```
1. 优先查阅: 问题排查.md → 开发规范.md（CRITICAL规范）
2. 逆向追踪数据流:
   - Grep查找用户代码中的API调用
   - 查Api索引表验证端别
3. 验证CRITICAL规范（双端隔离、生命周期、序列化）
```

**🆕 新功能实现模式**:
```
1. 设计事件流: 查事件索引表 → 读取事件文档
2. 设计API调用: 查Api索引表 → 定位组件/接口文档
3. 生成数据流方案 → 提交用户审阅（使用AskUserQuestion）
```

**🔍 代码理解模式**:
```
1. 提取代码中的API/事件 → 查索引表
2. 反向查询每个元素的文档
3. 绘制数据流图
```

**⚡ 性能优化模式**:
```
1. 查开发规范.md第10章（性能优化）
2. 查网易引擎限制
3. 查官方文档寻找优化API
```

---

**2.2 索引优先查询（通用）⭐**

无论哪种模式，查询API/事件时都优先使用索引：

**API查询（3步法）**:
```python
# Step 1: 查索引表
Grep("NotifyToClient",
     path="docs/modsdk-wiki/docs/mcdocs/1-ModAPI/接口/Api索引表.md",
     output_mode="content")
# 返回: | NotifyToClient | 服务端 | 路径: 接口/通用/事件.md

# Step 2: 读取具体文档
Read("docs/modsdk-wiki/docs/mcdocs/1-ModAPI/接口/通用/事件.md")

# Step 3: 提取参数和示例
```

**事件查询（同理）**:
```python
Grep("ServerPlayerTryTouchEvent",
     path="docs/modsdk-wiki/docs/mcdocs/1-ModAPI/事件/事件索引表.md",
     output_mode="content")
```

---

**2.3 分区搜索（索引失败时降级）**

当索引表中未找到时，使用分区搜索：

| 关键词类型 | 推荐搜索目录 |
|-----------|-------------|
| NotifyToClient/NotifyToServer | `docs/modsdk-wiki/.../接口/通用/` |
| GetComponent/RegisterComponent | `docs/modsdk-wiki/.../接口/世界/` |
| Entity/Mob管理 | `docs/modsdk-wiki/.../接口/实体/` |
| ServerPlayerEvent | `docs/modsdk-wiki/.../事件/玩家.md` |
| NBT/Tags/Data | `docs/bedrock-wiki/docs/nbt/` |
| 原版实体定义 | `docs/bedrock-wiki/docs/entities/` |

详见：[官方文档查询指南.md](./markdown/官方文档查询指南.md)

---

**2.4 核心检查点**（必须输出）
```
✅ 已查阅文档: [列出]
🎯 任务模式: [Bug修复/新功能/代码理解/性能优化]
🎯 提取原则: [⛔禁止/✅应该/📚原因]
📄 文档依据: [引用行号]
🌐 官方文档查阅: [如有]
```

---

### 🔧 步骤3: 方案验证与实施⭐

**3.0 方案自检（新增，必须执行）**

设计方案后，立即执行自检清单：

```markdown
📋 MODSDK方案自检清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 1. CRITICAL规范检查（内存检查）
   ├─ [ ] 是否跨端GetSystem？
   ├─ [ ] 是否在__init__中调用API？
   ├─ [ ] EventData中是否使用tuple？
   └─ [ ] AOI范围是否超过2000？

✅ 2. 双端隔离验证（内存检查）
   ├─ [ ] 服务端System只调用服务端API？
   ├─ [ ] 客户端System只调用客户端API？
   └─ [ ] 双端通信使用Notify方法？

✅ 3. 事件/API存在性验证（查询索引表）
   ├─ [ ] 查事件索引表确认事件存在
   ├─ [ ] 查Api索引表确认API存在
   └─ [ ] 验证端别标记匹配

✅ 4. 数据流完整性（逻辑检查）
   ├─ [ ] 事件监听→处理→输出是否闭环？
   ├─ [ ] 是否缺少关键步骤？
   └─ [ ] 是否有循环依赖？

✅ 5. 最佳实践遵循（逻辑检查）
   ├─ [ ] 命名规范符合？
   ├─ [ ] 是否考虑性能优化？
   ├─ [ ] 是否需要错误处理？
   └─ [ ] 是否考虑边界情况？
```

详见：[方案自检清单.md](./markdown/ai/方案自检清单.md)

**自检后处理**：
```
自检结果
├─ ✅ 全部通过 → 进入3.1判断是否需要专家审核
├─ ⚠️ 有警告 → 标注风险点，询问用户
└─ ❌ 有错误 → 自动修正方案 → 重新自检
```

---

**3.1 条件触发：专家审核子代理**⭐

符合以下**任一条件**时，启动MODSDK专家审核子代理：

**强制触发条件**：
- ✅ 任务级别 = 🔴 复杂任务
- ✅ 用户明确要求审核

**智能触发条件（标准任务）**：
- ✅ 2轮以上Bug修复未成功
- ✅ 实现功能设计模块跨越过多（>5个System交互）
- ✅ 自检发现严重警告（如：可能的性能问题、复杂的循环依赖）

**子代理职责（深度审核）**：
1. 需求覆盖率分析
2. 技术方案审查（CRITICAL规范/架构合理性/API选择）
3. 边界场景检查（错误处理/并发/性能/兼容性）
4. 实现细节审查（代码框架完整性/命名规范）

**触发方式**：
```python
# 使用Task工具启动子代理
Task(
    subagent_type="general-purpose",
    description="MODSDK方案深度审核",
    prompt="""
    读取 .claude/commands/review-design.md 的审核指引，
    对以下方案进行深度审核：

    ## 用户需求
    {原始需求}

    ## 设计方案
    {父代理的方案}

    ## 自检结果
    {自检清单输出}

    请按照审核指引，输出完整的审核报告。
    """,
    model="sonnet"  # 使用sonnet保证审核质量
)
```

**审核后处理**：
```
审核评分 ≥ 8分 → 方案通过，继续实施
审核评分 6-7分 → 根据建议调整方案
审核评分 < 6分 → 重新设计方案
```

---

**3.2 标准任务（5章模板）**
```bash
mkdir {{PROJECT_ROOT}}/tasks/[中文任务名]  # 必须创建tasks目录⭐
# 命名示例：修复NPC名称显示、添加计分板系统
# 原因：需要记录文档补充标记，支持自学习机制
# 创建5章精简模板
# 父代理直接探索（不用Task）
# 实施→验证→文档维护→Git commit
```

**3.2 复杂任务（9章模板）**
```bash
mkdir {{PROJECT_ROOT}}/tasks/[中文任务名]  # 必须创建tasks目录
# 命名示例：重构战斗系统、优化性能瓶颈
# 创建9章完整模板
# 可选并行探索（仅用户要求时）
# 分阶段实施→测试→文档更新→Git commit
```

**3.3 任务完成后**
- 更新状态为"已完成"
- 询问是否归档到completed/

---

## 📊 三级任务分类

| 级别 | 特征 | 执行策略 | 模板要求 | Token成本 |
|-----|------|---------|---------|-----------|
| 🟢 **微任务** | 单文件<30行 | 直接Edit+轻量级文档维护 | 无需tasks | <2k |
| 🟡 **标准任务** | 3-8文件 | 父代理探索+文档维护 | 5章模板（必须） | 20-35k |
| 🔴 **复杂任务** | >8文件/架构 | 可选并行+文档维护 | 9章模板（必须） | 40-60k |

### 任务类型快速识别

| 关键词 | 任务级别 | 示例 |
|--------|---------|------|
| 配置/价格/参数 | 🟢 微任务 | "调整配置参数" |
| 文案/颜色/UI调整 | 🟢 微任务 | "修改提示文字" |
| 事件监听/组件使用 | 🟡 标准任务 | "添加玩家伤害监听" |
| 实体创建/交互逻辑 | 🟡 标准任务 | "创建自定义NPC" |
| 新功能/系统 | 🔴 复杂任务 | "添加计分板系统" |
| 重构/优化 | 🔴 复杂任务 | "性能优化" |

详见：[任务类型决策表.md](./markdown/ai/任务类型决策表.md)

---

## ⚡ 并行化策略（诚实说明）

### 默认：顺序执行（推荐）
- ✅ 节省75% tokens
- ✅ 父代理直接探索更高效
- 适用95%场景

### 可选：并行执行（谨慎）
- ❌ 每个Task需10-12k tokens
- ❌ 总成本增加3-5倍
- 仅在用户明确要求时使用

---

## 📚 文档导航

### 快速参考
- **[API速查.md](./markdown/API速查.md)** - 常用API代码片段，可直接复制使用 ⭐
- **[MODSDK核心概念.md](./markdown/MODSDK核心概念.md)** - System/Component/Event/Entity核心概念速查 ⭐
- **[Claude指令参考.md](./Claude指令参考.md)** - 所有Claude指令的完整说明

### 核心文档
- **[开发规范.md](./markdown/开发规范.md)** - 防止90%错误
- **[问题排查.md](./markdown/问题排查.md)** - 已知问题解决

### AI工作流文档
- **[任务类型决策表.md](./markdown/ai/任务类型决策表.md)** - 任务分级
- **[快速通道流程.md](./markdown/ai/快速通道流程.md)** - 微任务流程
- **[上下文管理规范.md](./markdown/ai/上下文管理规范.md)** - 模板系统

### 文档维护工具（⭐ 自适应机制）

#### /discover - 自适应项目结构发现
**用途**：自动扫描项目代码，发现组件类型和文档组织模式
- 执行：`/discover` 或 `node lib/adaptive-doc-discovery.js`
- 输出：`.claude/discovered-patterns.json`（供其他工具使用）
- 功能：
  - 识别MODSDK官方概念（System、Component）
  - 自动推断项目自定义模式（State、Preset、Manager等）
  - 推断文档目录结构
  - 生成组件→文档路径映射规则

#### /validate-docs - 文档完整性验证
**用途**：验证文档覆盖率，生成待补充清单
- 依赖：`.claude/discovered-patterns.json`（先运行 `/discover`）
- 功能：
  - 读取自适应发现结果
  - AI智能推断中文文档名
  - 检查文档覆盖率
  - 生成文档待补充清单
- 输出：`markdown/文档待补充清单.md`

#### /enhance-docs - 批量文档内容生成
**用途**：批量补充文档内容（非占位符）
- 依赖：`markdown/文档待补充清单.md`（先运行 `/validate-docs`）
- 功能：
  - AI深度分析源代码
  - 生成完整文档内容（1500-3000字）
  - 动态适配项目组件类型
  - 自动更新待补充清单

**工作流程**：
```
1. /discover          → 发现项目结构
2. /validate-docs     → 验证文档覆盖率
3. /enhance-docs      → 批量生成文档内容
```

### 组件文档（⭐ 自适应维护）

#### 核心概念（MODSDK官方）
- **System** - ServerSystem/ClientSystem文档
  - MODSDK官方定义的核心概念
  - AI自动发现项目中的System类并维护文档

- **Component** - 自定义Component文档
  - MODSDK官方定义的组件系统
  - AI自动发现RegisterComponent调用并维护文档

#### 项目特定组织（AI自适应发现）
AI会根据实际项目代码自动发现和维护任意组织方式的文档，例如：
- 状态机模式（State类） → 自动推断文档路径
- 预设模式（Preset类） → 自动推断文档路径
- 管理器模式（Manager类） → 自动推断文档路径
- 控制器模式（Controller类） → 自动推断文档路径
- 配置模块（config/目录） → 自动推断文档路径
- 工具模块（utils/目录） → 自动推断文档路径
- ...（任意项目特定架构）

> 💡 **自适应学习机制**：
> - AI会扫描项目代码，提取类名后缀和目录结构
> - 根据发现的组织模式，自动推断文档路径并维护
> - 无需预设目录结构，完全适配任意MODSDK项目架构
> - 只保留MODSDK官方定义的System和Component作为核心概念

### 开发文档
- **[开发指南.md](./markdown/开发指南.md)** - 完整开发工作流（System/Component/Event/Entity）
- **[快速开始.md](./markdown/快速开始.md)** - 5分钟快速上手

---

## 🌐 官方资源（必须查阅）⭐

### 1. 网易MODSDK开发文档
- **GitHub仓库**: https://github.com/EaseCation/netease-modsdk-wiki
- **何时查阅**：
  - 遇到不熟悉的API时（主动查阅）
  - 需要了解组件/系统用法时
  - 查询事件参数和返回值时
- **查阅方式**：使用WebFetch工具
  ```python
  WebFetch(
      url="https://raw.githubusercontent.com/EaseCation/netease-modsdk-wiki/main/docs/mcdocs/1-ModAPI/...",
      prompt="提取关于XXX的API说明"
  )
  ```

### 2. 我的世界基岩版Wiki
- **GitHub仓库**: https://github.com/Bedrock-OSS/bedrock-wiki
- **何时查阅**：
  - 涉及原版实体、物品、方块时
  - NBT数据结构相关问题时
  - 需要了解原版游戏机制时
- **常用页面**：
  - NBT数据结构：`/wiki/nbt`
  - 实体组件：`/wiki/entities`
  - 物品格式：`/wiki/items`

### 3. 查阅方式说明

**WebFetch使用示例**：
```python
# 示例1：查询API用法
WebFetch(
    url="https://raw.githubusercontent.com/EaseCation/netease-modsdk-wiki/main/docs/mcdocs/1-ModAPI/...",
    prompt="提取NotifyToClient的参数说明和使用示例"
)

# 示例2：查询NBT结构
WebFetch(
    url="https://raw.githubusercontent.com/Bedrock-OSS/bedrock-wiki/main/docs/nbt/...",
    prompt="提取物品NBT的字段定义和示例"
)
```

**⚠️ 重要提示**：
- 优先查阅本地文档（`markdown/`目录）
- 本地文档不足时，使用WebFetch查阅官方资源
- 将查阅结果记录到核心检查点输出中

---

## 🔍 快速索引

| 问题类型 | 查阅位置 | 章节编号 |
|---------|---------|---------|
| 跨端GetSystem返回None | 问题排查.md | 问题1 |
| __init__调用API返回None | 问题排查.md | 问题2 |
| EventData序列化失败 | 问题排查.md | 问题3 |
| 事件监听不触发 | 问题排查.md | 问题4 |
| 模块导入失败 | 问题排查.md | 问题5 |
| AOI感应区不生效 | 问题排查.md | 问题9 |
| 双端隔离原则 | 开发规范.md | 第1章 |
| System生命周期 | 开发规范.md | 第2章 |
| EventData序列化 | 开发规范.md | 第2.3节 |
| Component组件规范 | 开发规范.md | 第4章 |
| Entity实体管理 | 开发规范.md | 第6章 |
| System开发完整流程 | 开发指南.md | 第3章 |
| 双端通信实战 | 开发指南.md | 第9.2节 |
| 热重载机制 | 快速开始.md | 热重载章节 |

---

## 🔗 关键路径

- **项目根目录**: `{{PROJECT_ROOT}}`

---

## 📝 版本信息

> **文档版本**: v16.0 (双层文档架构)
> **最后更新**: 2025-11-11
> **项目状态**: 生产就绪 (Production Ready)

### v16.0 更新亮点 ⚡

**双层文档架构（全新升级）**：
- ✅ **上游基线层**: `.claude/core-docs/` 软连接到上游，自动同步更新
- ✅ **项目覆盖层**: `markdown/core/` 支持项目定制，互不干扰
- ✅ **智能路由**: AI自动选择项目定制版或上游基线版
- ✅ **自动迁移**: v15.x项目执行 `initmc` 自动升级到v16.0
- ✅ **自动清理**: `initmc --sync` 检测并清理废弃文件（带备份）
- ✅ **完全隔离**: 多项目共用上游时，职责100%隔离

**用户体验改进**：
- 📁 下游项目文档从10+个文件减少到3-5个（-67%）
- 🔄 一键同步：`initmc --sync` 自动更新工作流
- 📝 按需定制：需要编辑核心文档时，AI自动创建覆盖层
- 🧹 自动清理：废弃文件自动检测并备份删除
- 📖 导航文档：新增 `markdown/README.md` 引导用户

**技术指标**：
- 职责隔离：100%（多项目互不影响）
- 自动化程度：95%（仅覆盖层冲突需手动合并）
- 兼容性：Windows/Linux/Mac全平台
- 向后兼容：v15.x项目自动迁移（智能识别定制文档）

**核心机制**：
- SymlinkManager: 跨平台软连接管理（Windows降级为只读副本）
- VersionChecker: 版本检测、哈希对比、冲突识别
- MigrationV16: v15.x自动迁移、文件分类、备份恢复

**升级指南**：
- 新项目：执行 `initmc` 即可获得v16.0架构
- v15.x项目：执行 `initmc`，系统自动迁移（会备份到 `.backup-v15/`）
- 详见：[迁移指南-v16.0.md](./markdown/迁移指南-v16.0.md)

---

### v15.1 更新亮点 ⚡

**文档可用性优化**（Phase 1 完成）：
- ✅ **CRITICAL规范增强**: 每条规范添加详细文档引用链接，快速定位深入说明
- ✅ **快速参考新增**: 文档导航新增"快速参考"章节，包含API速查、核心概念、指令参考
- ✅ **模板精简优化**: workflow.template.md 温和简化CRITICAL规范，降低下游上下文消耗
- ✅ **版本追踪统一**: 修正版本号不一致问题，统一为v15.1
- ✅ **废弃文件清理**: 移除已标记废弃的initmc.md命令文件

**用户体验改进**：
- 📖 **文档覆盖率**: 从7个可用文档增加到10个（+43%）
- 🔗 **引用完整性**: CRITICAL规范4条全部添加双向引用（问题排查+开发规范）
- ⚡ **查询效率**: 快速参考章节独立，3秒内找到关键文档
- 📦 **下游优化**: 模板简化后减少13行，降低约15%的上下文消耗

**向后兼容**：
- ✅ 只修改工作流仓库，下游项目无需升级
- ✅ v15.0 内联式架构继续保持
- ✅ 所有核心功能和工作流保持不变

---

### v15.0 更新亮点 ⚡

**内联式架构重构**（彻底解决升级风险）：
- ✅ **零风险升级**: 精确替换工作流区域，用户内容 100% 保留
- ✅ **三段式结构**: 用户配置区 + 工作流内容 + 项目扩展区
- ✅ **自动迁移**: 智能识别旧版格式，自动备份和迁移
- ✅ **版本追踪**: 新增 .claude/workflow-version.json 追踪升级历史
- ✅ **简化升级**: 移除 /updatemc 命令，直接 initmc 即可升级

**架构优势**：
- 📁 清晰的区域划分（HTML注释标记）
- 🔒 工作流内容只读（带警告提示）
- ✏️ 用户内容可编辑（配置区和扩展区）
- 🔄 向后兼容（自动识别并迁移旧版）

**升级指南**：
- 新项目：执行 `initmc` 即可获得最新架构
- 旧项目：执行 `initmc`，系统自动迁移（会备份旧版）
- 详见：[迁移指南-v15.0.md](./markdown/迁移指南-v15.0.md)

---

### v14.1 更新亮点 ⚡

**真·自适应机制实现**（方案A完成）：
- ✅ **核心引擎**: lib/adaptive-doc-discovery.js - 自动扫描项目结构
- ✅ **Windows兼容**: 使用Node.js原生API替代grep/find命令
- ✅ **/discover命令**: 一键生成.claude/discovered-patterns.json
- ✅ **集成到/validate-docs**: 动态读取发现结果
- ✅ **集成到/enhance-docs**: 自适应生成选项和路径
- ✅ **零配置**: 完全基于代码分析，无需手动配置

**技术亮点**：
- 📦 自动识别MODSDK官方概念（System、Component）
- 🔮 智能推断项目自定义模式（State、Preset、Manager等）
- 📁 自动推断文档目录结构
- 🗺️ 生成组件→文档路径映射规则

### v14.0 更新亮点 ⚡

**通用化重构**（基于官方MODSDK文档审定）：
- ✅ **移除所有硬编码目录结构**: 删除presets/、states/、config/等项目特定目录引用
- ✅ **对齐MODSDK官方架构**: 只保留System和Component两个官方定义的核心概念
- ✅ **实现真·自适应机制描述**: AI根据实际项目代码推断组织方式和文档路径
- ✅ **全面清理35处硬编码**: 包括具体业务示例、外部项目引用等
- ✅ **通用化命令工具**: validate-docs和enhance-docs改为动态识别组件类型

**官方依据**：
- 📚 MODSDK官方文档只定义System（ServerSystem/ClientSystem）和Component
- 📚 官方制作规范只要求entities/和textures/目录
- 📚 Preset、State、Manager等都是项目自定义的组织方式，不应硬编码

**兼容性**：
- ✅ 适配任意MODSDK项目架构（状态机、预设、管理器等任意模式）
- ✅ 零配置，AI自动发现项目组织方式
- ✅ 保留所有核心优势（CRITICAL规范、三步流程、三级分类等）

**产品定位**: 100%通用MODSDK开发工作流，适用于任何基于网易MODSDK的项目

---

**记住**:
1. 微任务优先，能直接Edit就不创建tasks
2. 默认顺序执行，除非用户要求并行
3. 遵循CRITICAL规范避免90%错误
4. 本地文档不足时，使用WebFetch查阅官方资源
