# Hooks状态机功能实现文档

> **基于代码逆向分析生成 | 版本: v3.0 Final / v22.1**
> **分析日期**: 2025-11-16 | **精简版**（AI高效阅读优化）

---

## 目录

1. [系统概览](#1-系统概览)
2. [项目架构](#2-项目架构)
3. [核心模块](#3-核心模块)
4. [Hooks编排器](#4-hooks编排器)
5. [并发安全机制](#5-并发安全机制)
6. [错误处理与降级](#6-错误处理与降级)

---

## 1. 系统概览

### 1.1 核心理念

基于**Claude Code Hooks机制**的AI工作流强制执行系统，通过拦截AI的工具调用（Read、Write、Edit、Bash等）来实施严格的开发流程控制。

**设计哲学**：
- **零信任原则**：假设AI会违反规范，通过技术手段强制执行
- **单一数据源**：task-meta.json作为唯一真相源（v3.0架构）
- **会话隔离**：每个会话独立绑定任务（v3.1多会话支持）
- **原子操作**：所有状态更新使用文件锁+原子写入

### 1.2 四层验证架构

每次工具调用执行四层验证：

| 层次 | 验证内容 | 示例 |
|------|---------|------|
| Layer 1 | 工具类型是否在白名单 | Planning阶段禁止Write |
| Layer 2 | 前置条件检查 | 文档数量、专家审查完成 |
| Layer 3 | 文件路径验证 | 白名单/黑名单/glob匹配 |
| Layer 4 | 操作语义分析 | Write代码前必须Read、危险命令 |

### 1.3 语义化四步状态机

| 阶段 | 英文名 | 允许工具 | 状态转移条件 |
|------|--------|---------|-------------|
| 任务激活 | activation | - | 自动完成（任务类型识别） |
| 方案制定 | planning | Read, Grep, Glob, Task, WebFetch | 用户输入"同意"+文档数量达标+专家审查完成（bug_fix类型） |
| 代码实施 | implementation | Read, Write, Edit, Bash, Grep, Glob | 用户输入"修复了" |
| 收尾归档 | finalization | Task（启动子代理） | 子代理完成归档 |

**关键转移规则**：
- Planning → Implementation：需满足 `docs_read >= required_doc_count` + `expert_review_completed=true`（bug_fix类型）
- Implementation → Finalization：用户确认"修复了"
- Implementation → Planning：用户反馈"没修复"（回滚重新分析）

---

## 2. 项目架构

### 2.1 目录结构（简化版）

```
templates/.claude/hooks/
├── core/                      # 核心引擎
│   ├── task_meta_manager.py   # 任务元数据管理器（唯一数据源）
│   ├── stage_validator.py     # 四层验证引擎
│   ├── tool_matrix.py          # 工具矩阵配置
│   ├── semantic_analyzer.py    # 语义分析器
│   ├── path_validator.py       # 路径验证器
│   └── expert_trigger.py       # 专家触发器
├── orchestrator/              # Hooks编排器
│   ├── user_prompt_handler.py         # UserPromptSubmit Hook
│   ├── pretooluse_enforcer.py         # PreToolUse Hook
│   ├── posttooluse_updater.py         # PostToolUse Hook
│   └── task_cancellation_handler.py   # 任务取消处理
├── lifecycle/                 # 生命周期管理
│   ├── session_start.py, session_end.py, stop.py
│   ├── subagent_stop.py, pre_compact.py
└── utils/                     # 工具库

运行时数据:
.claude/
├── .task-active.json          # 会话→任务绑定映射（v3.1）
└── workflow-config.json

tasks/<task_id>/
├── .task-meta.json            # 唯一数据源（完整运行时状态）
├── .cleanup-subagent.lock     # 子代理锁文件
├── context.md, solution.md
```

### 2.2 数据结构（关键字段）

**task-meta.json**（完整示例见 `docs/schemas/task-meta-example.json`）：
```python
{
  "task_id": str,                # 任务ID
  "task_type": str,              # bug_fix | feature_implementation | general
  "current_step": str,           # activation | planning | implementation | finalization

  "steps": {
    "planning": {
      "status": str,             # pending | in_progress | completed
      "required_doc_count": int, # 最少文档阅读数（bug_fix=0, 其他=3）
      "user_confirmed": bool,    # 用户是否确认
      "expert_review_required": bool,     # BUG修复强制审查（v22.1）
      "expert_review_completed": bool,    # 审查是否完成
      "expert_review_result": str         # pass | 需要调整
    },
    "implementation": {
      "user_confirmed": bool     # 用户是否确认修复成功
    }
  },

  "metrics": {
    "docs_read": [{"file": str, "timestamp": str}],
    "code_changes": [{"file": str, "tool": str, "success": bool}],
    "tools_used": [{"tool": str, "success": bool}]
  },

  "bug_fix_tracking": {          # 仅bug_fix类型
    "iterations": [{"user_feedback": str, "feedback_sentiment": str}],
    "loop_indicators": {
      "same_file_edit_count": int,
      "negative_feedback_count": int
    }
  }
}
```

**.task-active.json**（v3.1会话绑定）：
```python
{
  "version": "v3.1",
  "active_tasks": {
    "<session_id>": {
      "task_id": str,
      "task_dir": str,
      "current_step": str,
      "bound_at": str,
      "session_history": [str]  # 压缩恢复链
    }
  }
}
```

---

## 3. 核心模块

### 3.1 TaskMetaManager - 任务元数据管理器

**职责**：唯一数据源，管理所有运行时状态，提供原子更新能力

#### 核心API

| 方法 | 功能 | 并发安全 |
|------|------|---------|
| `bind_task_to_session(task_id, session_id)` | 绑定任务到会话（v3.1） | ✅ 文件锁 |
| `get_active_task_by_session(session_id)` | 获取会话绑定的任务 | ✅ 只读 |
| `load_task_meta(task_id)` | 加载任务元数据 | ⚠️ 重试机制 |
| `atomic_update(task_id, update_func)` | 原子更新元数据 | ✅ 锁+重试 |

#### 原子更新机制

```python
def atomic_update(task_id, update_func):
    """
    原子更新流程：
    1. 获取全局lockfile（.task-meta.json.lock）
    2. 在锁内执行：读取 → update_func(task_meta) → 保存
    3. 释放锁并清理lockfile

    重试策略：最多10次，指数退避（50ms → 2000ms）
    """
    lock_path = meta_path + '.lock'
    for attempt in range(10):
        with portalocker.Lock(lock_path, 'w', timeout=0) as lock:
            task_meta = load_task_meta(task_id)
            updated_meta = update_func(task_meta)  # 闭包模式
            save_task_meta(task_id, updated_meta)  # 原子写入（临时文件+rename）
            return updated_meta
        # 锁失败：指数退避
        time.sleep(min(0.05 * (2 ** attempt), 2.0))
```

---

### 3.2 StageValidator - 四层验证引擎

**职责**：对每次工具调用执行四层验证，决定DENY或ALLOW

#### 验证流程

```python
def validate(current_step, tool_name, tool_input, task_meta):
    # Layer 1: 工具名称归一化 + 基础验证
    tool_name = normalize_tool_alias(tool_name)  # Update → Edit
    if tool_name not in STAGE_TOOL_MATRIX[current_step]["allowed_tools"]:
        return {"allowed": False, "reason": f"阶段 {current_step} 不允许使用工具: {tool_name}"}

    # Layer 2: 前置条件检查
    if current_step == "implementation":
        planning = task_meta['steps']['planning']
        if not planning.get('user_confirmed'):
            return {"allowed": False, "reason": "Planning阶段未确认"}

    # Layer 3: 文件路径验证（仅Read/Write/Edit）
    if tool_name in ["Read", "Write", "Edit"]:
        file_path = tool_input.get("file_path")
        path_result = PathValidator.validate(current_step, tool_name, file_path)
        if not path_result["allowed"]:
            return path_result

    # Layer 4: 操作语义分析
    return SemanticAnalyzer.validate(current_step, tool_name, tool_input, task_meta)
```

#### 工具别名归一化（v3.0）

| Claude Code工具 | 归一化后 |
|----------------|---------|
| Update | Edit |
| Patch | Edit |

---

### 3.3 ToolMatrix - 工具矩阵配置

**职责**：定义每个阶段的工具白名单、路径规则、语义规则

#### 四阶段配置（表格化）

**Planning阶段**：
| 配置项 | 值 |
|--------|---|
| allowed_tools | Read, Grep, Glob, Task, WebFetch, WebSearch |
| 禁止工具 | Write, Edit, Bash（严禁修改文件） |
| 前置条件 | activation已完成 |
| 文档要求 | bug_fix=0, 其他=3 |

**Implementation阶段**：
| 配置项 | 值 |
|--------|---|
| allowed_tools | Read, Write, Edit, NotebookEdit, Bash, Grep, Glob |
| 前置条件 | planning已完成, user_confirmed=true |
| 路径规则-Write白名单 | `behavior_packs/**/*.py`, `resource_packs/**/*.json` |
| 路径规则-黑名单 | `.task-meta.json`, `workflow-state.json` |
| 语义规则 | Write前必须Read（代码文件）, 同文件修改>5次触发专家 |
| Bash危险命令 | `rm -rf /`, `git push --force`, `sudo`, `mkfs`, `dd if=` |

**Finalization阶段**：
| 配置项 | 父代理 | 子代理 |
|--------|--------|--------|
| allowed_tools | Task, Read | Read, Write, Edit, Grep, Glob |
| Write权限 | ❌ 禁止 | ✅ 仅.task-meta.json, markdown/**/*.md |
| Task限制 | 仅启动1次子代理 | - |

---

### 3.4 SemanticAnalyzer - 语义分析器

**职责**：第四层验证，区分工具用途、检测危险命令

#### 关键规则

**Write语义分析**：
1. Finalization父代理禁止Write
2. 禁止修改元数据文件（.task-meta.json）
3. Implementation阶段：Write代码文件前必须Read过该文件

**Bash危险检测**：
```python
dangerous_patterns = [
    (r"rm\s+-rf\s+/", "删除根目录"),
    (r"git\s+push\s+--force", "强制推送"),
    (r"sudo\b", "提权命令"),
]
```

---

### 3.5 PathValidator - 路径验证器

**验证逻辑**（优先级从高到低）：
1. 黑名单优先：`file_path in blacklist` → DENY
2. 黑名单glob模式：`matches_glob_pattern(file_path, blacklist_patterns)` → DENY
3. 白名单检查：如定义白名单，则必须匹配 → 不匹配则DENY
4. 默认放行

**Glob模式匹配**：
- `behavior_packs/**/*.py`：任意子目录的py文件
- `*.md`：顶层md文件

---

### 3.6 ExpertTrigger - 专家触发器

**职责**：检测循环模式（BUG修复循环），生成专家分析Prompt

#### 循环检测条件（bug_fix类型）

```python
触发条件（同时满足）：
- 迭代次数 >= 2
- 负面反馈 >= 2（"还是没修复", "需要调整"）
- 同文件修改 >= 2
```

#### 专家Prompt生成

```python
专家分析框架：
1. 根因分析：为什么反复修改仍失败？
2. 失败模式：历史修改中的错误假设
3. 备选路径：3-5种不同的解决思路
4. 推荐策略：具体实施步骤 + 验证方法
5. 澄清问题：需要向用户确认的关键信息
```

---

## 4. Hooks编排器

### 4.1 UserPromptSubmit Hook

**触发时机**：用户提交提示词后
**职责**：任务初始化、玩法包匹配、状态转移处理

#### 关键功能

| 功能 | 触发条件 | 核心逻辑 |
|------|---------|---------|
| 任务初始化 | 用户输入 `/mc <描述>` | 1. 生成任务ID（时间戳+描述前16字符）<br>2. 检测任务类型（bug_fix/general）<br>3. 创建task-meta.json<br>4. 绑定到当前会话（v3.1）<br>5. 注入BUG修复指引或玩法包内容 |
| 状态转移-Planning→Implementation | 用户输入"同意" | **前置检查**：<br>1. 文档数量 >= required_doc_count<br>2. expert_review_completed=true（bug_fix类型）<br>**执行转移**（原子更新）：<br>- `current_step = 'implementation'`<br>- `planning.status = 'completed'`<br>- `planning.user_confirmed = true` |
| 状态转移-Implementation→Finalization | 用户输入"修复了" | `current_step = 'finalization'`<br>`implementation.user_confirmed = true` |
| 状态转移-Implementation→Planning | 用户输入"没修复" | 回滚到Planning，记录迭代历史 |

#### 专家审查阻止机制（v22.1）

```python
if expert_review_required and not expert_review_completed:
    输出错误消息：
    """
    ⚠️ 无法进入Implementation阶段
    当前任务类型: BUG修复
    专家审查状态: 未完成

    ✅ 解决方案:
    1. 使用 Task 工具启动专家审查子代理
    2. 等待子代理完成审查并返回结果
    3. 根据审查结果调整方案
    4. 重新输入"同意"推进到Implementation阶段
    """
    阻止状态转移（返回原样task_meta）
```

---

### 4.2 PreToolUse Hook - 四层验证拦截器

**触发时机**：AI调用工具前
**职责**：执行四层验证，违规则DENY（exit code 2）

#### 主流程

```python
def main():
    # 1. 解析输入
    tool_name = event_data.get("tool_name")
    tool_input = event_data.get("tool_input")
    session_id = event_data.get("session_id")

    # 2. 获取绑定任务（v3.1）
    task_binding = mgr.get_active_task_by_session(session_id)
    if not task_binding:
        allow_and_exit("无绑定任务", suppress=True)  # 默认放行

    # 3. 四层验证
    validation_result = StageValidator.validate(
        current_step, tool_name, tool_input, task_meta
    )

    # 4. 决策
    if validation_result["allowed"]:
        allow_and_exit(suppress=True)
    else:
        deny_and_exit(tool_name, current_step, reason, suggestion)  # exit code 2
```

#### 拒绝消息格式

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ 工具调用被拒绝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前阶段: 📝 方案制定
尝试工具: Write

❌ 拒绝原因:
阶段 方案制定 不允许使用工具: Write

✅ 正确做法:
阶段 方案制定:
- 描述: 深度研究问题根因和技术约束,制定解决方案
- 允许的工具: Read, Grep, Glob, Task, WebFetch

请查阅至少3个相关文档，理解问题根因和技术约束，
明确说明研究结论后继续

⚠️ 工作流强制执行 - 违规操作已被阻止
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 4.3 PostToolUse Hook - 状态更新器

**触发时机**：工具执行后
**职责**：更新metrics、检测循环、触发专家审查

#### 主流程（原子更新模式）

```python
def main():
    # 原子更新闭包
    def update_func(task_meta):
        # 1. 更新度量指标
        update_metrics(task_meta, tool_name, tool_input, is_error)

        # 2. 更新BUG修复追踪（仅bug_fix类型）
        update_bug_fix_tracking(task_meta, tool_name, tool_input, is_error)

        # 3. 检测循环并触发专家
        if ExpertTrigger.should_trigger(task_meta):
            task_meta['expert_triggered'] = True
            sys.stderr.write(expert_prompt)  # 输出专家Prompt

        return task_meta

    updated_meta = mgr.atomic_update(task_id, update_func)

    # 4. 生成用户可见提示（v22.0）
    if tool_name in ['Write', 'Edit']:
        current_round = get_current_round(updated_meta)
        total_changes = len(updated_meta['metrics']['code_changes'])
        print(f"💾 代码修改已记录: {file_name} (第{current_round}轮, 共{total_changes}次修改)")
```

#### Metrics更新规则

| 工具 | 记录到 | 条件 |
|------|--------|------|
| Read | docs_read[] | 文件路径包含 'markdown' 或 '.md' |
| Edit/Write/NotebookEdit | code_changes[] | 所有文件 |
| 所有工具 | tools_used[] | 所有调用（含错误） |
| 失败操作 | failed_operations[] | is_error=true |

---

### 4.4 Stop Hook - 轮次边界验证

**触发时机**：会话结束前
**职责**：阻止未完成的任务结束，强制继续分析

#### 关键检查

| 阶段 | 检查条件 | 阻止消息 |
|------|---------|---------|
| Planning | `user_confirmed = false` | 生成方案摘要，提示用户确认 |
| Implementation | `user_confirmed = false` | 生成修改摘要，提示用户测试并反馈 |

#### Race Condition优化（v3.0）

```python
# 问题：Stop Hook可能比PostToolUse早执行，读到旧数据
# 解决：主动等待PostToolUse完成
def wait_for_posttooluse_completion(meta_path, max_wait=0.5):
    start = time.time()
    while time.time() - start < max_wait:
        if not os.path.exists(meta_path + '.lock'):
            return  # PostToolUse已释放锁
        time.sleep(0.05)
```

---

### 4.5 SessionStart Hook - 状态仪表盘（v22.0）

**触发时机**：会话启动时
**职责**：显示任务进度条、阶段信息

#### 输出示例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 当前任务状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
任务ID: 任务-1116-161424-修复玩家掉落BUG
任务类型: BUG修复

进度条:
✅ 任务激活 → ✅ 方案制定 → 🔄 代码实施 → ⏳ 收尾归档

当前阶段: 🔄 代码实施（第2轮）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

### 4.6 SubagentStop Hook - 专家审查结果处理（v22.1）

**触发时机**：子代理停止时
**职责**：解析专家审查结果，更新task-meta.json

#### 结果解析

```python
def parse_expert_review_result(subagent_output):
    """
    解析专家审查结果（关键词匹配）

    通过：包含 "通过", "approved", "looks good"
    不通过：包含 "需要调整", "有问题", "建议修改"
    """
    positive_keywords = ["通过", "approved", "looks good", "可以实施"]
    negative_keywords = ["需要调整", "有问题", "建议修改", "需要重新"]

    if any(kw in output.lower() for kw in positive_keywords):
        return "pass"
    elif any(kw in output.lower() for kw in negative_keywords):
        return "需要调整"
    else:
        return "未明确"
```

#### 原子更新专家审查状态

```python
def update_func(task_meta):
    planning = task_meta['steps']['planning']
    planning['expert_review_completed'] = True
    planning['expert_review_count'] = planning.get('expert_review_count', 0) + 1
    planning['expert_review_result'] = result  # "pass" | "需要调整"
    return task_meta

mgr.atomic_update(task_id, update_func)
```

---

## 5. 并发安全机制

### 5.1 文件锁机制

**实现**：portalocker库（跨平台文件锁）

| 锁文件 | 用途 | 锁模式 | 重试策略 |
|--------|------|--------|---------|
| `.task-meta.json.lock` | 保护task-meta.json | LOCK_EX \| LOCK_NB（非阻塞） | 10次, 指数退避（50ms→2s） |
| `.task-active.json.lock` | 保护.task-active.json | LOCK_EX \| LOCK_NB | 同上 |
| `.cleanup-subagent.lock` | 标识子代理上下文 | 仅作标记（无实际锁） | - |

### 5.2 原子写入机制

```python
def save_task_meta(task_id, task_meta):
    """
    原子写入流程（避免写入一半时被读取）
    1. 写入临时文件: .task-meta.json.tmp
    2. fsync() 强制刷盘
    3. os.rename(.tmp → .json)  # 原子操作（系统级保证）
    """
    tmp_path = meta_path + '.tmp'
    with open(tmp_path, 'w') as f:
        json.dump(task_meta, f)
        f.flush()
        os.fsync(f.fileno())
    os.rename(tmp_path, meta_path)  # 原子替换
```

### 5.3 会话隔离机制（v3.1）

**机制**：`.task-active.json`维护`session_id → task_id`映射，确保：
- 不同会话可以并行处理不同任务
- 同一任务不会被多个会话同时处理（绑定锁定）
- 压缩恢复时通过`session_history`链追踪任务

---

## 6. 错误处理与降级

### 6.1 Hook执行失败降级

**原则**：技术故障不应完全阻塞用户工作

| Hook类型 | 失败降级策略 | 风险 |
|---------|-------------|------|
| PreToolUse | 默认放行（exit code 0） | ⚠️ 可能绕过验证 |
| PostToolUse | 静默失败（不更新metrics） | ⚠️ 循环检测失效 |
| Stop | 允许结束（不阻塞） | ⚠️ 未完成任务可能结束 |

### 6.2 文件锁超时降级

```python
try:
    portalocker.lock(lock_file, LOCK_EX | LOCK_NB)
    # ...
except LockException:
    if attempt >= MAX_RETRIES:
        # 降级：无锁模式（有风险，但至少可用）
        task_meta = load_json(meta_path)
        updated_meta = update_func(task_meta)
        save_json(meta_path, updated_meta)
```

### 6.3 PostToolUse失效保护（Stop Hook Fallback）

**问题**：PostToolUse失败导致metrics未更新
**解决**：Stop Hook检测到`code_changes`为空时，主动扫描任务目录的代码文件，生成降级摘要

### 6.4 portalocker降级

**问题**：某些环境无法安装portalocker
**解决**：检测导入失败，降级到无锁模式（记录警告日志）

---

## 附录

### A. 关键常量配置

```python
# TaskMetaManager
ATOMIC_UPDATE_MAX_RETRIES = 10  # 原子更新最大重试
ATOMIC_UPDATE_BASE_DELAY = 0.05  # 50ms基础延迟（指数退避）

# Stop Hook
RACE_CONDITION_MAX_WAIT = 0.5  # 500ms最大等待PostToolUse
RACE_CONDITION_POLL_INTERVAL = 0.05  # 50ms轮询间隔

# ExpertTrigger
BUG_FIX_MIN_ITERATIONS = 2  # BUG修复最少迭代数
BUG_FIX_MIN_NEGATIVE_FEEDBACK = 2  # 最少负面反馈数
BUG_FIX_MIN_SAME_FILE_EDITS = 2  # 最少同文件修改数

# config_loader
DEFAULT_MAX_TASK_DESC_LENGTH = 16  # v20.2.7
DEFAULT_PLANNING_MIN_DOCS = 3  # v3.0 Final（bug_fix=0）
```

### B. 外部文件引用

- **完整task-meta.json示例**：[docs/schemas/task-meta-example.json](../schemas/task-meta-example.json)
- **完整.task-active.json示例**：[docs/schemas/task-active-example.json](../schemas/task-active-example.json)

---

## 总结

本文档基于代码逆向分析，详细描述了Hooks状态机系统的功能实现。核心要点：

1. **唯一数据源架构**：task-meta.json存储所有运行时状态
2. **四层验证机制**：工具类型 → 前置条件 → 文件路径 → 操作语义
3. **会话隔离（v3.1）**：支持多会话并行处理不同任务
4. **原子操作保证**：文件锁+原子写入+指数退避重试
5. **降级容错设计**：Hook失败时默认放行，避免完全阻塞

**版本历史**：
- v2.0：单一数据源架构
- v3.0 Final：语义化4步状态机
- v3.1：会话隔离支持
- v22.0：用户体验增强（状态仪表盘、轮次可见性）
- v22.1：BUG修复强制专家审查

---

_文档版本: v3.0 精简版 | 最后更新: 2025-11-16_
