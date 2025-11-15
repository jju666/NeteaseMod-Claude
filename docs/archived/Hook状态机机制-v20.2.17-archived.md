# Hook 状态机机制

> **版本**: v20.2.17
> **最后更新**: 2025-11-14
> **数据来源**: 项目当前实现（不参考任何外部文档）

本文档基于项目代码实际实现，完整解析 NeteaseMod-Claude 工作流系统的 Hook 状态机运作机制。

---

## 📋 目录

1. [核心架构](#核心架构)
2. [工作流阶段](#工作流阶段)
3. [状态数据存储](#状态数据存储)
4. [Hook 触发链](#hook-触发链)
5. [状态转换逻辑](#状态转换逻辑)
6. [专家触发机制](#专家触发机制)
7. [收尾阶段机制](#收尾阶段机制)
8. [任务恢复机制](#任务恢复机制)
9. [循环检测与防护](#循环检测与防护)
10. [数据流图](#数据流图)

---

## 核心架构

### 设计理念

Hook 状态机是一个**事件驱动的工作流编排系统**，通过拦截 AI 的工具调用（Read/Write/Edit/Bash/Task）来实现：

1. **任务生命周期管理** - 从初始化到归档的完整追踪
2. **工作流阶段推进** - 自动检测步骤完成并推进到下一阶段
3. **智能循环检测** - 识别无效迭代并触发专家审查
4. **强制规范执行** - 阻止违反工作流规范的操作

### 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                   Claude Code IDE                       │
│  ┌───────────┐  ┌───────────┐  ┌──────────────────┐   │
│  │   User    │→ │ AI Agent  │→ │  Tool Execution  │   │
│  │  Prompt   │  │ Response  │  │  (Read/Write...) │   │
│  └───────────┘  └───────────┘  └──────────────────┘   │
└──────────┬──────────────────────────┬──────────────────┘
           │                          │
           ↓ SessionStart             ↓ PreToolUse/PostToolUse/Stop
  ┌────────────────────────────────────────────────────┐
  │          Hook System (状态机核心)                   │
  │  ┌──────────────────────────────────────────────┐ │
  │  │  user-prompt-submit-hook.py                  │ │
  │  │  - 任务初始化/恢复                            │ │
  │  │  - 玩法包注入                                 │ │
  │  │  - 任务边界验证                               │ │
  │  └──────────────────────────────────────────────┘ │
  │  ┌──────────────────────────────────────────────┐ │
  │  │  unified-workflow-driver.py (核心驱动器)     │ │
  │  │  - 工具调用分发                               │ │
  │  │  - 状态机推进                                 │ │
  │  │  - 专家触发检测                               │ │
  │  └──────────────────────────────────────────────┘ │
  │  ┌──────────────────────────────────────────────┐ │
  │  │  iteration-tracker-hook.py                   │ │
  │  │  - 意图分类                                   │ │
  │  │  - 情感分析                                   │ │
  │  │  - 迭代计数                                   │ │
  │  └──────────────────────────────────────────────┘ │
  │  ┌──────────────────────────────────────────────┐ │
  │  │  enforce-cleanup.py                          │ │
  │  │  - 收尾检查                                   │ │
  │  │  - 用户确认验证                               │ │
  │  └──────────────────────────────────────────────┘ │
  └────────────┬──────────────────────────────────────┘
               │
               ↓
  ┌────────────────────────────────────────────────────┐
  │           State Storage (三文件同步)                │
  │  ┌────────────────┐  ┌─────────────────────────┐  │
  │  │ workflow-state │  │   .task-meta.json       │  │
  │  │     .json      │←→│  (持久化元数据)          │  │
  │  │ (运行时主源)    │  └─────────────────────────┘  │
  │  └────────────────┘            ↑                   │
  │         ↑                      │                   │
  │         │      ┌───────────────┴────────────┐      │
  │         └──────│  .task-active.json         │      │
  │                │  (快速活跃任务检查)          │      │
  │                └────────────────────────────┘      │
  └────────────────────────────────────────────────────┘
```

---

## 工作流阶段

### 阶段定义

系统定义了 5 个工作流阶段（v20.1 移除了 step2）：

| 阶段ID | 名称 | 描述 | 完成条件 | 推进方式 |
|--------|------|------|----------|----------|
| `step0_context` | 理解项目上下文 | 阅读 CLAUDE.md | 检测到 CLAUDE.md 被读取 | 自动推进 |
| `step1_understand` | 理解任务需求 | 阅读相关文档 | docs_read_count > 0 | 自动推进 |
| ~~`step2_docs`~~ | ~~查阅文档~~ | ~~已移除（v20.1）~~ | - | - |
| `step3_execute` | 执行实施 | 代码修改、测试、迭代 | user_confirmed = true | **需用户确认** |
| `step4_cleanup` | 收尾归档 | 文档更新、DEBUG清理 | status = "completed" | **子代理执行** |

**代码位置**：[unified-workflow-driver.py:475-504](../../../templates/.claude/hooks/unified-workflow-driver.py#L475-L504)

### 阶段推进逻辑

```python
# unified-workflow-driver.py line 1040-1097
if step_changed or check_step_completed(current_step, meta):
    # 标记当前步骤完成
    meta["workflow_state"]["steps"][current_step]["status"] = "completed"
    meta["workflow_state"]["steps"][current_step]["completed_at"] = datetime.now().isoformat()

    # 获取下一步
    next_step = get_next_step(current_step)

    if next_step and current_step != last_injection:
        # 更新状态机
        meta["workflow_state"]["current_step"] = next_step
        meta["workflow_state"]["steps"][next_step]["status"] = "in_progress"

        # 三文件同步
        save_json(meta_path, meta)
        save_json(active_flag_path, {...})
        save_json(workflow_state_path, workflow_state)

        # 注入下一步提示
        inject_next_step_prompt(next_step, meta, cwd)
```

### 特殊推进规则

#### Step3 → Step4 的推进条件

Step3（执行实施）是整个工作流的核心阶段，只有在**用户明确确认修复完成**后才能进入 Step4。

**实现机制**：

1. **用户确认检测** - [iteration-tracker-hook.py:203-208](../../../templates/.claude/hooks/iteration-tracker-hook.py#L203-L208)
   ```python
   confirmation_keywords = [
       r'(?:已修复|修复完成|已解决|解决了)',
       r'(?:好了|可以了|没问题了|work了)',
       r'(?:/mc-confirm)'  # 显式确认命令
   ]
   ```

2. **状态更新** - [iteration-tracker-hook.py:586-591](../../../templates/.claude/hooks/iteration-tracker-hook.py#L586-L591)
   ```python
   if intent.get("is_confirmation", False):
       state["steps"]["step3_execute"]["user_confirmed"] = True
       state["steps"]["step3_execute"]["confirmed_at"] = datetime.now().isoformat()
   ```

3. **Stop Hook 强制验证** - [enforce-cleanup.py:227-265](../../../templates/.claude/hooks/enforce-cleanup.py#L227-L265)
   ```python
   if task_type == 'bug_fix' and not user_confirmed:
       # 阻止会话结束，强制等待用户确认
       output = {
           "decision": "block",
           "reason": "BUG修复任务必须等待用户明确确认修复完成（user_confirmed=false）",
           "continue": False
       }
   ```

---

## 状态数据存储

### 三文件同步机制

系统使用三个文件维护状态，确保数据一致性和容错能力：

#### 1. workflow-state.json（运行时主数据源）

**位置**: `.claude/workflow-state.json`
**生命周期**: 会话级（Session Start → Session End）
**更新频率**: 高（每次工具调用后）

**关键字段**：
```json
{
  "task_id": "任务-1114-153022-修复玩家死亡时背包物品未掉落",
  "task_description": "...",
  "task_type": "bug_fix",
  "current_step": "step3_execute",
  "created_at": "2025-11-14T15:30:22",
  "last_injection_step": null,
  "steps": {
    "step0_context": { "status": "completed", "completed_at": "..." },
    "step1_understand": { "status": "completed", "completed_at": "..." },
    "step3_execute": {
      "status": "in_progress",
      "started_at": "...",
      "user_confirmed": false,
      "last_test_reminder_at": null,
      "last_error": null,
      "last_error_time": null
    },
    "step4_cleanup": { "status": "pending" }
  },
  "bug_fix_tracking": {
    "enabled": true,
    "bug_description": "...",
    "iterations": [
      {
        "iteration_id": 1,
        "timestamp": "...",
        "trigger": "user_feedback",
        "user_feedback": "...",
        "feedback_sentiment": "negative",
        "changes_made": [...],
        "test_result": "failed"
      }
    ],
    "loop_indicators": {
      "same_file_edit_count": 3,
      "failed_test_count": 2,
      "negative_feedback_count": 2,
      "time_spent_minutes": 15
    },
    "expert_triggered": false
  }
}
```

**代码位置**：
- 初始化：[user-prompt-submit-hook.py:944-978](../../../templates/.claude/hooks/user-prompt-submit-hook.py#L944-L978)
- 更新：[unified-workflow-driver.py:1066-1080](../../../templates/.claude/hooks/unified-workflow-driver.py#L1066-L1080)

#### 2. .task-meta.json（持久化元数据）

**位置**: `tasks/{task_id}/.task-meta.json`
**生命周期**: 任务级（任务创建 → 任务归档）
**更新频率**: 中（步骤推进、迭代追踪时）

**关键字段**：
```json
{
  "task_id": "任务-1114-153022-修复玩家死亡时背包物品未掉落",
  "task_description": "...",
  "task_type": "bug_fix",
  "task_complexity": "standard",
  "created_at": "2025-11-14T15:30:22",
  "updated_at": "2025-11-14T15:45:10",
  "workflow_state": {
    // 完整同步自 workflow-state.json（v20.2.6 修复）
    "steps": {...},
    "current_step": "step3_execute",
    "bug_fix_tracking": {...}
  },
  "metrics": {
    "docs_read": ["markdown/系统设计.md", "..."],
    "docs_read_count": 5,
    "code_changes": [
      {
        "file": "behavior_packs/.../player_death.py",
        "timestamp": "...",
        "operation": "Edit",
        "status": "success"
      }
    ],
    "code_changes_count": 8,
    "failure_count": 2,
    "failures": [...],
    "expert_review_triggered": false,
    "consecutive_failures": 0
  },
  "tracking_state": {
    // v20.2.6: 向后兼容字段
    "bug_fix_tracking": {...}
  },
  "archived": false
}
```

**代码位置**：
- 初始化：[user-prompt-submit-hook.py:1013-1030](../../../templates/.claude/hooks/user-prompt-submit-hook.py#L1013-L1030)
- 同步逻辑：[iteration-tracker-hook.py:730-777](../../../templates/.claude/hooks/iteration-tracker-hook.py#L730-L777)

#### 3. .task-active.json（快速活跃任务检查）

**位置**: `.claude/.task-active.json`
**生命周期**: 会话级
**更新频率**: 低（任务初始化、步骤推进时）

**关键字段**：
```json
{
  "task_id": "任务-1114-153022-修复玩家死亡时背包物品未掉落",
  "task_dir": "D:/path/tasks/任务-1114-153022-修复玩家死亡时背包物品未掉落",
  "current_step": "step3_execute",
  "created_at": "2025-11-14T15:30:22",
  "updated_at": "2025-11-14T15:45:10"
}
```

**用途**：
- unified-workflow-driver.py 在处理每个工具调用前快速检查是否有活跃任务
- 避免读取完整的 task-meta.json（性能优化）

**代码位置**：[unified-workflow-driver.py:795-819](../../../templates/.claude/hooks/unified-workflow-driver.py#L795-L819)

### 数据同步时机

| 触发事件 | workflow-state.json | .task-meta.json | .task-active.json |
|----------|---------------------|-----------------|-------------------|
| `/mc` 命令初始化 | ✅ 创建 | ✅ 创建 | ✅ 创建 |
| SessionStart | ✅ 从 task-meta 恢复 | - | ✅ 更新 |
| UserPromptSubmit（反馈） | ✅ 更新迭代追踪 | ✅ 同步 | - |
| PostToolUse（代码修改） | ✅ 更新 metrics | ✅ 同步 | - |
| 步骤推进 | ✅ 更新 current_step | ✅ 同步 | ✅ 更新 |
| 任务归档 | - | ✅ 标记 archived=true | ✅ 删除 |

**同步代码位置**：[unified-workflow-driver.py:1066-1080](../../../templates/.claude/hooks/unified-workflow-driver.py#L1066-L1080)

---

## Hook 触发链

### 完整触发时机

系统在以下 6 个事件点注册了 Hook：

| 事件 | 触发时机 | 注册的 Hook | 主要职责 |
|------|---------|------------|---------|
| **SessionStart** | 会话启动 | `session-start-hook.py` | 恢复任务状态、注入恢复提示 |
| **UserPromptSubmit** | 用户提交提示词 | `user-prompt-submit-hook.py`<br>`iteration-tracker-hook.py` | 任务初始化/恢复<br>意图分类、迭代追踪 |
| **PreToolUse** | 工具调用前 | `check-critical-rules.py`（Edit/Write）<br>`validate-api-usage.py`（Edit/Write）<br>`enforce-step2.py`（Read/Write/Edit）<br>`workflow-stage-enforcer.py`（All）<br>`prevent-git-history-confusion.py`（Bash） | CRITICAL 规范检查<br>API 使用验证<br>步骤顺序强制<br>工作流阶段强制<br>Git 历史混淆防护 |
| **PostToolUse** | 工具调用后 | `conversation-recorder.py`<br>`unified-workflow-driver.py`<br>`post-archive-hook.py`<br>`post-archive-doc-enforcer.py`<br>`doc-sync-enforcer.py`<br>`suggest-docs-on-error.py`（Bash）<br>`log-changes.py`（Edit/Write）<br>`create-cleanup-lock.py`（Task） | 会话历史记录<br>**状态机核心驱动**<br>任务归档<br>文档创建验证<br>文档同步验证<br>错误时推荐文档<br>代码修改日志<br>创建收尾锁文件 |
| **Stop** | 会话结束前 | `enforce-cleanup.py`<br>`post-archive-hook.py` | 收尾检查、用户确认验证<br>归档兜底 |
| **SubagentStop** | 子代理结束 | `subagent-complete-notifier.py`<br>`cleanup-subagent-stop.py` | 子代理完成通知<br>清理收尾锁文件 |

**配置文件**：[settings.json.template](../../../templates/.claude/settings.json.template)

### 关键 Hook 详解

#### unified-workflow-driver.py（PostToolUse）

**触发条件**: 任何工具（Read/Write/Edit/Bash）执行后

**执行流程**：

```
1. 快速检查 .task-active.json
   ├─ 无活跃任务 → 跳过
   └─ 有活跃任务 → 继续

2. 加载任务元数据
   └─ 读取 .task-meta.json

3. 工具类型分发处理
   ├─ Read → 更新文档阅读记录
   ├─ Write/Edit → 记录代码修改 + 同文件编辑计数
   │             → v20.2.7: 注入测试提醒（BUG修复任务）
   └─ Bash → 检测测试失败

4. 检查步骤完成条件
   └─ 完成 → 推进到下一步骤 + 三文件同步

5. 循环检测与专家触发
   ├─ check_expert_trigger()
   └─ 满足条件 → launch_meta_expert()

6. 状态保存
   └─ save_json(meta_path, meta)
```

**代码位置**：[unified-workflow-driver.py:784-1163](../../../templates/.claude/hooks/unified-workflow-driver.py#L784-L1163)

#### iteration-tracker-hook.py（UserPromptSubmit）

**触发条件**: 用户提交每条输入

**意图分类**：

```python
classify_intent(user_input) → {
  "task_type": "bug_fix" | "feature_implementation" | "general",
  "is_feedback": bool,
  "sentiment": "positive" | "negative" | "frustrated" | "neutral",
  "confidence": float,
  "is_confirmation": bool,  # v20.3: 用户确认标志
  "feedback_source": "user" | "tool_error"
}
```

**更新逻辑**：

```
1. 检测用户确认关键词
   └─ "已修复" / "/mc-confirm" → is_confirmation = true

2. 更新 workflow-state.json
   ├─ step3_execute.user_confirmed = true（如果是确认）
   └─ bug_fix_tracking.iterations.append(...)

3. 同步到 .task-meta.json
   └─ 使用原子更新（atomic_update_json）

4. 记录到 .conversation.jsonl
```

**代码位置**：
- 意图分类：[iteration-tracker-hook.py:51-220](../../../templates/.claude/hooks/iteration-tracker-hook.py#L51-L220)
- 状态更新：[iteration-tracker-hook.py:553-778](../../../templates/.claude/hooks/iteration-tracker-hook.py#L553-L778)

#### enforce-cleanup.py（Stop）

**触发条件**: AI 尝试结束会话

**检查逻辑**：

```
1. 读取 workflow-state.json（v20.2.6 优先级修复）

2. 检查 step4_cleanup.status
   ├─ completed → 允许结束
   └─ 未完成 → 继续检查

3. 检查 task_type + user_confirmed
   ├─ bug_fix + !user_confirmed → 阻止结束（等待用户确认）
   └─ user_confirmed → 询问收尾意愿

4. 询问收尾意愿（v20.2.7 防重复询问）
   ├─ !asked_cleanup_intent → 首次询问 + 设置标记
   ├─ asked_cleanup_intent + wait_time < 10min → 静默等待
   └─ asked_cleanup_intent + wait_time ≥ 10min → 重置标记
```

**代码位置**：[enforce-cleanup.py:176-365](../../../templates/.claude/hooks/enforce-cleanup.py#L176-L365)

---

## 状态转换逻辑

### 步骤完成条件

每个步骤有明确的完成条件，由 `check_step_completed()` 函数判断：

```python
# unified-workflow-driver.py line 475-492
def check_step_completed(step_name, meta):
    steps = meta["workflow_state"]["steps"]

    if step_name == "step0_context":
        # 检测 CLAUDE.md 是否被读取
        docs_read = meta.get("metrics", {}).get("docs_read", [])
        return any("CLAUDE.md" in doc.upper() for doc in docs_read)

    elif step_name == "step1_understand":
        # 至少阅读 1 个文档
        return meta.get("metrics", {}).get("docs_read_count", 0) > 0

    elif step_name == "step3_execute":
        # 用户明确确认修复完成
        return steps["step3_execute"].get("user_confirmed", False)

    elif step_name == "step4_cleanup":
        # 收尾子代理标记完成
        return steps["step4_cleanup"]["status"] == "completed"

    return False
```

### 步骤推进顺序

```python
# unified-workflow-driver.py line 494-503
def get_next_step(current_step):
    step_order = ["step0_context", "step1_understand", "step3_execute", "step4_cleanup"]

    try:
        current_idx = step_order.index(current_step)
        if current_idx < len(step_order) - 1:
            return step_order[current_idx + 1]
    except ValueError:
        pass

    return None
```

### 状态转换图

```
┌─────────────────┐
│ /mc 命令初始化   │
└────────┬────────┘
         │ user-prompt-submit-hook.py
         │ 创建 workflow-state.json
         │ 创建 .task-meta.json
         │ 创建 .task-active.json
         ↓
┌─────────────────┐
│  step0_context  │ ← Read CLAUDE.md
│   (已跳过v20.1) │
└────────┬────────┘
         │ unified-workflow-driver.py
         │ check_step_completed("step0_context") → true
         │ get_next_step() → "step1_understand"
         │ inject_next_step_prompt()
         ↓
┌─────────────────┐
│ step1_understand│ ← Read 至少 1 个文档
└────────┬────────┘
         │ unified-workflow-driver.py
         │ check_step_completed("step1_understand") → true
         │ get_next_step() → "step3_execute"
         │ inject_next_step_prompt()
         ↓
┌─────────────────────────────────────────────────────┐
│              step3_execute                          │
│  核心执行阶段（代码修改、测试、迭代）                 │
│                                                     │
│  循环：                                              │
│  1. AI 修改代码（Write/Edit）                       │
│  2. AI 运行测试（Bash）                             │
│  3. 用户反馈（UserPromptSubmit）                    │
│     ├─ 负面反馈 → iteration_tracker 记录迭代        │
│     ├─ same_file_edit_count++                      │
│     └─ 循环检测 → 触发专家？                        │
│  4. 直到用户输入"已修复"                             │
│     └─ iteration_tracker 设置 user_confirmed=true  │
└────────┬────────────────────────────────────────────┘
         │ unified-workflow-driver.py
         │ check_step_completed("step3_execute") → user_confirmed=true
         │ get_next_step() → "step4_cleanup"
         │ inject_next_step_prompt() → trigger_doc_update_agent()
         ↓
┌─────────────────────────────────────────────────────┐
│              step4_cleanup                          │
│  收尾阶段（子代理执行）                               │
│                                                     │
│  1. unified-workflow-driver 注入子代理任务提示       │
│  2. AI 调用 Task 工具启动收尾子代理                  │
│  3. create-cleanup-lock.py 创建 .cleanup-subagent.lock│
│  4. 子代理执行收尾工作：                             │
│     ├─ 读取 .conversation.jsonl                    │
│     ├─ 生成 context.md / solution.md               │
│     ├─ 清理 DEBUG 代码                             │
│     ├─ 更新 markdown/ 文档                         │
│     └─ Write 更新 .task-meta.json                  │
│        └─ workflow_state.steps.step4_cleanup.status = "completed"│
│  5. cleanup-subagent-stop.py 删除锁文件             │
└────────┬────────────────────────────────────────────┘
         │ post-archive-hook.py
         │ check_if_just_completed() → step4=completed
         │ acquire_archive_lock()
         │ move_to_archive() → tasks/已归档/
         │ mark_as_archived() → archived=true
         │ inject_doc_sync_task() → 注入文档同步提示
         ↓
┌─────────────────┐
│   任务归档完成   │
└─────────────────┘
```

---

## 专家触发机制

### 触发条件

系统通过监测**循环模式**来识别AI陷入无效迭代，触发专家审查。

**检测函数**：`check_expert_trigger(meta, cwd)` - [unified-workflow-driver.py:211-307](../../../templates/.claude/hooks/unified-workflow-driver.py#L211-L307)

#### Bug修复循环检测

```python
# unified-workflow-driver.py line 232-272
if workflow_state.get("bug_fix_tracking", {}).get("enabled"):
    tracking = workflow_state["bug_fix_tracking"]
    indicators = tracking.get("loop_indicators", {})
    iterations_count = len(tracking.get("iterations", []))

    # 触发条件：
    # 1. 至少 2 次迭代
    # 2. 至少 2 次负面反馈
    # 3. 至少 2 次同文件修改
    negative_count = indicators.get("negative_feedback_count", 0)
    same_file_count = indicators.get("same_file_edit_count", 0)

    if (iterations_count >= 2 and
        negative_count >= 2 and
        same_file_count >= 2):

        return {
            "should_trigger": True,
            "loop_type": "bug_fix_loop",
            "confidence": 0.9,
            "evidence": {
                "iterations": iterations_count,
                "negative_feedback": negative_count,
                "same_file_edits": same_file_count,
                "pattern": "表象修复循环 - 反复修改同一位置但未解决根本问题"
            }
        }
```

**实际案例**：

```
任务: 修复玩家死亡时背包物品未掉落

迭代1:
  - AI 修改 player_death.py，添加物品掉落代码
  - 用户反馈："还是不掉落"（negative_feedback_count: 1）
  - same_file_edit_count: 1

迭代2:
  - AI 再次修改 player_death.py，调整触发条件
  - 用户反馈："依然没效果"（negative_feedback_count: 2）
  - same_file_edit_count: 2

触发专家：
  ✅ iterations_count = 2
  ✅ negative_feedback_count = 2
  ✅ same_file_edit_count = 2
  → 专家系统启动，生成根因分析报告
```

#### 需求实现循环检测

```python
# unified-workflow-driver.py line 274-300
if workflow_state.get("feature_tracking", {}).get("enabled"):
    tracking = workflow_state["feature_tracking"]
    iterations_count = len(tracking.get("iterations", []))

    # 触发条件：
    # 1. 至少 2 次迭代
    # 2. 至少 2 次不满意反馈
    dissatisfied_count = sum(
        1 for iter in tracking.get("iterations", [])
        if iter.get("user_satisfaction") == "dissatisfied"
    )

    if (iterations_count >= 2 and dissatisfied_count >= 2):
        return {
            "should_trigger": True,
            "loop_type": "requirement_mismatch",
            "confidence": 0.85,
            "evidence": {
                "iterations": iterations_count,
                "dissatisfied_count": dissatisfied_count,
                "pattern": "需求理解偏差 - 实现方向与用户期望不一致"
            }
        }
```

### 专家分析流程

```
1. 检测到循环模式
   └─ check_expert_trigger() → should_trigger=true

2. 读取完整迭代历史
   └─ workflow_state["bug_fix_tracking"]["iterations"]

3. 构建历史摘要
   ├─ 每次迭代的时间、反馈、修改文件
   └─ loop_indicators（同文件编辑次数、负面反馈次数）

4. 生成专家分析 Prompt
   └─ launch_meta_expert() → expert_prompt

5. 注入到对话上下文
   ├─ additionalContext: expert_prompt
   └─ AI 看到完整历史 + 专家任务指引

6. AI 生成诊断报告
   ├─ 根因分析
   ├─ 备选方案（A/B/C）
   ├─ 推荐策略
   └─ 需要澄清的问题

7. 标记专家已触发
   └─ meta["metrics"]["expert_review_triggered"] = true
```

**代码位置**：[unified-workflow-driver.py:310-471](../../../templates/.claude/hooks/unified-workflow-driver.py#L310-L471)

### 专家 Prompt 结构

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 专家审查系统已触发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 检测到的问题模式

**循环类型**: bug_fix_loop
**置信度**: 90%
**证据**:
- iterations: 3
- negative_feedback: 3
- same_file_edits: 5
- pattern: 表象修复循环 - 反复修改同一位置但未解决根本问题

## 迭代历史

### 迭代 1
- 时间: 2025-11-14T15:35:10
- 用户反馈: 还是不掉落
- 情感: negative
- 修改文件:
  - player_death.py: 添加物品掉落代码

### 迭代 2
- 时间: 2025-11-14T15:42:30
- 用户反馈: 依然没效果
- 情感: frustrated
- 修改文件:
  - player_death.py: 调整触发条件

## 你的任务

你现在需要从**战略高度**分析问题，而非继续尝试修复。

### 场景A: Bug修复循环
如果是Bug修复循环，请回答：

1. **根因分析**: 为什么反复修改仍失败?
   - 是否陷入表象修复?
   - 是否存在架构层面的缺陷?
   - 是否对问题的理解有误?

2. **失败模式**: 历史修改中有哪些共同的错误假设?

3. **备选路径**: 除了当前方向，还有哪3-5种可能的解决思路?
   - 路径A: [名称] - [优点] - [缺点] - [适用场景]
   - 路径B: ...

4. **推荐策略**: 推荐哪种路径，以及如何验证?

## 输出格式

使用以下Markdown格式输出：

# 🎯 专家诊断报告

## 1. 问题根因

[深度分析...]

## 2. 备选方案

### 方案A: [名称]
- **优点**: ...
- **缺点**: ...
- **适用场景**: ...
- **预计工作量**: ...

### 方案B: [名称]
...

## 3. 推荐策略

[具体建议，包括实施步骤和验证方法]

## 4. 需要向用户澄清的问题

1. [问题1]
2. [问题2]
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

请立即开始分析。
```

---

## 收尾阶段机制

Step4（收尾归档）采用**强制子代理执行**机制，确保收尾工作规范执行且不污染主会话上下文。

### 设计理念

1. **父代理职责隔离** - 父代理只负责推进工作流，不执行具体收尾工作
2. **子代理独立执行** - 收尾工作由独立子代理完成，避免上下文污染
3. **PreToolUse 强制拦截** - workflow-stage-enforcer.py 阻止父代理直接操作
4. **锁文件识别机制** - .cleanup-subagent.lock 区分父代理和子代理

### 收尾流程

#### 1. 推进到 Step4

```python
# unified-workflow-driver.py line 638-686
def inject_next_step_prompt(next_step, meta, cwd=None):
    # 特殊处理：步骤4启动子代理
    if next_step == "step4_cleanup" and cwd:
        # v20.2.7: 先从会话历史生成 context.md 和 solution.md
        task_id = meta.get("task_id")
        task_dir = os.path.join(cwd, 'tasks', task_id)
        conversation_file = os.path.join(task_dir, '.conversation.jsonl')

        if os.path.exists(conversation_file):
            # 调用 generate-docs-from-conversation.py
            result = subprocess.run(
                [sys.executable, '.claude/hooks/generate-docs-from-conversation.py', task_dir],
                ...
            )

        # 继续启动子代理
        agent_message = trigger_doc_update_agent(meta, cwd)
        if agent_message:
            output = {
                "continue": True,
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": agent_message
                }
            }
            print(json.dumps(output, ensure_ascii=False))
```

注入到对话的内容：

```markdown
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 启动文档更新子代理
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

检测到步骤4（收尾归档）开始，系统将启动专门的子代理完成以下工作：
- 📝 自动更新markdown文档中的"待补充"内容
- 🧹 检查并清理DEBUG代码
- 📦 整理任务归档

**请使用Task工具启动子代理**：

```
Task(
    subagent_type="general-purpose",
    description="文档更新与收尾工作",
    prompt=Read(".claude/.agent-doc-update.txt").content
)
```

子代理将独立完成所有收尾工作，不消耗主会话上下文。
完成后会输出详细报告。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 2. 父代理调用 Task 工具

```python
# AI 收到上述提示后，调用 Task 工具
Task(
    subagent_type="general-purpose",
    description="文档更新与收尾工作",
    prompt=Read(".claude/.agent-doc-update.txt").content
)
```

#### 3. create-cleanup-lock.py（PostToolUse[Task]）

```python
# create-cleanup-lock.py
# 检测到 Task 工具被调用，且 current_step = "step4_cleanup"
if tool_name == "Task" and current_step == "step4_cleanup":
    # 创建锁文件
    lock_file = os.path.join(task_dir, '.cleanup-subagent.lock')
    with open(lock_file, 'w', encoding='utf-8') as f:
        f.write(f"locked_at: {datetime.now().isoformat()}\n")
```

**代码位置**：[create-cleanup-lock.py](../../../templates/.claude/hooks/create-cleanup-lock.py)

#### 4. workflow-stage-enforcer.py（PreToolUse）

在子代理执行期间，所有工具调用都会被 workflow-stage-enforcer.py 拦截检查：

```python
# workflow-stage-enforcer.py line 99-109
if current_step == "step4_cleanup":
    # 检查收尾子代理锁文件是否存在
    lock_file = os.path.join(task_dir, '.cleanup-subagent.lock')

    if os.path.exists(lock_file):
        # 子代理正在执行，允许所有工具调用
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "收尾子代理正在执行（检测到锁文件）"
            },
            "suppressOutput": True
        }))
        sys.exit(0)
```

如果**没有锁文件**（父代理试图直接操作），则拦截：

```python
# workflow-stage-enforcer.py line 204-266
# 拦截：其他所有工具调用
denial_reason = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 工具调用被拒绝: {tool_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 当前阶段: step4_cleanup
❌ 违规行为: 在父代理中直接执行收尾工作

⚠️ 根据CLAUDE.md P0规则，收尾工作**必须在子代理中执行**！

✅ 正确做法:

如果你已收到Hook提示"启动文档更新子代理"，使用Task工具：

Task(
    subagent_type="general-purpose",
    description="文档更新与收尾工作",
    prompt=Read(".claude/.agent-doc-update.txt").content
)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": denial_reason
    }
}, ensure_ascii=False))
sys.exit(0)
```

**代码位置**：[workflow-stage-enforcer.py:89-266](../../../templates/.claude/hooks/workflow-stage-enforcer.py#L89-L266)

#### 5. 子代理执行收尾工作

子代理按照 `.agent-doc-update.txt` 中的任务执行：

```
Step 1: 搜索待补充标记
  └─ Grep("待补充|TODO", path="markdown/", output_mode="files_with_matches")

Step 2: 分析相关性
  └─ 判断是否与主任务相关

Step 3: 执行更新
  ├─ ≤2个相关文档 → 使用 Edit 更新
  └─ >2个相关文档 → 追加到 markdown/文档待补充清单.md

Step 4: DEBUG clean check
  └─ Grep("DEBUG|print.*debug", path=".", glob="*.py")

Step 5: ⚠️ CRITICAL - 标记 step4_cleanup 完成
  1. Read latest task's .task-meta.json
  2. Set workflow_state.steps.step4_cleanup.status = "completed"
  3. Write back the updated JSON

Step 6: Output completion report
```

**关键点**：子代理必须执行 **Step 5**，否则任务无法完成归档。

#### 6. cleanup-subagent-stop.py（SubagentStop）

```python
# cleanup-subagent-stop.py
# 子代理结束时删除锁文件
lock_file = os.path.join(task_dir, '.cleanup-subagent.lock')
if os.path.exists(lock_file):
    os.remove(lock_file)
```

**代码位置**：[cleanup-subagent-stop.py](../../../templates/.claude/hooks/cleanup-subagent-stop.py)

#### 7. post-archive-hook.py（PostToolUse）

```python
# post-archive-hook.py line 102-120
# 检查任务是否刚完成
just_completed, meta = check_if_just_completed(str(meta_file))

def check_if_just_completed(meta_file):
    meta = json.load(open(meta_file))

    # 检查是否已归档
    if meta.get("archived", False):
        return False, None

    # 检查step4是否完成
    step4_status = meta.get("workflow_state", {}).get("steps", {}).get("step4_cleanup", {}).get("status")
    if step4_status != "completed":
        return False, None

    return True, meta
```

如果 step4_cleanup.status = "completed"，则执行归档：

```python
# post-archive-hook.py line 426-500
# 获取归档锁
if not acquire_archive_lock(task_dir):
    # 跳过（防止并发执行）
    sys.exit(0)

try:
    # 1. 移动到归档目录
    archived_path = move_to_archive(task_dir, project_path)
    # tasks/任务-XXXX → tasks/已归档/任务-XXXX

    # 2. 标记为已归档
    mark_as_archived(archived_path)
    # meta["archived"] = True

    # 3. 注入文档同步任务（如果是 PostToolUse 触发）
    if event_name == "PostToolUse":
        injection = inject_doc_sync_task(meta, archived_path)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": injection
            },
            "continue": True
        }

    # 4. 释放锁
    release_archive_lock(archived_path)

finally:
    release_archive_lock(task_dir)
```

**代码位置**：[post-archive-hook.py:102-516](../../../templates/.claude/hooks/post-archive-hook.py#L102-L516)

### 收尾阶段时序图

```
[Step3完成] user_confirmed=true
      │
      ↓ unified-workflow-driver.py (PostToolUse)
      │ check_step_completed("step3_execute") → true
      │ get_next_step() → "step4_cleanup"
      │
      ↓ inject_next_step_prompt("step4_cleanup")
      │ trigger_doc_update_agent()
      │ 注入子代理启动提示 → additionalContext
      │
      ↓ AI 收到提示
      │ 调用 Task 工具
      │
      ↓ create-cleanup-lock.py (PostToolUse[Task])
      │ 创建 .cleanup-subagent.lock
      │
      ┌─────────────────────────────────────────┐
      │         收尾子代理执行                   │
      │                                         │
      │  每次工具调用前：                        │
      │  └─ workflow-stage-enforcer.py (PreToolUse)
      │     └─ 检测到 .cleanup-subagent.lock  │
      │        └─ allow（豁免）                │
      │                                         │
      │  Step 1: Grep 搜索待补充文档            │
      │  Step 2: 分析相关性                     │
      │  Step 3: Edit 更新文档                 │
      │  Step 4: Grep 搜索 DEBUG 代码          │
      │  Step 5: ⚠️ Write 更新 .task-meta.json│
      │           └─ step4_cleanup.status="completed"│
      │  Step 6: 输出报告                       │
      └────────┬────────────────────────────────┘
               │
               ↓ cleanup-subagent-stop.py (SubagentStop)
               │ 删除 .cleanup-subagent.lock
               │
               ↓ post-archive-hook.py (PostToolUse)
               │ check_if_just_completed()
               │   └─ step4_status="completed" → true
               │ acquire_archive_lock()
               │ move_to_archive()
               │   └─ tasks/任务-XXXX → tasks/已归档/任务-XXXX
               │ mark_as_archived()
               │   └─ meta["archived"] = true
               │ inject_doc_sync_task()
               │   └─ 注入文档同步提示
               │
               ↓ [任务归档完成]
```

---

## 任务恢复机制

### 恢复触发

用户可以通过以下方式恢复已有任务：

```bash
/mc tasks/任务-1114-153022-修复玩家死亡时背包物品未掉落
/mc 任务-1114-153022-修复玩家死亡时背包物品未掉落
/mc D:\path\tasks\任务-1114-153022-修复玩家死亡时背包物品未掉落
```

### 检测逻辑

```python
# user-prompt-submit-hook.py line 501-597
def detect_existing_task_dir(prompt, cwd):
    """检测用户输入中是否包含已存在的任务目录"""

    tasks_base_dir = os.path.join(cwd, 'tasks')

    # 获取所有已存在的任务目录名
    existing_tasks = [
        d for d in os.listdir(tasks_base_dir)
        if os.path.isdir(os.path.join(tasks_base_dir, d))
        and d.startswith('任务-')
    ]

    # 检测用户输入中是否包含任何已存在的任务目录
    for task_id in existing_tasks:
        patterns = [
            re.escape(task_id),  # 精确匹配任务ID
            re.escape(os.path.join('tasks', task_id).replace('\\', '/')),
            re.escape(os.path.join('tasks', task_id)),
        ]

        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                task_dir = os.path.join(tasks_base_dir, task_id)

                # 验证 .task-meta.json 存在
                meta_path = os.path.join(task_dir, '.task-meta.json')
                if not os.path.exists(meta_path):
                    continue

                # 提取新用户输入（去除路径部分）
                new_user_input = prompt.replace('/mc', '').strip()
                new_user_input = new_user_input.replace(match.group(0), '').strip()

                return {
                    "is_resume": True,
                    "task_dir": task_dir,
                    "task_id": task_id,
                    "new_user_input": new_user_input
                }

    return {"is_resume": False}
```

**代码位置**：[user-prompt-submit-hook.py:501-597](../../../templates/.claude/hooks/user-prompt-submit-hook.py#L501-L597)

### 恢复流程

```python
# user-prompt-submit-hook.py line 599-794
def resume_existing_task(task_dir, task_id, new_user_input, cwd):
    """恢复已有任务的工作流"""

    # 1. 加载任务元数据
    with open(meta_path, 'r', encoding='utf-8') as f:
        task_meta = json.load(f)

    # 2. 恢复 workflow-state.json（复用 session-start-hook 逻辑）
    workflow_state = task_meta.get('workflow_state', {})
    workflow_state['task_id'] = task_id
    workflow_state['resumed_at'] = datetime.now().isoformat()
    workflow_state['resume_reason'] = new_user_input

    # 强制删除旧文件（确保不会残留旧数据）
    if os.path.exists(workflow_state_path):
        os.remove(workflow_state_path)

    # 保存恢复的状态
    with open(workflow_state_path, 'w', encoding='utf-8') as f:
        json.dump(workflow_state, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())

    # 3. 更新 .task-active.json
    active_data = {
        "task_id": task_id,
        "task_dir": task_dir,
        "current_step": workflow_state.get('current_step', 'step3_execute'),
        "updated_at": datetime.now().isoformat(),
        "resumed": True
    }
    with open(active_flag_path, 'w', encoding='utf-8') as f:
        json.dump(active_data, f, indent=2, ensure_ascii=False)

    # 4. 记录恢复事件到 .conversation.jsonl
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": "system",
        "content": f"任务恢复: {new_user_input}",
        "event_type": "task_resume",
        "new_user_input": new_user_input
    }
    with open(conversation_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    # 5. 生成智能恢复提示（包含历史迭代摘要）
    tracking_state = task_meta.get('tracking_state', {})
    bug_fix_tracking = tracking_state.get('bug_fix_tracking', {})
    iterations = bug_fix_tracking.get('iterations', [])

    resume_prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **任务恢复模式已激活** (v20.2.16)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {task_id}
**任务类型**: {task_type_display}
**原始需求**: {task_meta.get('task_description', '')}
**当前步骤**: {workflow_state.get('current_step', 'unknown')}
**已完成迭代**: {len(iterations)}次

## 📜 历史迭代摘要

{历史迭代详情...}

## 🎯 用户新需求

{new_user_input}

## 📋 恢复任务建议

1. ✅ **查看历史会话**:
   ```
   Read("tasks/{task_id}/context.md")
   Read("tasks/{task_id}/solution.md")
   ```

2. ✅ **查看代码修改历史**:
   - 检查 .task-meta.json 中的 metrics.code_changes
   - 了解之前修改了哪些文件

3. ✅ **分析失败原因**:
   - 为什么之前的尝试失败了?
   - 是否存在错误的假设?
   - 用户反馈中的关键信息是什么?

4. ✅ **制定新策略**:
   - 基于历史经验调整方案
   - 避免重复已失败的路径
   - 聚焦用户新提出的问题

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**立即开始**: 基于历史上下文,继续任务实施
"""

    return resume_prompt
```

**代码位置**：[user-prompt-submit-hook.py:599-794](../../../templates/.claude/hooks/user-prompt-submit-hook.py#L599-L794)

### 恢复输出

```python
# user-prompt-submit-hook.py line 826-845
# 输出控制JSON（官方格式 v20.2.17）
output = {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": resume_prompt
    },
    "continue": True
}
print(json.dumps(output, ensure_ascii=False))

# VSCode 通知
notify_info(
    f"✅ 任务已恢复 | {task_id}",
    f"继续执行: {new_user_input[:40]}"
)
```

---

## 循环检测与防护

### 意图分类系统

系统通过 NLP 模式匹配实现用户意图分类：

```python
# iteration-tracker-hook.py line 51-220
def classify_intent(user_input: str, tool_error=None) -> dict:
    """意图分类器 - 识别任务类型和反馈特征"""

    intent = {
        "task_type": "general",
        "is_feedback": False,
        "sentiment": "neutral",
        "confidence": 0.0,
        "feedback_source": "user",
        "is_confirmation": False
    }

    # === v20.3新增：工具失败识别 ===
    if tool_error:
        intent["is_feedback"] = True
        intent["sentiment"] = "negative"
        intent["confidence"] = 0.95
        intent["feedback_source"] = "tool_error"
        return intent

    # === Bug修复特征 ===
    bug_keywords = [
        r'(?:修复|fix|bug|错误|报错|崩溃|不work|不生效)',
        r'(?:还是|仍然|依然).*(?:不行|失败|有问题)',
        r'测试.*(?:失败|不通过|有问题)',
        r'掉落.*失败', r'物品.*未', r'死亡.*问题',
    ]

    # === 反馈特征 ===
    feedback_keywords = [
        r'(?:还是|仍然|依然|又|再次).*(?:不行|有问题|失败)',
        r'(?:不对|不是|不太对|不太行)',
        r'(?:能不能|可以|希望|想要).*(?:改成|换成|调整)',
        r'(?:又|还|还有).*(?:问题|错误|Bug)',
        r'(?:测试|试了|运行).*(?:失败|不行|有问题)'
    ]

    # === 情感分析 ===
    negative_sentiment = [
        r'(?:还是不行|完全不work|根本没用)',
        r'(?:怎么|为什么).*(?:还是|仍然)',
        r'(?:又出|又有|又是).*(?:问题|错误)',
        r'(?:问题|错误).*(?:依旧|还是|仍然)',
        r'(?:没有|未).*(?:修复|解决|生效)'
    ]

    frustrated_sentiment = [
        r'(?:沮丧|无语|崩溃|绝望)',
        r'(?:一直|总是|每次).*(?:失败|不行)',
        r'(?:怎么办|没办法|搞不定)'
    ]

    positive_sentiment = [
        r'(?:好了|成功|搞定|修复了|解决了|已修复)',
        r'(?:没问题|可以了|work|正常|完成了)'
    ]

    # === 用户确认关键词（v20.3）===
    confirmation_keywords = [
        r'(?:已修复|修复完成|已解决|解决了)',
        r'(?:好了|可以了|没问题了|work了)',
        r'(?:/mc-confirm)'
    ]

    # === 分类逻辑 ===
    for pattern in bug_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            intent["task_type"] = "bug_fix"
            intent["confidence"] = 0.8
            break

    for pattern in confirmation_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            intent["is_confirmation"] = True
            intent["is_feedback"] = True
            intent["sentiment"] = "positive"
            break

    return intent
```

**代码位置**：[iteration-tracker-hook.py:51-220](../../../templates/.claude/hooks/iteration-tracker-hook.py#L51-L220)

### 迭代追踪更新

```python
# iteration-tracker-hook.py line 553-778
def update_tracking_state(intent: dict, user_input: str, cwd: str, logger):
    """更新迭代追踪状态"""

    # v20.3: 使用原子更新防止并行冲突
    def update_workflow_state_data(state):
        # === v20.3: 用户确认检测 ===
        if intent.get("is_confirmation", False):
            state["steps"]["step3_execute"]["user_confirmed"] = True
            state["steps"]["step3_execute"]["confirmed_at"] = datetime.now().isoformat()

        # === Bug修复追踪 ===
        if intent["task_type"] == "bug_fix" or state.get("task_type") == "bug_fix":
            if "bug_fix_tracking" not in state:
                state["bug_fix_tracking"] = {
                    "enabled": True,
                    "iterations": [],
                    "loop_indicators": {
                        "same_file_edit_count": 0,
                        "failed_test_count": 0,
                        "negative_feedback_count": 0
                    },
                    "expert_triggered": False
                }

            # 如果是反馈，记录新迭代
            if intent["is_feedback"]:
                tracking = state["bug_fix_tracking"]
                iteration_id = len(tracking["iterations"]) + 1

                tracking["iterations"].append({
                    "iteration_id": iteration_id,
                    "timestamp": datetime.now().isoformat(),
                    "trigger": "user_feedback",
                    "user_feedback": user_input,
                    "feedback_sentiment": intent["sentiment"],
                    "changes_made": [],
                    "test_result": "pending"
                })

                # 更新循环指标
                if intent["sentiment"] in ["negative", "frustrated"]:
                    tracking["loop_indicators"]["negative_feedback_count"] += 1
                    tracking["loop_indicators"]["failed_test_count"] += 1

        return state

    # 执行原子更新 workflow-state.json
    atomic_update_json(workflow_state_path, update_workflow_state_data)

    # 同步到 .task-meta.json
    def update_task_meta_data(task_meta):
        # v20.2.6核心修复: 完整同步 workflow_state（包括 steps）
        task_meta["workflow_state"]["steps"] = workflow_state.get("steps", {})
        task_meta["workflow_state"]["bug_fix_tracking"] = workflow_state.get("bug_fix_tracking")
        task_meta["task_type"] = workflow_state.get("task_type", "general")
        task_meta["updated_at"] = datetime.now().isoformat()
        return task_meta

    atomic_update_json(meta_path, update_task_meta_data)
```

**代码位置**：[iteration-tracker-hook.py:553-778](../../../templates/.claude/hooks/iteration-tracker-hook.py#L553-L778)

### 同文件编辑计数

```python
# unified-workflow-driver.py line 97-131
def update_code_changes(meta, tool_data, cwd):
    """记录代码修改并更新同文件编辑计数"""

    file_path = tool_data.get("tool_input", {}).get("file_path", "")

    change_record = {
        "file": file_path,
        "timestamp": datetime.now().isoformat(),
        "operation": tool_data.get("tool_name", "Unknown"),
        "status": "success"
    }

    meta["metrics"]["code_changes"].append(change_record)
    meta["metrics"]["code_changes_count"] = len(meta["metrics"]["code_changes"])

    # v20.2: 统计同文件编辑次数
    same_file_edits = sum(
        1 for change in meta["metrics"]["code_changes"]
        if change["file"] == file_path
    )

    # 同步到 workflow-state.json 的 bug_fix_tracking
    workflow_state = load_json(workflow_state_path)
    if workflow_state and "bug_fix_tracking" in workflow_state:
        workflow_state["bug_fix_tracking"]["loop_indicators"]["same_file_edit_count"] = same_file_edits
        save_json(workflow_state_path, workflow_state)
```

**代码位置**：[unified-workflow-driver.py:97-131](../../../templates/.claude/hooks/unified-workflow-driver.py#L97-L131)

### 任务类型自动纠正

```python
# unified-workflow-driver.py line 890-908
# v20.2.13新增：运行时任务类型纠正
# 如果同文件修改≥3次且task_type=general，自动纠正为bug_fix
workflow_state_for_check = meta.get("workflow_state", {})
bug_tracking = workflow_state_for_check.get("bug_fix_tracking", {})

if bug_tracking.get("enabled"):
    same_file_edits = bug_tracking.get("loop_indicators", {}).get("same_file_edit_count", 0)

    if same_file_edits >= 3 and meta.get("task_type") == "general":
        sys.stderr.write("[AUTO-CORRECT] 任务类型从general纠正为bug_fix（同文件修改≥3次）\n")
        meta["task_type"] = "bug_fix"

        # 同步到 workflow-state.json
        workflow_state_path = os.path.join(cwd, '.claude', 'workflow-state.json')
        workflow_state_data = load_json(workflow_state_path)
        if workflow_state_data:
            workflow_state_data["task_type"] = "bug_fix"
            save_json(workflow_state_path, workflow_state_data)

        save_json(meta_path, meta)
```

**代码位置**：[unified-workflow-driver.py:890-908](../../../templates/.claude/hooks/unified-workflow-driver.py#L890-L908)

---

## 数据流图

### 任务初始化数据流

```
用户输入: /mc 修复玩家死亡时背包物品未掉落
         │
         ↓ user-prompt-submit-hook.py (UserPromptSubmit)
         │
    [任务恢复检测]
         │ detect_existing_task_dir() → is_resume=false
         │
    [提取任务描述]
         │ task_desc = "修复玩家死亡时背包物品未掉落"
         │ timestamp = "1114-153022"
         │ task_id = "任务-1114-153022-修复玩家死亡时背包物品未掉落"
         │
    [创建任务目录]
         │ tasks/任务-1114-153022-修复玩家死亡时背包物品未掉落/
         │
    [初始化 workflow-state.json]
         │ {
         │   "task_id": "...",
         │   "task_type": "bug_fix",  # is_bugfix_task() → true
         │   "current_step": "step3_execute",
         │   "steps": {...},
         │   "bug_fix_tracking": {
         │     "enabled": true,
         │     "iterations": [],
         │     "loop_indicators": {
         │       "same_file_edit_count": 0,
         │       "negative_feedback_count": 0,
         │       "failed_test_count": 0
         │     }
         │   }
         │ }
         │ 保存到 .claude/workflow-state.json
         │
    [初始化 .task-meta.json]
         │ {
         │   "task_id": "...",
         │   "task_type": "bug_fix",
         │   "workflow_state": {...},  # 同步自 workflow-state.json
         │   "metrics": {
         │     "docs_read": [],
         │     "code_changes": [],
         │     "failure_count": 0
         │   }
         │ }
         │ 保存到 tasks/任务-1114-.../. task-meta.json
         │
    [初始化 .task-active.json]
         │ {
         │   "task_id": "...",
         │   "task_dir": "...",
         │   "current_step": "step3_execute"
         │ }
         │ 保存到 .claude/.task-active.json
         │
    [创建 .conversation.jsonl]
         │ {
         │   "timestamp": "...",
         │   "role": "user",
         │   "content": "/mc 修复玩家死亡时背包物品未掉落",
         │   "event_type": "task_init"
         │ }
         │ 保存到 tasks/任务-1114-.../.conversation.jsonl
         │
    [生成任务头部 + 边界声明 + 玩法包/BUG修复指引]
         │ task_header = generate_task_header()
         │ task_boundary = generate_task_boundary_notice()
         │ guidance = format_bugfix_guide()  # BUG修复智能指引
         │
         ↓ 注入到对话
    [输出 hookSpecificOutput]
         {
           "hookSpecificOutput": {
             "hookEventName": "UserPromptSubmit",
             "additionalContext": task_header + task_boundary + guidance
           },
           "continue": true
         }
```

### 工具调用数据流

```
AI 调用 Write 工具
  └─ Write("behavior_packs/.../player_death.py", content="...")
         │
         ↓ PreToolUse Hook Chain
         │
    [check-critical-rules.py]
         │ 检查 CRITICAL 规范
         │ └─ 无违规 → allow
         │
    [validate-api-usage.py]
         │ 检查 API 使用
         │ └─ 无问题 → allow
         │
    [workflow-stage-enforcer.py]
         │ current_step = "step3_execute"
         │ └─ 非 step4 → allow
         │
         ↓ 工具执行
         │ Write 成功
         │
         ↓ PostToolUse Hook Chain
         │
    [conversation-recorder.py]
         │ 记录到 .conversation.jsonl
         │
    [unified-workflow-driver.py] ← 核心驱动
         │
    [快速检查]
         │ Read .task-active.json
         │ └─ task_id = "任务-1114-..."
         │
    [加载元数据]
         │ Read tasks/任务-1114-.../.task-meta.json
         │ meta = {...}
         │
    [工具分发处理]
         │ tool_name = "Write"
         │ └─ update_code_changes(meta, tool_data, cwd)
         │     ├─ meta["metrics"]["code_changes"].append({...})
         │     ├─ same_file_edits = 1
         │     └─ 同步到 workflow-state.json
         │         └─ bug_fix_tracking.loop_indicators.same_file_edit_count = 1
         │
    [检查步骤完成]
         │ check_step_completed("step3_execute", meta)
         │ └─ user_confirmed = false → 未完成
         │
    [循环检测]
         │ check_expert_trigger(meta, cwd)
         │ └─ iterations=0, negative=0, same_file=1
         │     └─ 不触发专家（条件不满足）
         │
    [保存状态]
         │ save_json(meta_path, meta)
         │
         ↓ 输出
    {"continue": true}
```

### 用户反馈数据流

```
用户输入: "还是不掉落"
         │
         ↓ iteration-tracker-hook.py (UserPromptSubmit)
         │
    [意图分类]
         │ classify_intent("还是不掉落")
         │ └─ {
         │      "task_type": "bug_fix",  # 匹配 bug_keywords
         │      "is_feedback": true,     # 匹配 feedback_keywords
         │      "sentiment": "negative", # 匹配 negative_sentiment
         │      "confidence": 0.9,
         │      "is_confirmation": false
         │    }
         │
    [更新 workflow-state.json]
         │ atomic_update_json(workflow_state_path, update_func)
         │
         │ update_func(state):
         │   ├─ state["bug_fix_tracking"]["iterations"].append({
         │   │     "iteration_id": 1,
         │   │     "timestamp": "2025-11-14T15:35:10",
         │   │     "trigger": "user_feedback",
         │   │     "user_feedback": "还是不掉落",
         │   │     "feedback_sentiment": "negative",
         │   │     "changes_made": [],
         │   │     "test_result": "pending"
         │   │  })
         │   │
         │   └─ state["bug_fix_tracking"]["loop_indicators"]["negative_feedback_count"] = 1
         │       state["bug_fix_tracking"]["loop_indicators"]["failed_test_count"] = 1
         │
    [同步到 .task-meta.json]
         │ atomic_update_json(meta_path, update_func)
         │
         │ update_func(task_meta):
         │   ├─ task_meta["workflow_state"]["steps"] = state["steps"]
         │   ├─ task_meta["workflow_state"]["bug_fix_tracking"] = state["bug_fix_tracking"]
         │   └─ task_meta["task_type"] = "bug_fix"
         │
    [记录到 .conversation.jsonl]
         │ {
         │   "timestamp": "...",
         │   "role": "user",
         │   "content": "还是不掉落",
         │   "event_type": "feedback",
         │   "sentiment": "negative",
         │   "is_confirmation": false
         │ }
         │
         ↓ 输出
    {"continue": true}
```

### 专家触发数据流

```
[循环条件达成]
  ├─ iterations_count = 2
  ├─ negative_feedback_count = 2
  └─ same_file_edit_count = 2
         │
         ↓ unified-workflow-driver.py (PostToolUse)
         │
    [循环检测]
         │ check_expert_trigger(meta, cwd)
         │
         │ workflow_state = load_json('.claude/workflow-state.json')
         │ bug_tracking = workflow_state["bug_fix_tracking"]
         │ indicators = bug_tracking["loop_indicators"]
         │
         │ if (iterations ≥ 2 and negative ≥ 2 and same_file ≥ 2):
         │   └─ return {
         │        "should_trigger": true,
         │        "loop_type": "bug_fix_loop",
         │        "confidence": 0.9,
         │        "evidence": {...}
         │      }
         │
    [启动专家分析]
         │ launch_meta_expert(expert_check, meta, cwd, logger)
         │
         │ 1. 读取完整迭代历史
         │    └─ tracking["iterations"] = [
         │         {iteration_id:1, feedback:"还是不掉落", ...},
         │         {iteration_id:2, feedback:"依然没效果", ...}
         │       ]
         │
         │ 2. 构建历史摘要
         │    └─ history_summary = "## 迭代历史\n### 迭代1\n..."
         │
         │ 3. 生成专家 Prompt
         │    └─ expert_prompt = """
         │         🎯 专家审查系统已触发
         │         **循环类型**: bug_fix_loop
         │         **证据**: iterations=2, negative=2, same_file=2
         │         {history_summary}
         │         ## 你的任务
         │         从战略高度分析问题...
         │        """
         │
    [标记专家已触发]
         │ meta["metrics"]["expert_review_triggered"] = true
         │ save_json(meta_path, meta)
         │
    [注入专家 Prompt]
         │ output = {
         │   "hookSpecificOutput": {
         │     "hookEventName": "PostToolUse",
         │     "additionalContext": expert_prompt
         │   },
         │   "continue": true
         │ }
         │
         ↓ AI 收到专家任务
    [生成诊断报告]
         │ AI 分析历史 → 输出诊断报告
         │ 包含：根因分析、备选方案、推荐策略
```

---

## 附录：文件路径速查

| 文件 | 路径 | 用途 |
|------|------|------|
| **核心驱动** | [unified-workflow-driver.py](../../../templates/.claude/hooks/unified-workflow-driver.py) | 工作流状态机核心驱动器 |
| **任务初始化** | [user-prompt-submit-hook.py](../../../templates/.claude/hooks/user-prompt-submit-hook.py) | 任务初始化/恢复、玩法包注入 |
| **迭代追踪** | [iteration-tracker-hook.py](../../../templates/.claude/hooks/iteration-tracker-hook.py) | 意图分类、情感分析、迭代追踪 |
| **收尾检查** | [enforce-cleanup.py](../../../templates/.claude/hooks/enforce-cleanup.py) | 收尾工作检查、用户确认验证 |
| **阶段强制** | [workflow-stage-enforcer.py](../../../templates/.claude/hooks/workflow-stage-enforcer.py) | 工作流阶段强制执行器 |
| **任务归档** | [post-archive-hook.py](../../../templates/.claude/hooks/post-archive-hook.py) | 任务归档与文档同步 |
| **会话恢复** | [session-start-hook.py](../../../templates/.claude/hooks/session-start-hook.py) | 会话启动时恢复任务状态 |
| **停止钩子** | [stop-hook.py](../../../templates/.claude/hooks/stop-hook.py) | 会话结束前的任务完成验证 |
| **锁文件创建** | [create-cleanup-lock.py](../../../templates/.claude/hooks/create-cleanup-lock.py) | 收尾子代理锁文件创建 |
| **锁文件清理** | [cleanup-subagent-stop.py](../../../templates/.claude/hooks/cleanup-subagent-stop.py) | 收尾子代理锁文件清理 |
| **Hook配置** | [settings.json.template](../../../templates/.claude/settings.json.template) | Hook 注册配置 |

---

**版本**: v20.2.17
**最后更新**: 2025-11-14
**维护者**: NeteaseMod-Claude 工作流团队
