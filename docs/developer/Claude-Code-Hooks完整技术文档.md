# Claude Code Hooks 完整技术文档

> **文档版本**: v1.0
> **最后更新**: 2025-11-12
> **适用版本**: Claude Code v2.0.10+
> **官方文档**: https://docs.anthropic.com/en/docs/claude-code/hooks

---

## 📋 目录

- [第一章：Hooks概述](#第一章hooks概述)
- [第二章：配置方法](#第二章配置方法)
- [第三章：Hook事件详解](#第三章hook事件详解)
- [第四章：环境变量与输入输出](#第四章环境变量与输入输出)
- [第五章：控制流机制](#第五章控制流机制)
- [第六章：实战示例](#第六章实战示例)
- [第七章：最佳实践](#第七章最佳实践)
- [第八章：安全考量](#第八章安全考量)
- [第九章：问题排查](#第九章问题排查)
- [附录：快速参考](#附录快速参考)

---

## 第一章：Hooks概述

### 1.1 什么是Hooks？

**Claude Code Hooks** 是用户定义的Shell命令，在Claude Code生命周期的特定时刻自动执行。它们提供**确定性控制**，确保特定操作始终执行，而非依赖LLM的选择。

**核心特性**：
- ✅ **自动化触发**：在关键时刻自动执行，无需手动干预
- ✅ **确定性行为**：将规则编码为钩子，确保一致执行
- ✅ **双向反馈**：可以向Claude和用户提供反馈
- ✅ **阻塞能力**：可以阻止危险操作或不符合规范的行为

### 1.2 为什么需要Hooks？

**传统方式的问题**：
```markdown
# ❌ 传统提示词方式（不可靠）
"请在每次编辑TypeScript文件后运行Prettier"
→ AI可能忘记执行
→ 行为不一致
→ 依赖AI记忆
```

**Hooks方式的优势**：
```json
// ✅ Hooks方式（确定性）
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Edit|Write",
      "hooks": [{
        "type": "command",
        "command": "prettier --write \"$CLAUDE_FILE_PATHS\""
      }]
    }]
  }
}
→ 每次编辑后自动格式化
→ 100%执行
→ 无需AI记忆
```

### 1.3 Hooks的典型应用场景

| 场景 | 用途 | 示例 |
|------|------|------|
| **代码质量** | 自动格式化、Lint检查 | Prettier、ESLint、Black |
| **自动化测试** | 代码变更后自动运行测试 | Jest、Pytest、Go test |
| **版本控制** | 自动提交、创建分支 | Git commit、Git branch |
| **安全防护** | 阻止危险操作、保护敏感文件 | 阻止`rm -rf`、保护`.env` |
| **通知系统** | 任务完成提醒 | Slack通知、桌面通知 |
| **日志记录** | 追踪所有命令执行 | 命令日志、审计记录 |
| **自定义验证** | 强制规范、权限检查 | 代码规范检查、权限验证 |

### 1.4 发布历史

- **2025-06-30**：Claude Code Hooks正式发布
- **v2.0.10**：PreToolUse hooks支持修改工具输入
- **最新版本**：支持8种Hook事件类型

---

## 第二章：配置方法

### 2.1 配置文件位置

Claude Code支持三个层级的配置文件（优先级从高到低）：

```
1. 本地项目配置（优先级最高，不提交到Git）
   .claude/settings.local.json

2. 项目配置（提交到Git，团队共享）
   .claude/settings.json

3. 用户配置（应用到所有项目）
   ~/.claude/settings.json
```

**配置合并规则**：
- 低优先级配置会被高优先级覆盖
- 同一Hook事件的多个配置会**合并执行**（而非覆盖）

### 2.2 基本配置结构

```json
{
  "hooks": {
    "EventName": [
      {
        "matcher": "ToolPattern",
        "hooks": [
          {
            "type": "command",
            "command": "your-shell-command-here"
          }
        ]
      }
    ]
  }
}
```

**字段说明**：

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `EventName` | string | ✅ | Hook事件名称（如`PreToolUse`、`PostToolUse`等） |
| `matcher` | string | ⚠️ | 工具名称匹配模式（某些事件不需要） |
| `type` | string | ✅ | Hook类型，固定为`"command"` |
| `command` | string | ✅ | 要执行的Shell命令 |

### 2.3 快速配置方法

**方法1：使用`/hooks`命令**（推荐）

```bash
# 在Claude Code中运行
/hooks
```

**交互式配置流程**：
1. 选择Hook事件类型（如`PreToolUse`）
2. 添加匹配器（如`Bash`）
3. 输入Shell命令
4. 选择存储位置（User/Project/Local）
5. 保存配置

**方法2：手动编辑配置文件**

```bash
# 编辑用户配置
vim ~/.claude/settings.json

# 编辑项目配置
vim .claude/settings.json

# 编辑本地配置
vim .claude/settings.local.json
```

**⚠️ 重要提醒**：
- 直接编辑配置文件后，**必须**在Claude Code中运行`/hooks`命令并审查更改，修改才会生效
- 这是安全机制，防止恶意钩子代码在当前会话中生效

### 2.4 Matcher匹配模式

**Matcher**用于指定哪些工具触发Hook。

**支持的匹配模式**：

```json
// 1. 精确匹配单个工具
{"matcher": "Bash"}

// 2. 匹配多个工具（使用正则表达式）
{"matcher": "Edit|Write"}

// 3. 匹配所有工具
{"matcher": "*"}

// 4. 不指定matcher（某些Hook事件）
// UserPromptSubmit、SessionStart等不需要matcher
```

**匹配示例**：

| Matcher | 匹配工具 | 说明 |
|---------|---------|------|
| `"Bash"` | Bash | 精确匹配Bash工具 |
| `"Edit\|Write"` | Edit、Write | 匹配编辑和写入操作 |
| `"Notebook.*"` | Notebook开头的所有工具 | 正则表达式匹配 |
| `"*"` | 所有工具 | 通配符匹配 |
| `""` 或不指定 | 所有工具 | 空字符串等同于`*` |

**⚠️ 注意**：Matcher是**区分大小写**的。

### 2.5 完整配置示例

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "comment": "阻止危险命令",
            "command": "if echo \"$CLAUDE_TOOL_INPUT\" | grep -q 'rm -rf'; then echo '⚠️ 危险命令已阻止' >&2; exit 2; fi"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "comment": "自动格式化TypeScript文件",
            "command": "if [[ \"$CLAUDE_FILE_PATHS\" =~ \\.(ts|tsx)$ ]]; then prettier --write \"$CLAUDE_FILE_PATHS\"; fi"
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "comment": "记录用户提示",
            "command": "echo \"[$(date)] Prompt submitted\" >> ~/.claude/prompt-log.txt"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "comment": "任务完成通知（macOS）",
            "command": "osascript -e 'display notification \"Claude has finished!\" with title \"Claude Code\" sound name \"Glass\"'"
          }
        ]
      }
    ]
  }
}
```

---

## 第三章：Hook事件详解

### 3.1 Hook事件总览

Claude Code支持**8种Hook事件类型**：

| 事件名称 | 触发时机 | 支持Matcher | 可阻塞 | 典型用途 |
|---------|---------|------------|-------|---------|
| **PreToolUse** | 工具调用前 | ✅ | ✅ | 验证、阻止危险操作 |
| **PostToolUse** | 工具成功执行后 | ✅ | ⚠️ 有限 | 格式化、测试、验证 |
| **UserPromptSubmit** | 用户提交提示前 | ❌ | ✅ | 注入上下文、验证提示 |
| **SessionStart** | 会话开始时 | ❌ | ❌ | 加载项目上下文 |
| **SessionEnd** | 会话结束时 | ❌ | ❌ | 清理、保存状态 |
| **Stop** | AI响应结束时 | ❌ | ✅ | 通知、验证完成度 |
| **SubagentStop** | 子代理结束时 | ❌ | ✅ | 子任务验证 |
| **PreCompact** | 上下文压缩前 | ❌ | ❌ | 保存完整记录 |
| **Notification** | 发送通知时 | ⚠️ 通知类型 | ❌ | 自定义通知方式 |

### 3.2 PreToolUse Hook

**触发时机**：在Claude执行任何工具**之前**

**主要用途**：
- ✅ 验证工具输入
- ✅ 阻止危险操作
- ✅ 修改工具输入（v2.0.10+）
- ✅ 强制权限检查

**支持Matcher**：✅ 是

**可阻塞**：✅ 是（通过exit code 2或`"decision": "block"`）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "ask",
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la",
    "description": "List directory contents"
  }
}
```

**输出格式**：

```json
{
  "continue": true,
  "stopReason": "Optional reason when continue is false",
  "suppressOutput": false,
  "systemMessage": "Warning message to user",
  "permissionDecision": "deny",  // "allow" | "deny" | "ask"
  "reason": "Why this decision was made"
}
```

**阻塞机制**：

1. **Exit Code 2**（推荐，简单）：
   ```bash
   if [[ "$CLAUDE_TOOL_INPUT" == *"rm -rf"* ]]; then
     echo "⚠️ 危险命令已阻止" >&2
     exit 2
   fi
   ```

2. **JSON决策字段**（高级，可提供详细原因）：
   ```bash
   echo '{
     "permissionDecision": "deny",
     "reason": "Cannot delete production database. Use staging environment instead."
   }'
   exit 0
   ```

**完整示例**：

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "comment": "阻止危险的Bash命令",
          "command": ".claude/hooks/block-dangerous-commands.sh"
        }
      ]
    },
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "comment": "保护敏感文件",
          "command": "python .claude/hooks/protect-sensitive-files.py"
        }
      ]
    }
  ]
}
```

**Hook脚本示例**（`block-dangerous-commands.sh`）：

```bash
#!/bin/bash

# 读取JSON输入
INPUT=$(cat)

# 提取命令
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 检查危险模式
if [[ "$COMMAND" =~ (rm[[:space:]]+-rf|dd[[:space:]]+if=|:(){) ]]; then
  cat <<EOF >&2
{
  "permissionDecision": "deny",
  "reason": "Dangerous command detected: $COMMAND. This pattern is blocked for safety."
}
EOF
  exit 2
fi

# 允许执行
exit 0
```

### 3.3 PostToolUse Hook

**触发时机**：在工具**成功执行后**立即触发

**主要用途**：
- ✅ 自动格式化代码
- ✅ 运行测试
- ✅ 提供反馈（但不能阻止已执行的操作）
- ✅ 记录日志

**支持Matcher**：✅ 是

**可阻塞**：⚠️ 有限（可以提供反馈，但工具已执行）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "hook_event_name": "PostToolUse",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file.ts",
    "content": "file content"
  },
  "tool_response": {
    "exit_code": 0,
    "stdout": "Success",
    "stderr": ""
  }
}
```

**输出格式**：

```json
{
  "continue": true,
  "stopReason": "Optional reason",
  "suppressOutput": false,
  "systemMessage": "Warning to user",
  "decision": "block",
  "reason": "Why Claude should reconsider"
}
```

**关键差异**：
- `tool_response`包含工具执行结果（exit_code、stdout、stderr）
- 即使返回`"decision": "block"`，工具**已经执行**，无法撤销
- `"decision": "block"`只是向Claude提供反馈，提示重新考虑

**完整示例**：

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "comment": "自动格式化TypeScript",
          "command": "if [[ \"$CLAUDE_FILE_PATHS\" =~ \\.(ts|tsx)$ ]]; then prettier --write \"$CLAUDE_FILE_PATHS\" 2>&1 || echo '⚠️ Prettier failed'; fi"
        }
      ]
    },
    {
      "matcher": "Write",
      "hooks": [
        {
          "type": "command",
          "comment": "TypeScript类型检查",
          "command": "python .claude/hooks/ts-type-check.py"
        }
      ]
    }
  ]
}
```

**Hook脚本示例**（`ts-type-check.py`）：

```python
#!/usr/bin/env python3
import json
import sys
import subprocess
import os

# 读取JSON输入
data = json.load(sys.stdin)

file_path = data.get('tool_input', {}).get('file_path', '')

# 只检查TypeScript文件
if not file_path.endswith(('.ts', '.tsx')):
    sys.exit(0)

# 运行TypeScript编译器检查
result = subprocess.run(
    ['npx', 'tsc', '--noEmit', '--skipLibCheck', file_path],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    # 类型错误，提供反馈
    output = {
        "decision": "block",
        "reason": f"TypeScript type errors detected in {file_path}:\n{result.stdout}\n{result.stderr}"
    }
    print(json.dumps(output))
    sys.exit(0)

# 通过检查
sys.exit(0)
```

### 3.4 UserPromptSubmit Hook

**触发时机**：用户提交提示**之前**，Claude还未开始处理

**主要用途**：
- ✅ 注入项目上下文（如Git diff）
- ✅ 验证提示内容
- ✅ 阻止不合规的提示
- ✅ 记录用户提示日志

**支持Matcher**：❌ 否（不需要）

**可阻塞**：✅ 是（通过`"continue": false`）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "hook_event_name": "UserPromptSubmit",
  "prompt": "Fix the login bug",
  "attachments": []
}
```

**输出格式**：

```json
{
  "continue": true,
  "stopReason": "Prompt blocked",
  "suppressOutput": false,
  "systemMessage": "Warning to user"
}
```

**特殊能力**：
- 如果exit code为0，**stdout内容会被注入**到Claude的上下文中
- 这允许自动添加项目信息，无需用户手动输入

**完整示例**：

```json
{
  "UserPromptSubmit": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "自动注入Git变更上下文",
          "command": ".claude/hooks/inject-git-context.sh"
        },
        {
          "type": "command",
          "comment": "记录用户提示日志",
          "command": "jq -r '.prompt' >> ~/.claude/prompt-history.txt"
        }
      ]
    }
  ]
}
```

**Hook脚本示例**（`inject-git-context.sh`）：

```bash
#!/bin/bash

# 读取输入（可选，这里不使用）
INPUT=$(cat)

# 获取Git状态
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  cat <<EOF
📊 **Git Context**:

**Uncommitted changes:**
\`\`\`
$(git status --short)
\`\`\`

**Recent diff:**
\`\`\`diff
$(git diff HEAD --stat)
\`\`\`
EOF
fi

exit 0
```

### 3.5 SessionStart Hook

**触发时机**：Claude Code会话开始或恢复时

**主要用途**：
- ✅ 加载项目配置
- ✅ 输出欢迎信息
- ✅ 初始化环境
- ✅ 记录会话开始

**支持Matcher**：❌ 否

**可阻塞**：❌ 否（不能阻止会话启动）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "ask",
  "hook_event_name": "SessionStart",
  "source": "startup"  // "startup" | "resume"
}
```

**特殊能力**：
- 如果exit code为0，**stdout内容会被注入**到Claude的上下文中
- 可用于提供项目README、架构说明等初始上下文

**完整示例**：

```json
{
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "加载项目上下文",
          "command": "cat PROJECT_CONTEXT.md 2>/dev/null || echo 'No project context found'"
        }
      ]
    }
  ]
}
```

### 3.6 SessionEnd Hook

**触发时机**：Claude Code会话结束时

**主要用途**：
- ✅ 清理临时文件
- ✅ 保存会话状态
- ✅ 记录会话统计
- ✅ 通知会话结束

**支持Matcher**：❌ 否

**可阻塞**：❌ 否（不能阻止会话结束）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "ask",
  "hook_event_name": "SessionEnd",
  "reason": "user_requested"  // 会话结束原因
}
```

**完整示例**：

```json
{
  "SessionEnd": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "保存会话记录",
          "command": ".claude/hooks/archive-session.sh"
        }
      ]
    }
  ]
}
```

### 3.7 Stop Hook

**触发时机**：Claude完成响应时（包括子代理）

**主要用途**：
- ✅ 发送完成通知
- ✅ 创建任务摘要
- ✅ 验证任务完成度
- ✅ 强制继续未完成任务

**支持Matcher**：❌ 否

**可阻塞**：✅ 是（通过`"decision": "block"`可强制继续）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "hook_event_name": "Stop"
}
```

**输出格式**：

```json
{
  "continue": true,
  "stopReason": "Optional reason",
  "suppressOutput": false,
  "decision": "block",
  "reason": "Task incomplete, continue working"
}
```

**特殊能力**：
- `"decision": "block"`可以**阻止Claude停止**，强制继续工作
- `reason`字段必须提供，告诉Claude如何继续

**完整示例**：

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "验证任务完成度",
          "command": ".claude/hooks/validate-task-completion.py"
        },
        {
          "type": "command",
          "comment": "发送macOS通知",
          "command": "osascript -e 'display notification \"Claude has finished!\" with title \"Claude Code\"'"
        }
      ]
    }
  ]
}
```

**Hook脚本示例**（`validate-task-completion.py`）：

```python
#!/usr/bin/env python3
import json
import sys

# 读取输入
data = json.load(sys.stdin)

# 读取transcript，检查任务是否完成
transcript_path = data.get('transcript_path')

# 示例：检查是否有未解决的TODO
with open(transcript_path, 'r') as f:
    transcript_lines = f.readlines()

last_message = transcript_lines[-1] if transcript_lines else ''

# 如果最后一条消息包含"TODO"或"未完成"，阻止停止
if 'TODO' in last_message or '未完成' in last_message:
    output = {
        "decision": "block",
        "reason": "Task incomplete. There are TODOs remaining. Please complete them before stopping."
    }
    print(json.dumps(output))

sys.exit(0)
```

### 3.8 SubagentStop Hook

**触发时机**：子代理（subagent）完成响应时

**主要用途**：
- ✅ 验证子任务完成度
- ✅ 子任务结果验证
- ✅ 强制子代理继续

**支持Matcher**：❌ 否

**可阻塞**：✅ 是（通过`"decision": "block"`）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "hook_event_name": "SubagentStop",
  "subagent_name": "ReviewAgent"
}
```

**行为**：与`Stop` Hook类似，但专门针对子代理。

### 3.9 PreCompact Hook

**触发时机**：Claude Code准备压缩上下文（compact operation）之前

**主要用途**：
- ✅ 保存完整transcript备份
- ✅ 提取关键信息
- ✅ 记录压缩前状态

**支持Matcher**：❌ 否

**可阻塞**：❌ 否（不能阻止压缩操作）

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "ask",
  "hook_event_name": "PreCompact",
  "trigger": "token_limit",
  "custom_instructions": "..."
}
```

**完整示例**：

```json
{
  "PreCompact": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "备份完整transcript",
          "command": "cp \"$TRANSCRIPT_PATH\" ~/.claude/backups/$(date +%s)-transcript.jsonl"
        }
      ]
    }
  ]
}
```

### 3.10 Notification Hook

**触发时机**：Claude Code发送通知时

**主要用途**：
- ✅ 自定义通知方式（Slack、Email等）
- ✅ 过滤通知类型
- ✅ 记录通知日志

**支持Matcher**：⚠️ 支持通知类型匹配

**可阻塞**：❌ 否

**输入JSON Schema**：

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "hook_event_name": "Notification",
  "notification_type": "info",  // "info" | "warning" | "error"
  "message": "Notification message"
}
```

**完整示例**：

```json
{
  "Notification": [
    {
      "matcher": "error",
      "hooks": [
        {
          "type": "command",
          "comment": "发送错误通知到Slack",
          "command": ".claude/hooks/send-slack-notification.sh"
        }
      ]
    }
  ]
}
```

---

## 第四章：环境变量与输入输出

### 4.1 环境变量

Claude Code会为Hook脚本设置以下环境变量：

| 环境变量 | 说明 | 示例值 | 适用Hook |
|---------|------|--------|---------|
| `$CLAUDE_FILE_PATHS` | 空格分隔的文件路径列表 | `/path/file1.ts /path/file2.ts` | PreToolUse、PostToolUse（文件操作） |
| `$CLAUDE_PROJECT_DIR` | 项目根目录绝对路径 | `/Users/username/project` | 所有Hook |
| `$CLAUDE_CODE_REMOTE` | 是否在远程环境运行 | `"true"` 或空 | 所有Hook |
| `$CLAUDE_TOOL_NAME` | 工具名称 | `"Bash"`, `"Edit"` | PreToolUse、PostToolUse |
| `$CLAUDE_TOOL_INPUT` | 工具输入（简化版） | `"ls -la"` | PreToolUse、PostToolUse |

**使用示例**：

```bash
#!/bin/bash

# 示例1：格式化所有TypeScript文件
if [[ "$CLAUDE_FILE_PATHS" =~ \.tsx?$ ]]; then
  prettier --write $CLAUDE_FILE_PATHS
fi

# 示例2：使用项目根目录
SCRIPT_PATH="$CLAUDE_PROJECT_DIR/.claude/hooks/my-script.sh"
bash "$SCRIPT_PATH"

# 示例3：检查是否在远程环境
if [[ "$CLAUDE_CODE_REMOTE" == "true" ]]; then
  echo "Running in remote environment"
fi

# 示例4：分割文件路径
IFS=' ' read -ra FILES <<< "$CLAUDE_FILE_PATHS"
for file in "${FILES[@]}"; do
  echo "Processing: $file"
done
```

### 4.2 标准输入（stdin）

所有Hook都会通过**stdin**接收完整的JSON对象。

**通用JSON字段**：

```json
{
  "session_id": "abc123-def456",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/current/working/directory",
  "permission_mode": "ask",
  "hook_event_name": "PreToolUse"
}
```

**解析JSON的方法**：

**方法1：使用`jq`（推荐）**

```bash
#!/bin/bash

# 读取并解析JSON
TOOL_NAME=$(jq -r '.tool_name // empty')
COMMAND=$(jq -r '.tool_input.command // empty')
FILE_PATH=$(jq -r '.tool_input.file_path // empty')

echo "Tool: $TOOL_NAME"
echo "Command: $COMMAND"
echo "File: $FILE_PATH"
```

**方法2：使用Python**

```python
#!/usr/bin/env python3
import json
import sys

# 读取JSON输入
data = json.load(sys.stdin)

tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {})
command = tool_input.get('command', '')

print(f"Tool: {tool_name}")
print(f"Command: {command}")
```

**方法3：使用Node.js**

```javascript
#!/usr/bin/env node

const fs = require('fs');

// 读取JSON输入
const input = fs.readFileSync(0, 'utf-8');
const data = JSON.parse(input);

const toolName = data.tool_name || '';
const command = data.tool_input?.command || '';

console.log(`Tool: ${toolName}`);
console.log(`Command: ${command}`);
```

### 4.3 标准输出（stdout）

Hook脚本通过**stdout**返回JSON对象来控制Claude Code的行为。

**通用输出字段**：

```json
{
  "continue": true,
  "stopReason": "Optional reason when continue is false",
  "suppressOutput": false,
  "systemMessage": "Optional warning to user"
}
```

**字段说明**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `continue` | boolean | `true` | 是否继续执行（`false`会立即停止） |
| `stopReason` | string | - | `continue: false`时显示给用户的原因 |
| `suppressOutput` | boolean | `false` | 是否隐藏stdout输出（不显示在transcript中） |
| `systemMessage` | string | - | 警告消息（显示给用户） |

**特定Hook的额外输出字段**：

**PreToolUse**：

```json
{
  "permissionDecision": "deny",  // "allow" | "deny" | "ask"
  "reason": "Why this decision was made"
}
```

**PostToolUse、Stop、SubagentStop**：

```json
{
  "decision": "block",  // "approve" | "block" | undefined
  "reason": "Why Claude should reconsider"
}
```

### 4.4 标准错误（stderr）

**stderr用途**：
- ✅ 输出错误信息
- ✅ 调试日志
- ✅ 提供给Claude的反馈（exit code 2时）

**重要规则**：
- Exit code 0：stderr不会显示给Claude（只记录在日志）
- Exit code 2：stderr会作为反馈发送给Claude
- Exit code 1：stderr显示给用户但不发送给Claude

**示例**：

```bash
#!/bin/bash

# 错误信息（仅记录）
echo "Debug: Processing file $1" >&2

# 阻塞并提供反馈给Claude
if [[ "$COMMAND" == *"rm -rf"* ]]; then
  echo "⚠️ Dangerous command blocked: $COMMAND" >&2
  exit 2
fi

# 非阻塞错误（显示给用户）
if [[ ! -f "$FILE" ]]; then
  echo "❌ File not found: $FILE" >&2
  exit 1
fi

exit 0
```

---

## 第五章：控制流机制

### 5.1 退出码（Exit Codes）

Hook脚本通过退出码控制Claude Code的行为。

**退出码优先级**（从高到低）：

```
1. `"continue": false` （JSON字段）
   └─ 最高优先级，立即停止所有操作

2. `"decision": "block"` （JSON字段）
   └─ Hook特定的阻塞行为

3. Exit Code 2
   └─ 简单的阻塞机制（通过stderr反馈）

4. Exit Code 1
   └─ 非阻塞错误（显示给用户）

5. Exit Code 0
   └─ 成功执行，继续正常流程
```

**详细说明**：

| Exit Code | 行为 | stderr | stdout | 典型用途 |
|-----------|------|--------|--------|---------|
| **0** | 成功，继续 | 不显示给Claude | 部分Hook注入到上下文 | 正常执行 |
| **2** | 阻塞操作 | 发送给Claude作为反馈 | 忽略 | 阻止危险操作 |
| **1** | 非阻塞错误 | 显示给用户 | 忽略 | 警告但不阻止 |
| **其他** | 非阻塞错误 | 显示给用户 | 忽略 | 脚本错误 |

**示例对比**：

```bash
# ✅ 示例1：成功执行（Exit 0）
#!/bin/bash
echo "Processing..."
exit 0
# 结果：继续正常流程

# ⛔ 示例2：阻塞操作（Exit 2）
#!/bin/bash
if [[ "$COMMAND" == *"rm -rf"* ]]; then
  echo "Dangerous command blocked" >&2
  exit 2
fi
# 结果：操作被阻止，stderr反馈给Claude

# ⚠️ 示例3：非阻塞警告（Exit 1）
#!/bin/bash
if [[ ! -f "README.md" ]]; then
  echo "Warning: No README found" >&2
  exit 1
fi
# 结果：警告显示给用户，但操作继续
```

### 5.2 JSON控制字段

**通用控制字段**：

```json
{
  "continue": false,
  "stopReason": "Reason shown to user",
  "suppressOutput": true,
  "systemMessage": "Warning to user"
}
```

**`continue`字段**：
- **最高优先级**的控制字段
- `false`会立即停止当前操作
- `stopReason`会显示给用户

**示例**：

```python
#!/usr/bin/env python3
import json
import sys

# 检查某些条件
if condition_failed:
    output = {
        "continue": False,
        "stopReason": "Critical validation failed. Cannot proceed."
    }
    print(json.dumps(output))
    sys.exit(0)

# 继续执行
sys.exit(0)
```

### 5.3 Hook特定控制字段

#### PreToolUse的`permissionDecision`

```json
{
  "permissionDecision": "deny",  // "allow" | "deny" | "ask"
  "reason": "Detailed reason"
}
```

**行为**：
- `"allow"`：绕过权限系统，直接执行
- `"deny"`：阻止执行，原因发送给Claude
- `"ask"`：触发权限提示（默认行为）

#### PostToolUse/Stop的`decision`

```json
{
  "decision": "block",  // "approve" | "block" | undefined
  "reason": "Why Claude should reconsider"
}
```

**行为**：
- `"approve"`：批准操作（PostToolUse中，工具已执行）
- `"block"`：提供反馈给Claude，提示重新考虑
- `undefined`：正常流程

### 5.4 优先级系统完整示例

**场景**：PreToolUse Hook中同时使用多种控制机制

```python
#!/usr/bin/env python3
import json
import sys

data = json.load(sys.stdin)
command = data.get('tool_input', {}).get('command', '')

# 优先级1：最严重的错误（continue: false）
if 'format_disk' in command:
    output = {
        "continue": False,
        "stopReason": "CRITICAL: Disk format command blocked."
    }
    print(json.dumps(output))
    sys.exit(0)

# 优先级2：阻塞操作（permissionDecision: deny）
if 'rm -rf' in command:
    output = {
        "permissionDecision": "deny",
        "reason": "Dangerous rm -rf command blocked."
    }
    print(json.dumps(output))
    sys.exit(0)

# 优先级3：简单阻塞（exit 2）
if 'dd if=' in command:
    sys.stderr.write("Dangerous dd command blocked\n")
    sys.exit(2)

# 优先级4：非阻塞警告（exit 1）
if 'sudo' in command:
    sys.stderr.write("Warning: Using sudo\n")
    sys.exit(1)

# 允许执行
sys.exit(0)
```

### 5.5 控制流决策树

```
Hook脚本执行
    ↓
检查输出JSON
    ↓
┌─ "continue": false? ─→ 是 ─→ 立即停止，显示stopReason
│
├─ "permissionDecision": "deny"? ─→ 是 ─→ 阻止工具执行，反馈给Claude
│
├─ "decision": "block"? ─→ 是 ─→ 提供反馈给Claude
│
├─ Exit Code 2? ─→ 是 ─→ 阻止操作，stderr反馈给Claude
│
├─ Exit Code 1? ─→ 是 ─→ 警告用户，继续执行
│
└─ Exit Code 0 ─→ 正常继续
```

---

## 第六章：实战示例

### 6.1 代码格式化

**需求**：每次编辑TypeScript文件后自动运行Prettier

**配置**：

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "comment": "Auto-format TypeScript files",
          "command": "if [[ \"$CLAUDE_FILE_PATHS\" =~ \\.(ts|tsx)$ ]]; then prettier --write \"$CLAUDE_FILE_PATHS\" 2>&1; fi"
        }
      ]
    }
  ]
}
```

**进阶版本**（使用脚本）：

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/format-files.sh"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/format-files.sh`）：

```bash
#!/bin/bash

# 读取JSON输入
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 只处理特定文件类型
case "$FILE_PATH" in
  *.ts|*.tsx)
    echo "Formatting TypeScript file: $FILE_PATH" >&2
    prettier --write "$FILE_PATH"
    ;;
  *.py)
    echo "Formatting Python file: $FILE_PATH" >&2
    black "$FILE_PATH"
    ;;
  *.go)
    echo "Formatting Go file: $FILE_PATH" >&2
    gofmt -w "$FILE_PATH"
    ;;
  *.rs)
    echo "Formatting Rust file: $FILE_PATH" >&2
    rustfmt "$FILE_PATH"
    ;;
esac

exit 0
```

### 6.2 自动化测试

**需求**：编辑测试文件后自动运行测试

**配置**：

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "comment": "Auto-run tests",
          "command": ".claude/hooks/run-tests.py"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/run-tests.py`）：

```python
#!/usr/bin/env python3
import json
import sys
import subprocess
import os

# 读取输入
data = json.load(sys.stdin)
file_path = data.get('tool_input', {}).get('file_path', '')

# 只在测试文件修改时运行
if not any(pattern in file_path for pattern in ['test_', '_test.', '.test.', '.spec.']):
    sys.exit(0)

print(f"Running tests for {file_path}...", file=sys.stderr)

# 根据文件类型运行对应测试
if file_path.endswith('.py'):
    result = subprocess.run(['pytest', file_path, '-v'], capture_output=True, text=True)
elif file_path.endswith(('.js', '.ts', '.tsx')):
    result = subprocess.run(['npm', 'test', '--', file_path], capture_output=True, text=True)
elif file_path.endswith('.go'):
    result = subprocess.run(['go', 'test', '-v', file_path], capture_output=True, text=True)
else:
    sys.exit(0)

# 如果测试失败，提供反馈
if result.returncode != 0:
    output = {
        "decision": "block",
        "reason": f"Tests failed for {file_path}:\n{result.stdout}\n{result.stderr}"
    }
    print(json.dumps(output))

sys.exit(0)
```

### 6.3 保护敏感文件

**需求**：阻止修改`.env`、`.git/`等敏感文件

**配置**：

```json
{
  "PreToolUse": [
    {
      "matcher": "Edit|Write|Bash",
      "hooks": [
        {
          "type": "command",
          "comment": "Protect sensitive files",
          "command": ".claude/hooks/protect-sensitive-files.sh"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/protect-sensitive-files.sh`）：

```bash
#!/bin/bash

# 读取JSON输入
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 敏感文件/目录列表
SENSITIVE_PATTERNS=(
  ".env"
  ".env.local"
  ".env.production"
  ".git/"
  "id_rsa"
  "id_ed25519"
  ".ssh/"
  "credentials"
  "secrets"
  ".aws/"
  ".gcp/"
)

# 检查文件路径
for pattern in "${SENSITIVE_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]] || [[ "$COMMAND" == *"$pattern"* ]]; then
    cat <<EOF >&2
{
  "permissionDecision": "deny",
  "reason": "Access to sensitive file/directory blocked: $pattern"
}
EOF
    exit 2
  fi
done

exit 0
```

### 6.4 阻止危险命令

**需求**：阻止`rm -rf`、`dd`等危险Bash命令

**配置**：

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "comment": "Block dangerous commands",
          "command": ".claude/hooks/block-dangerous-commands.sh"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/block-dangerous-commands.sh`）：

```bash
#!/bin/bash

# 读取JSON输入
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 危险命令模式列表
DANGEROUS_PATTERNS=(
  "rm -rf"
  "rm -fr"
  "> /dev/sda"
  "dd if="
  "mkfs."
  "format"
  ":(){:|:&};:"  # Fork bomb
  "chmod -R 777"
  "chown -R"
  "sudo rm"
  "curl.*|.*sh"  # 管道到sh的curl命令
  "wget.*|.*sh"
)

# 检查命令是否包含危险模式
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if [[ "$COMMAND" =~ $pattern ]]; then
    cat <<EOF >&2
{
  "permissionDecision": "deny",
  "reason": "Dangerous command blocked: '$pattern' detected in command: $COMMAND"
}
EOF
    exit 2
  fi
done

exit 0
```

### 6.5 自动Git提交

**需求**：每次文件修改后自动创建Git提交

**配置**：

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "comment": "Auto-commit changes",
          "command": ".claude/hooks/auto-commit.sh"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/auto-commit.sh`）：

```bash
#!/bin/bash

# 读取JSON输入
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')

# 跳过非Git仓库
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  exit 0
fi

# 检查文件是否有变化
if ! git diff --quiet "$FILE_PATH"; then
  # 从transcript提取最后一条用户提示作为commit消息
  COMMIT_MSG=$(tail -n 50 "$TRANSCRIPT_PATH" | jq -r 'select(.type == "user") | .content' | tail -n 1)

  # 如果没有提取到消息，使用默认消息
  if [[ -z "$COMMIT_MSG" ]]; then
    COMMIT_MSG="Auto-commit: Update $FILE_PATH"
  fi

  # 创建提交
  git add "$FILE_PATH"
  git commit -m "$COMMIT_MSG (Claude Code auto-commit)" >/dev/null 2>&1

  echo "Auto-committed: $FILE_PATH" >&2
fi

exit 0
```

### 6.6 通知系统

**需求**：Claude完成任务时发送通知

**配置（macOS）**：

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "Send macOS notification",
          "command": "osascript -e 'display notification \"Claude has finished!\" with title \"Claude Code\" sound name \"Glass\"'"
        }
      ]
    }
  ]
}
```

**配置（Linux）**：

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "Send Linux notification",
          "command": "notify-send 'Claude Code' 'Task completed!' --icon=dialog-information"
        }
      ]
    }
  ]
}
```

**配置（跨平台 + Slack）**：

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": ".claude/hooks/send-notification.sh"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/send-notification.sh`）：

```bash
#!/bin/bash

# 读取JSON输入
INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty')

# 提取最后一条Claude响应作为摘要
SUMMARY=$(tail -n 50 "$TRANSCRIPT_PATH" | jq -r 'select(.type == "assistant") | .content' | tail -n 1 | head -c 200)

# 跨平台通知
if [[ "$OSTYPE" == "darwin"* ]]; then
  # macOS
  osascript -e "display notification \"$SUMMARY\" with title \"Claude Code Finished\""
elif [[ -n "$DISPLAY" ]]; then
  # Linux with GUI
  notify-send "Claude Code" "$SUMMARY"
fi

# 可选：发送Slack通知
if [[ -n "$SLACK_WEBHOOK_URL" ]]; then
  curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"Claude Code finished: $SUMMARY\"}" \
    "$SLACK_WEBHOOK_URL"
fi

exit 0
```

### 6.7 命令日志记录

**需求**：记录所有Bash命令执行日志

**配置**：

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "comment": "Log Bash commands",
          "command": "jq -r '\"[\\(.timestamp // now | todate)] \\(.tool_input.command) - \\(.tool_input.description // \"No description\")\"' >> ~/.claude/bash-command-log.txt"
        }
      ]
    }
  ]
}
```

**进阶版本**（结构化日志）：

```json
{
  "PreToolUse": [
    {
      "matcher": "Bash",
      "hooks": [
        {
          "type": "command",
          "command": ".claude/hooks/log-bash-commands.py"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/log-bash-commands.py`）：

```python
#!/usr/bin/env python3
import json
import sys
from datetime import datetime
import os

# 读取输入
data = json.load(sys.stdin)

# 构造日志条目
log_entry = {
    "timestamp": datetime.now().isoformat(),
    "session_id": data.get('session_id', ''),
    "tool_name": data.get('tool_name', ''),
    "command": data.get('tool_input', {}).get('command', ''),
    "description": data.get('tool_input', {}).get('description', ''),
    "cwd": data.get('cwd', '')
}

# 写入日志文件
log_file = os.path.expanduser('~/.claude/command-log.jsonl')
os.makedirs(os.path.dirname(log_file), exist_ok=True)

with open(log_file, 'a') as f:
    f.write(json.dumps(log_entry) + '\n')

sys.exit(0)
```

### 6.8 TypeScript类型检查

**需求**：编辑TypeScript文件后自动运行类型检查

**配置**：

```json
{
  "PostToolUse": [
    {
      "matcher": "Edit|Write",
      "hooks": [
        {
          "type": "command",
          "comment": "TypeScript type checking",
          "command": ".claude/hooks/ts-type-check.sh"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/ts-type-check.sh`）：

```bash
#!/bin/bash

# 读取JSON输入
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 只检查TypeScript文件
if [[ ! "$FILE_PATH" =~ \.(ts|tsx)$ ]]; then
  exit 0
fi

echo "Running TypeScript type check for $FILE_PATH..." >&2

# 运行TypeScript编译器检查
if ! npx tsc --noEmit --skipLibCheck "$FILE_PATH" 2>&1; then
  # 类型错误，提供反馈
  cat <<EOF
{
  "decision": "block",
  "reason": "TypeScript type errors detected in $FILE_PATH. Please fix type errors before continuing."
}
EOF
fi

exit 0
```

### 6.9 项目上下文注入

**需求**：会话开始时自动加载项目README和Git状态

**配置**：

```json
{
  "SessionStart": [
    {
      "hooks": [
        {
          "type": "command",
          "command": ".claude/hooks/inject-project-context.sh"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/inject-project-context.sh`）：

```bash
#!/bin/bash

# 输出项目上下文（会被注入到Claude的上下文中）
cat <<EOF
# 📊 Project Context

## Project Overview
$(cat README.md 2>/dev/null || echo "No README.md found")

## Git Status
\`\`\`
$(git status --short 2>/dev/null || echo "Not a git repository")
\`\`\`

## Recent Commits
\`\`\`
$(git log --oneline -5 2>/dev/null || echo "No git history")
\`\`\`

## Uncommitted Changes
\`\`\`diff
$(git diff HEAD --stat 2>/dev/null || echo "No changes")
\`\`\`
EOF

exit 0
```

### 6.10 任务完成度验证

**需求**：阻止Claude在任务未完成时停止

**配置**：

```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "comment": "Validate task completion",
          "command": ".claude/hooks/validate-task-completion.py"
        }
      ]
    }
  ]
}
```

**Hook脚本**（`.claude/hooks/validate-task-completion.py`）：

```python
#!/usr/bin/env python3
import json
import sys

# 读取输入
data = json.load(sys.stdin)
transcript_path = data.get('transcript_path', '')

# 读取transcript
with open(transcript_path, 'r') as f:
    lines = f.readlines()

# 检查最后几条消息
last_messages = [json.loads(line) for line in lines[-10:] if line.strip()]

# 检查是否有未完成的TODO或警告
incomplete_indicators = ['TODO', '未完成', '待完成', 'FIXME', '⚠️']

for msg in last_messages:
    content = msg.get('content', '')

    for indicator in incomplete_indicators:
        if indicator in content:
            # 任务未完成，阻止停止
            output = {
                "decision": "block",
                "reason": f"Task incomplete. Found '{indicator}' in recent messages. Please complete all tasks before stopping."
            }
            print(json.dumps(output))
            sys.exit(0)

# 任务完成，允许停止
sys.exit(0)
```

---

## 第七章：最佳实践

### 7.1 Hook脚本开发规范

#### 7.1.1 使用Shell脚本（推荐）

**优点**：
- ✅ 简单快速
- ✅ 无需额外依赖
- ✅ 适合大多数场景

**示例**：

```bash
#!/bin/bash
set -euo pipefail  # 严格模式

# 读取输入
INPUT=$(cat)

# 解析JSON
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')

# 业务逻辑
if [[ "$TOOL_NAME" == "Bash" ]]; then
  echo "Processing Bash command" >&2
fi

exit 0
```

#### 7.1.2 使用Python（复杂逻辑）

**优点**：
- ✅ 强大的标准库
- ✅ 易于处理复杂JSON
- ✅ 适合复杂逻辑

**示例**：

```python
#!/usr/bin/env python3
import json
import sys
import os

def main():
    # 读取输入
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        sys.exit(1)

    # 业务逻辑
    tool_name = data.get('tool_name', '')

    if tool_name == 'Bash':
        print("Processing Bash command", file=sys.stderr)

    sys.exit(0)

if __name__ == '__main__':
    main()
```

#### 7.1.3 使用UV单文件脚本（现代推荐）

**优点**：
- ✅ 声明依赖在脚本顶部
- ✅ 自动管理虚拟环境
- ✅ 无需手动安装依赖

**示例**：

```python
#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = [
#   "requests",
#   "anthropic"
# ]
# ///

import json
import sys
import requests

def main():
    data = json.load(sys.stdin)

    # 使用第三方库
    response = requests.get('https://api.example.com/data')

    sys.exit(0)

if __name__ == '__main__':
    main()
```

### 7.2 错误处理最佳实践

#### 7.2.1 Graceful Failure（优雅失败）

**原则**：非关键Hook应该fail-open，避免中断工作流

```bash
#!/bin/bash

# ✅ 优雅失败示例
if ! command -v prettier &> /dev/null; then
  echo "⚠️ prettier not found, skipping formatting" >&2
  exit 0  # 继续执行，不阻塞
fi

prettier --write "$CLAUDE_FILE_PATHS" || {
  echo "⚠️ prettier failed, but continuing" >&2
  exit 0  # 即使失败也不阻塞
}
```

#### 7.2.2 明确的错误消息

```python
#!/usr/bin/env python3
import json
import sys

def validate_file(file_path):
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"

    if not file_path.endswith('.py'):
        return False, f"Expected Python file, got: {file_path}"

    return True, None

# ...

if not valid:
    output = {
        "permissionDecision": "deny",
        "reason": f"Validation failed: {error_msg}"
    }
    print(json.dumps(output))
    sys.exit(0)
```

#### 7.2.3 Try-Catch包裹

```python
#!/usr/bin/env python3
import json
import sys

def main():
    try:
        data = json.load(sys.stdin)

        # 业务逻辑
        process_data(data)

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
```

### 7.3 性能优化

#### 7.3.1 智能分发（避免不必要的执行）

```bash
#!/bin/bash

# 读取输入
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 快速退出：只处理TypeScript文件
if [[ ! "$FILE_PATH" =~ \.(ts|tsx)$ ]]; then
  exit 0
fi

# 继续处理...
```

#### 7.3.2 并行执行独立检查

```bash
#!/bin/bash

# 并行执行多个检查
check_linting &
PID1=$!

check_formatting &
PID2=$!

check_tests &
PID3=$!

# 等待所有检查完成
wait $PID1 $PID2 $PID3
```

#### 7.3.3 缓存结果（避免重复计算）

```python
#!/usr/bin/env python3
import json
import sys
import hashlib
import os

CACHE_DIR = os.path.expanduser('~/.claude/cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def get_file_hash(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def check_cached_result(file_path):
    file_hash = get_file_hash(file_path)
    cache_file = os.path.join(CACHE_DIR, f"{file_hash}.json")

    if os.path.exists(cache_file):
        # 使用缓存结果
        with open(cache_file, 'r') as f:
            return json.load(f)

    return None

# ...
```

### 7.4 调试技巧

#### 7.4.1 启用调试日志

```bash
#!/bin/bash

DEBUG=1  # 设置调试模式

log_debug() {
  if [[ "$DEBUG" == "1" ]]; then
    echo "[DEBUG] $1" >&2
  fi
}

log_debug "Input JSON: $INPUT"
log_debug "Tool name: $TOOL_NAME"
```

#### 7.4.2 保存输入输出快照

```bash
#!/bin/bash

# 保存输入快照（用于调试）
INPUT=$(cat)
SNAPSHOT_DIR="$HOME/.claude/debug"
mkdir -p "$SNAPSHOT_DIR"

echo "$INPUT" > "$SNAPSHOT_DIR/$(date +%s)-input.json"

# 处理逻辑...
```

#### 7.4.3 使用--mcp-debug模式

```bash
# 启动Claude Code时启用调试
CLAUDE_DEBUG=1 claude

# 或使用MCP调试
claude --mcp-debug
```

### 7.5 可维护性建议

#### 7.5.1 单一职责原则

```
❌ 错误：一个Hook做所有事情
.claude/hooks/mega-hook.sh (2000+ lines)

✅ 正确：每个Hook专注一件事
.claude/hooks/format-code.sh (50 lines)
.claude/hooks/run-tests.sh (80 lines)
.claude/hooks/check-security.sh (100 lines)
```

#### 7.5.2 配置外置化

```bash
#!/bin/bash

# ✅ 配置文件外置
CONFIG_FILE=".claude/hooks/config.json"
SENSITIVE_PATTERNS=$(jq -r '.sensitive_patterns[]' "$CONFIG_FILE")

# ❌ 硬编码配置
SENSITIVE_PATTERNS=(".env" ".git/" "id_rsa")
```

#### 7.5.3 文档注释

```bash
#!/bin/bash
# Hook: Block Dangerous Commands
# Author: Your Name
# Created: 2025-11-12
# Description: Prevents execution of dangerous Bash commands like rm -rf
# Exit Codes:
#   0 - Success, command allowed
#   2 - Command blocked

# 业务逻辑...
```

### 7.6 团队协作建议

#### 7.6.1 项目级Hooks（团队共享）

```
.claude/settings.json          # 提交到Git，团队共享
.claude/settings.local.json    # 添加到.gitignore，个人定制
```

#### 7.6.2 Hooks文档化

在项目README中说明Hooks用途：

```markdown
## Claude Code Hooks

本项目使用以下Hooks：

### PreToolUse Hooks
- `protect-sensitive-files.sh` - 阻止修改敏感文件
- `block-dangerous-commands.sh` - 阻止危险Bash命令

### PostToolUse Hooks
- `format-code.sh` - 自动格式化代码
- `run-tests.sh` - 自动运行测试

## 自定义配置

如需个人定制，请编辑 `.claude/settings.local.json`（不要提交到Git）。
```

#### 7.6.3 版本管理

```bash
# .claude/hooks/version.txt
v1.0.0

# .claude/hooks/CHANGELOG.md
## v1.0.0 (2025-11-12)
- Added: protect-sensitive-files hook
- Added: auto-format hook
```

---

## 第八章：安全考量

### 8.1 安全警告

**⚠️ 极其重要**：

Claude Code Hooks执行任意Shell命令，具有与您的用户账户相同的权限。**使用Hooks即表示您同意以下风险**：

1. **Hooks可以访问、修改或删除任何您有权限的文件**
2. **恶意或编写不当的Hooks可能导致数据丢失或系统损坏**
3. **Hooks在代理循环期间使用您的当前环境凭据自动运行**
4. **恶意Hooks代码可以窃取您的数据**
5. **Anthropic不对Hooks造成的任何损害承担责任**

**安全责任**：
- ✅ **您**负责审查所有Hook脚本
- ✅ **您**负责测试Hooks的安全性
- ✅ **您**负责Hook造成的任何后果

### 8.2 安全最佳实践

#### 8.2.1 最小权限原则

```bash
#!/bin/bash

# ✅ 好：只读取必要文件
if [[ -f ".env" ]]; then
  echo "Sensitive file exists" >&2
  exit 2
fi

# ❌ 坏：尝试读取敏感内容
cat .env > /tmp/stolen-secrets.txt
```

#### 8.2.2 输入验证和清理

```bash
#!/bin/bash

# ✅ 好：验证和清理输入
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# 检查路径遍历攻击
if [[ "$FILE_PATH" == *".."* ]]; then
  echo "Path traversal detected" >&2
  exit 2
fi

# 检查绝对路径
if [[ "$FILE_PATH" != /* ]]; then
  echo "Relative path not allowed" >&2
  exit 2
fi
```

#### 8.2.3 引用所有变量

```bash
# ✅ 好：正确引用变量
prettier --write "$CLAUDE_FILE_PATHS"

# ❌ 坏：未引用变量（可能被注入）
prettier --write $CLAUDE_FILE_PATHS
```

#### 8.2.4 使用绝对路径

```bash
#!/bin/bash

# ✅ 好：使用绝对路径
HOOK_SCRIPT="$CLAUDE_PROJECT_DIR/.claude/hooks/my-script.sh"
bash "$HOOK_SCRIPT"

# ❌ 坏：相对路径（可能被劫持）
bash .claude/hooks/my-script.sh
```

#### 8.2.5 跳过敏感文件

```bash
#!/bin/bash

# 敏感文件列表
SENSITIVE_FILES=(
  ".env"
  ".env.local"
  ".env.production"
  ".git/"
  ".ssh/"
  "id_rsa"
  "id_ed25519"
  "credentials.json"
  "secrets.yml"
  ".aws/credentials"
  ".gcp/credentials.json"
)

# 检查并跳过
for pattern in "${SENSITIVE_FILES[@]}"; do
  if [[ "$FILE_PATH" == *"$pattern"* ]]; then
    exit 0  # 直接退出，不处理
  fi
done
```

### 8.3 审查Hooks配置的安全机制

Claude Code提供了一个安全机制：**直接编辑配置文件的Hooks修改不会立即生效**。

**流程**：
1. 手动编辑`.claude/settings.json`
2. 运行`/hooks`命令
3. **Claude Code要求审查所有变更**
4. 用户批准后，修改才会生效

**目的**：防止恶意Hook代码在当前会话中自动生效。

### 8.4 安全审查清单

在启用新Hook前，检查以下项：

- [ ] Hook脚本是否来自可信来源？
- [ ] 是否审查了完整的Hook代码？
- [ ] 是否使用了绝对路径？
- [ ] 是否正确引用了所有变量？
- [ ] 是否验证和清理了用户输入？
- [ ] 是否跳过了敏感文件/目录？
- [ ] 是否遵循最小权限原则？
- [ ] 是否在安全环境中测试过？
- [ ] 是否编写了错误处理逻辑？
- [ ] 是否记录了Hook的行为？

### 8.5 推荐的安全配置

**最安全的配置**（适合敏感项目）：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "comment": "Block all sensitive file access",
            "command": ".claude/hooks/security-guard.sh"
          }
        ]
      }
    ]
  }
}
```

**安全守卫脚本**（`.claude/hooks/security-guard.sh`）：

```bash
#!/bin/bash
set -euo pipefail

# 读取输入
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty')
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# 白名单：允许的目录
ALLOWED_DIRS=(
  "src/"
  "tests/"
  "docs/"
  ".claude/hooks/"
)

# 检查是否在白名单内
ALLOWED=0
for dir in "${ALLOWED_DIRS[@]}"; do
  if [[ "$FILE_PATH" == *"$dir"* ]]; then
    ALLOWED=1
    break
  fi
done

if [[ "$ALLOWED" == "0" ]]; then
  cat <<EOF >&2
{
  "permissionDecision": "deny",
  "reason": "Access denied: $FILE_PATH is not in allowed directories. Allowed: ${ALLOWED_DIRS[*]}"
}
EOF
  exit 2
fi

# 检查危险命令模式
DANGEROUS_PATTERNS=(
  "rm -rf"
  "dd if="
  "> /dev/"
  "chmod 777"
  "curl.*|.*sh"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if [[ "$COMMAND" =~ $pattern ]]; then
    cat <<EOF >&2
{
  "permissionDecision": "deny",
  "reason": "Dangerous pattern blocked: $pattern"
}
EOF
    exit 2
  fi
done

exit 0
```

---

## 第九章：问题排查

### 9.1 常见问题

#### 问题1：Hooks不执行

**症状**：配置了Hook但从未触发

**排查步骤**：

1. **检查配置文件语法**

```bash
# 验证JSON语法
cat .claude/settings.json | python -m json.tool

# 或使用jq
jq . .claude/settings.json
```

2. **检查matcher是否正确**

```json
// ❌ 错误：matcher拼写错误
{"matcher": "edt"}  // 应该是 "Edit"

// ✅ 正确
{"matcher": "Edit"}
```

3. **检查Hook脚本权限**

```bash
# 确保脚本可执行
chmod +x .claude/hooks/my-hook.sh

# 检查权限
ls -la .claude/hooks/
```

4. **运行`/hooks`命令审查配置**

```bash
# 在Claude Code中运行
/hooks

# 审查所有Hook配置
```

#### 问题2：Hook脚本权限错误

**症状**：`Permission denied`错误

**解决方案**：

```bash
# 添加执行权限
chmod +x .claude/hooks/*.sh

# 或使用Python解释器
#!/usr/bin/env python3
```

#### 问题3：环境变量未设置

**症状**：`$CLAUDE_FILE_PATHS`为空

**原因**：某些Hook事件不设置特定环境变量

**解决方案**：从stdin读取JSON

```bash
#!/bin/bash

# ❌ 依赖环境变量（可能为空）
echo "$CLAUDE_FILE_PATHS"

# ✅ 从JSON读取（可靠）
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
```

#### 问题4：Exit Code不生效

**症状**：返回exit code 2但操作未阻塞

**排查步骤**：

1. 检查stderr输出

```bash
# 确保错误信息输出到stderr
echo "Error message" >&2
exit 2
```

2. 检查Hook类型是否支持阻塞

```
PreToolUse: ✅ 支持阻塞
PostToolUse: ⚠️ 有限支持（工具已执行）
SessionStart/SessionEnd: ❌ 不支持阻塞
```

#### 问题5：JSON输出格式错误

**症状**：Hook返回的JSON无效

**解决方案**：

```bash
# ✅ 使用Here Document
cat <<EOF
{
  "permissionDecision": "deny",
  "reason": "Access denied"
}
EOF

# ❌ 手动拼接（容易出错）
echo "{\"permissionDecision\": \"deny\"}"
```

#### 问题6：Hook执行超时

**症状**：Hook执行时间过长

**解决方案**：

```bash
# 添加超时限制
timeout 5s my-expensive-command || {
  echo "Command timed out" >&2
  exit 1
}

# 或使用异步处理
my-long-command &
```

### 9.2 调试技巧

#### 9.2.1 启用详细日志

```bash
# 启动Claude Code时启用调试
CLAUDE_DEBUG=1 claude

# 或使用verbose模式
claude --verbose
```

#### 9.2.2 保存Hook输入/输出

```bash
#!/bin/bash

# 保存输入
INPUT=$(cat)
echo "$INPUT" > /tmp/hook-input-$(date +%s).json

# 保存输出
OUTPUT='{"continue": true}'
echo "$OUTPUT" | tee /tmp/hook-output-$(date +%s).json
```

#### 9.2.3 使用Debug Hook

```json
{
  "PreToolUse": [
    {
      "matcher": "*",
      "hooks": [
        {
          "type": "command",
          "comment": "Debug: Log all tool calls",
          "command": "cat >> /tmp/claude-debug.log"
        }
      ]
    }
  ]
}
```

#### 9.2.4 手动测试Hook脚本

```bash
# 创建测试输入
cat > /tmp/test-input.json <<EOF
{
  "session_id": "test123",
  "tool_name": "Bash",
  "tool_input": {
    "command": "ls -la"
  }
}
EOF

# 手动执行Hook
cat /tmp/test-input.json | .claude/hooks/my-hook.sh
echo "Exit code: $?"
```

### 9.3 性能问题排查

#### 问题：Hooks导致Claude Code变慢

**排查步骤**：

1. **测量Hook执行时间**

```bash
#!/bin/bash

# 记录开始时间
START_TIME=$(date +%s%N)

# Hook逻辑
# ...

# 记录结束时间
END_TIME=$(date +%s%N)
DURATION=$(( ($END_TIME - $START_TIME) / 1000000 ))

echo "Hook execution time: ${DURATION}ms" >&2
```

2. **识别慢Hook**

```bash
# 查看Hook日志
grep "execution time" ~/.claude/logs/*.log | sort -t: -k2 -n
```

3. **优化策略**

- 使用缓存
- 并行执行
- 快速退出（提前判断）
- 异步处理

### 9.4 获取帮助

如果问题仍未解决：

1. **查阅官方文档**
   - Hooks参考：https://docs.anthropic.com/en/docs/claude-code/hooks
   - 快速入门：https://docs.claude.com/en/docs/claude-code/hooks-guide

2. **查看示例仓库**
   - https://github.com/disler/claude-code-hooks-mastery

3. **提交Issue**
   - https://github.com/anthropics/claude-code/issues

4. **社区讨论**
   - Claude Code Discord
   - Reddit /r/ClaudeCode

---

## 附录：快速参考

### A. Hook事件速查表

| 事件名称 | 触发时机 | Matcher | 阻塞 | 注入上下文 |
|---------|---------|---------|------|-----------|
| PreToolUse | 工具调用前 | ✅ | ✅ | ❌ |
| PostToolUse | 工具执行后 | ✅ | ⚠️ | ❌ |
| UserPromptSubmit | 提示提交前 | ❌ | ✅ | ✅ |
| SessionStart | 会话开始 | ❌ | ❌ | ✅ |
| SessionEnd | 会话结束 | ❌ | ❌ | ❌ |
| Stop | AI响应结束 | ❌ | ✅ | ❌ |
| SubagentStop | 子代理结束 | ❌ | ✅ | ❌ |
| PreCompact | 上下文压缩前 | ❌ | ❌ | ❌ |
| Notification | 发送通知 | ⚠️ 类型 | ❌ | ❌ |

### B. 退出码速查表

| Exit Code | 行为 | stderr → Claude | stdout → 上下文 | 典型用途 |
|-----------|------|----------------|----------------|---------|
| 0 | 成功 | ❌ | 部分Hook ✅ | 正常执行 |
| 2 | 阻塞 | ✅ | ❌ | 阻止危险操作 |
| 1 | 非阻塞错误 | ❌ | ❌ | 警告但不阻止 |
| 其他 | 非阻塞错误 | ❌ | ❌ | 脚本错误 |

### C. 环境变量速查表

| 环境变量 | 说明 | 示例值 |
|---------|------|--------|
| `$CLAUDE_FILE_PATHS` | 空格分隔的文件路径 | `/path/file1.ts /path/file2.ts` |
| `$CLAUDE_PROJECT_DIR` | 项目根目录 | `/Users/username/project` |
| `$CLAUDE_CODE_REMOTE` | 是否远程环境 | `"true"` 或空 |
| `$CLAUDE_TOOL_NAME` | 工具名称 | `"Bash"`, `"Edit"` |
| `$CLAUDE_TOOL_INPUT` | 工具输入（简化） | `"ls -la"` |

### D. JSON字段速查表

**通用字段**：

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `continue` | boolean | `true` | 是否继续执行 |
| `stopReason` | string | - | 停止原因（显示给用户） |
| `suppressOutput` | boolean | `false` | 隐藏stdout输出 |
| `systemMessage` | string | - | 警告消息（显示给用户） |

**PreToolUse特定**：

| 字段 | 类型 | 值 | 说明 |
|------|------|------|------|
| `permissionDecision` | string | `"allow"` \| `"deny"` \| `"ask"` | 权限决策 |
| `reason` | string | - | 决策原因 |

**PostToolUse/Stop特定**：

| 字段 | 类型 | 值 | 说明 |
|------|------|------|------|
| `decision` | string | `"approve"` \| `"block"` | Hook决策 |
| `reason` | string | - | 决策原因 |

### E. 常用命令速查

```bash
# 配置Hooks
/hooks

# 启用调试模式
CLAUDE_DEBUG=1 claude

# 禁用Hooks运行
claude --no-hooks

# 验证JSON配置
jq . .claude/settings.json

# 测试Hook脚本
cat test-input.json | .claude/hooks/my-hook.sh

# 添加执行权限
chmod +x .claude/hooks/*.sh

# 查看Hook日志
tail -f ~/.claude/logs/hooks.log
```

### F. 模板示例

**最小Hook配置**：

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Hook executed' >&2"
          }
        ]
      }
    ]
  }
}
```

**最小Hook脚本**：

```bash
#!/bin/bash
# 读取输入
INPUT=$(cat)

# 业务逻辑
echo "Processing..." >&2

# 成功退出
exit 0
```

**阻塞示例**：

```bash
#!/bin/bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ "$COMMAND" == *"rm -rf"* ]]; then
  echo "Dangerous command blocked" >&2
  exit 2
fi

exit 0
```

---

## 总结

Claude Code Hooks是一个强大的自动化系统，通过将规则编码为确定性的Shell命令，确保特定操作始终执行。

**核心要点**：
- ✅ Hooks在关键时刻自动触发，无需依赖AI记忆
- ✅ 8种Hook事件覆盖完整生命周期
- ✅ 通过exit code和JSON字段精确控制行为
- ✅ 支持阻塞危险操作、自动化工作流、通知系统等
- ⚠️ 必须注意安全性，审查所有Hook脚本

**最佳实践**：
- 从简单Hook开始，逐步增加复杂度
- 遵循最小权限原则
- 编写完善的错误处理
- 优化性能，避免阻塞工作流
- 在安全环境中测试

**参考资源**：
- 官方文档：https://docs.anthropic.com/en/docs/claude-code/hooks
- 示例仓库：https://github.com/disler/claude-code-hooks-mastery
- 社区：Claude Code Discord

---

**文档结束**
