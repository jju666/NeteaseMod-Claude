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

**原因:** 双端进程分离，跨端调用返回None
详见：[问题排查.md](./markdown/问题排查.md#问题1)

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

**原因:** __init__阶段游戏未初始化，API不可用
详见：[问题排查.md](./markdown/问题排查.md#问题2)

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

**原因:** 序列化机制不支持tuple，必须使用list
详见：[问题排查.md](./markdown/问题排查.md#问题3)

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

**原因:** 引擎硬性限制，每维度≤2000格
详见：[问题排查.md](./markdown/问题排查.md#问题9)

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
dir {{PROJECT_ROOT}}/tasks /b  # 检查是否有相关任务
```

**1.3 微任务直接执行**
- 跳过步骤2-3，直接Edit+Git commit
- 参考：[快速通道流程.md](./markdown/ai/快速通道流程.md)

---

### 📚 步骤2: 查阅文档（仅标准/复杂任务）

**2.1 智能搜索相关文档**
```python
# 不要浏览列表，直接搜索
Grep("关键词", path="markdown/", output_mode="files_with_matches")
```

**2.2 优先级**

**快速参考**（无需查阅完整文档）：
- 🔍 **API速查.md** - 常用API代码片段，可直接复制使用 ⭐
- 📖 **MODSDK核心概念.md** - System/Component/Event/Entity速查 ⭐

**详细文档**（需要深入理解时查阅）：
1. **开发规范.md** - CRITICAL规范，防止90%错误 ⭐⭐⭐
2. **问题排查.md** - 已知问题和调试技巧
3. **Systems文档** - 系统实现文档
   - 路径: `markdown/systems/`
   - 查阅对应系统的技术文档

4. **官方MODSDK文档** - 遇到不熟悉API时查阅 ⭐
   - 仓库：https://github.com/EaseCation/netease-modsdk-wiki
   - 使用WebFetch工具在线获取最新文档
   - 示例：
     ```python
     WebFetch(
         url="https://raw.githubusercontent.com/EaseCation/netease-modsdk-wiki/main/docs/...",
         prompt="提取关于[API名称]的使用说明、参数和返回值"
     )
     ```

5. **基岩版Wiki** - 涉及原版实体/物品/NBT时查阅 ⭐
   - 仓库：https://github.com/Bedrock-OSS/bedrock-wiki
   - 查阅NBT结构、实体属性、原版机制
   - 使用WebFetch工具获取文档

**⚠️ 何时查阅官方文档**：
- ❌ **文档不足时**：本地文档未找到相关信息
- 🔍 **遇到不熟悉API时**：不确定API参数、返回值、使用方式
- 🐛 **遇到原版机制问题时**：NBT结构、实体行为、游戏规则

**2.3 核心检查点**（必须输出）
```
✅ 已查阅文档: [列出]
🎯 提取原则: [⛔禁止/✅应该/📚原因]
📄 文档依据: [引用行号]
🌐 官方文档查阅: [如有]
```

---

### 🔧 步骤3: 执行与收尾

**3.1 标准任务（5章模板）**
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

**记住**:
1. 微任务优先，能直接Edit就不创建tasks
2. 默认顺序执行，除非用户要求并行
3. 遵循CRITICAL规范避免90%错误
4. 本地文档不足时，使用WebFetch查阅官方资源
