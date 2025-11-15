# Claude Code CLI Reference - Complete Content

## CLI Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `claude` | Start interactive REPL | `claude` |
| `claude "query"` | Start REPL with initial prompt | `claude "explain this project"` |
| `claude -p "query"` | Query via SDK, then exit | `claude -p "explain this function"` |
| `cat file \| claude -p "query"` | Process piped content | `cat logs.txt \| claude -p "explain"` |
| `claude -c` | Continue recent conversation | `claude -c` |
| `claude -c -p "query"` | Continue via SDK | `claude -c -p "Check for type errors"` |
| `claude -r "<session-id>" "query"` | Restore session by ID | `claude -r "abc123" "Finish this PR"` |
| `claude update` | Update to latest version | `claude update` |
| `claude mcp` | Configure Model Context Protocol servers | See Claude Code MCP docs |

## CLI Flags

| Flag | Description | Example |
| :--- | :--- | :--- |
| `--add-dir` | Add additional working directories | `claude --add-dir ../apps ../lib` |
| `--agents` | Dynamically define custom sub-agents via JSON | `claude --agents '{"reviewer":{"description":"Reviews code","prompt":"You are a code reviewer"}}'` |
| `--allowedTools` | List of tools allowed without prompting | `"Bash(git log:*)" "Bash(git diff:*)" "Read"` |
| `--disallowedTools` | List of prohibited tools | `"Bash(git log:*)" "Bash(git diff:*)" "Edit"` |
| `--print`, `-p` | Print response without entering interactive mode | `claude -p "query"` |
| `--system-prompt` | Replace entire default system prompt | `claude --system-prompt "You are a Python expert"` |
| `--system-prompt-file` | Load system prompt from file (print mode only) | `claude -p --system-prompt-file ./custom-prompt.txt "query"` |
| `--append-system-prompt` | Append custom text to default prompt | `claude --append-system-prompt "Always use TypeScript"` |
| `--output-format` | Specify output format: `text`, `json`, `stream-json` | `claude -p "query" --output-format json` |
| `--input-format` | Specify input format: `text`, `stream-json` | `claude -p --output-format json --input-format stream-json` |
| `--include-partial-messages` | Include partial stream events in output | `claude -p --output-format stream-json --include-partial-messages "query"` |
| `--verbose` | Enable detailed logging | `claude --verbose` |
| `--max-turns` | Limit agent turns in non-interactive mode | `claude -p --max-turns 3 "query"` |
| `--model` | Set model for session | `claude --model claude-sonnet-4-5-20250929` |
| `--permission-mode` | Start with specified permission mode | `claude --permission-mode plan` |
| `--permission-prompt-tool` | Specify MCP tool for permission handling | `claude -p --permission-prompt-tool mcp_auth_tool "query"` |
| `--resume` | Resume specific session by ID | `claude --resume abc123 "query"` |
| `--continue` | Load most recent conversation | `claude --continue` |
| `--dangerously-skip-permissions` | Skip permission prompts (use cautiously) | `claude --dangerously-skip-permissions` |

> Tip: "The `--output-format json` flag is particularly useful for scripts and automation, allowing programmatic parsing of responses."

### Sub-Agent Flag Format

The `--agents` flag accepts JSON defining one or more custom sub-agents. Required fields per agent:

| Field | Required | Description |
| :--- | :--- | :--- |
| `description` | Yes | Natural language description of when to invoke |
| `prompt` | Yes | System prompt guiding agent behavior |
| `tools` | No | Specific tools array (e.g. `["Read", "Edit", "Bash"]`) |
| `model` | No | Model alias: `sonnet`, `opus`, or `haiku` |

Example:
```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer. Focus on code quality, security, and best practices.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  },
  "debugger": {
    "description": "Debugging specialist for errors and test failures.",
    "prompt": "You are an expert debugger. Analyze errors, identify root causes, and provide fixes."
  }
}'
```

### System Prompt Flags

Three flags customize system prompts with different purposes:

| Flag | Behavior | Modes | Use Case |
| :--- | :--- | :--- | :--- |
| `--system-prompt` | Replace entire prompt | Interactive + Print | Complete control over Claude's behavior |
| `--system-prompt-file` | Replace with file content | Print only | Load from file for reproducibility |
| `--append-system-prompt` | Append to default prompt | Interactive + Print | Add instructions while maintaining defaults |

**When to use each:**

* `--system-prompt`: For complete control, removing all default Claude Code instructions
  ```bash
  claude --system-prompt "You are a Python expert who only writes type-annotated code"
  ```

* `--system-prompt-file`: For loading custom prompts from files, useful for team consistency
  ```bash
  claude -p --system-prompt-file ./prompts/code-review.txt "Review this PR"
  ```

* `--append-system-prompt`: For adding specific instructions while preserving defaults (recommended)
  ```bash
  claude --append-system-prompt "Always use TypeScript and include JSDoc comments"
  ```

> Note: `--system-prompt` and `--system-prompt-file` are mutually exclusive.

> Tip: "For most use cases, `--append-system-prompt` is recommended, as it retains Claude Code's built-in functionality while adding custom requirements."

## See Also

* Interactive mode - keyboard shortcuts, input modes, interactive features
* Slash commands - session commands
* Quickstart guide - getting started with Claude Code
* Common workflows - advanced patterns
* Settings - configuration options
* SDK documentation - programmatic use and integration
