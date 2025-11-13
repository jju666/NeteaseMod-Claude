# Claude Code Hooks 使用指南

> 学习如何通过注册 Shell 命令来自定义和扩展 Claude Code 的行为

Claude Code hooks 是用户自定义的 Shell 命令,可在 Claude Code 生命周期的不同阶段执行。Hooks 提供了对 Claude Code 行为的确定性控制,确保某些操作始终执行,而不是依赖 LLM 自行选择是否运行。

<Tip>
  关于 hooks 的参考文档,请参见 [Hooks 参考文档](/en/hooks)。
</Tip>

Hooks 的典型使用场景包括:

* **通知**: 自定义当 Claude Code 等待您输入或运行权限时的通知方式
* **自动格式化**: 对 .ts 文件运行 `prettier`,对 .go 文件运行 `gofmt` 等
* **日志记录**: 跟踪和统计所有执行的命令,用于合规或调试
* **反馈**: 当 Claude Code 生成的代码不符合代码规范时提供自动反馈
* **自定义权限**: 阻止对生产文件或敏感目录的修改

通过将这些规则编码为 hooks 而非提示指令,您可以将建议转化为应用级代码,确保在预期时机每次都能执行。

<Warning>
  在添加 hooks 时必须考虑安全影响,因为 hooks 会在代理循环中使用您当前环境的凭证自动运行。
  例如,恶意的 hooks 代码可能会窃取您的数据。在注册 hooks 之前,务必审查其实现。

  完整的安全最佳实践,请参见 hooks 参考文档中的[安全注意事项](/en/hooks#security-considerations)。
</Warning>

## Hook 事件概述

Claude Code 提供了多个在工作流不同阶段运行的 hook 事件:

* **PreToolUse**: 在工具调用前运行(可以阻止调用)
* **PostToolUse**: 在工具调用完成后运行
* **UserPromptSubmit**: 在用户提交提示且 Claude 处理前运行
* **Notification**: 在 Claude Code 发送通知时运行
* **Stop**: 在 Claude Code 完成响应时运行
* **SubagentStop**: 在子代理任务完成时运行
* **PreCompact**: 在 Claude Code 即将执行压缩操作前运行
* **SessionStart**: 在 Claude Code 启动新会话或恢复现有会话时运行
* **SessionEnd**: 在 Claude Code 会话结束时运行

每个事件接收不同的数据,并能以不同方式控制 Claude 的行为。

## 快速入门

在本快速入门中,您将添加一个 hook 来记录 Claude Code 运行的 Shell 命令。

### 前置条件

安装 `jq` 用于在命令行中处理 JSON。

### 步骤 1: 打开 hooks 配置

运行 `/hooks` [斜杠命令](/en/slash-commands),并选择 `PreToolUse` hook 事件。

`PreToolUse` hooks 在工具调用前运行,可以阻止调用并向 Claude 提供反馈。

### 步骤 2: 添加匹配器

选择 `+ Add new matcher…` 使您的 hook 仅在 Bash 工具调用时运行。

为匹配器输入 `Bash`。

<Note>您可以使用 `*` 来匹配所有工具。</Note>

### 步骤 3: 添加 hook

选择 `+ Add new hook…` 并输入以下命令:

```bash  theme={null}
jq -r '"\(.tool_input.command) - \(.tool_input.description // "No description")"' >> ~/.claude/bash-command-log.txt
```

### 步骤 4: 保存配置

对于存储位置,选择 `User settings`,因为您要记录到主目录。这样该 hook 将应用于所有项目,而不仅是当前项目。

然后按 Esc 直到返回 REPL。您的 hook 现已注册!

### 步骤 5: 验证您的 hook

再次运行 `/hooks` 或检查 `~/.claude/settings.json` 查看您的配置:

```json  theme={null}
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '\"\\(.tool_input.command) - \\(.tool_input.description // \"No description\")\"' >> ~/.claude/bash-command-log.txt"
          }
        ]
      }
    ]
  }
}
```

### 步骤 6: 测试您的 hook

让 Claude 运行一个简单的命令如 `ls`,然后检查您的日志文件:

```bash  theme={null}
cat ~/.claude/bash-command-log.txt
```

您应该看到类似以下的条目:

```
ls - Lists files and directories
```

## 更多示例

<Note>
  完整的示例实现,请参见我们公共代码库中的 [bash 命令验证器示例](https://github.com/anthropics/claude-code/blob/main/examples/hooks/bash_command_validator_example.py)。
</Note>

### 代码格式化 Hook

编辑后自动格式化 TypeScript 文件:

```json  theme={null}
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.file_path' | { read file_path; if echo \"$file_path\" | grep -q '\\.ts$'; then npx prettier --write \"$file_path\"; fi; }"
          }
        ]
      }
    ]
  }
}
```

### Markdown 格式化 Hook

自动修复 markdown 文件中缺失的语言标签和格式问题:

```json  theme={null}
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/markdown_formatter.py"
          }
        ]
      }
    ]
  }
}
```

创建 `.claude/hooks/markdown_formatter.py` 文件,内容如下:

````python  theme={null}
#!/usr/bin/env python3
"""
Markdown formatter for Claude Code output.
Fixes missing language tags and spacing issues while preserving code content.
"""
import json
import sys
import re
import os

def detect_language(code):
    """Best-effort language detection from code content."""
    s = code.strip()

    # JSON detection
    if re.search(r'^\s*[{\[]', s):
        try:
            json.loads(s)
            return 'json'
        except:
            pass

    # Python detection
    if re.search(r'^\s*def\s+\w+\s*\(', s, re.M) or \
       re.search(r'^\s*(import|from)\s+\w+', s, re.M):
        return 'python'

    # JavaScript detection
    if re.search(r'\b(function\s+\w+\s*\(|const\s+\w+\s*=)', s) or \
       re.search(r'=>|console\.(log|error)', s):
        return 'javascript'

    # Bash detection
    if re.search(r'^#!.*\b(bash|sh)\b', s, re.M) or \
       re.search(r'\b(if|then|fi|for|in|do|done)\b', s):
        return 'bash'

    # SQL detection
    if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE)\s+', s, re.I):
        return 'sql'

    return 'text'

def format_markdown(content):
    """Format markdown content with language detection."""
    # Fix unlabeled code fences
    def add_lang_to_fence(match):
        indent, info, body, closing = match.groups()
        if not info.strip():
            lang = detect_language(body)
            return f"{indent}```{lang}\n{body}{closing}\n"
        return match.group(0)

    fence_pattern = r'(?ms)^([ \t]{0,3})```([^\n]*)\n(.*?)(\n\1```)\s*$'
    content = re.sub(fence_pattern, add_lang_to_fence, content)

    # Fix excessive blank lines (only outside code fences)
    content = re.sub(r'\n{3,}', '\n\n', content)

    return content.rstrip() + '\n'

# Main execution
try:
    input_data = json.load(sys.stdin)
    file_path = input_data.get('tool_input', {}).get('file_path', '')

    if not file_path.endswith(('.md', '.mdx')):
        sys.exit(0)  # Not a markdown file

    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        formatted = format_markdown(content)

        if formatted != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted)
            print(f"✓ Fixed markdown formatting in {file_path}")

except Exception as e:
    print(f"Error formatting markdown: {e}", file=sys.stderr)
    sys.exit(1)
````

使脚本可执行:

```bash  theme={null}
chmod +x .claude/hooks/markdown_formatter.py
```

此 hook 会自动:

* 检测未标记代码块中的编程语言
* 为语法高亮添加适当的语言标签
* 修复过多的空行,同时保留代码内容
* 仅处理 markdown 文件(`.md`, `.mdx`)

### 自定义通知 Hook

当 Claude 需要输入时获取桌面通知:

```json  theme={null}
{
  "hooks": {
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "notify-send 'Claude Code' 'Awaiting your input'"
          }
        ]
      }
    ]
  }
}
```

### 文件保护 Hook

阻止编辑敏感文件:

```json  theme={null}
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -c \"import json, sys; data=json.load(sys.stdin); path=data.get('tool_input',{}).get('file_path',''); sys.exit(2 if any(p in path for p in ['.env', 'package-lock.json', '.git/']) else 0)\""
          }
        ]
      }
    ]
  }
}
```

## 了解更多

* 关于 hooks 的参考文档,请参见 [Hooks 参考文档](/en/hooks)。
* 全面的安全最佳实践和安全指南,请参见 hooks 参考文档中的[安全注意事项](/en/hooks#security-considerations)。
* 故障排除步骤和调试技术,请参见 hooks 参考文档中的[调试](/en/hooks#debugging)部分。

---

_最后更新: 2025-11-13_
