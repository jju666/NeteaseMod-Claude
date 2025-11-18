# Hooks 状态机系统 - 实现分析

> **基于代码逆向分析生成** | 版本: v3.0 Final | 分析时间: 2025-11-18
> **代码路径**: `templates/.claude/hooks` | **文件数**: 25 个 Python 文件 | **代码行数**: ~9,111 行

---

## 🗺️ 快速导航

[概览](#概览) | [架构](#架构) | [数据结构](#数据结构) | [执行流程](#执行流程) | [API索引](#api索引) | [运维](#运维)

---

## 📋 概览 (3分钟速读)

### 核心功能
基于 Claude Code Hooks 机制的 **AI 工作流强制执行系统**，通过拦截 AI 的工具调用（Read/Write/Edit/Bash）实施严格的四阶段开发流程控制（Activation → Planning → Implementation → Finalization）。

### 架构总览
```mermaid
graph TB
    subgraph "入口层 (Orchestrator)"
        UPH[UserPromptSubmit<br/>用户输入处理]
        PTU[PreToolUse<br/>工具调用拦截]
        POTU[PostToolUse<br/>状态更新]
    end

    subgraph "核心引擎 (Core)"
        TMM[TaskMetaManager<br/>任务元数据管理器]
        SV[StageValidator<br/>四层验证引擎]
        TM[ToolMatrix<br/>工具矩阵配置]
        SA[SemanticAnalyzer<br/>语义分析器]
        PV[PathValidator<br/>路径验证器]
        ET[ExpertTrigger<br/>专家审查触发器]
    end

    subgraph "生命周期 (Lifecycle)"
        SS[SessionStart<br/>会话启动]
        SE[SessionEnd<br/>会话结束]
        SUBS[SubagentStop<br/>子代理停止]
    end

    subgraph "数据层"
        META[.task-meta.json<br/>任务完整状态]
        ACTIVE[.task-active.json<br/>会话绑定]
    end

    UPH --> TMM
    PTU --> SV
    SV --> TM
    SV --> SA
    SV --> PV
    SA --> PV
    POTU --> TMM
    POTU --> ET
    SS --> TMM
    SUBS --> TMM

    TMM --> META
    TMM --> ACTIVE

    style TMM fill:#90caf9
    style SV fill:#81c784
    style META fill:#ffcc80
```

### 关键指标
| 指标 | 值 | 说明 |
|------|---|------|
| 模块数 | 5 个 | core(6), orchestrator(4), lifecycle(5), utils(3), validators(2), archiver(2) |
| 核心文件 | 3 个 | task_meta_manager.py, stage_validator.py, tool_matrix.py |
| 主要语言 | Python | 100% Python 3.7+ |
| 设计模式 | 状态机 + 责任链 + 策略 | 四阶段状态机 + 四层验证责任链 + 工具矩阵策略 |
| 数据源 | 单一真相源 | task-meta.json 作为唯一数据源 (v3.0 架构) |

---

## 🏗️ 架构详解

### 目录结构
```
templates/.claude/hooks/
├── core/                      # 核心引擎（6个文件）
│   ├── task_meta_manager.py   # 任务元数据管理器（原子更新）
│   ├── stage_validator.py     # 四层验证引擎
│   ├── tool_matrix.py          # 工具矩阵配置（4阶段 x 工具规则）
│   ├── semantic_analyzer.py    # 语义分析器
│   ├── path_validator.py       # 路径验证器（白名单/黑名单）
│   ├── expert_trigger.py       # 专家审查触发器（循环检测）
│   └── __init__.py
├── orchestrator/              # Hooks 编排器（4个文件）
│   ├── user_prompt_handler.py         # UserPromptSubmit Hook（/mc命令、状态转移）
│   ├── pretooluse_enforcer.py         # PreToolUse Hook（工具调用拦截）
│   ├── posttooluse_updater.py         # PostToolUse Hook（度量记录、循环检测）
│   ├── task_cancellation_handler.py   # 任务取消处理
│   └── __init__.py
├── lifecycle/                 # 生命周期管理（5个文件）
│   ├── session_start.py       # SessionStart Hook（状态仪表盘）
│   ├── session_end.py         # SessionEnd Hook（会话结束清理）
│   ├── subagent_stop.py       # SubagentStop Hook（专家审查结果提取）
│   ├── stop.py                # Stop Hook（通知发送）
│   ├── pre_compact.py         # PreCompact Hook（压缩前提醒）
│   └── __init__.py
├── utils/                     # 工具库（3个文件）
│   ├── notify.py              # 桌面通知（跨平台）
│   ├── config_loader.py       # 配置加载器
│   └── __init__.py
├── validators/                # 验证器（2个文件）
│   ├── pre_compact_reminder.py  # 压缩提醒验证器
│   └── __init__.py
└── archiver/                  # 归档器（2个文件）
    ├── post_archive.py        # 归档后处理
    └── __init__.py
```

### 模块职责表
| 模块 | 关键文件 | 职责 | 关键函数 | 依赖关系 |
|------|---------|------|---------|---------|
| **Core** | [task_meta_manager.py](../templates/.claude/hooks/core/task_meta_manager.py) | 任务元数据管理，原子更新，文件锁 | `atomic_update()`, `load_task_meta()`, `get_active_task_by_session()` | portalocker（文件锁） |
| **Core** | [stage_validator.py](../templates/.claude/hooks/core/stage_validator.py) | 四层验证引擎，整合工具-路径-语义验证 | `validate()`, `_validate_tool_allowed()` | tool_matrix, path_validator, semantic_analyzer |
| **Core** | [tool_matrix.py](../templates/.claude/hooks/core/tool_matrix.py) | 工具矩阵配置（4阶段规则） | `get_stage_config()`, `get_allowed_tools()` | 无（纯配置） |
| **Core** | [semantic_analyzer.py](../templates/.claude/hooks/core/semantic_analyzer.py) | 语义分析（危险命令检测、代码修改前置条件） | `analyze()`, `_analyze_write()`, `_analyze_bash()` | path_validator |
| **Core** | [path_validator.py](../templates/.claude/hooks/core/path_validator.py) | 路径验证（白名单/黑名单/glob 匹配） | `validate()`, `_match_glob()` | 无 |
| **Core** | [expert_trigger.py](../templates/.claude/hooks/core/expert_trigger.py) | 专家审查触发器（循环检测逻辑） | `should_trigger()`, `_detect_bug_fix_loop()` | 无 |
| **Orchestrator** | [user_prompt_handler.py](../templates/.claude/hooks/orchestrator/user_prompt_handler.py) | 用户输入处理（/mc 命令、状态转移关键词检测） | `main()`, `_handle_mc_command()`, `_detect_state_transition()` | task_meta_manager |
| **Orchestrator** | [pretooluse_enforcer.py](../templates/.claude/hooks/orchestrator/pretooluse_enforcer.py) | 工具调用拦截（四层验证执行） | `main()`, `allow_and_exit()`, `deny_and_exit()` | stage_validator, task_meta_manager |
| **Orchestrator** | [posttooluse_updater.py](../templates/.claude/hooks/orchestrator/posttooluse_updater.py) | 工具调用后更新（度量记录、循环检测） | `main()`, `update_metrics()` | task_meta_manager, expert_trigger |
| **Lifecycle** | [session_start.py](../templates/.claude/hooks/lifecycle/session_start.py) | 会话启动（状态仪表盘显示） | `main()`, `generate_status_dashboard()` | task_meta_manager |
| **Lifecycle** | [subagent_stop.py](../templates/.claude/hooks/lifecycle/subagent_stop.py) | 子代理停止（专家审查结果提取） | `main()`, `extract_subagent_result()` | task_meta_manager |

### 模块依赖图
```mermaid
graph TB
    TMM[task_meta_manager.py<br/>任务元数据管理]
    TM[tool_matrix.py<br/>工具矩阵配置]
    PV[path_validator.py<br/>路径验证器]
    SA[semantic_analyzer.py<br/>语义分析器]
    SV[stage_validator.py<br/>四层验证引擎]
    ET[expert_trigger.py<br/>专家触发器]

    UPH[user_prompt_handler.py<br/>用户输入处理]
    PTU[pretooluse_enforcer.py<br/>工具拦截]
    POTU[posttooluse_updater.py<br/>状态更新]

    SS[session_start.py<br/>会话启动]
    SUBS[subagent_stop.py<br/>子代理停止]

    SA --> PV
    SV --> TM
    SV --> PV
    SV --> SA
    SV --> TMM

    PTU --> SV
    PTU --> TMM
    UPH --> TMM
    POTU --> TMM
    POTU --> ET
    SS --> TMM
    SUBS --> TMM

    style TMM fill:#ffeb3b
    style SV fill:#4caf50
    style TM fill:#2196f3
```

---

## 📊 数据结构速查

### 核心数据对象

```typescript
// task-meta.json - 任务完整状态（唯一数据源）
interface TaskMeta {
  // 基础信息
  task_id: string                    // 任务ID（格式：任务-MMDD-HHMMSS-描述）
  task_type: "bug_fix" | "feature_implementation" | "general"
  task_description: string
  current_step: "activation" | "planning" | "implementation" | "finalization"

  // 玩法包匹配
  gameplay_pack_matched?: {
    name: string                     // 玩法包名称（如"房间系统"）
    keywords: string[]               // 匹配关键词
    implementation_guide: object     // 实现指南（代码片段）
  }

  // 阶段状态
  steps: {
    activation: StepState
    planning: PlanningStepState
    implementation: ImplementationStepState
    finalization: FinalizationStepState
  }

  // 度量数据
  metrics: {
    tools_used: ToolUsageRecord[]    // 所有工具调用记录
    docs_read: DocRecord[]           // 阅读的文档
    code_changes: CodeChangeRecord[] // 代码修改记录
  }

  // BUG 修复追踪
  bug_fix_tracking?: {
    enabled: boolean
    iterations: IterationRecord[]    // 迭代历史
    loop_indicators: {
      same_file_edit_count: number   // 同文件修改次数
      failed_test_count: number
      negative_feedback_count: number
    }
  }

  // 专家审查
  expert_triggered: boolean          // 是否已触发专家审查
  expert_review?: {
    prompt: string
    triggered_at: string
  }

  // 状态转移历史
  state_transitions: TransitionRecord[]

  // 元数据
  session_started_at: string
  updated_at: string
  architecture_version: "v3.0 Final"
}

// .task-active.json - 会话绑定映射（v3.1多会话支持）
interface TaskActive {
  version: "v3.1"
  active_tasks: {
    [session_id: string]: {
      task_id: string
      task_dir: string               // tasks/{task_id}
      current_step: string
      bound_at: string
      session_history: string[]      // 会话历史（支持压缩恢复）
    }
  }
}

// 工具矩阵配置（tool_matrix.py）
interface StageConfig {
  display_name: string               // 显示名称
  description: string
  allowed_tools: string[]            // 工具白名单
  preconditions: string[]            // 前置条件
  path_rules: {
    [tool_name: string]: {
      whitelist_patterns?: string[]
      blacklist?: string[]
      allowed_commands_patterns?: RegExp[]  // Bash 命令白名单
      forbidden_commands_patterns?: RegExp[]
    }
  }
  semantic_rules: {
    [tool_name: string]: {
      purpose?: string
      min_reads?: number             // Planning 阶段最少文档数
      requires_read_first?: boolean  // Write/Edit 前必须 Read
      max_same_file_edits?: number   // 同文件最大修改次数
      forbidden?: boolean
      reason?: string
    }
  }
  subagent_rules?: {                 // Finalization 子代理规则
    allowed_tools: string[]
    path_rules: object
  }
}
```

### 配置项速查
| 配置键 | 位置 | 类型 | 默认值 | 说明 |
|--------|------|------|--------|------|
| `STAGE_TOOL_MATRIX` | [tool_matrix.py:8](../templates/.claude/hooks/core/tool_matrix.py#L8) | Dict[str, StageConfig] | 见文件 | 四阶段工具矩阵配置 |
| `STEP_ORDER` | [tool_matrix.py:354](../templates/.claude/hooks/core/tool_matrix.py#L354) | List[str] | `["activation", "planning", ...]` | 阶段顺序 |
| `MAX_RETRIES` | [task_meta_manager.py:39](../templates/.claude/hooks/core/task_meta_manager.py#L39) | int | 3 | 原子更新最大重试次数 |
| `RETRY_DELAY` | [task_meta_manager.py:40](../templates/.claude/hooks/core/task_meta_manager.py#L40) | float | 0.1 | 重试延迟（秒） |

### 数据流向表
| 数据源 | 数据目标 | 触发条件 | 数据格式 | Hook |
|--------|---------|---------|---------|------|
| 用户输入 `/mc` | `.task-meta.json` | UserPromptSubmit 检测到 `/mc` | JSON（初始化任务） | user_prompt_handler.py |
| 工具调用 | `.task-meta.json`.metrics | PostToolUse 工具执行成功 | JSON（追加记录） | posttooluse_updater.py |
| 用户确认关键词 | `.task-meta.json`.current_step | UserPromptSubmit 检测到"同意"/"研究完成" | JSON（状态转移） | user_prompt_handler.py |
| 子代理 transcript | `.task-meta.json`.expert_review_result | SubagentStop 解析 SUBAGENT_RESULT 标记 | JSON（审查结果） | subagent_stop.py |
| session_id | `.task-active.json` | UserPromptSubmit 绑定任务到会话 | JSON（会话映射） | user_prompt_handler.py |

---

## 🔄 执行流程

### 主流程图（完整任务生命周期）
```mermaid
stateDiagram-v2
    [*] --> UserInput: 用户输入 /mc 修复xxx

    UserInput --> UPH: UserPromptSubmit Hook
    UPH --> CreateTask: 创建任务目录
    CreateTask --> InitMeta: 初始化 task-meta.json
    InitMeta --> BindSession: 绑定到 session_id
    BindSession --> Activation: current_step = activation

    Activation --> Planning: 自动转移

    state Planning {
        [*] --> PlanningRead: AI 尝试 Read 文档
        PlanningRead --> PreToolUse1: PreToolUse 验证
        PreToolUse1 --> AllowRead: 允许 Read
        AllowRead --> PostToolUse1: PostToolUse 记录 docs_read
        PostToolUse1 --> PlanningRead: docs_read < min_reads
        PostToolUse1 --> AISaysReady: docs_read >= min_reads
        AISaysReady --> [*]: AI 说"研究完成"
    }

    Planning --> UPH2: UserPromptSubmit 检测关键词
    UPH2 --> Implementation: current_step = implementation

    state Implementation {
        [*] --> ImplEdit: AI 尝试 Edit 代码
        ImplEdit --> PreToolUse2: PreToolUse 验证
        PreToolUse2 --> CheckDocs: 检查 docs_read 数量
        CheckDocs --> DenyEdit: 不足，DENY
        DenyEdit --> ImplEdit
        CheckDocs --> AllowEdit: 足够，允许
        AllowEdit --> PostToolUse2: PostToolUse 更新 code_changes
        PostToolUse2 --> LoopCheck: 循环检测
        LoopCheck --> TriggerExpert: iterations>=2 AND negative>=2
        LoopCheck --> AskUser: 未触发
        TriggerExpert --> LaunchExpert: AI 启动 Task 子代理
        LaunchExpert --> SubagentStop: SubagentStop 解析结果
        SubagentStop --> AskUser: 显示审查结果
        AskUser --> UserNegative: 用户说"没修复"
        UserNegative --> ImplEdit: negative_feedback++
        AskUser --> UserPositive: 用户说"修复了"
        UserPositive --> [*]
    }

    Implementation --> UPH3: UserPromptSubmit 检测"同意"
    UPH3 --> Finalization: current_step = finalization

    state Finalization {
        [*] --> SessionStartMsg: SessionStart 提示必须启动子代理
        SessionStartMsg --> AITryTools: AI 尝试 Read/Grep
        AITryTools --> PreToolUse3: PreToolUse 计数
        PreToolUse3 --> AllowAnalysis: non_task_count < 5
        AllowAnalysis --> AITryTools
        PreToolUse3 --> ForceDeny: non_task_count >= 5
        ForceDeny --> LaunchCleanup: AI 被迫启动 Task
        AllowAnalysis --> LaunchCleanup: AI 主动启动
        LaunchCleanup --> CreateLock: 创建 .cleanup-subagent.lock
        CreateLock --> SubagentWork: 子代理生成文档
        SubagentWork --> UpdateStatus: 更新 finalization.status = completed
        UpdateStatus --> RemoveLock: 删除锁文件
        RemoveLock --> [*]
    }

    Finalization --> Archive: archived = true
    Archive --> [*]
```

### 关键路径表
| 场景 | 入口函数 | 执行步骤 | 输出结果 |
|------|---------|---------|---------|
| **用户输入 /mc** | `user_prompt_handler.main()` | 1. 检测 `/mc` 命令<br>2. 创建任务目录<br>3. 初始化 task-meta.json<br>4. 玩法包匹配<br>5. 绑定 session_id<br>6. DENY + 注入系统 Prompt | `.task-meta.json` 创建，`.task-active.json` 更新 |
| **工具调用拦截** | `pretooluse_enforcer.main()` | 1. 读取 stdin 获取工具信息<br>2. 查询 active task<br>3. 四层验证<br>4. 决策（allow/deny） | exit 0（允许）或 exit 2（拒绝） |
| **状态转移** | `user_prompt_handler._detect_state_transition()` | 1. 关键词匹配（"同意"/"研究完成"）<br>2. 前置条件检查<br>3. 保存快照（_snapshot_step_state）<br>4. 更新 current_step | task-meta.json 状态转移 |
| **专家审查触发** | `expert_trigger.should_trigger()` | 1. 检查 expert_triggered 标志<br>2. 循环检测（iterations/negative/same_file）<br>3. 返回 boolean | PostToolUse 设置 expert_triggered=true |
| **子代理结果提取** | `subagent_stop.extract_subagent_result()` | 1. 读取 transcript.jsonl<br>2. 反向遍历消息<br>3. 正则提取 `<!-- SUBAGENT_RESULT {...} -->`<br>4. JSON 解析 | expert_review_result 对象 |

### 四层验证流程（PreToolUse Hook）
```mermaid
sequenceDiagram
    participant AI as Claude AI
    participant PTU as PreToolUse Hook
    participant SV as StageValidator
    participant TM as ToolMatrix
    participant SA as SemanticAnalyzer
    participant PV as PathValidator

    AI->>PTU: 工具调用 (tool_name, tool_input)
    PTU->>PTU: 查询 active task (session_id)
    PTU->>SV: validate(current_step, tool_name, tool_input, task_meta)

    Note over SV: Layer 1: 工具类型白名单
    SV->>TM: get_allowed_tools(current_step)
    TM-->>SV: ['Read', 'Grep', ...]
    SV->>SV: tool_name in allowed_tools?

    alt 工具不在白名单
        SV-->>PTU: {"allowed": false, "reason": "工具不在白名单"}
        PTU-->>AI: exit 2 (DENY)
    end

    Note over SV: Layer 2: 前置条件检查
    SV->>SV: 检查 planning_completed / user_confirmed

    alt 前置条件不满足
        SV-->>PTU: {"allowed": false, "reason": "前置条件不满足"}
        PTU-->>AI: exit 2 (DENY)
    end

    Note over SV: Layer 3: 文件路径验证
    SV->>PV: validate(tool_name, file_path, path_rules)
    PV->>PV: 白名单/黑名单/glob 匹配

    alt 路径不合法
        PV-->>SV: {"allowed": false, "reason": "路径在黑名单"}
        SV-->>PTU: {"allowed": false, ...}
        PTU-->>AI: exit 2 (DENY)
    end

    Note over SV: Layer 4: 语义分析
    SV->>SA: analyze(tool_name, tool_input, semantic_rules, task_meta)
    SA->>SA: 检查 requires_read_first / min_reads / 危险命令

    alt 语义检查失败
        SA-->>SV: {"allowed": false, "reason": "Write前未Read"}
        SV-->>PTU: {"allowed": false, ...}
        PTU-->>AI: exit 2 (DENY)
    end

    SA-->>SV: {"allowed": true}
    SV-->>PTU: {"allowed": true}
    PTU-->>AI: exit 0 (ALLOW)
```

### 状态转换表
| 当前状态 | 触发条件 | 下一状态 | 执行动作 | Hook |
|---------|---------|---------|---------|------|
| `activation` | 自动完成 | `planning` | 无需用户操作 | user_prompt_handler.py |
| `planning` | 用户输入"研究完成"/"已理解问题根因" | `implementation` | 保存 planning 快照，转移状态 | user_prompt_handler.py |
| `implementation` | 用户输入"同意"/"方案可行" + `planning_completed=true` | `finalization` | 保存 implementation 快照，设置 user_confirmed=true | user_prompt_handler.py |
| `implementation` | 用户输入"没修复"/"方案错了" | `planning` | 回退到 planning，清除 implementation 状态 | user_prompt_handler.py (v22.7) |
| `finalization` | 子代理完成归档 | (archived) | 设置 `finalization.status=completed`, `archived=true` | subagent_stop.py |

---

## 🔍 API 索引

### 核心函数速查
| 函数名 | 位置 | 用途 | 关键参数 | 返回值 |
|--------|------|------|---------|--------|
| `TaskMetaManager.atomic_update()` | [task_meta_manager.py:121](../templates/.claude/hooks/core/task_meta_manager.py#L121) | 原子更新 task-meta.json（文件锁 + 重试） | `task_id`, `update_func: Callable` | `Optional[Dict]` |
| `TaskMetaManager.load_task_meta()` | [task_meta_manager.py:56](../templates/.claude/hooks/core/task_meta_manager.py#L56) | 加载任务元数据 | `task_id: str` | `Optional[Dict]` |
| `TaskMetaManager.get_active_task_by_session()` | [task_meta_manager.py:266](../templates/.claude/hooks/core/task_meta_manager.py#L266) | 根据 session_id 查询绑定任务 | `session_id: str` | `Optional[Dict]` |
| `StageValidator.validate()` | [stage_validator.py:42](../templates/.claude/hooks/core/stage_validator.py#L42) | 四层验证（工具-路径-语义） | `current_step`, `tool_name`, `tool_input`, `task_meta` | `Dict[str, Any]` |
| `SemanticAnalyzer.analyze()` | [semantic_analyzer.py:45](../templates/.claude/hooks/core/semantic_analyzer.py#L45) | 语义分析（危险命令、前置条件） | `tool_name`, `tool_input`, `semantic_rules`, `task_meta` | `Dict[str, Any]` |
| `PathValidator.validate()` | [path_validator.py:28](../templates/.claude/hooks/core/path_validator.py#L28) | 路径验证（白名单/黑名单/glob） | `tool_name`, `file_path`, `path_rules` | `Dict[str, Any]` |
| `ExpertTrigger.should_trigger()` | [expert_trigger.py:34](../templates/.claude/hooks/core/expert_trigger.py#L34) | 循环检测，判断是否触发专家审查 | `workflow_state: Dict` | `bool` |
| `user_prompt_handler._handle_mc_command()` | [user_prompt_handler.py:158](../templates/.claude/hooks/orchestrator/user_prompt_handler.py#L158) | 处理 /mc 命令（创建任务、玩法包匹配） | `user_input`, `session_id` | `None` (side effect) |
| `pretooluse_enforcer.deny_and_exit()` | [pretooluse_enforcer.py:135](../templates/.claude/hooks/orchestrator/pretooluse_enforcer.py#L135) | 拒绝工具调用，输出错误信息 | `reason: str`, `current_step`, `tool_name` | `NoReturn` |
| `posttooluse_updater.update_metrics()` | [posttooluse_updater.py:89](../templates/.claude/hooks/orchestrator/posttooluse_updater.py#L89) | 更新度量数据（tools_used/docs_read/code_changes） | `task_meta`, `tool_name`, `tool_input`, `is_error` | `Dict` |
| `subagent_stop.extract_subagent_result()` | [subagent_stop.py:78](../templates/.claude/hooks/lifecycle/subagent_stop.py#L78) | 从 transcript 提取 SUBAGENT_RESULT 标记 | `transcript_path: str` | `Optional[Dict]` |
| `session_start.generate_status_dashboard()` | [session_start.py:102](../templates/.claude/hooks/lifecycle/session_start.py#L102) | 生成状态仪表盘（进度条、任务类型） | `task_meta: Dict` | `str` |

### 核心类速查
| 类名 | 位置 | 职责 | 关键方法 |
|------|------|------|---------|
| `TaskMetaManager` | [task_meta_manager.py:35](../templates/.claude/hooks/core/task_meta_manager.py#L35) | 任务元数据管理（原子更新、会话绑定） | `atomic_update()`, `load_task_meta()`, `bind_task_to_session()` |
| `StageValidator` | [stage_validator.py:26](../templates/.claude/hooks/core/stage_validator.py#L26) | 四层验证引擎 | `validate()`, `_validate_tool_allowed()`, `_validate_path()` |
| `SemanticAnalyzer` | [semantic_analyzer.py:15](../templates/.claude/hooks/core/semantic_analyzer.py#L15) | 语义分析器 | `analyze()`, `_analyze_write()`, `_analyze_edit()`, `_analyze_bash()` |
| `PathValidator` | [path_validator.py:14](../templates/.claude/hooks/core/path_validator.py#L14) | 路径验证器 | `validate()`, `_match_glob()` |
| `ExpertTrigger` | [expert_trigger.py:12](../templates/.claude/hooks/core/expert_trigger.py#L12) | 专家审查触发器 | `should_trigger()`, `_detect_bug_fix_loop()` |

---

## 🛠️ 运维速查

### 调试清单
| 场景 | 日志位置 | 关键字 | 诊断命令 |
|------|---------|--------|---------|
| PreToolUse 拦截失败 | `pretooluse-debug.log` | `Task条件匹配`, `标记注入` | `tail -f pretooluse-debug.log` |
| PostToolUse 更新失败 | `posttooluse-debug.log` | `原子更新`, `docs_read` | `tail -f posttooluse-debug.log` |
| SubagentStop 解析失败 | `subagent-stop-debug.log` | `解析transcript`, `提取结果` | `tail -f subagent-stop-debug.log` |
| 专家审查未触发 | `posttooluse-debug.log` | `循环检测`, `expert_triggered` | `grep "循环检测" posttooluse-debug.log` |
| 状态转移失败 | stderr 输出 | `状态转移`, `关键词检测` | 查看 Claude Code 输出 |
| task-meta.json 损坏 | 无 | N/A | `python -m json.tool tasks/{task_id}/.task-meta.json` |

### 修改场景表
| 需求 | 修改文件 | 修改位置 | 注意事项 |
|------|---------|---------|---------|
| **添加新阶段** | [tool_matrix.py](../templates/.claude/hooks/core/tool_matrix.py) | `STAGE_TOOL_MATRIX` 字典，`STEP_ORDER` 列表 | 同时修改 user_prompt_handler.py 的状态转移逻辑 |
| **修改工具白名单** | [tool_matrix.py](../templates/.claude/hooks/core/tool_matrix.py) | 对应阶段的 `allowed_tools` 数组 | 确保工具名称正确（注意别名：Update→Edit） |
| **调整文档要求** | [tool_matrix.py](../templates/.claude/hooks/core/tool_matrix.py) | `planning.semantic_rules.Read.min_reads` | 区分 bug_fix（min_reads_bug_fix=0）和 feature（min_reads=3） |
| **修改循环检测阈值** | [expert_trigger.py](../templates/.claude/hooks/core/expert_trigger.py) | `_detect_bug_fix_loop()` 函数的条件判断 | 默认：iterations>=2 AND negative>=2 AND same_file>=2 |
| **添加路径黑名单** | [tool_matrix.py](../templates/.claude/hooks/core/tool_matrix.py) | 对应阶段的 `path_rules.{tool}.blacklist` | 使用 glob 模式（如 `**/*.lock`） |
| **禁用某个工具** | [tool_matrix.py](../templates/.claude/hooks/core/tool_matrix.py) | `semantic_rules.{tool}.forbidden = true` | 添加 `reason` 字段说明原因 |
| **自定义状态转移关键词** | [user_prompt_handler.py](../templates/.claude/hooks/orchestrator/user_prompt_handler.py) | `_detect_state_transition()` 函数的关键词列表 | 使用 `match_keyword_safely()` 避免误匹配 |
| **增强专家审查标记** | [pretooluse_enforcer.py](../templates/.claude/hooks/orchestrator/pretooluse_enforcer.py) | Task 工具标记注入逻辑 | 确保 `updatedInput` 保留所有原始字段 |

---

## 📝 附录

### 完整文件清单

**核心模块 (core/)**
- [`task_meta_manager.py`](../templates/.claude/hooks/core/task_meta_manager.py) - 任务元数据管理器（原子更新、文件锁、会话绑定）
- [`stage_validator.py`](../templates/.claude/hooks/core/stage_validator.py) - 四层验证引擎（工具-路径-语义-前置条件）
- [`tool_matrix.py`](../templates/.claude/hooks/core/tool_matrix.py) - 工具矩阵配置（4阶段规则定义）
- [`semantic_analyzer.py`](../templates/.claude/hooks/core/semantic_analyzer.py) - 语义分析器（危险命令检测、前置条件检查）
- [`path_validator.py`](../templates/.claude/hooks/core/path_validator.py) - 路径验证器（白名单/黑名单/glob 匹配）
- [`expert_trigger.py`](../templates/.claude/hooks/core/expert_trigger.py) - 专家审查触发器（循环检测逻辑）

**编排器 (orchestrator/)**
- [`user_prompt_handler.py`](../templates/.claude/hooks/orchestrator/user_prompt_handler.py) - UserPromptSubmit Hook（/mc 命令处理、状态转移关键词检测）
- [`pretooluse_enforcer.py`](../templates/.claude/hooks/orchestrator/pretooluse_enforcer.py) - PreToolUse Hook（工具调用拦截、四层验证执行）
- [`posttooluse_updater.py`](../templates/.claude/hooks/orchestrator/posttooluse_updater.py) - PostToolUse Hook（度量记录、循环检测、专家触发）
- [`task_cancellation_handler.py`](../templates/.claude/hooks/orchestrator/task_cancellation_handler.py) - 任务取消处理（/mc cancel 命令）

**生命周期 (lifecycle/)**
- [`session_start.py`](../templates/.claude/hooks/lifecycle/session_start.py) - SessionStart Hook（状态仪表盘、压缩恢复提示）
- [`session_end.py`](../templates/.claude/hooks/lifecycle/session_end.py) - SessionEnd Hook（会话结束清理）
- [`subagent_stop.py`](../templates/.claude/hooks/lifecycle/subagent_stop.py) - SubagentStop Hook（专家审查结果提取、Finalization 状态更新）
- [`stop.py`](../templates/.claude/hooks/lifecycle/stop.py) - Stop Hook（桌面通知发送）
- [`pre_compact.py`](../templates/.claude/hooks/lifecycle/pre_compact.py) - PreCompact Hook（会话压缩前提醒）

**工具库 (utils/)**
- [`notify.py`](../templates/.claude/hooks/utils/notify.py) - 桌面通知（跨平台：Windows/macOS/Linux）
- [`config_loader.py`](../templates/.claude/hooks/utils/config_loader.py) - 配置加载器（加载 workflow-config.json）

**验证器 (validators/)**
- [`pre_compact_reminder.py`](../templates/.claude/hooks/validators/pre_compact_reminder.py) - 压缩提醒验证器

**归档器 (archiver/)**
- [`post_archive.py`](../templates/.claude/hooks/archiver/post_archive.py) - 归档后处理

### 版本信息
- **v3.0 Final**: 单一数据源架构（task-meta.json）、四层验证机制
- **v3.1**: 多会话支持（session_id 绑定、压缩恢复）
- **v22.0-v22.7**: Phase 3 用户体验增强（状态仪表盘、进度条、友好提示）
- **v23.0**: Finalization 倒计时机制（5次非Task工具后强制启动子代理）
- **v23.1**: Bash 工具文件修改检测、关键词扩充

---

**文档元信息**
- **生成时间**: 2025-11-18 (手动生成示例)
- **分析深度**: 完整代码级别
- **可信度**: 高（基于实际代码实现）
- **生成工具**: /code-to-docs 命令（首次演示）
- **维护方式**: 代码变更后重新运行 `/code-to-docs templates/.claude/hooks`

---

*本文档通过深度代码分析自动生成，不依赖注释和设计文档，是当前代码实现的真实反映。*
