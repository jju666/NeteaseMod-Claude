# CLAUDE.md

> 🤖 **Claude Code AI Assistant 项目参考文档 v16.2**
>
> This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
>
> **当前版本**: v16.2 (强制文档查阅 + 自学习闭环)
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

---



---

## 📋 三步核心流程

### 🔍 步骤1: 理解任务与分级（2分钟）

**1.1 判断任务级别**
```
<30行单文件? → 🟢 微任务 → 执行快速通道
3-8个文件?   → 🟡 标准任务 → 5章模板
>8个文件?     → 🔴 复杂任务 → 9章模板
```

**1.2 检查历史上下文**（如有）
```bash
dir tasks /b  # 检查是否有相关任务（Windows）
ls tasks/    # 检查是否有相关任务（Linux/Mac）
```

**1.3 微任务快速通道**
- 先查阅Systems文档定位代码
- 直接Edit修改
- 完成后更新文档
- Git commit
- 参考：[快速通道流程.md](./markdown/ai/快速通道流程.md)

---

### 📚 步骤2: 查阅文档（两阶段）⭐

#### **阶段A: 代码定位（必须第一步）** ⭐

**目标**：快速定位工作区域，避免盲目搜索

**1️⃣ 查阅项目文档（最高优先级）**
```python
# 所有任务类型都必须先查阅项目文档
# 根据项目类型自动选择：
# - System架构项目: markdown/systems/[系统名].md
# - 模块化项目: markdown/modules/[模块名].md
# - 其他架构: markdown/[相关文档].md

Read("markdown/[项目文档目录]/[相关模块].md")

# 提取关键信息：
# - 文件路径
# - 关键类/函数
# - 配置位置
# - 数据流向
```

**2️⃣ 定向搜索验证（文档提供关键词）**
```python
# 基于文档中的关键词进行精确搜索
Grep(pattern="[关键类名/函数名]", type="py")
```

**3️⃣ 盲目搜索（最后手段）**
```python
# 仅当前两步都失败时使用
Grep(pattern="[模糊关键词]", output_mode="content")
```

**输出检查点**：
```
📂 已查阅项目文档: [列出文件名]
🎯 定位到的代码位置: [文件路径:行号]
🔍 搜索策略: [文档定向/关键词搜索/盲目搜索]
```

---

#### **阶段B: 编码规范约束（防错检查）**

**目标**：避免常见错误，确保代码质量

**4️⃣ 查阅核心规范（修改代码前）**
```python
# 智能路由：优先项目覆盖层，回退上游基线
if exists("markdown/core/[文档名].md"):
    Read("markdown/core/[文档名].md")  # 📝 项目定制版
else:
    Read(".claude/core-docs/[文档名].md")  # 📦 上游基线

# 核心文档：
# - 开发规范.md: CRITICAL规范（双端隔离、生命周期等）
# - 问题排查.md: 已知问题和解决方案
```

**5️⃣ 查阅官方文档（遇到不熟悉API时）** ⭐
```python
# 优先读取本地Git Submodule（软连接到下游）
Read("docs/modsdk-wiki/docs/[模块路径]/[API名称].md")
Read("docs/bedrock-wiki/docs/[主题]/[页面].md")

# 仅在本地文档缺失时使用WebFetch
WebFetch(
    url="https://raw.githubusercontent.com/EaseCation/netease-modsdk-wiki/main/docs/...",
    prompt="提取关于[API名称]的使用说明"
)
```

**输出检查点**：
```
✅ 已查阅规范文档: [列出，标注📝/📦]
🎯 提取的约束原则: [⛔禁止/✅应该/📚原因]
📄 文档依据: [引用行号]
🌐 官方文档查阅: [本地/在线]
```

#### 2.2 AI编辑规则 ⚠️

**禁止编辑（只读）:**
- ❌ `.claude/core-docs/` (上游基线，软连接)
- ❌ `docs/` (官方文档，Git Submodule或软连接)

**允许编辑（可写）:**
- ✅ `markdown/core/` (项目覆盖层)
- ✅ `markdown/` (项目技术文档，根据项目类型自适应)
- ✅ `markdown/文档待补充清单.md` (项目跟踪)
- ✅ `tasks/` (任务历史)

**自动创建覆盖层:**
当AI需要编辑核心文档时，自动执行以下操作：
1. 检查 `markdown/core/[文档名].md` 是否存在
2. 如不存在，从 `.claude/core-docs/` 复制到 `markdown/core/`
3. 在文件头部添加项目定制标记：
   ```markdown
   <!-- 📝 项目定制版本 - 基于上游 v{{VERSION}} -->
   <!-- 本文件覆盖上游基线，仅影响当前项目 -->
   ```
4. 编辑项目副本

---

### 🔧 步骤3: 执行与收尾

**3.1 标准任务（5章模板）**
```bash
mkdir tasks/[任务名]
# 创建5章精简模板
# 父代理直接探索（不用Task）
# 实施→验证→Git commit
```

**3.2 复杂任务（9章模板）**
```bash
mkdir tasks/[任务名]
# 创建9章完整模板
# 可选并行探索（仅用户要求时）
# 分阶段实施→测试→文档更新→Git commit
```

**3.3 任务完成后（所有任务级别）** ⭐

**必须执行**：
1. **更新项目文档**
   - 根据项目类型更新对应文档（systems/modules/其他）
   - 补充新增的类/函数/配置位置
   - 更新文件结构（如有变化）
   - 标记文档最后更新时间

2. **维护文档清单**（如发现空白区域）
   - 更新 `markdown/文档待补充清单.md`
   - 标记文档质量问题

3. **Git commit**
   - 包含代码修改和文档更新

**可选操作**：
- 更新任务状态为"已完成"
- 询问是否归档到completed/

---

## 📊 三级任务分类

| 级别 | 特征 | 执行策略 | 模板要求 | Token成本 |
|-----|------|---------|---------|-----------|
| 🟢 **微任务** | 单文件<30行 | 直接Edit | 无需tasks | <2k |
| 🟡 **标准任务** | 3-8文件 | 父代理探索 | 5章模板 | 20-35k |
| 🔴 **复杂任务** | >8文件/架构 | 可选并行 | 9章模板 | 40-60k |

### 任务类型快速识别

| 关键词 | 任务级别 | 示例 |
|--------|---------|------|
| 配置/价格/参数 | 🟢 微任务 | "调整钻石剑价格" |
| 文案/颜色/UI调整 | 🟢 微任务 | "修改提示文字" |
| 预设/交互修复 | 🟡 标准任务 | "商店点击无响应" |
| 状态机/流程 | 🟡 标准任务 | "调整倒计时流程" |
| 新功能/系统 | 🔴 复杂任务 | "添加排行榜系统" |
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

### 文档架构说明 ⭐

本项目采用**双层文档架构**：

**📦 上游基线层（只读）**
- 位置：`.claude/core-docs/`（隐藏目录，软连接到上游仓库）
- 内容：核心工作流文档（开发规范、问题排查、AI工作流等）
- 更新：执行 `initmc --sync` 自动同步上游更新
- **⚠️ 禁止直接编辑**

**📝 项目覆盖层（可编辑）**
- 位置：`markdown/core/`
- 内容：项目定制的核心文档（覆盖上游基线）
- 使用：AI需要编辑核心文档时，自动从上游复制到此处
- **✅ 允许编辑，仅影响当前项目**

**📂 项目特定层（可编辑）**
- 位置：`markdown/`（根据项目类型自适应）
  - System架构项目：`markdown/systems/`
  - 模块化项目：`markdown/modules/`
  - 其他架构：`markdown/[自定义目录]/`
- 内容：项目自己的技术文档和跟踪清单
- **✅ 完全由项目自主维护**

### 核心文档（智能路由）
优先读取 `markdown/core/`，不存在时回退到 `.claude/core-docs/`：
- **[开发规范.md]** - 防止90%错误 ⭐
- **[问题排查.md]** - 已知问题解决
- **[AI工作流文档]** - 任务类型决策表、快速通道流程、上下文管理规范

### 项目文档（直接读取）
- **[markdown/](./markdown/)** - 项目技术文档（根据项目类型自适应）
  - System架构项目：`markdown/systems/`
  - 模块化项目：`markdown/modules/`
  - 其他架构：`markdown/[自定义]/`
- **[markdown/文档待补充清单.md](./markdown/文档待补充清单.md)** - 文档覆盖率跟踪
{{PRESETS_DOCS_SECTION}}
### 文档更新机制

**同步上游更新：**
```bash
initmc --sync  # 检测新版本，更新软连接，清理废弃文件
```

**定制核心文档：**
1. AI检测需要编辑核心文档
2. 自动从 `.claude/core-docs/` 复制到 `markdown/core/`
3. 添加定制标记
4. 编辑项目副本
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

| 问题类型 | 查阅位置 | 行号 |
|---------|---------|------|
| 双端隔离错误 | 开发规范.md | - |
| System生命周期 | 开发规范.md | - |
| 模块导入错误 | 开发规范.md | - |
{{QUICK_INDEX_EXTRA}}

---

## 🔗 关键路径

- **项目根目录**: 当前工作目录（通过环境变量获取）

---

## 📝 版本信息

> **文档版本**: v16.2 (强制文档查阅 + 自学习闭环)
> **最后更新**: 2025-11-11
> **项目状态**: {{PROJECT_STATUS}}

### v16.2 更新亮点 ⚡

**核心问题修复**：
- 🎯 **修复文档查阅优先级错误**: 所有任务类型现在都必须先查阅Systems文档定位代码
- 🔄 **完整自学习闭环**: 查阅→使用→更新文档，形成知识积累
- 📉 **大幅降低Token消耗**: 微任务节省80% tokens（盲目搜索→定向搜索）

**步骤2重构（两阶段）**：
- ✅ **阶段A: 代码定位**（最高优先级）
  1. 查阅Systems文档
  2. 定向搜索验证
  3. 盲目搜索（最后手段）
- ✅ **阶段B: 编码规范约束**
  1. 查阅开发规范.md
  2. 查阅问题排查.md
  3. 查阅官方文档（优先本地docs/）

**微任务快速通道升级**：
- ✅ 3步→4步：增加"查阅Systems文档"和"更新文档"
- ✅ 强制文档查阅，不再跳过步骤2
- ✅ 完成后必须更新Systems文档

**文档体系完善**：
- ✅ 新增 `系统文档模板.md`：标准化System文档结构
- ✅ 强制更新机制：任务完成后必须更新文档
- ✅ 官方文档优先级调整：优先读取本地 `docs/` Git Submodule

**效果验证**：
- 📊 微任务Token节省：80%（8k → 1.5k）
- 📊 标准任务Token节省：30%（35k → 24k）
- 📊 复杂任务Token节省：40%（60k → 36k）
- ⏱️ 微任务时间节省：67%（5-8分钟 → <3分钟）

**保留v16.1优势**：
- ✅ 双层文档架构
- ✅ CRITICAL规范前置
- ✅ 三步工作流程
- ✅ 三级任务分类

---

**记住**:
1. 微任务优先，能直接Edit就不创建tasks
2. 默认顺序执行，除非用户要求并行
3. 遵循CRITICAL规范避免90%错误
4. 本地文档不足时，使用WebFetch查阅官方资源
