# /mc - MODSDK标准工作流

> **版本**: v22.0 (Hook驱动强制工作流)
> **设计理念**: PreToolUse拦截 + 强制研究阶段

---

## 📋 快速开始

```bash
/mc <任务描述>
```

**示例**：
/mc 修复System初始化错误
/mc 添加新功能模块
/mc 优化代码性能
/mc 日志显示错误

---

## 🎯 Hook驱动机制（v22.0）

### 核心原则

**工作流完全由Hook驱动，AI无法跳过任何强制阶段**。

传统v21.0设计依赖PostToolUse提示AI要做什么，但AI经常忽略提示，跳过文档查阅直接修改代码，导致违反CRITICAL规范。

**v22.0架构变更**：
- ✅ **PreToolUse拦截**：在AI执行工具之前进行四层验证，不满足条件直接阻断
- ✅ **强制研究阶段**：新增step2_research，禁止任何修改操作，必须查阅≥3个文档
- ✅ **研究深度检查**：step3执行阶段，验证文档查阅数量后才允许Write/Edit
- ✅ **自动状态推进**：Hook检测AI确认关键词（"研究完成"），自动推进到下一阶段

### 工作流阶段

**所有任务统一遵循以下流程**（Hook自动管理）：

```
step0_context (skipped)
    ↓
step1_understand (skipped)
    ↓
step2_research (强制) ← 你从这里开始
    ↓ (Hook检测"研究完成"关键词)
step3_execute
    ↓ (用户输入"/mc-confirm")
step4_cleanup (子代理执行)
```

**你不需要关心阶段推进**，Hook会自动管理。你只需要：
1. 使用Read/Grep/Glob查阅文档
2. 明确说明"研究完成"或"已理解问题根因"
3. Hook检测到关键词后自动推进到step3
4. 实施代码修改
5. 用户确认后Hook启动收尾子代理

---

## 🔒 当前阶段规则（PreToolUse强制执行）

### Step2: 任务研究阶段（强制）

**当前状态**: 你现在处于step2_research阶段

**允许的工具**:
- ✅ Read - 阅读文档和代码
- ✅ Grep - 搜索相关实现
- ✅ Glob - 查找文件

**禁止的工具**（PreToolUse会拦截）:
- ❌ Write - 严禁创建文件
- ❌ Edit - 严禁修改文件
- ❌ Bash - 禁止执行命令

**最少文档数要求**:
- 标准模式: ≥3个文档
- 玩法包模式: ≥2个文档（已提供完整代码，但仍需验证）

**完成条件**:
明确说明研究结论，包含以下任一关键词：
- "研究完成"
- "已理解问题根因"
- "开始实施"
- "准备修改"
- "可以开始编码"

**PreToolUse拦截示例**:

如果你尝试在step2_research执行Write/Edit：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 当前阶段: 任务研究（Step2 - 强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你现在处于强制研究阶段，需要先完成文档查阅。

📊 进度: 已查阅 1/3 个文档

下一步操作:
1. 继续使用 Read/Grep/Glob 查阅相关文档
2. 至少查阅 3 个文档后
3. 明确说明你的研究结论（包含关键词："研究完成"或"已理解问题根因"）
4. Hook会自动推进到step3执行阶段，届时可以使用Write/Edit修改代码

**当前禁止操作**:
- ❌ Write/Edit任何文件
- ❌ Bash执行命令

**当前允许操作**:
- ✅ Read 阅读文档和代码
- ✅ Grep 搜索相关实现
- ✅ Glob 查找文件

请遵守工作流规范，完成研究后再进行修改。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### Step3: 执行实施阶段

**前置条件**:
- step2_research已完成
- 已查阅≥3个文档（玩法包≥2个）

**允许的工具**:
- ✅ Read/Write/Edit - 修改代码
- ✅ Bash - 执行测试
- ✅ Grep/Glob - 继续查阅

**PreToolUse研究深度检查**:

如果你在step3执行Write/Edit，但文档数不足：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 研究深度不足 - 修改被拒绝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前模式: 标准模式
已查阅文档: 1/3

❌ 问题: 修改决策需要基于充分的文档研究

✅ 解决方案:
1. 返回step2_research阶段
2. 继续查阅至少 2 个相关文档
3. 重点查阅:
   - CRITICAL规范文档（确保合规）
   - 相关系统实现文档
   - 问题排查指南

完成文档查阅后，Hook会自动允许修改操作。

💡 提示: 充分的文档研究能避免违反CRITICAL规范，
         减少返工迭代，提高修复成功率。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**CRITICAL规范自动检查**:
当你Edit/Write Python文件时，Hook会自动检查：
- ✅ 生命周期规范（禁止在`__init__`调用MODSDK API）
- ✅ 双端隔离（禁止跨端GetSystem）
- ✅ EventData结构（禁止使用tuple）
- ✅ AOI范围限制（禁止超过2000）

违规会立即阻断并提示错误。

**完成条件**:
用户输入"/mc-confirm"或"已修复"确认任务完成

---

### Step4: 收尾归档阶段（自动子代理）

**触发条件**: 用户确认任务完成

**执行方式**: Hook自动启动收尾子代理，你无需手动操作

**子代理任务**:
1. 清理DEBUG代码
2. 更新markdown文档
3. 标记step4_cleanup.status=completed
4. 触发任务归档

---

## 📚 文档查询指南

### 优先级（按顺序查阅）

**🔍 必查文档**：

1. **开发规范.md** - 检查CRITICAL规范 ⭐⭐⭐
   ```bash
   # 优先项目定制版
   Read markdown/core/开发规范.md
   # 降级：上游基线版
   Read .claude/core-docs/核心工作流文档/开发规范.md
   ```

2. **问题排查.md** - 查找已知问题
   ```bash
   Read markdown/core/问题排查.md
   ```

3. **Systems文档** - 系统实现参考
   ```bash
   Read markdown/systems/[SystemName].md
   ```

### MODSDK官方文档查询（3步法）

**查阅路径**（三级降级）：
- ✅ **优先**：本地离线（`C:/Users/28114/.claude-modsdk-workflow/docs/modsdk-wiki/`）
- 🌐 **降级**：在线GitHub（WebFetch）
- ⚠️ **失败**：标记为"未找到"（高风险）

**【事件查询】**：
```bash
# 步骤1：查索引表
Grep("ServerPlayerTryDestroyBlockEvent",
     path="C:/Users/28114/.claude-modsdk-workflow/docs/modsdk-wiki/docs/mcdocs/1-ModAPI/事件/事件索引表.md",
     output_mode="content")
# → 输出：位于"方块.md"

# 步骤2：读分类文档
Read("C:/Users/28114/.claude-modsdk-workflow/docs/modsdk-wiki/docs/mcdocs/1-ModAPI/事件/方块.md")

# 步骤3：定位章节（在输出中搜索事件名）
```

**【API查询】**：
```bash
# 直接Grep搜索API名
Grep("GetHealth",
     path="C:/Users/28114/.claude-modsdk-workflow/docs/modsdk-wiki/docs/mcdocs/1-ModAPI/",
     output_mode="files_with_matches")
# → 找到文件后Read该文件
```

**【事件/API分类索引】**：
```
事件按端别和功能分类：
  - 玩家事件 → 事件/玩家.md
  - 方块事件 → 事件/方块.md
  - 实体事件 → 事件/实体.md
  - 等级事件 → 事件/等级.md
  (完整列表见：事件/事件索引表.md)

API按功能分类：
  - Component → Component/healthComp.md
  - 接口类 → 接口/玩家.md, 接口/物品.md
  (完整列表见：接口/接口索引.md)
```



### 输出研究报告（step2完成时必须）

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 研究完成 - 进入实施阶段
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 📚 已查阅文档（≥3个）:
   - 开发规范.md:164-210 - CRITICAL规范
   - MODSDK核心概念.md:50-80 - Part设计模式
   - markdown/systems/CombatSystem.md - 战斗系统架构

2. 🔑 提取的关键原则（禁止推测）:
   ⛔ 禁止: 在Part.__init__()中调用MODSDK API
   ✅ 应该: 在Create()方法中初始化Component
   📚 原因: 网易引擎生命周期限制

   ⛔ 禁止: 使用GetSystem跨端获取System
   ✅ 应该: 使用NotifyToClient/NotifyToServer通信
   📚 原因: 双端隔离原则

3. 📋 实施方案:
   [简要说明修改计划]

Hook检测到"研究完成"关键词，将自动推进到step3执行阶段。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 🔄 Hook自动化功能

**Hook会自动处理**（你无需关心）：
- ✅ 任务元数据创建（.task-meta.json）
- ✅ 阶段推进检测（检测"研究完成"关键词）
- ✅ 文档阅读统计（docs_read_count）
- ✅ 修改日志记录（记录到metrics.code_changes）
- ✅ CRITICAL规范检查（Edit/Write时自动拦截违规）
- ✅ 收尾子代理启动（用户确认后自动）

**你只需专注**：
- 📖 查阅文档（Read/Grep/Glob）
- 🔍 理解问题根因（明确说明研究结论）
- 💻 实施代码修改（Write/Edit）
- 🧪 测试验证（Bash执行测试）

---

## 📚 附录

### A. CRITICAL规范速查

**必须遵守**（违反会导致PreToolUse阻断或运行时错误）：

| 规范 | 禁止 | 应该 | 文档引用 |
|------|------|------|----------|
| **生命周期** | 在`__init__`调用MODSDK API | 在`Create()`初始化 | 开发规范.md:164 |
| **双端隔离** | 跨端`GetSystem` | 使用`NotifyToClient/Server` | 开发规范.md:210 |
| **数据结构** | EventData使用`tuple` | 使用`list`/`dict` | 开发规范.md:258 |
| **AOI范围** | 超过2000范围 | 限制在2000内 | 开发规范.md:312 |
| **Python模块** | 使用未授权模块 | 只用白名单模块 | 开发规范.md:375 |

### B. 常用代码模板

**ServerSystem基础框架**：
```python
# -*- coding: utf-8 -*-
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class MyServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MyServerSystem, self).__init__(namespace, systemName)
        self.comp = None
        self.Create()  # ⚠️ 手动调用

    def Create(self):
        """✅ 在Create中初始化"""
        levelId = serverApi.GetLevelId()
        self.comp = serverApi.GetEngineCompFactory().CreateXXX(levelId)

        # 监听事件
        self.ListenForEvent(namespace, system, event, self, self.OnEvent)

    def OnEvent(self, args):
        """事件处理器"""
        # 业务逻辑
        pass
```

**ClientSystem基础框架**：
```python
# -*- coding: utf-8 -*-
from mod.client.system.clientSystem import ClientSystem
import mod.client.extraClientApi as clientApi

class MyClientSystem(ClientSystem):
    def __init__(self, namespace, systemName):
        super(MyClientSystem, self).__init__(namespace, systemName)
        self.Create()

    def Create(self):
        """监听服务端事件"""
        self.ListenForEvent(namespace, server_system, custom_event,
                           self, self.OnServerEvent)

    def OnServerEvent(self, args):
        """更新UI"""
        pass
```

**双端通信**：
```python
# Server → Client
data = self.CreateEventData()
data["key"] = value
self.NotifyToClient(playerId, "CustomEvent", data)

# Client → Server
data = self.CreateEventData()
data["key"] = value
self.NotifyToServer("CustomEvent", data)
```

### C. 文档路径速查

| 文档类型 | 路径 | 用途 |
|---------|------|------|
| 项目指导 | `../../CLAUDE.md` | 项目上下文 |
| 开发规范 | `markdown/core/开发规范.md` | CRITICAL规范 |
| 问题排查 | `markdown/core/问题排查.md` | 已知问题 |
| System文档 | `markdown/systems/[Name].md` | 系统实现 |
| 事件索引 | `C:/Users/28114/.claude-modsdk-workflow/docs/modsdk-wiki/.../事件/事件索引表.md` | 事件查询 |
| API文档 | `C:/Users/28114/.claude-modsdk-workflow/docs/modsdk-wiki/.../Component/` | API参考 |

---

## 🎯 总结

**v22.0核心变革**:
- ❌ 删除AI自主决策流程
- ✅ PreToolUse四层验证强制拦截
- ✅ step2_research强制研究阶段
- ✅ 文档深度检查（≥3个，玩法包≥2个）
- ✅ 自动状态推进（检测关键词）

**工作流极简化**:
```
1. Read/Grep/Glob 查阅≥3个文档
2. 明确说明"研究完成"
3. Hook自动推进到step3
4. Write/Edit 实施修改
5. Bash 测试验证
6. 用户"/mc-confirm"确认
7. Hook启动收尾子代理
```

**Hook驱动，AI专注核心价值！** 🚀
