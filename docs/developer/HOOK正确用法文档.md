# Claude Code Hooks 正确用法文档

> **文档版本**: v4.1 - 补充 updatedInput 详解
> **文档目的**: Hook 开发的唯一标准实现规范
> **维护原则**: 基于官方文档和实战经验的最佳实践
> **创建日期**: 2025-11-19
> **最终修订**: 2025-11-19

---

## 📚 核心概念

### Hook类型与阻止机制

Claude Code提供多种Hook类型，**每种Hook的阻止机制不同**：

| Hook类型 | 阻止机制 | 阻止效果 | 用途场景 |
|---------|---------|---------|---------|
| **PreToolUse** | `sys.exit(2)` 或 `"permissionDecision": "deny"` | **阻止工具执行** | 阻止Planning阶段的Write操作 |
| **UserPromptSubmit** | `sys.exit(2)` 或 `"decision": "block"` | **阻止提示处理** | 阻止未完成前置条件的状态转移 |
| **PostToolUse** | `"decision": "block"` | **工具已执行，自动向 Claude 发送反馈** | 检测到问题后向 Claude 反馈 |
| **SubagentStop** | `sys.exit(2)` 或 `"decision": "block"` | **阻止 subagent 停止，强制继续工作** | 审查未通过时强制 subagent 继续 |
| **SessionStart** | 无阻止能力 | 仅展示信息 | 显示任务进度仪表盘 |

**关键要点**:
- 所有 Hook 都支持 `"continue": False` 强制停止 Claude（最强阻止机制，默认值为 `True`）
- PreToolUse 是唯一能**真正阻止工具执行**的 Hook
- PostToolUse 的 `"decision": "block"` **不能阻止工具执行**（工具已执行），但会**自动向 Claude 发送反馈**

**字段速查表**:
- **PreToolUse** → `"permissionDecision"` (权限决策: "allow", "deny", "ask")
- **PreToolUse** → `"updatedInput"` (类型: `Record<string, unknown>` - 修改工具参数，仅 "allow" 时有效)
- **UserPromptSubmit / PostToolUse / SubagentStop** → `"decision"` (通用决策: "block" | undefined)
- **PostToolUse** → `"decision": "block"` 是反馈机制，不是阻止机制
- **SubagentStop** → `"decision": "block"` 阻止 subagent 停止，强制继续工作
- **所有 Hook** → `"continue"` (通用字段: False = 强制停止Claude，默认值为 True)

### 通用字段说明

所有 Hook 都支持以下通用字段：

| 字段 | 类型 | 说明 | 使用场景 |
|------|------|------|---------|
| `"continue"` | `boolean` | `False` = 强制停止 Claude | 检测到严重错误时 |
| `"suppressOutput"` | `boolean` | `True` = 隐藏 stdout 输出（不显示在 transcript 中） | 静默记录场景 |
| `"systemMessage"` | `string` | 向用户显示警告消息 | 需要用户关注的警告信息 |

**示例**:
```python
# 静默记录（不打扰用户）
return {
    "hookSpecificOutput": {...},
    "suppressOutput": True
}

# 向用户显示警告
return {
    "hookSpecificOutput": {...},
    "systemMessage": "⚠️ 检测到高风险操作，请谨慎确认"
}

# 强制停止 Claude
return {
    "continue": False,
    "stopReason": "🛑 严重错误：任务无法继续"
}
```

---

## ✅ 正确用法

### 1. PreToolUse Hook - 阻止工具调用

**场景**: 在Planning阶段阻止代码修改工具

PreToolUse 提供**两种阻止机制**，可根据需要选择：

#### 方法1: Exit Code 2（推荐用于简单阻止）

```python
def deny_and_exit(tool_name, current_step, reason, suggestion):
    """使用exit code 2阻止工具调用"""
    denial_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⛔ 工具调用被拒绝
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前阶段: {current_step}
尝试工具: {tool_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ 拒绝原因:
{reason}

✅ 正确做法:
{suggestion}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    sys.stderr.write(denial_message)
    sys.stderr.flush()
    sys.exit(2)  # ✅ 这会真正阻止工具调用
```

**关键要点**:
- ✅ `sys.exit(2)` 是阻止信号
- ✅ stderr 消息会显示给 Claude
- ✅ 简单直接，适合大多数阻止场景

**Exit Code 2 的行为说明**:

| Hook 类型 | Exit Code 2 行为 |
|---------|-----------------|
| **PreToolUse** | 阻止工具执行，stderr 输出显示给 Claude |
| **UserPromptSubmit** | **阻止提示处理并清除提示内容**，stderr 输出显示给 Claude |
| **PostToolUse** | **工具已执行，无法撤销操作**，stderr 输出显示给 Claude |
| **SubagentStop** | 阻止 subagent 停止，stderr 输出显示给 Claude |
| **通用** | 适用于所有 Hook 类型，但效果因 Hook 类型而异 |

**重要说明**:
- UserPromptSubmit 的 exit 2 会"清除提示"（erases prompt），这是一个重要细节
- PostToolUse 的 exit 2 **无法阻止或撤销**已执行的操作，只能显示信息给 Claude

#### 方法2: JSON响应格式（支持更多控制）

```python
def deny_with_json(tool_name, current_step, reason):
    """使用JSON响应阻止工具调用"""
    response = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",  # "allow", "deny", "ask"
            "permissionDecisionReason": f"""
⛔ 工具调用被拒绝

当前阶段: {current_step}
尝试工具: {tool_name}

❌ 拒绝原因:
{reason}

✅ 正确做法:
请先向用户展示方案，等待用户确认后再修改代码。
"""
        }
    }
    print(json.dumps(response, ensure_ascii=False))
    sys.exit(0)  # ✅ 使用 exit 0（不是 exit 2）+ permissionDecision: deny = 阻止
```

**JSON响应的三种决策**:
- `"allow"`: 允许执行，可通过 `updatedInput` 修改工具参数
- `"deny"`: **阻止执行**，向 Claude 显示 `permissionDecisionReason`
- `"ask"`: 请求用户确认（弹出对话框）

**关键要点**:
- ✅ JSON 响应**必须**使用 `sys.exit(0)`
- ✅ `"permissionDecision": "deny"` 是阻止机制
- ⚠️ Exit code 2 会**忽略 JSON 输出**，只使用 stderr
- ✅ `permissionDecisionReason` 显示给 Claude
- ✅ `updatedInput` 用于修改工具参数（仅 `"allow"` 时）

**updatedInput 字段详解**:
- **字段类型**: `Record<string, unknown>` - 一个包含你想要修改或添加的字段的对象
- **使用时机**: 仅在 `"permissionDecision": "allow"` 时有效
- **作用**: 修改 Claude 传递给工具的参数（例如修改文件路径、添加额外参数等）
- **示例**:
```python
# 示例：允许执行，但修改文件路径为备份路径
response = {
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "updatedInput": {  # 修改工具参数
            "file_path": f"/backup/{original_file_path}",  # 修改路径
            "add_timestamp": True  # 添加新字段
        }
    }
}
print(json.dumps(response, ensure_ascii=False))
sys.exit(0)
```

**两种方法的对比**:

| 特性 | Exit Code 2 | JSON 响应 |
|------|------------|-----------|
| 阻止能力 | ✅ 完全阻止 | ✅ 完全阻止 |
| 简洁性 | ✅ 简单 | ⚠️ 较复杂 |
| 修改参数 | ❌ 不支持 | ✅ 支持 `updatedInput` |
| 用户确认 | ❌ 不支持 | ✅ 支持 `"ask"` |
| 推荐场景 | 简单阻止 | 需要参数修改或用户确认 |

---

### 2. UserPromptSubmit Hook - 阻止提示处理

**场景**: 检测到前置条件未满足，阻止状态转移

```python
def handle_state_transition(user_input, cwd, session_id):
    """处理状态转移的标准实现"""

    # 前置条件检查
    if blocked:  # 前置条件未满足
        return {
            "decision": "block",  # 阻止关键字段
            "reason": "前置条件未满足",  # Claude会看到
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": detailed_message  # 用户会看到
            }
        }

    # 允许继续
    return {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": success_message
        }
        # 注意：不需要显式返回 "continue": True（默认值）
    }
```

**关键要点**:
- ✅ `"decision": "block"` 是阻止机制
- ✅ `"reason"` 字段：简短原因（Claude会看到）
- ✅ `"additionalContext"` 字段：详细说明（用户会看到）
- ⚠️ `"continue"` 是所有 hook 的通用字段（默认为 True），与阻止机制无关

**UserPromptSubmit 的特殊行为**:
- **Plain stdout（简单方式）**: 任何非 JSON 文本输出到 stdout 都会被添加到 Claude 的上下文，**并显示在 transcript 中**
- **JSON additionalContext（推荐方式）**: 通过 `"additionalContext"` 字段添加上下文，**更隐蔽，不显示在 transcript 中**
- 这是 UserPromptSubmit **独有的行为**，其他 hook 不适用
- 适合场景：向 Claude 提供额外的上下文信息（如当前时间、系统状态等）

**两种方式的对比**:

| 特性 | Plain stdout | JSON additionalContext |
|------|-------------|----------------------|
| 添加上下文 | ✅ 自动添加 | ✅ 通过字段添加 |
| 显示在 transcript | ✅ **会显示** | ❌ **不显示（更隐蔽）** |
| 结构化 | ❌ 纯文本 | ✅ JSON 格式 |
| 推荐场景 | 简单场景 | **推荐使用（更干净）** |

**示例**:
```python
# 方法1: 使用 stdout（简单，但会显示在 transcript）
print(f"当前时间: {datetime.now().isoformat()}")
print(f"任务进度: {progress}%")
sys.exit(0)  # stdout 内容会被添加到 Claude 的上下文，并显示在 transcript 中

# 方法2: 使用 JSON（推荐，更隐蔽，不显示在 transcript）
return {
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": f"""
当前时间: {datetime.now().isoformat()}
任务进度: {progress}%
"""
    }
}
```

---

### 3. PostToolUse Hook - 工具执行后的反馈

**场景**: 工具执行后向 Claude 发送反馈或向用户显示信息

**重要**: PostToolUse 在工具**执行后**调用，**无法阻止工具执行**。PostToolUse 主要用于：
- 向 Claude 发送反馈（使用 `"decision": "block"` + `"reason"`）
- 记录元数据（如代码修改记录）
- 向用户显示工具执行后的信息

#### 用法1: 静默记录（常用）

```python
def main():
    """PostToolUse常用于静默记录"""
    tool_name = input_data.get('tool_name')
    tool_result = input_data.get('tool_result')

    # 更新元数据
    if tool_name in ['Write', 'Edit', 'NotebookEdit']:
        meta_data['metrics']['code_changes'].append({
            'file_path': tool_args.get('file_path'),
            'operation': tool_name,
            'timestamp': datetime.now().isoformat()
        })
        save_task_meta(meta_data)

    # 静默返回
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        },
        "suppressOutput": True  # 不打扰用户
    }
```

#### 用法2: 向 Claude 发送反馈

```python
def main():
    """PostToolUse向Claude发送反馈"""
    tool_name = input_data.get('tool_name')
    tool_args = input_data.get('tool_args', {})

    # 检测到问题（例如：修改了不应该修改的文件）
    if tool_name == 'Write':
        file_path = tool_args.get('file_path')
        if 'config.json' in file_path and current_step == 'planning':
            # ⚠️ 工具已经执行，文件已经被修改
            # 但我们可以通过 "decision": "block" 向 Claude 发送反馈
            # Claude 会收到 reason 并可能采取补救措施（如撤销修改）
            return {
                "decision": "block",  # 自动向 Claude 发送反馈
                "reason": "Planning阶段不应该修改配置文件",  # Claude 会看到
                "hookSpecificOutput": {
                    "hookEventName": "PostToolUse",
                    "additionalContext": """
⚠️ 检测到问题操作

你刚刚在Planning阶段修改了配置文件，这违反了工作流规则。

✅ 建议操作：
1. 使用 Edit 工具撤销刚才的修改
2. 等待用户确认方案后再进入Implementation阶段
3. 在Implementation阶段再修改配置文件
"""  # 用户会看到
                }
            }

    # 正常情况：静默返回
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": ""
        },
        "suppressOutput": True
    }
```

**关键要点**:
- ⚠️ PostToolUse 在工具**执行后**调用，**无法阻止或撤销已执行的操作**
- ✅ 支持 `"decision": "block"` 字段，**自动向 Claude 发送 reason** 作为反馈
- ✅ 这是一种**自动化反馈机制**，让 Claude 意识到问题并采取补救措施
- ✅ `"reason"` 字段内容会显示给 Claude
- ✅ `"additionalContext"` 字段内容会显示给用户
- ✅ 适合用于记录元数据、检测问题并向 Claude 反馈
- ⚠️ 如果需要**真正阻止**工具执行，必须在 PreToolUse 中拦截

---

### 4. continue: False - 强制停止机制

**场景**: 检测到严重错误，需要立即停止 Claude

```python
def main():
    """检测到严重问题时强制停止Claude"""
    if critical_error_detected:
        return {
            "continue": False,  # 强制停止Claude
            "stopReason": """
🛑 严重错误：检测到任务元数据损坏

任务无法继续执行。请手动修复以下文件：
- .claude/.task-active.json

修复后重新启动任务。
"""
        }
```

**continue 字段的三种用法**:

| 场景 | 字段设置 | 效果 |
|------|---------|------|
| **正常流程** | 不设置或 `"continue": True`（默认值） | Hook执行完成，Claude继续正常流程 |
| **验证失败** | `"decision": "block"` | Hook阻止当前操作，Claude收到反馈 |
| **强制停止** | `"continue": False` | **立即停止Claude**，显示stopReason给用户 |

**使用场景**:
- ✅ 检测到严重错误（如元数据损坏）
- ✅ 检测到安全问题（如尝试访问敏感文件）
- ✅ 检测到不可恢复的状态（如任务配置缺失）
- ❌ 不要用于普通的验证失败（应该用 `"decision": "block"`）

---

## 📖 实战案例

### 案例1：Planning阶段禁止代码修改

**需求**: 用户未确认方案前，不允许修改代码

**解决方案**: PreToolUse + UserPromptSubmit 双重机制

**实现**:

**1. UserPromptSubmit** - 检测用户确认
```python
# 当用户说"同意"时
if match_keywords(user_input, CONFIRM_KEYWORDS):
    # 检查前置条件
    if not docs_sufficient:
        return {
            "decision": "block",
            "reason": "文档不足"
        }

    # 前置条件通过，转移状态
    meta_data['current_step'] = 'implementation'
    meta_data['steps']['planning']['user_confirmed'] = True
    return {"hookSpecificOutput": {...}}
```

**2. PreToolUse** - 双重保险
```python
# 即使用户说了"认同"但未被识别为"同意"
if current_step == 'planning':
    if tool_name in ['Write', 'Edit']:
        user_confirmed = meta_data['steps']['planning']['user_confirmed']
        if not user_confirmed:
            sys.stderr.write("Planning阶段禁止修改代码")
            sys.exit(2)  # 强制阻止
```

**为什么需要双重机制？**
- UserPromptSubmit可能因关键词不匹配而失效
- Claude可能自行判断应该进入Implementation
- PreToolUse作为最后防线，强制检查user_confirmed状态

---

### 案例2：专家审查未完成阻止状态转移

**需求**: BUG修复任务必须先完成专家审查

**解决方案**: UserPromptSubmit阻止 + PreToolUse防御

**1. UserPromptSubmit** - 主要检查
```python
if match_keywords(user_input, CONFIRM_KEYWORDS):
    # 检查专家审查
    expert_review_required = task_meta['steps']['planning']['expert_review_required']
    expert_review_completed = task_meta['steps']['planning']['expert_review_completed']

    if expert_review_required and not expert_review_completed:
        return {
            "decision": "block",
            "reason": "专家审查未完成",
            "hookSpecificOutput": {
                "additionalContext": """
❌ 问题: BUG修复任务必须先完成专家审查

✅ 解决方案:
1. 使用Task工具启动专家审查
2. 等待审查结果
3. 重新输入"同意"
"""
            }
        }
```

**2. PreToolUse** - 防御检查
```python
if current_step == 'planning' and tool_name in ['Write', 'Edit']:
    if not user_confirmed:  # 如果审查未完成，user_confirmed必为false
        sys.exit(2)  # 阻止代码修改
```

---

## 🎯 最佳实践

### 1. 使用多层防御

**原则**: 不要依赖单一Hook，使用多层检查

```python
# Layer 1: UserPromptSubmit - 状态转移检查
if user_agrees but preconditions_not_met:
    return {"decision": "block"}

# Layer 2: PreToolUse - 工具调用检查
if tool_is_modification and state_not_ready:
    sys.exit(2)
```

**理由**:
- UserPromptSubmit可能因关键词不匹配而失效
- Claude可能自行判断跳过检查
- 多层防御确保规则强制执行

---

### 2. 清晰的错误消息

**原则**: 告诉Claude为什么被阻止，以及如何正确操作

```python
# ✅ 好的错误消息
denial_message = """
❌ 检测到问题：
你尝试在Planning阶段修改代码，但用户尚未确认方案。

✅ 正确流程：
1. 向用户展示完整方案
2. 等待用户输入"同意"/"认同"/"确认"
3. Hook会自动更新状态
4. 然后你才能修改代码

💡 提示：如果用户已表示认同，请提醒他们明确说"同意"
"""
```

---

### 3. 记录调试信息

**原则**: 使用stderr输出调试信息（仅DEBUG模式）

```python
DEBUG = os.getenv("CLAUDE_HOOK_DEBUG") == "1"

if DEBUG:
    sys.stderr.write(f"[PreToolUse] 当前阶段: {current_step}\n")
    sys.stderr.write(f"[PreToolUse] 工具名称: {tool_name}\n")
    sys.stderr.write(f"[PreToolUse] user_confirmed: {user_confirmed}\n")

# 正式环境只输出关键信息
sys.stderr.write(f"[PreToolUse v24.0] Planning阶段代码修改被拒绝\n")
```

---

### 4. 兼容性检查

**原则**: 优雅处理字段不存在的情况

```python
# ✅ 安全地获取字段
planning_step = meta_data.get('steps', {}).get('planning', {})
user_confirmed = planning_step.get('user_confirmed', False)  # 默认false

# ❌ 危险的访问（可能抛异常）
user_confirmed = meta_data['steps']['planning']['user_confirmed']
```

---

## 📚 参考资料

### 官方文档
- [Claude Code Hooks 官方文档](https://code.claude.com/docs/en/hooks)
- [Hook 规范说明](https://code.claude.com/docs/en/hooks-specification)

### 项目文档
- [Hook状态机功能实现](./docs/developer/Hook状态机功能实现.md)
- [Hook状态机机制](./docs/developer/Hook状态机机制.md)
- [v24.0修复报告](./tests/Hook状态机-v24.0-修复报告.md)

---

## 📝 版本历史

### v4.1 - 补充 updatedInput 详解 (2025-11-19)

**本次更新**:
基于官方文档反馈，补充 `updatedInput` 字段的详细说明

**更新内容**:
1. **字段速查表** - 添加 `updatedInput` 字段说明
2. **PreToolUse 章节** - 新增"updatedInput 字段详解"小节，包括：
   - 字段类型：`Record<string, unknown>`
   - 使用时机：仅在 `"permissionDecision": "allow"` 时有效
   - 作用说明：修改工具参数的对象
   - 完整示例：展示如何修改文件路径和添加新字段

**官方反馈**:
- ✅ 文档整体质量很高，大部分内容与官方文档一致
- ✅ 核心机制描述准确（PreToolUse 阻止机制、UserPromptSubmit 特殊行为、PostToolUse 反馈机制）
- ✅ 补充了官方文档容易忽略的细节（如 exit 2 清除提示）
- ✅ 建议补充 `updatedInput` 的类型说明 - **已完成**

---

### v4.0 - 最终标准版 (2025-11-19)

**文档定位**: 作为 Hook 开发的唯一标准指导文档

**核心内容**:
1. **Hook 类型与阻止机制** - 完整的 Hook 类型对照表和字段速查表
2. **正确用法** - 4种核心 Hook 的标准实现（PreToolUse、UserPromptSubmit、PostToolUse、强制停止）
3. **实战案例** - Planning阶段禁止代码修改、专家审查阻止等真实场景
4. **最佳实践** - 多层防御、清晰错误消息、调试信息、兼容性检查

**关键特性**:
- ✅ 完全对齐 Claude Code 官方文档
- ✅ 补充官方文档容易被忽略的细节（如 UserPromptSubmit 的 stdout 行为、exit 2 清除提示等）
- ✅ 基于 v24.0 实战经验验证所有用法
- ✅ 提供可直接使用的标准实现代码

**技术要点**:
- **PreToolUse**: 唯一能真正阻止工具执行的 Hook，支持 exit 2 和 JSON 两种方式
- **UserPromptSubmit**: 阻止提示处理，exit 2 会清除提示内容
- **PostToolUse**: 工具已执行，`"decision": "block"` 是反馈机制，不能阻止
- **continue: False**: 所有 Hook 的最强阻止机制，立即停止 Claude

**文档质量保证**:
- 所有示例均可直接复制使用
- 所有描述均经过官方文档验证
- 所有最佳实践均基于真实项目经验

---

### v3.0 - 工作指导文档 (2025-11-19)

**重大调整**:
- 删除所有错误示例，只保留正确用法
- 删除"常见错误"章节，简化文档结构
- 增强速查功能，添加字段速查表
- 优化代码示例，突出关键代码

**文档定位**: 从参考文档升级为工作指导文档

---

### v1.0 - 初始版本 (2025-11-19)

**初始内容**:
- PreToolUse 和 UserPromptSubmit 的正确阻止机制
- 基础实战案例和最佳实践
- 基于官方文档的核心用法

---

**文档维护**: 仅记录正确用法和最佳实践，不包含错误示例
**官方文档**: [Claude Code Hooks](https://code.claude.com/docs/en/hooks)
**最后更新**: 2025-11-19 v4.0
