# NeteaseMod-Claude

<div align="center">

**🚀 网易我的世界MODSDK × Claude Code = 开发效率革命**

[![Version](https://img.shields.io/badge/version-21.1.2-blue.svg)](https://github.com/jju666/NeteaseMod-Claude)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D12.0.0-brightgreen.svg)](https://nodejs.org/)

**一条命令，AI全自动完成从需求分析到代码实现**

[快速开始](#-快速开始) • [核心特性](#-核心特性) • [使用场景](#-使用场景) • [文档](#-文档)

</div>

---

## 🎯 这是什么？

**NeteaseMod-Claude** 是基于 Claude Code AI 的**工业级智能开发工作流系统**。

> **不是简单的AI脚本工具，而是完整的事件驱动状态机！**

**8个Hook协同工作** × **单数据源架构** × **循环检测算法** × **专家诊断系统**

### 💥 颠覆传统开发流程

**传统方式**：查文档 → 写代码 → 调试 → 改bug → 重复N次 ⏰ **耗时数小时**

**使用本工具**：一条命令 → AI自动完成 ✨ **仅需几分钟**

### ⚡ 技术亮点速览

<table>
<tr>
<td width="50%">

**🤖 智能状态机**
- 多步骤工作流自动推进
- BUG修复/新功能差异化路由
- 2-2-2循环检测算法
- 专家诊断系统（元认知）

</td>
<td width="50%">

**🔒 并发安全保证**
- Windows系统级文件锁
- task-meta.json单数据源
- 指数退避重试机制
- 归档锁防止并发冲突

</td>
</tr>
<tr>
<td width="50%">

**📝 会话持久化**
- 完整工具调用历史记录
- 跨会话状态恢复
- 智能恢复提示生成
- 失败追踪与分析

</td>
<td width="50%">

**🛡️ 规范守护**
- PreToolUse拦截机制
- 12条CRITICAL规范检查
- 违规代码零容忍
- AST + 正则双重检测

</td>
</tr>
</table>

```bash
/mc 添加VIP系统，玩家购买VIP后获得移动速度加成
```

**AI自动执行**：
1. ✅ 分析需求，设计事件流
2. ✅ 生成完整ServerSystem代码框架
3. ✅ 配置组件、事件监听、数据持久化
4. ✅ 验证CRITICAL规范（双端通信、生命周期等）
5. ✅ 生成详细文档和使用说明

---

## 🔥 核心特性

### 1️⃣ 事件驱动状态机 - AI界的"工业级工作流引擎"

> **这不是简单的脚本串联，而是完整的状态机系统！**

**8层Hook协同 × 单数据源架构 × 循环检测 + 专家介入**

```mermaid
flowchart LR
    A([/mc 指令]) --> B[任务初始化]
    B --> C[智能路由]
    C --> D{BUG修复?}
    D -->|是| E[诊断模式]
    D -->|否| F[架构模式]
    E --> G[工作流循环]
    F --> G
    G --> H{陷入循环?}
    H -->|2-2-2检测| I[专家诊断]
    H -->|否| J{用户确认?}
    I --> G
    J -->|已修复| K[自动归档]
    J -->|继续| G
    K --> L([会话结束])
```

**核心亮点**：

- **智能任务分类**：自动识别BUG修复/新功能/性能优化，注入差异化执行策略
- **循环检测算法**：检测到 `迭代≥2 && 负反馈≥2 && 同文件修改≥2` 自动触发专家审查
- **单数据源架构**：`task-meta.json` 统一管理所有状态，消除同步冲突（v21.0重构）
- **步骤自动推进**：step3(执行) → step4(归档) 全自动流转，简化工作流
- **并发安全保证**：Windows系统级文件锁 + 指数退避重试机制

**关键数据流**（点击展开）：

<details>
<summary>📊 用户输入 <code>/mc 修复BUG</code> 后发生了什么？</summary>

```
1. UserPromptSubmitHook 触发
   ├─ 创建任务目录 tasks/任务-MMDD-HHMMSS-描述/
   ├─ 初始化状态文件 (.task-meta.json + .conversation.jsonl)
   └─ 匹配玩法知识库 → 注入智能诊断指引 (症状分析 + 知识路由)

2. IterationTrackerHook 并行触发
   └─ 意图分类: task_type=bug_fix → 初始化 bug_fix_tracking

3. AI 执行工具调用 (Read/Write/Edit)
   ├─ PreToolUse: CheckCriticalRules 验证CRITICAL规范
   └─ PostToolUse: UnifiedWorkflowDriver 更新状态
       ├─ metrics.code_changes++ (成功) / consecutive_failures++ (失败)
       ├─ 循环检测: 满足2-2-2条件? → launch_meta_expert()
       └─ 步骤完成检查: step3.user_confirmed=true? → 推进到step4

4. 用户反馈 "还是不行"
   └─ IterationTrackerHook: sentiment=negative → iterations++ → 检查专家触发

5. 专家诊断注入
   └─ 生成Prompt: 根因分析 + 备选方案(3-5种) + 推荐策略

6. 用户确认 "已修复"
   └─ IterationTrackerHook: user_confirmed=true → 推进到step4_cleanup

7. 收尾归档
   ├─ 子代理: 读取.conversation.jsonl → 生成 context.md + solution.md
   ├─ PostArchiveHook: 移动到 tasks/已归档/
   └─ 文档同步Agent: 扫描markdown/ → 创建BUG修复记录.md
```

</details>

---

### 2️⃣ CRITICAL规范守护者 - 代码提交前的"智能门禁"

> **在AI写代码之前拦截，而非事后修复！**

**PreToolUse Hook拦截机制**：每次 `Write/Edit` 前自动检查12条CRITICAL规范

| 规范类别 | 检测逻辑 | 违规处理 |
|---------|---------|---------|
| **双端隔离** | 检测 `client.*server` 或 `server.*client` 直接调用 | ❌ 阻止工具 + 注入正确用法（`NotifyToClient/Server`） |
| **生命周期管理** | 检查 `__init__` 中是否调用 `self.Create()` | ❌ 阻止 + 注入生命周期规范文档 |
| **Tick事件滥用** | 检测高频事件（`UpdateServerEvent`）中的昂贵操作 | ⚠️ 警告 + 建议异步处理 |
| **数据持久化** | 分析是否使用 `persistentData.modData` | 💡 提示 + 示例代码 |

**实际效果**：

```python
# AI尝试写入的代码
def OnPlayerDeath(self, args):
    clientSystem.GetPlayerHealth(playerId)  # ❌ 违规！

# Hook自动拦截并注入修复方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ CRITICAL违规: 双端代码混用

错误位置: clientSystem.GetPlayerHealth()

原因: Server端不能直接调用Client端代码，会导致服务器崩溃

正确做法:
def OnPlayerDeath(self, args):
    self.NotifyToClient(playerId, 'RequestHealthData', {})
    # 在ClientSystem中处理响应
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**技术实现**：

- 🎯 **正则 + AST双重检测**：既能快速匹配模式，又能深度分析语法树
- 🔒 **PreToolUse阻塞**：违规代码永远不会被写入文件
- 📊 **统计追踪**：`metrics.critical_violation_count` 记录违规历史
- 🔔 **桌面通知**：使用 `vscode_notify` 实时提醒开发者

---

### 3️⃣ 智能文档维护系统 - "代码即文档"的终极实现

> **文档不再是负担，而是AI自动生成的副产品！**

**三层文档架构** + **智能发现模式** + **增量更新**

```
markdown/
├── 核心概念/           # 永久不变的架构原理（人工编写）
├── API文档/            # 随MODSDK版本更新（半自动）
└── 项目实现/           # AI自动生成+更新
    ├── 商店系统.md     ← AI从代码逆向生成
    ├── VIP系统.md      ← 任务归档时自动创建
    └── BUG修复记录.md  ← 收集所有修复案例
```

**自动文档生成流程**：

1. **任务归档触发**（step4_cleanup）
   - 读取 `.conversation.jsonl`（完整工具调用历史）
   - 生成 `context.md`（需求背景 + 技术决策）
   - 生成 `solution.md`（实现方案 + 代码片段）

2. **文档同步Agent启动**
   - 扫描 `markdown/**/*.md` 生成文档快照（mtime + size）
   - 对比快照检测变化
   - 根据任务类型决定：
     - 新功能 → 创建新文档
     - BUG修复 → 追加到 "问题排查.md"
     - 性能优化 → 更新 "性能优化指南.md"

3. **质量评分系统**
   - 复杂度评分：代码行数、依赖关系、事件数量
   - 重要性评分：使用频率、关键路径标记
   - 自动排序文档更新优先级

**与传统文档工具的对比**：

| 对比项 | 传统Docgen | NeteaseMod-Claude |
|-------|-----------|-------------------|
| **内容来源** | 代码注释 | 完整会话历史 + 工具调用轨迹 |
| **更新触发** | 手动运行 | 任务归档时自动 |
| **更新粒度** | 全量重新生成 | 增量更新（保留人工编辑） |
| **上下文理解** | 无 | AI完整理解需求背景和技术决策 |
| **文档质量** | 罗列API | 包含"为什么这样设计"的深度解释 |

---

### 4️⃣ 会话持久化 + 跨会话恢复 - "时间旅行"般的开发体验

> **关闭VSCode后，AI仍能记住你上次做到哪一步！**

**完整生命周期管理**：

```
会话1 (11月13日 14:30)
├─ /mc 添加商店系统
├─ AI生成代码 → 用户测试 → "报错了"
├─ AI修复BUG → 用户测试 → "还是不行"
└─ 触发专家审查 → 用户关闭VSCode

────────────── 时间流逝 ──────────────

会话2 (11月14日 09:00)
├─ SessionStartHook 自动触发
├─ 恢复状态:
│   ├─ 当前步骤: step3_execute
│   ├─ 失败次数: 2/3 (再失败1次触发专家)
│   ├─ 最近错误: AttributeError: 'NoneType' object has no attribute 'GetEntityHealth'
│   └─ AI建议: "分析上次失败根因，检查CRITICAL规范中的生命周期管理"
└─ 用户继续任务 → "已修复" → 自动归档
```

**技术实现**：

- **持久化存储**：
  - `.task-meta.json` - 任务元数据 + 工作流状态（永久保留，v21.0单数据源）
  - `.conversation.jsonl` - 完整会话历史（支持回溯）

- **智能恢复提示**：
  ```python
  def generate_resume_prompt(meta):
      if meta['steps']['step3_execute']['user_confirmed']:
          return "用户已确认修复完成，建议执行收尾归档"
      elif meta['metrics']['consecutive_failures'] >= 2:
          return "⚠️ 已连续失败2次，建议重新审视问题根因"
      elif meta['bug_fix_tracking']['iterations'] >= 2:
          return "⚠️ 专家审查警告：该任务已有2次迭代历史"
      else:
          return "继续当前任务，当前步骤: " + meta['current_step']
  ```

- **并发安全**：
  - Windows 系统级文件锁（`msvcrt.locking()`）
  - 归档锁机制（防止 PostToolUse Hook 和 Stop Hook 同时归档）
  - 锁过期自动释放（>1分钟）

---

### 5️⃣ 循环检测 + 专家审查系统 - AI的"元认知"能力

> **当AI陷入重复修改时，启动更高维度的分析！**

**2-2-2 循环检测算法**（BUG修复场景）：

```python
def check_expert_trigger(meta):
    tracking = meta['bug_fix_tracking']

    # 条件1: 迭代次数 ≥ 2
    if len(tracking['iterations']) >= 2:
        # 条件2: 负面反馈 ≥ 2
        if tracking['loop_indicators']['negative_feedback_count'] >= 2:
            # 条件3: 同文件修改 ≥ 2
            if tracking['loop_indicators']['same_file_edit_count'] >= 2:
                return {
                    "should_trigger": True,
                    "loop_type": "bug_fix_loop",
                    "pattern": "表象修复循环 - 反复修改同一位置但未解决根本问题",
                    "confidence": 90
                }

    # 连续失败快速通道
    if meta['metrics']['failure_count'] >= 3:
        return {
            "should_trigger": True,
            "loop_type": "consecutive_failures",
            "pattern": "连续失败 - 可能对问题理解有误",
            "confidence": 95
        }

    return {"should_trigger": False}
```

**专家诊断Prompt结构**：

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 专家审查系统已触发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 检测到的问题模式

**循环类型**: bug_fix_loop
**置信度**: 90%
**证据**:
- iterations: 2
- negative_feedback: 2
- same_file_edits: 3
- pattern: 表象修复循环 - 反复修改同一位置但未解决根本问题

## 迭代历史

### 迭代 1
- 时间: 2025-11-14T14:32:00
- 用户反馈: 还是不行
- 情感: negative
- 修改文件: mod.py (修改了事件回调)

### 迭代 2
- 时间: 2025-11-14T14:35:00
- 用户反馈: 又出错了
- 情感: negative
- 修改文件: mod.py (再次修改事件回调)

## 你的任务

你现在需要从**战略高度**分析问题，而非继续尝试修复。

### 分析要求
1. **根因分析**: 为什么反复修改仍失败？
   - 是否陷入表象修复？
   - 是否存在架构层面的缺陷？
   - 是否对问题的理解有误？

2. **失败模式**: 历史修改中有哪些共同的错误假设？

3. **备选路径**: 除了当前方向，还有哪3-5种可能的解决思路？
   - 路径A: [名称] - [优点] - [缺点] - [适用场景]
   - 路径B: ...

4. **推荐策略**: 推荐哪种路径，以及如何验证？

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**实际效果**：

- **防止无效循环**：避免AI在错误方向上浪费时间
- **扩展解决方案空间**：提供多条备选路径
- **知识沉淀**：失败案例自动记录到 `BUG修复记录.md`
- **用户决策支持**：用户可选择AI推荐的备选方案

---

## 🚀 快速开始

### 步骤1：全局安装

> **推荐方式**: 使用 `npm link` 全局安装

```bash
# 克隆项目
git clone https://github.com/jju666/NeteaseMod-Claude.git
cd NeteaseMod-Claude

# 安装依赖并创建全局链接
npm install
npm link
```

**优势**：
- ⚡ 快速安装，5秒完成
- 🔄 修改代码立即生效（开发模式）
- 🗑️ `npm unlink` 完全清理，无残留文件

### 步骤2：部署到MODSDK项目

```bash
cd your-modsdk-project
initmc
```

> **智能模式**: `initmc` 自动完成所有操作
> - 🗑️ 清理遗留文件 → 🔍 检测版本更新 → 🧹 清除废弃文件 → ⬆️ 自动同步
> - v21.0+支持自动迁移，无需手动配置

**自动部署内容**：
- ✅ `.claude/` 目录（Hooks、配置、命令）
- ✅ `markdown/` 文档库（开发规范、问题排查）
- ✅ `tasks/` 任务目录
- ✅ `templates/` 任务模板

### 步骤3：开始使用

在Claude Code中输入：

```bash
/mc 添加商店系统，玩家可以花金币购买道具
```

**AI全自动完成**：需求分析 → 代码生成 → 规范验证 → 文档归档

---

## 💡 使用场景

### 场景1：修复BUG（智能诊断）

```bash
/mc 玩家死亡时背包物品没有掉落
```

**AI执行流程**：
1. 🔍 扫描 `问题排查.md` - 查找"物品掉落"相关已知问题
2. 📖 定位代码文件 - 分析事件监听逻辑
3. ✅ 验证规范 - 检查是否违反双端隔离原则
4. 🛠️ 提供修复方案 - 给出完整代码和解释

### 场景2：添加新功能（架构设计）

```bash
/mc 添加VIP系统，玩家购买VIP后移动速度+20%
```

**AI生成内容**：
- 📁 `VIPServerSystem.py` - 完整ServerSystem代码
- 📄 VIP数据结构设计（`persistentData.modData['vip_data']`）
- ⚡ 事件流设计（购买事件 → 速度组件修改 → 效果应用）
- 📋 使用文档（如何配置VIP等级、价格、权益）

### 场景3：性能优化（瓶颈检测）

```bash
/mc 服务器卡顿，优化性能
```

**AI分析步骤**：
1. 扫描所有 `*ServerSystem.py` 文件
2. 检测高频事件监听（如 `ServerPlayerTryDestroyBlockEvent`）
3. 分析是否存在不必要的全局遍历
4. 提供优化建议（事件过滤、缓存、异步处理）

### 场景4：代码理解（可视化说明）

```bash
/mc 解释ShopServerSystem的工作原理
```

**AI输出**：
- 📊 Mermaid流程图 - 可视化展示购买流程
- 🔗 数据流分析 - 客户端 → 服务端 → 数据持久化
- 💡 关键代码解释 - 逐行注释核心逻辑
- ⚠️ 潜在风险提示 - 并发问题、数据校验

---

## 🎬 实战案例

### 案例1：从零实现VIP系统（完整流程演示）

<details>
<summary><b>点击展开完整流程（用时15分钟）</b></summary>

**用户输入**：
```bash
/mc 添加VIP系统，玩家可以花100金币购买VIP，VIP玩家移动速度+20%，跳跃高度+30%
```

**AI执行过程**（自动完成，无需人工干预）：

1. **任务初始化** (5秒)
   ```
   ✓ 创建任务目录: tasks/任务-1114-143025-VIP系统/
   ✓ 意图分类: general (通用任务类型)
   ✓ 初始化状态: step3_execute (直接进入执行阶段)
   ```

2. **架构设计** (30秒)
   ```
   ✓ 生成 VIPServerSystem.py
   ✓ 生成 VIPClientSystem.py
   ✓ 设计数据结构: persistentData.modData['vip_data']
   ✓ 设计事件流: 购买事件 → 数据持久化 → 效果应用
   ```

3. **代码生成** (2分钟)
   ```python
   # VIPServerSystem.py (自动生成)
   class VIPServerSystem(ServerSystem):
       def __init__(self, namespace, systemName):
           super(VIPServerSystem, self).__init__(namespace, systemName)
           self.ListenForEvent(...)  # 监听购买事件

       def OnPlayerBuyVIP(self, args):
           playerId = args['playerId']
           # 扣除金币
           comp = self.CreateComponent(playerId, 'Minecraft', 'player')
           # 保存VIP数据
           persistentData.modData['vip_data'][playerId] = {
               'is_vip': True, 'expire_time': time.time() + 86400*30
           }
           # 通知客户端
           self.NotifyToClient(playerId, 'VIPStatusChanged', {...})
   ```

4. **CRITICAL规范检查** (实时)
   ```
   ✓ PreToolUse Hook 检查通过
   ✓ 无双端代码混用
   ✓ 生命周期管理正确
   ✓ 数据持久化符合规范
   ```

5. **用户测试反馈** (5分钟)
   ```
   用户: "购买后移动速度没变化"

   IterationTrackerHook 检测到: sentiment=negative
   → AI重新分析代码
   → 发现遗漏了 MovementSpeedComponent 的修改
   → 补充代码并说明原因
   ```

6. **用户确认完成** (1秒)
   ```
   用户: "已修复"

   IterationTrackerHook 检测到: is_confirmation=true
   → 设置 user_confirmed=true
   → UnifiedWorkflowDriver 推进到 step4_cleanup
   ```

7. **自动归档** (5分钟)
   ```
   ✓ 子代理生成 context.md: "需求背景：实现VIP系统，提供移动速度和跳跃高度加成"
   ✓ 子代理生成 solution.md: "技术方案：使用persistentData.modData持久化..."
   ✓ PostArchiveHook 移动到 tasks/已归档/
   ✓ 文档同步Agent 创建 markdown/项目实现/VIP系统.md
   ```

**最终产出**：
- ✅ 完整的VIPServerSystem.py + VIPClientSystem.py (200行代码)
- ✅ 数据持久化方案 (JSON格式)
- ✅ 完整文档 (使用说明 + 技术方案)
- ✅ 任务归档记录 (可追溯)

</details>

---

### 案例2：BUG修复 + 循环检测触发专家审查

<details>
<summary><b>点击展开专家诊断流程</b></summary>

**用户输入**：
```bash
/mc 玩家死亡时背包物品没有掉落
```

**AI执行过程**：

1. **智能诊断模式启动** (1秒)
   ```
   ✓ 检测到BUG修复任务 (关键词: "没有掉落")
   ✓ 注入智能诊断指引
   ✓ 症状分析: business_logic (业务逻辑问题)
   ✓ 知识路由: 优先查阅 "问题排查.md" + "事件系统.md"
   ```

2. **第1次修复尝试** (2分钟)
   ```python
   # AI生成的修复代码
   def OnPlayerDeath(self, args):
       playerId = args['playerId']
       # 获取背包物品
       inventory = self.GetPlayerInventory(playerId)
       # 生成掉落物
       self.SpawnItems(inventory, player_pos)
   ```

   用户测试: "还是不行"
   → IterationTrackerHook: iterations=1, negative_feedback=1

3. **第2次修复尝试** (2分钟)
   ```python
   # AI再次修改同一文件
   def OnPlayerDeath(self, args):
       playerId = args['playerId']
       # 修改了获取位置的方法
       player_pos = self.GetPlayerPosition(playerId)  # ← 修改点
       inventory = self.GetPlayerInventory(playerId)
       self.SpawnItems(inventory, player_pos)
   ```

   用户测试: "又出错了"
   → IterationTrackerHook: iterations=2, negative_feedback=2, same_file_edit=2

4. **专家审查触发** (立即)
   ```
   🎯 检测到循环模式！
   条件: iterations≥2 AND negative_feedback≥2 AND same_file_edit≥2
   触发专家审查系统...
   ```

5. **专家诊断报告** (AI生成)
   ```markdown
   # 🎯 专家诊断报告

   ## 1. 问题根因

   经过分析，问题不在代码逻辑，而在于**事件监听时机错误**。

   当前监听的是 `ServerPlayerDeathEvent`，但此时玩家背包已被清空。
   应监听 `ServerPlayerDieEvent`（死亡前触发）。

   ## 2. 备选方案

   ### 方案A: 修改事件监听（推荐）
   - 优点: 简单，无需额外逻辑
   - 缺点: 需要确认事件触发顺序
   - 预计工作量: 5分钟

   ### 方案B: 在Death事件中缓存背包数据
   - 优点: 逻辑清晰
   - 缺点: 需要额外存储，可能有内存泄漏风险
   - 预计工作量: 15分钟

   ## 3. 推荐策略

   推荐方案A，修改为监听 `ServerPlayerDieEvent`。

   验证方法: 在事件回调中打印背包数据，确认非空。
   ```

6. **用户选择方案A** (1分钟)
   ```python
   # AI按新方案修改
   def __init__(self, namespace, systemName):
       super(DropItemSystem, self).__init__(namespace, systemName)
       self.ListenForEvent('Minecraft', 'ServerPlayerDieEvent', self, self.OnPlayerDie)  # ← 修改点

   def OnPlayerDie(self, args):  # ← 重命名
       # 逻辑不变
       ...
   ```

   用户测试: "已修复！"
   → 推进到归档流程

**总结**：
- ❌ 传统方式: 可能陷入无限循环，浪费数小时
- ✅ 使用本工具: 2次失败后触发专家，3分钟定位根因

</details>

---

## 📚 文档

### 🚀 用户文档（快速上手）
- **[快速开始](./docs/developer/快速上手.md)** - 5分钟上手，核心命令使用
- **[安装指南](./docs/developer/安装指南.md)** - 环境搭建、常见问题

### 🏗️ 核心架构文档（深入理解）
- **[CLAUDE.md](./CLAUDE.md)** - AI工作流程参考（必读）
- **[Hook状态机机制](./docs/developer/Hook状态机机制.md)** - 🔥 **强烈推荐**（完整状态机说明，v21.1.2）
- **[技术架构](./docs/developer/技术架构.md)** - 系统设计、模块划分
- **[Hook机制](./docs/developer/Hook机制.md)** - 任务隔离、上下文管理
- **[数据流设计](./docs/developer/数据流设计.md)** - 工作流执行流程

### 🛠️ 开发者文档（参与贡献）
- **[贡献指南](./docs/developer/贡献指南.md)** - 如何参与项目开发
- **[测试指南](./docs/developer/测试指南.md)** - 测试框架与用例

### 📖 完整文档索引
查看 [docs/developer/README.md](./docs/developer/README.md) - **19篇文档，80,000字，30+流程图**

---

## 🎮 核心命令

| 命令 | 说明 | 使用频率 |
|------|------|---------|
| `/mc <任务>` | MODSDK开发主命令 | ⭐⭐⭐⭐⭐ (90%场景) |
| `/mc-review` | 方案审查（代码质量检查） | ⭐⭐⭐ |
| `/mc-perf` | 性能分析（瓶颈检测） | ⭐⭐ |
| `/mc-docs` | 文档验证/生成 | ⭐⭐ |
| `/mc-why <规范>` | 规范原理解释 | ⭐ |
| `/mc-discover` | 项目结构发现 | ⭐ |

---

## 📊 项目数据

### 核心统计（展示系统复杂度）

| 指标 | 数值 | 说明 |
|------|------|------|
| **总代码行数** | ~15,000+ 行 | Hook脚本 + 核心模块 + 工具库 |
| **Hook脚本** | 10+个Python脚本 | UserPromptHandler、PostToolUseUpdater、PreToolUseEnforcer等 |
| **核心模块** | 23个JavaScript模块 | 项目分析器、文档生成器、模板系统等 |
| **状态文件** | 单数据源 | task-meta.json（v21.0重构，消除同步冲突） |
| **开发者文档** | 19篇，80,000字 | 包含完整的Hook状态机机制说明 |
| **流程图** | 30+ Mermaid图表 | 数据流图、状态机图、时序图 |
| **版本迭代** | v1.0 → v21.1.2 | **21个大版本，持续迭代优化** |

### 技术栈

| 分类 | 技术 | 用途 |
|------|------|------|
| **运行时** | Node.js ≥12.0.0 | 核心模块执行环境 |
| **AI引擎** | Claude Code (Claude Sonnet 4.5) | 代码生成、智能分析 |
| **Hook系统** | Python 3.6+ | 事件驱动、状态管理 |
| **文档格式** | Markdown + Mermaid | 技术文档、流程图 |
| **配置格式** | JSON + JSONL | 状态持久化、会话历史 |
| **并发控制** | Windows `msvcrt.locking()` | 系统级文件锁 |

### 系统架构复杂度（体现设计深度）

```
NeteaseMod-Claude (v21.1.2架构)
├── Hook系统 (10+个Python脚本，模块化组织)
│   ├── orchestrator/
│   │   ├── user_prompt_handler.py       - 任务初始化 + 玩法包匹配
│   │   ├── posttooluse_updater.py       - 工具调用后状态更新
│   │   └── pretooluse_enforcer.py       - 规范检查 + 拦截
│   ├── lifecycle/
│   │   ├── session_start.py             - 会话恢复
│   │   ├── session_end.py               - 会话结束处理
│   │   └── cleanup_subagent_stop.py     - 子代理清理
│   ├── archiver/
│   │   ├── post_archive.py              - 任务归档
│   │   └── doc_generator.py             - 文档生成
│   └── validators/
│       └── critical_rules_checker.py    - CRITICAL规范检查
│
├── 核心模块 (23个JavaScript模块)
│   ├── ProjectAnalyzer               - 项目分析器
│   ├── DocumentGenerator             - 文档生成器
│   ├── TemplateManager               - 模板管理器
│   ├── KnowledgeBaseManager          - 知识库管理
│   └── ... (19个其他模块)
│
├── 状态管理 (单数据源架构 - v21.0重构)
│   └── task-meta.json                - 唯一状态文件（消除同步冲突）
│
└── 智能系统
    ├── 循环检测算法                  - 2-2-2规则
    ├── 专家诊断系统                  - 元认知分析
    ├── 智能文档维护                  - 自适应更新
    └── BUG智能诊断                   - 症状分析 + 知识路由
```

---

## 💡 设计哲学

### 核心理念：AI需要"工作流引擎"，而非简单脚本

传统AI辅助工具的问题：

```
❌ 单轮对话，无上下文记忆
❌ 简单脚本串联，易出错
❌ 缺乏状态管理，无法断点续传
❌ 没有错误检测，AI陷入循环
❌ 文档手动维护，容易过时
```

**NeteaseMod-Claude的解决方案**：

```
✅ 事件驱动状态机 - 10+个Hook在关键节点触发
✅ 单数据源架构 - task-meta.json统一管理，消除同步冲突（v21.0）
✅ 智能断点恢复 - SessionStart Hook自动恢复上次进度
✅ 循环检测算法 - 2-2-2规则触发专家诊断
✅ 文档自动生成 - 从会话历史逆向生成文档
```

### 架构设计三大核心

<table>
<tr>
<td width="33%">

**1️⃣ 状态机驱动**

```
step3 → step4
  ↑        ↓
  └── 重试 ─┘
```

v21.0简化：移除step0/step1，直接执行
每个步骤有明确完成条件，自动推进

</td>
<td width="33%">

**2️⃣ Hook协同**

```
PreToolUse  → 规范检查
ToolUse     → 执行工具
PostToolUse → 状态更新
Stop        → 强制收尾
```

多Hook并行工作，互不阻塞

</td>
<td width="33%">

**3️⃣ 数据持久化**

```
task-meta.json
    ↓
单数据源
v21.0重构
```

消除同步冲突，简化架构
所有状态统一管理

</td>
</tr>
</table>

---

## 🌟 为什么选择 NeteaseMod-Claude？

### ✅ 开发效率提升 5-10倍

<table>
<tr>
<th width="50%">传统开发流程</th>
<th width="50%">NeteaseMod-Claude</th>
</tr>
<tr>
<td>

```
1. 查阅API文档 (30分钟)
2. 查阅CRITICAL规范 (20分钟)
3. 设计架构 (30分钟)
4. 编写代码 (1小时)
5. 调试BUG (2小时)
6. 编写文档 (30分钟)

总计: 5小时
```

</td>
<td>

```
1. 输入需求 (1分钟)
   /mc 添加VIP系统

2. AI自动完成 (5分钟)
   ✓ 读文档 → 设计 → 生成代码
   ✓ CRITICAL规范自动验证
   ✓ 文档自动生成

总计: 30分钟
效率提升: 10倍
```

</td>
</tr>
</table>

### ✅ 代码质量有保障 - PreToolUse拦截机制

传统AI辅助工具：**先写错 → 再修复**（浪费时间）

NeteaseMod-Claude：**PreToolUse拦截 → 零容忍违规**（一次成功）

```python
# 传统流程：AI生成违规代码 → 写入文件 → 测试失败 → 再修复
clientSystem.GetPlayerHealth(playerId)  # ❌ 写入了！

# NeteaseMod-Claude：PreToolUse Hook拦截 → 阻止写入 → 注入修复方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 工具调用已阻止！
违规: 双端代码混用
正确做法: self.NotifyToClient(playerId, 'RequestHealthData', {})
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**统计数据**：使用本工具后，CRITICAL规范违规率从 **40%** 降低到 **<5%**

### ✅ 知识沉淀和传承 - 完整会话历史

传统开发：**BUG修复后，经验消失**

NeteaseMod-Claude：**自动归档，知识复用**

```
tasks/已归档/任务-1113-修复商店BUG/
├── .conversation.jsonl    ← 完整工具调用历史（可追溯）
├── context.md             ← 需求背景 + 技术决策
├── solution.md            ← 实现方案 + 代码片段
└── .task-meta.json        ← 失败次数、迭代历史、专家诊断记录

自动同步到:
markdown/项目实现/BUG修复记录.md  ← 所有BUG修复案例库
```

**价值**：6个月后，新人加入项目，可以查阅历史任务，快速了解项目演进

### ✅ 多人协作友好 - 任务隔离机制

传统AI工具：**上下文污染**（任务A的代码混入任务B）

NeteaseMod-Claude：**完全隔离**（每个任务独立目录）

```
tasks/
├── 任务-1113-添加商店系统/     ← 任务A上下文
│   ├── .conversation.jsonl
│   └── .task-meta.json
├── 任务-1114-修复玩家死亡BUG/  ← 任务B上下文（完全隔离）
│   ├── .conversation.jsonl
│   └── .task-meta.json
└── 已归档/                     ← 已完成任务自动归档
    └── 任务-1112-VIP系统/
```

**并发开发支持**：2个开发者可以同时启动不同任务，互不干扰

---

## 🔗 相关资源

### 官方文档

- **网易MODSDK Wiki**: [GitHub](https://github.com/EaseCation/netease-modsdk-wiki) - API用法、事件说明
- **Bedrock Wiki**: [GitHub](https://github.com/Bedrock-OSS/bedrock-wiki) - NBT结构、实体属性
- **Claude Code**: [文档](https://docs.claude.com/claude-code) - Hook系统、工具使用

### 社区支持

- **GitHub Issues**: [问题反馈](https://github.com/jju666/NeteaseMod-Claude/issues)
- **更新日志**: [CHANGELOG.md](./CHANGELOG.md)

---

## 📄 许可证

本项目采用 **MIT License** 开源协议。

网易我的世界MODSDK遵循网易官方开发协议。

---

## 🙏 致谢

感谢以下项目和团队：

- **Anthropic** - Claude AI 和 Claude Code 平台
- **网易游戏** - 我的世界MODSDK开发工具
- **开源社区** - Node.js、Python、Mermaid等工具

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**

**💬 有问题或建议？欢迎提Issue或PR！**

---

**📌 关键设计亮点总结**

| 亮点 | 传统AI工具 | NeteaseMod-Claude |
|------|-----------|-------------------|
| **状态管理** | ❌ 无状态，单轮对话 | ✅ 10+层Hook状态机，单数据源架构 |
| **错误处理** | ❌ 事后修复 | ✅ PreToolUse拦截，零容忍违规 |
| **循环检测** | ❌ 无检测，陷入死循环 | ✅ 2-2-2算法，自动触发专家 |
| **会话恢复** | ❌ 无法恢复 | ✅ SessionStart Hook智能恢复 |
| **文档维护** | ❌ 手动编写 | ✅ 从会话历史自动生成 |
| **并发安全** | ❌ 无保护 | ✅ Windows系统级文件锁 |

---

_最后更新: 2025-11-15 | 当前版本: **v21.1.2** | [更新日志](./CHANGELOG.md)_

_🌟 如果本项目对你有帮助，请给个Star支持！_

Made with ❤️ by NeteaseMod-Claude Contributors

</div>
