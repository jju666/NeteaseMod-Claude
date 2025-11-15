# task-meta.json 文件结构说明 (v22.0)

> **版本**: v22.0.0
> **最后更新**: 2025-11-15
> **用途**: 任务持久化元数据存储（唯一数据源）

> ✅ **v22.0 PreToolUse驱动架构核心变更**:
> - **Step2改为强制研究阶段** (step2_research)，禁止任何修改操作
> - **任务统一初始化为step2_research**，包括玩法包模式
> - **新增required_doc_count字段**，动态要求文档数量（标准3，玩法包2）
> - **PreToolUse拦截机制**，文档深度不足则阻断Write/Edit
>
> ✅ **v21.0 架构核心变更**:
> - **task-meta.json 为唯一数据源**，删除 workflow-state.json
> - **简化状态管理**，减少60%数据不一致风险
> - **使用 TaskMetaManager** 统一管理（文件锁+原子更新+重试机制）
> - **向后兼容**：自动迁移v20.x任务（lib/migration-v21.js）

本文档详细说明了v21.0架构下 `.task-meta.json` 文件的完整结构和每个字段的含义。

---

## 📋 目录

1. [文件概述](#文件概述)
2. [架构变更说明](#架构变更说明)
3. [文件位置与生命周期](#文件位置与生命周期)
4. [完整结构示例](#完整结构示例)
5. [字段详细说明](#字段详细说明)
6. [数据管理机制](#数据管理机制)
7. [使用场景](#使用场景)
8. [代码位置索引](#代码位置索引)

---

## 文件概述

`.task-meta.json` 是v21.0架构中的**唯一运行时数据源**，用于存储：

- **任务基础信息**：ID、描述、类型、复杂度
- **工作流状态**：当前步骤、步骤完成情况
- **性能指标**：文档阅读、代码修改、失败记录
- **追踪数据**：Bug修复追踪、循环检测指标
- **架构版本**：v21.0标记（用于迁移识别）

**核心特点**：
- 📦 **任务级生命周期**：从任务创建到归档
- 🔄 **高频原子更新**：所有工具调用后实时更新
- 💾 **持久化存储**：跨会话保存，支持任务恢复
- 🔒 **文件锁保护**：portalocker实现并发安全
- 🔁 **自动重试机制**：3次重试，100ms延迟

---

## 架构变更说明

### v20.x → v21.0 架构演进

```
┌──────────────────────────────────────────────────────────┐
│              v20.x 架构（已废弃）                         │
├──────────────────────────────────────────────────────────┤
│  workflow-state.json (运行时主数据源)                     │
│       ↓ 同步                                             │
│  .task-meta.json (冗余副本 + workflow_state字段)         │
│       ↓ 精简同步                                         │
│  .task-active.json (活跃标记)                            │
│                                                          │
│  ❌ 问题：                                               │
│   - 数据不一致风险（workflow_state字段冗余）              │
│   - 文件I/O开销大（3个文件同步）                          │
│   - StateManager复杂度高                                 │
└──────────────────────────────────────────────────────────┘

                        ↓ 迁移

┌──────────────────────────────────────────────────────────┐
│              v21.0 架构（当前）                           │
├──────────────────────────────────────────────────────────┤
│  .task-meta.json (唯一数据源)                            │
│       ↓ 快速引用                                         │
│  .task-active.json (活跃标记指针)                        │
│                                                          │
│  ✅ 优势：                                               │
│   - 单一数据源，无数据不一致                             │
│   - 减少60%文件I/O开销                                   │
│   - TaskMetaManager统一管理（文件锁+原子更新）           │
│   - 架构版本标记：architecture_version: "v21.0"         │
└──────────────────────────────────────────────────────────┘
```

### 删除的字段（v20.x）

- ❌ `workflow_state`（顶层字段）：冗余的运行时状态副本
- ❌ `workflow_state_ref`（v20.3.x引用指针）：已废弃
- ❌ `archived_snapshot`：归档快照逻辑已简化

### 新增/变更字段（v21.0）

- ✅ `architecture_version: "21.0"`：架构版本标记
- ✅ 顶层直接包含所有运行时状态（无需嵌套）
- ✅ `current_step`、`steps`、`bug_fix_tracking` 提升到顶层

---

## 文件位置与生命周期

### 存储位置

```
项目根目录/
└── tasks/
    ├── {task_id}/                          # 活跃任务
    │   ├── .task-meta.json                 # ← 本文件（唯一数据源）
    │   ├── .conversation.jsonl             # 会话历史
    │   ├── context.md                      # 任务上下文
    │   └── solution.md                     # 解决方案
    ├── 已失败/
    │   └── {task_id}/
    │       └── .task-meta.json             # 已归档任务（archived=true,failed=true）
    └── 已取消/
        └── {task_id}/
            └── .task-meta.json             # 已取消任务（archived=true）
```

### 生命周期

```
创建 → 活跃 → 归档
  │      │      │
  │      │      └─ archived: true（移至 tasks/已失败/ 或 tasks/已归档/）
  │      │
  │      └─ 原子更新：PostToolUse Hook（每次工具调用后）
  │
  └─ /mc 命令初始化（user_prompt_handler.py）
```

---

## 完整结构示例

### 示例1：任务初始化时的结构（Bug修复任务 - v22.0）

**生成时机**: `/mc 修复玩家死亡时背包物品未掉落的BUG` 执行后立即生成

**代码位置**: `orchestrator/user_prompt_handler.py` lines 982-1027

**v22.0核心变更**:
- current_step初始化为`step2_research`（不再跳过研究阶段）
- 新增`required_doc_count`字段（玩法包2个，标准3个）

```json
{
  "task_id": "任务-1115-153022-修复玩家死亡时背包物品未掉落",
  "task_description": "修复玩家死亡时背包物品未掉落的BUG",
  "task_type": "bug_fix",
  "task_complexity": "standard",
  "created_at": "2025-11-15T15:30:22.123456",
  "updated_at": "2025-11-15T15:30:22.123456",
  "architecture_version": "v21.0",

  "current_step": "step2_research",
  "last_injection_step": null,
  "steps": {
    "step0_context": {
      "description": "阅读项目CLAUDE.md",
      "status": "skipped",
      "prompt": "（v22.0: 所有模式统一跳过step0/step1）"
    },
    "step1_understand": {
      "description": "理解任务需求",
      "status": "skipped",
      "prompt": "（v22.0: 所有模式统一跳过step0/step1）"
    },
    "step2_research": {
      "description": "任务研究阶段（强制）",
      "status": "in_progress",
      "started_at": "2025-11-15T15:30:22.123456",
      "required_doc_count": 2,
      "prompt": "查阅至少2个相关文档，理解问题根因和技术约束，明确说明研究结论后Hook自动推进到step3。"
    },
    "step3_execute": {
      "description": "执行实施",
      "status": "pending",
      "user_confirmed": false,
      "prompt": "基于充分的文档研究，实施代码修改，测试验证，直到用户确认修复完成。"
    },
    "step4_cleanup": {
      "description": "收尾归档",
      "status": "pending",
      "prompt": "清理DEBUG代码，更新文档，归档任务。"
    }
  },

  "gameplay_pack_matched": "gameplay-pack-player-death-items",
  "gameplay_pack_name": "玩法包-玩家死亡掉落物品",

  "metrics": {
    "docs_read": [],
    "code_changes": [],
    "tool_calls": [],
    "failure_count": 0,
    "expert_review_triggered": false
  },

  "session_started_at": "2025-11-15T15:30:22.123456",
  "session_ended_at": null,

  "archived": false,
  "failed": false,

  "bug_fix_tracking": {
    "enabled": true,
    "matched_gameplay_pack": "gameplay-pack-player-death-items",
    "bug_description": "修复玩家死亡时背包物品未掉落的BUG",
    "iterations": [],
    "loop_indicators": {
      "same_file_edit_count": 0,
      "failed_test_count": 0,
      "negative_feedback_count": 0,
      "time_spent_minutes": 0
    },
    "expert_triggered": false
  }
}
```

**关键说明**：
- ✅ `bug_fix_tracking` 仅 `task_type="bug_fix"` 时生成
- ✅ 玩法包模式下 step0/step1 状态为 `skipped`
- ✅ `metrics`, `session_started_at`, `failed` 等字段必须初始化（v21.1.1修复）
- ❌ 初始化时**不生成** `archived_at`, `failed_at`, `cancel_type` 等字段（运行时添加）

---

### 示例2：运行时完整结构（经过多次迭代后）

**场景**: Bug修复任务经过2次迭代，用户反馈仍失败

```json
{
  "task_id": "任务-1115-153022-修复玩家死亡时背包物品未掉落",
  "task_description": "修复玩家死亡时背包物品未掉落的BUG",
  "task_type": "bug_fix",
  "task_complexity": "standard",
  "created_at": "2025-11-15T15:30:22.123456",
  "updated_at": "2025-11-15T15:45:10.654321",
  "architecture_version": "v21.0",

  "current_step": "step3_execute",
  "last_injection_step": null,
  "steps": {
    "step0_context": {
      "description": "阅读项目CLAUDE.md",
      "status": "skipped",
      "prompt": "（玩法包模式：已跳过）"
    },
    "step1_understand": {
      "description": "理解任务需求",
      "status": "skipped",
      "prompt": "（玩法包模式：已跳过）"
    },
    "step3_execute": {
      "description": "执行实施",
      "status": "in_progress",
      "started_at": "2025-11-15T15:30:22.123456",
      "user_confirmed": false,
      "last_test_reminder_at": "2025-11-15T15:40:00",
      "last_error": "物品掉落事件未触发",
      "last_error_time": "2025-11-15T15:38:30",
      "prompt": "基于玩法包代码实现功能，测试验证，直到用户确认修复完成。"
    },
    "step4_cleanup": {
      "description": "收尾归档",
      "status": "pending",
      "prompt": "清理DEBUG代码，更新文档，归档任务。"
    }
  },

  "gameplay_pack_matched": "gameplay-pack-player-death-items",
  "gameplay_pack_name": "玩法包-玩家死亡掉落物品",

  "metrics": {
    "docs_read": [
      "markdown/systems/核心系统.md",
      "markdown/core/问题排查.md",
      "CLAUDE.md"
    ],
    "code_changes": [
      {
        "file": "behavior_packs/.../player_death.py",
        "timestamp": "2025-11-15T15:34:00.123456",
        "operation": "Edit",
        "status": "success"
      },
      {
        "file": "behavior_packs/.../player_death.py",
        "timestamp": "2025-11-15T15:40:15.789012",
        "operation": "Edit",
        "status": "success"
      }
    ],
    "tool_calls": [
      {
        "tool": "Read",
        "timestamp": "2025-11-15T15:30:30",
        "input": {"file_path": "CLAUDE.md"}
      },
      {
        "tool": "Edit",
        "timestamp": "2025-11-15T15:34:00",
        "input": {"file_path": "behavior_packs/.../player_death.py"}
      }
    ],
    "failure_count": 2,
    "expert_review_triggered": true
  },

  "session_started_at": "2025-11-15T15:30:22.123456",
  "session_ended_at": null,

  "archived": false,
  "failed": false,

  "bug_fix_tracking": {
    "enabled": true,
    "matched_gameplay_pack": "gameplay-pack-player-death-items",
    "bug_description": "修复玩家死亡时背包物品未掉落的BUG",
    "iterations": [
      {
        "iteration_id": 1,
        "timestamp": "2025-11-15T15:35:10",
        "trigger": "user_feedback",
        "user_feedback": "还是不掉落",
        "feedback_sentiment": "negative",
        "changes_made": [
          {
            "file": "behavior_packs/.../player_death.py",
            "operation": "Edit",
            "timestamp": "2025-11-15T15:34:00"
          }
        ],
        "test_result": "failed"
      },
      {
        "iteration_id": 2,
        "timestamp": "2025-11-15T15:42:00",
        "trigger": "user_feedback",
        "user_feedback": "物品还是没掉",
        "feedback_sentiment": "frustrated",
        "changes_made": [
          {
            "file": "behavior_packs/.../player_death.py",
            "operation": "Edit",
            "timestamp": "2025-11-15T15:40:15"
          }
        ],
        "test_result": "failed"
      }
    ],
    "loop_indicators": {
      "same_file_edit_count": 2,
      "failed_test_count": 2,
      "negative_feedback_count": 2,
      "time_spent_minutes": 12
    },
    "expert_triggered": true
  }
}
```

**运行时动态添加的字段**（仅在归档/失败时）:
```json
{
  "archived": true,
  "failed": true,
  "archived_at": "2025-11-15T16:00:00.123456",
  "failed_at": "2025-11-15T16:00:00.123456",
  "cancel_type": "fail",
  "failure_reason": "用户取消任务",
  "final_step": "step3_execute"
}
```

---

## 字段生成时机分类

### 初始化字段（任务创建时立即生成）

**生成时机**: `/mc` 命令执行时，`user_prompt_handler.py` 立即生成

| 字段 | 必填 | 条件生成 |
|------|------|---------|
| `architecture_version` | ✅ | 无条件 |
| `task_id` | ✅ | 无条件 |
| `task_description` | ✅ | 无条件 |
| `task_type` | ✅ | 无条件 |
| `task_complexity` | ✅ | 无条件 |
| `created_at` | ✅ | 无条件 |
| `updated_at` | ✅ | 无条件 |
| `current_step` | ✅ | 无条件 |
| `last_injection_step` | ✅ | 无条件（初始值null） |
| `steps` | ✅ | 无条件（包含description/status/prompt） |
| `gameplay_pack_matched` | ✅ | 无条件（未匹配时为null） |
| `gameplay_pack_name` | ✅ | 无条件（未匹配时为null） |
| `metrics` | ✅ | 无条件（空数组初始化） |
| `session_started_at` | ✅ | 无条件 |
| `session_ended_at` | ✅ | 无条件（初始值null） |
| `archived` | ✅ | 无条件（初始值false） |
| `failed` | ✅ | 无条件（初始值false） |
| `bug_fix_tracking` | ❌ | 仅 `task_type="bug_fix"` 时生成 |

### 运行时添加/更新字段

**生成时机**: 任务执行过程中动态添加

| 字段 | 添加时机 | Hook文件 |
|------|---------|---------|
| `steps.*.started_at` | 步骤开始时 | `orchestrator/user_prompt_handler.py` |
| `steps.*.completed_at` | 步骤完成时 | `orchestrator/user_prompt_handler.py` |
| `archived_at` | 任务归档时 | `archiver/post_archive.py` |
| `failed_at` | 任务失败时 | `orchestrator/task_cancellation_handler.py` |
| `cancel_type` | 任务取消/失败时 | `orchestrator/task_cancellation_handler.py` |
| `failure_reason` | 任务取消/失败时 | `orchestrator/task_cancellation_handler.py` |
| `final_step` | 任务取消/失败时 | `orchestrator/task_cancellation_handler.py` |

---

## 字段详细说明

### 1. 架构标识

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `architecture_version` | string | ✅ | 架构版本标记<br>**固定值**: `"v21.0"`<br>用于迁移识别和兼容性检查 |

### 2. 基础元数据

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task_id` | string | ✅ | 任务唯一标识符<br>格式：`任务-MMDD-HHMMSS-{描述}`<br>例如：`任务-1114-153022-修复玩家死亡时背包物品未掉落` |
| `task_description` | string | ✅ | 任务描述文本，来自用户输入 |
| `task_type` | enum | ✅ | 任务类型：<br>- `bug_fix`：Bug修复（启用bug_fix_tracking）<br>- `general`：通用任务<br>**自动检测**: 描述包含"修复"/"BUG"/"报错"等关键词时为bug_fix |
| `task_complexity` | string | ❌ | 任务复杂度（预留字段）<br>默认：`standard` |
| `created_at` | ISO 8601 | ✅ | 任务创建时间<br>格式：`YYYY-MM-DDTHH:MM:SS.ffffff` |
| `updated_at` | ISO 8601 | ✅ | 最后更新时间<br>**v21.0**: 原子更新时自动设置 |

### 3. 工作流状态（顶层字段）

| 字段 | 类型 | 说明 |
|------|------|------|
| `current_step` | enum | 当前工作流步骤：<br>- `step0_context`：理解项目上下文<br>- `step1_understand`：理解任务需求<br>- **`step2_research`**：**任务研究阶段（v22.0新增）**<br>- `step3_execute`：执行实施<br>- `step4_cleanup`：收尾归档<br>**v22.0**: 任务统一初始化为`step2_research` |
| `last_injection_step` | string \| null | 最后一次注入提示的步骤<br>防止重复注入 |
| `steps` | object | 步骤状态字典（见下表） |

#### 3.1 steps（步骤状态）

每个步骤的**通用字段**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `description` | string | ✅ | 步骤描述（中文）<br>用于UI展示和日志输出<br>例如："阅读项目CLAUDE.md"、"执行实施" |
| `status` | enum | ✅ | 步骤状态：<br>- `pending`：待执行<br>- `in_progress`：执行中<br>- `completed`：已完成<br>- `skipped`：已跳过（玩法包模式） |
| `prompt` | string | ✅ | 步骤提示文本<br>注入给AI的指导内容<br>玩法包模式下为"（玩法包模式：已跳过）" |
| `started_at` | ISO 8601 | ❌ | 步骤开始时间<br>仅 `in_progress` / `completed` 状态有值 |
| `completed_at` | ISO 8601 | ❌ | 步骤完成时间<br>仅 `completed` 状态有值 |

**示例**：
```json
"step0_context": {
  "description": "阅读项目CLAUDE.md",
  "status": "skipped",
  "prompt": "（玩法包模式：已跳过）"
},
"step3_execute": {
  "description": "执行实施",
  "status": "in_progress",
  "started_at": "2025-11-14T15:32:10.123456",
  "user_confirmed": false,
  "prompt": "基于玩法包代码实现功能，测试验证，直到用户确认修复完成。"
}
```

**step3_execute 特有字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_confirmed` | boolean | 用户是否确认修复完成<br>触发方式：用户输入 "已修复" / "修复完成" / `/mc-confirm` |
| `last_test_reminder_at` | ISO 8601 \| null | 上次测试提醒时间<br>用于控制提醒频率 |
| `last_error` | string \| null | 最后一次错误信息 |
| `last_error_time` | ISO 8601 \| null | 最后一次错误时间 |

**step2_research 特有字段** (v22.0):

| 字段 | 类型 | 说明 |
|------|------|------|
| `required_doc_count` | number | 要求查阅的最少文档数<br>**标准模式**: 3<br>**玩法包模式**: 2<br>用于PreToolUse文档深度检查，文档数不足会阻断Write/Edit操作 |

**示例**：
```json
"step2_research": {
  "description": "任务研究阶段（强制）",
  "status": "in_progress",
  "started_at": "2025-11-15T15:30:22.123456",
  "required_doc_count": 2,
  "prompt": "查阅至少2个相关文档，理解问题根因和技术约束，明确说明研究结论后Hook自动推进到step3。"
}
```

### 4. Bug修复追踪

**生成条件**: 仅当 `task_type = "bug_fix"` 时，在**任务初始化阶段**立即生成此字段。

**代码位置**: `orchestrator/user_prompt_handler.py` lines 1043-1056

**判断逻辑**: 检测任务描述包含 "修复"/"BUG"/"bug"/"报错"/"异常"/"错误" 等关键词

| 字段 | 类型 | 说明 |
|------|------|------|
| `enabled` | boolean | 是否启用追踪 |
| `bug_description` | string | Bug 描述 |
| `iterations` | array | 迭代历史数组（见下表） |
| `loop_indicators` | object | 循环检测指标（见下表） |
| `expert_triggered` | boolean | 是否已触发专家审查 |

**iterations 数组元素结构**：

```json
{
  "iteration_id": 1,                    // 迭代序号
  "timestamp": "2025-11-14T15:35:10",   // 时间戳
  "trigger": "user_feedback",           // 触发来源：user_feedback | tool_error
  "user_feedback": "还是不掉落",         // 用户反馈内容
  "feedback_sentiment": "negative",     // 情感：positive | negative | frustrated | neutral
  "changes_made": [                     // 本次迭代的代码修改
    {
      "file": "...",
      "operation": "Edit",
      "timestamp": "..."
    }
  ],
  "test_result": "failed"              // 测试结果：pending | passed | failed
}
```

**loop_indicators（循环指标）**：

| 字段 | 类型 | 说明 | 触发专家阈值 |
|------|------|------|-------------|
| `same_file_edit_count` | number | 同文件编辑次数 | ≥ 2 |
| `failed_test_count` | number | 测试失败次数 | ≥ 2 |
| `negative_feedback_count` | number | 负面反馈次数 | ≥ 2 |
| `time_spent_minutes` | number | 耗时（分钟） | - |

**专家触发条件**（同时满足）：
1. `iterations.length ≥ 2`
2. `negative_feedback_count ≥ 2`
3. `same_file_edit_count ≥ 2`

### 5. 性能指标

| 字段 | 类型 | 说明 |
|------|------|------|
| `metrics.docs_read` | array | 已读文档路径列表 |
| `metrics.code_changes` | array | 代码修改记录（见下表） |
| `metrics.tool_calls` | array | 工具调用记录 |
| `metrics.failure_count` | number | 失败总次数 |
| `metrics.expert_review_triggered` | boolean | 是否触发过专家审查 |

**code_changes 数组元素结构**：

```json
{
  "file": "behavior_packs/.../player_death.py",  // 文件路径
  "timestamp": "2025-11-14T15:34:00.123456",     // 修改时间
  "operation": "Edit",                           // 操作类型：Edit | Write
  "status": "success"                            // 执行状态：success | failed
}
```

### 6. 玩法包追踪

| 字段 | 类型 | 说明 |
|------|------|------|
| `gameplay_pack_matched` | string \| null | 匹配到的玩法包ID<br>**v19.0**: 知识库匹配功能<br>`null` 表示未匹配 |
| `gameplay_pack_name` | string \| null | 匹配到的玩法包名称<br>例如：`"玩法包-玩家死亡掉落物品"` |

**使用场景**：
- 任务初始化时根据关键词匹配知识库（.claude/knowledge-base.json）
- BUG修复任务优先匹配相关玩法包，提供精准代码实现
- 未匹配时使用通用指南

### 7. 归档状态

#### 7.1 初始化字段（任务创建时生成）

| 字段 | 类型 | 说明 |
|------|------|------|
| `archived` | boolean | 是否已归档<br>**初始值**: `false`<br>`true`：已移至 `tasks/已归档/` 或 `tasks/已失败/` |
| `failed` | boolean | 是否失败任务<br>**初始值**: `false`<br>`true`：归档到 `tasks/已失败/` |

#### 7.2 运行时添加字段（归档/取消/失败时动态生成）

**代码位置**: `archiver/post_archive.py`, `orchestrator/task_cancellation_handler.py`

| 字段 | 类型 | 添加时机 | 说明 |
|------|------|---------|------|
| `archived_at` | ISO 8601 | 任务归档时 | 归档时间戳<br>**v21.0**: SessionEnd Hook或手动归档时设置 |
| `failed_at` | ISO 8601 | 任务失败时 | 失败时间戳<br>仅 `failed=true` 时存在 |
| `cancel_type` | enum | 任务取消/失败时 | 取消类型：<br>- `"cancel"`: 用户主动取消<br>- `"fail"`: 任务失败 |
| `failure_reason` | string | 任务取消/失败时 | 失败原因描述<br>例如："用户取消任务"、"超时未响应" |
| `final_step` | string | 任务取消/失败时 | 任务终止时所在步骤<br>例如："step3_execute" |

### 8. 会话管理

| 字段 | 类型 | 说明 |
|------|------|------|
| `session_started_at` | ISO 8601 | 最后会话启动时间<br>**v21.0**: SessionStart Hook更新 |
| `session_ended_at` | ISO 8601 \| null | 最后会话结束时间<br>**v21.0**: SessionEnd Hook更新 |

---

## 数据管理机制

### v21.0+ 单一数据源架构 (v22.0 继承)

```
┌─────────────────────────────────────────────────────────┐
│              TaskMetaManager 统一管理                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  .task-meta.json (唯一运行时数据源)                      │
│  ├─ 更新频率: 高（每次工具调用后）                       │
│  ├─ 生命周期: 任务级                                    │
│  ├─ 存储位置: tasks/{task_id}/.task-meta.json          │
│  ├─ 并发保护: portalocker 文件锁                        │
│  ├─ 原子更新: atomic_update() API                       │
│  └─ 自动重试: 3次，100ms延迟                            │
│         │                                               │
│         │ 快速引用                                      │
│         ↓                                               │
│  .task-active.json (活跃任务指针)                       │
│  ├─ 更新频率: 低（任务初始化、切换时）                   │
│  ├─ 生命周期: 会话级                                    │
│  ├─ 存储位置: .claude/.task-active.json                │
│  └─ 包含字段:                                           │
│      - task_id (指向唯一活跃任务)                        │
│      - updated_at                                       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### TaskMetaManager 核心API

```python
# 初始化
mgr = TaskMetaManager(cwd)

# 获取活跃任务ID
task_id = mgr.get_active_task_id()

# 加载任务元数据
task_meta = mgr.load_task_meta(task_id)

# 原子更新（文件锁 + 重试）
def update_func(meta: Dict) -> Dict:
    meta['current_step'] = 'step3_execute'
    meta['updated_at'] = datetime.now().isoformat()
    return meta

updated_meta = mgr.atomic_update(task_id, update_func)

# 保存任务元数据
mgr.save_task_meta(task_id, task_meta)

# 清除活跃任务
mgr.clear_active_task()
```

### 更新时机

| 触发事件 | .task-meta.json | .task-active.json | Hook |
|----------|-----------------|-------------------|------|
| `/mc` 命令初始化 | ✅ 创建 | ✅ 创建 | `user_prompt_handler.py` |
| SessionStart | ✅ 更新会话时间 | - | `lifecycle/session_start.py` |
| UserPromptSubmit（反馈） | ✅ 原子更新迭代追踪 | - | `orchestrator/user_prompt_handler.py` |
| PostToolUse（工具调用） | ✅ 原子更新 metrics | - | `orchestrator/posttooluse_updater.py` |
| 步骤推进 | ✅ 原子更新 current_step | ✅ 更新 | `orchestrator/user_prompt_handler.py` |
| 任务归档 | ✅ 标记 archived=true | ✅ 清除 | `archiver/post_archive.py` |
| 任务取消/失败 | ✅ 标记 failed=true | ✅ 清除 | `orchestrator/task_cancellation_handler.py` |
| SessionEnd | ✅ 更新会话结束时间 | - | `lifecycle/session_end.py` |

---

## 使用场景

### 1. 任务初始化

```python
# orchestrator/user_prompt_handler.py (v22.0)
def initialize_new_task(task_id, description, task_type, is_gameplay_pack=False):
    mgr = TaskMetaManager(cwd)

    # v22.0: 统一初始化为step2_research
    task_meta = {
        "architecture_version": "v22.0",
        "task_id": task_id,
        "task_description": description,
        "task_type": task_type,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "current_step": "step2_research",
        "steps": {
            "step0_context": {"status": "skipped"},
            "step1_understand": {"status": "skipped"},
            "step2_research": {
                "status": "in_progress",
                "description": "任务研究阶段（强制）",
                "started_at": datetime.now().isoformat(),
                "required_doc_count": 2 if is_gameplay_pack else 3,
                "prompt": f"查阅至少{2 if is_gameplay_pack else 3}个相关文档，理解问题根因和技术约束，明确说明研究结论后Hook自动推进到step3。"
            },
            "step3_execute": {"status": "pending"},
            "step4_cleanup": {"status": "pending"}
        },
        "metrics": {
            "docs_read": [],
            "code_changes": [],
            "tool_calls": [],
            "failure_count": 0
        },
        "archived": False,
        "failed": False
    }

    mgr.save_task_meta(task_id, task_meta)
    mgr.set_active_task(task_id)
```

### 2. 任务恢复

```python
# lifecycle/session_start.py
def resume_task_on_session_start(cwd):
    mgr = TaskMetaManager(cwd)
    task_id = mgr.get_active_task_id()

    if not task_id:
        return  # 无活跃任务

    task_meta = mgr.load_task_meta(task_id)

    # 更新会话启动时间
    task_meta['session_started_at'] = datetime.now().isoformat()
    mgr.save_task_meta(task_id, task_meta)

    # 生成恢复上下文提示
    current_step = task_meta.get('current_step', 'unknown')
    iterations = task_meta.get('bug_fix_tracking', {}).get('iterations', [])
    ...
```

### 3. 原子更新（并发安全）

```python
# orchestrator/posttooluse_updater.py
def update_metrics_after_tool_call(task_id, tool_name, tool_input, is_error):
    mgr = TaskMetaManager(cwd)

    def update_func(task_meta: Dict) -> Dict:
        # 更新工具调用记录
        task_meta.setdefault('metrics', {}).setdefault('tool_calls', []).append({
            "tool": tool_name,
            "timestamp": datetime.now().isoformat(),
            "input": tool_input,
            "error": is_error
        })

        # 更新代码修改记录
        if tool_name in ["Edit", "Write"]:
            task_meta['metrics'].setdefault('code_changes', []).append({
                "file": tool_input.get('file_path'),
                "timestamp": datetime.now().isoformat(),
                "operation": tool_name,
                "status": "failed" if is_error else "success"
            })

        # 检测循环并触发专家
        if detect_loop_indicators(task_meta):
            task_meta['bug_fix_tracking']['expert_triggered'] = True

        return task_meta

    # 原子更新（文件锁 + 重试）
    mgr.atomic_update(task_id, update_func)
```

### 4. 任务归档

```python
# archiver/post_archive.py
def archive_task(task_id):
    mgr = TaskMetaManager(cwd)

    def mark_archived(meta: Dict) -> Dict:
        meta['archived'] = True
        meta['archived_at'] = datetime.now().isoformat()
        return meta

    updated = mgr.atomic_update(task_id, mark_archived)

    if updated:
        mgr.clear_active_task()
```

---

## 代码位置索引

| 功能 | 文件路径 (v21.0) | 关键方法 |
|------|------------------|----------|
| **初始化** | `orchestrator/user_prompt_handler.py` | `initialize_new_task()` |
| **原子更新** | `core/task_meta_manager.py` | `atomic_update()` |
| **并发保护** | `core/task_meta_manager.py` | `_acquire_lock()`, `_release_lock()` |
| **迭代追踪** | `orchestrator/user_prompt_handler.py` | `handle_bug_fix_iteration()` |
| **代码修改记录** | `orchestrator/posttooluse_updater.py` | `update_metrics()` |
| **循环检测** | `core/expert_trigger.py` | `detect_loop_indicators()` |
| **任务恢复** | `lifecycle/session_start.py` | `resume_task()` |
| **任务归档** | `archiver/post_archive.py` | `mark_archived()` |
| **任务取消** | `orchestrator/task_cancellation_handler.py` | `cancel_or_fail_task()` |
| **步骤验证** | `core/stage_validator.py` | `validate()` |

---

## 迁移指南

### 从 v20.x 迁移到 v21.0

**自动迁移**：
```bash
# 执行 initmc 自动触发迁移
cd your-modsdk-project
initmc
```

**手动迁移**：
```javascript
// lib/migration-v21.js
const { MigrationV21 } = require('./migration-v21');

const migration = new MigrationV21(upstreamPath, downstreamPath);
if (migration.needsMigration()) {
  await migration.migrate({ autoConfirm: true });
}
```

**迁移内容**：
1. ✅ 删除 `workflow-state.json`
2. ✅ 删除 `workflow_state`、`workflow_state_ref` 字段
3. ✅ 删除 `archived_snapshot` 字段
4. ✅ 提升运行时状态到顶层（`current_step`, `steps`, `bug_fix_tracking`）
5. ✅ 添加 `architecture_version: "v21.0"`

---

## 相关文档

- [Hook状态机机制](./Hook状态机机制.md) - 完整工作流状态机运作机制
- [数据流设计](./数据流设计.md) - 工作流执行流程
- [v21.0重构实施指南](./v21.0重构实施指南.md) - 架构重构详细说明

---

**版本**: v22.0.0
**最后更新**: 2025-11-15
**维护者**: NeteaseMod-Claude 工作流团队
