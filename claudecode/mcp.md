# Complete Text Content Extraction: Claude Code MCP Integration Guide

## Main Heading
通过 MCP 将 Claude Code 连接到工具

## Subheading
了解如何使用 Model Context Protocol 将 Claude Code 连接到您的工具。

## Introduction Section

Claude Code can connect to hundreds of external tools and data sources through the Model Context Protocol (MCP), described as "an open source standard for AI tool integration." MCP servers provide Claude Code access to tools, databases, and APIs.

## What You Can Do With MCP

After connecting MCP servers, users can request Claude Code to:

* Implement features from issue trackers: "添加 JIRA 问题 ENG-4521 中描述的功能,并在 GitHub 上创建 PR。"
* Analyze monitoring data: "检查 Sentry 和 Statsig 以检查 ENG-4521 中描述的功能的使用情况。"
* Query databases: "根据我们的 Postgres 数据库,查找使用功能 ENG-4521 的 10 个随机用户的电子邮件。"
* Integrate designs: "根据在 Slack 中发布的新 Figma 设计更新我们的标准电子邮件模板"
* Automate workflows: "创建 Gmail 草稿,邀请这 10 个用户参加关于新功能的反馈会议。"

## Popular MCP Servers

A comprehensive table lists available servers with categories:

**Development & Testing Tools**: Sentry, Socket, Hugging Face, Jam
**Project Management & Documentation**: Asana, Atlassian, ClickUp, Intercom, Linear, Notion, Fireflies, Monday, Box
**Databases & Data Management**: Airtable, HubSpot, Daloopa
**Payments & Commerce**: PayPal, Plaid, Square, Stripe
**Design & Media**: Figma, Cloudinary, invideo, Canva
**Infrastructure & DevOps**: Cloudflare, Netlify, Stytch, Vercel
**Automation & Integration**: Workato, Zapier

**Warning**: "使用第三方 MCP 服务器需自担风险 - Anthropic 尚未验证所有这些服务器的正确性或安全性。确保您信任要安装的 MCP 服务器。"

## Installing MCP Servers

### Option 1: Remote HTTP Servers

Basic syntax:
```
claude mcp add --transport http <name> <url>
```

Example for Notion:
```
claude mcp add --transport http notion https://mcp.notion.com/mcp
```

With Bearer token:
```
claude mcp add --transport http secure-api https://api.example.com/mcp \
  --header "Authorization: Bearer your-token"
```

### Option 2: Remote SSE Servers

**Warning**: "SSE(Server-Sent Events)传输已弃用。请在可用的地方使用 HTTP 服务器。"

Basic syntax:
```
claude mcp add --transport sse <name> <url>
```

Example for Asana:
```
claude mcp add --transport sse asana https://mcp.asana.com/sse
```

With authentication header:
```
claude mcp add --transport sse private-api https://api.company.com/sse \
  --header "X-API-Key: your-key-here"
```

### Option 3: Local Stdio Servers

Stdio servers run as local processes. Basic syntax:
```
claude mcp add --transport stdio <name> <command> [args...]
```

Airtable example:
```
claude mcp add --transport stdio airtable --env AIRTABLE_API_KEY=YOUR_KEY \
  -- npx -y airtable-mcp-server
```

**About the "--" parameter**: "The `--`(双破折号)将 Claude 自己的 CLI 标志与传递给 MCP 服务器的命令和参数分开。" Content before `--` are Claude's options; everything after are the server's command and arguments.

Examples of `--` usage:
```
claude mcp add --transport stdio myserver -- npx server
claude mcp add --transport stdio myserver --env KEY=value -- python server.py --port 8080
```

## Managing Servers

Available management commands:

```
# List all configured servers
claude mcp list

# Get details about specific server
claude mcp get github

# Delete a server
claude mcp remove github

# Check server status in Claude Code
/mcp
```

### Tips for Server Management

* Use `--scope` flag to specify configuration storage location:
  * `local` (default): Current project only
  * `project`: Shared via `.mcp.json` file with team
  * `user`: Available across all projects
* Use `--env` flag to set environment variables
* Configure MCP server startup timeout with `MCP_TIMEOUT` environment variable
* When MCP tool output exceeds 10,000 tokens, Claude Code displays warning
* Increase limit with `MAX_MCP_OUTPUT_TOKENS` environment variable

### Windows Users Note

"在本机 Windows(不是 WSL)上,使用 `npx` 的本地 MCP 服务器需要 `cmd /c` 包装器以确保正确执行。"

```
claude mcp add --transport stdio my-server -- cmd /c npx -y @some/package
```

Without the wrapper, you get "connection closed" errors.

## Plugin-Provided MCP Servers

Plugins can bundle MCP servers that automatically provide tools when enabled. Plugins define servers in `.mcp.json` at plugin root or inline in `plugin.json`.

Example `.mcp.json` in plugin root:
```json
{
  "database-tools": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
    "env": {
      "DB_URL": "${DB_URL}"
    }
  }
}
```

Example inline in `plugin.json`:
```json
{
  "name": "my-plugin",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

**Plugin MCP Features**:
* Automatic lifecycle: server starts when plugin enabled
* Must restart Claude Code to apply changes
* Supports environment variable expansion using `${CLAUDE_PLUGIN_ROOT}`
* Access same environment variables as manually configured servers
* Support stdio, SSE, and HTTP transports

View plugin MCP servers:
```
/mcp
```

**Plugin advantages**: Bundled distribution, automatic setup, team consistency.

## MCP Installation Scopes

### Local Scope

Default configuration level, stored in project-specific user settings. Private to user, accessible only in current project. Good for personal development servers, experimental configurations, or servers with sensitive credentials.

```
# Default local scope
claude mcp add --transport http stripe https://mcp.stripe.com

# Explicit local scope
claude mcp add --transport http stripe --scope local https://mcp.stripe.com
```

### Project Scope

Servers stored in `.mcp.json` file at project root, designed for version control and team collaboration. All team members access same MCP tools.

```
claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp
```

Standard `.mcp.json` format:
```json
{
  "mcpServers": {
    "shared-server": {
      "command": "/path/to/server",
      "args": [],
      "env": {}
    }
  }
}
```

**Security note**: Claude Code prompts for approval before using project-scoped servers from `.mcp.json`. Reset choices with:
```
claude mcp reset-project-choices
```

### User Scope

Cross-project accessible servers, available in all projects on computer. Good for personal utility servers, development tools, frequently-used services.

```
claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
```

### Choosing Correct Scope

* **Local**: Personal servers, experimental, project-specific credentials
* **Project**: Team-shared servers, project-specific tools
* **User**: Personal utilities, development tools, cross-project services

### Scope Hierarchy and Priority

Clear priority hierarchy when same-named servers exist in multiple scopes: local scope prioritized first, then project scope, then user scope. Personal configuration overrides shared configuration.

### Environment Variable Expansion in `.mcp.json`

Claude Code supports environment variable expansion in `.mcp.json`, allowing shared configuration while maintaining flexibility for sensitive values.

**Supported syntax**:
* `${VAR}` - Expands to environment variable value
* `${VAR:-default}` - Expands to VAR if set, otherwise uses default

**Expansion locations**:
* `command` - Server executable path
* `args` - Command line parameters
* `env` - Environment variables for server
* `url` - For HTTP server types
* `headers` - For HTTP server authentication

**Example with variable expansion**:
```json
{
  "mcpServers": {
    "api-server": {
      "type": "http",
      "url": "${API_BASE_URL:-https://api.example.com}/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

Missing required variables without defaults prevent Claude Code from resolving configuration.

## Practical Examples

### Example: Monitoring Errors with Sentry

```
# 1. Add Sentry MCP server
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp

# 2. Authenticate Sentry account
> /mcp

# 3. Debug production issues
> "过去 24 小时内最常见的错误是什么?"
> "显示错误 ID abc123 的堆栈跟踪"
> "哪个部署引入了这些新错误?"
```

### Example: GitHub Code Review Connection

```
# 1. Add GitHub MCP server
claude mcp add --transport http github https://api.githubcopilot.com/mcp/

# 2. Authenticate if needed
> /mcp
# Select "身份验证" for GitHub

# 3. Request Claude's help
> "审查 PR #456 并建议改进"
> "为我们刚发现的错误创建新问题"
> "显示分配给我的所有打开的 PR"
```

### Example: PostgreSQL Database Querying

```
# 1. Add database server with connection string
claude mcp add --transport stdio db -- npx -y @bytebase/dbhub \
  --dsn "postgresql://readonly:pass@prod.db.com:5432/analytics"

# 2. Natural language database queries
> "本月我们的总收入是多少?"
> "显示订单表的架构"
> "查找 90 天内未进行购买的客户"
```

## Authenticating Remote MCP Servers

Many cloud-based MCP servers require authentication. Claude Code supports OAuth 2.0 for secure connections.

**Steps**:

Step 1: Add authentication-requiring server
```
claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
```

Step 2: Use `/mcp` command in Claude Code
```
> /mcp
```
Then follow browser login steps.

**Tips**:
* Authentication tokens stored securely with automatic refresh
* Use "Clear authentication" in `/mcp` menu to revoke access
* If browser doesn't open, copy provided URL
* OAuth authentication works with HTTP servers

## Adding MCP Servers From JSON Configuration

If you have MCP server JSON configuration, add directly:

**Basic syntax**:
```
claude mcp add-json <name> '<json>'
```

**HTTP server example**:
```
claude mcp add-json weather-api '{"type":"http","url":"https://api.weather.com/mcp","headers":{"Authorization":"Bearer token"}}'
```

**Stdio server example**:
```
claude mcp add-json local-weather '{"type":"stdio","command":"/path/to/weather-cli","args":["--api-key","abc123"],"env":{"CACHE_DIR":"/tmp"}}'
```

**Verify server added**:
```
claude mcp get weather-api
```

**Tips**:
* Ensure JSON correctly escaped in shell
* JSON must comply with MCP server configuration schema
* Use `--scope user` for user configuration instead of project-specific

## Importing MCP Servers From Claude Desktop

If MCP servers already configured in Claude Desktop, import them:

**Basic syntax**:
```
claude mcp add-from-claude-desktop
```

After running, interactive dialog allows selecting servers to import.

**Verify import**:
```
claude mcp list
```

**Tips**:
* Feature only works on macOS and Windows Subsystem for Linux
* Reads from standard location for platform's Claude Desktop config
* Use `--scope user` flag for user configuration
* Imported servers have same names as in Claude Desktop
* Existing same-named servers get numeric suffix (e.g., `server_1`)

## Using Claude Code as MCP Server

Claude Code itself can serve as MCP server for other applications to connect:

```
# Start Claude as stdio MCP server
claude mcp serve
```

Use in Claude Desktop by adding to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "claude-code": {
      "type": "stdio",
      "command": "claude",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

**Important warning**: "The `command` field must reference Claude Code executable. If `claude` command not in system PATH, specify full path."

Find full path:
```
which claude
```

Use full path in config:
```json
{
  "mcpServers": {
    "claude-code": {
      "type": "stdio",
      "command": "/full/path/to/claude",
      "args": ["mcp", "serve"],
      "env": {}
    }
  }
}
```

Without correct path, get errors like `spawn claude ENOENT`.

**Tips**:
* Server exposes Claude tools access
* In Claude Desktop, request Claude read files, make edits
* Note: client responsible for user confirmation per tool

## MCP Output Limits and Warnings

Claude Code manages token usage when MCP tools produce large output:

* **Output warning threshold**: Warning displayed when any MCP tool output exceeds 10,000 tokens
* **Configurable limit**: Adjust with `MAX_MCP_OUTPUT_TOKENS` environment variable
* **Default limit**: Default maximum is 25,000 tokens

Increase limit for high-output tools:
```
export MAX_MCP_OUTPUT_TOKENS=50000
claude
```

Useful for MCP servers that:
* Query large datasets or databases
* Generate detailed reports or documents
* Process voluminous log files or debug information

**Warning**: Frequent output warnings suggest increasing limits or configuring server pagination/filtering.

## Using MCP Resources

MCP servers can expose resources referenced using @ mentions, similar to file references.

### Referencing MCP Resources

**Step 1**: List available resources
Type `@` in prompt to view resources from connected MCP servers. Resources appear in autocomplete menu alongside files.

**Step 2**: Reference specific resources
Use format `@server:protocol://resource/path`:
```
> 您能分析 @github:issue://123 并建议修复吗?
> 请查看 @docs:file://api/authentication 处的 API 文档
```

**Step 3**: Multiple resource references
Reference multiple resources in single prompt:
```
> 比较 @postgres:schema://users 和 @docs:file://database/user-model
```

**Tips**:
* Resources automatically fetched when referenced
* Resource paths fuzzy-searchable in @ mention autocomplete
* Claude Code automatically provides tools for listing and reading MCP resources when supported by server
* Resources can contain any content type provided by MCP server

## Using MCP Prompts as Slash Commands

MCP servers can expose prompts available as slash commands in Claude Code.

### Executing MCP Prompts

**Step 1**: Discover available prompts
Type `/` to view all available commands including MCP server commands. MCP prompts appear as `/mcp__servername__promptname`.

**Step 2**: Execute prompts without parameters
```
> /mcp__github__list_prs
```

**Step 3**: Execute prompts with parameters
Many prompts accept parameters. Pass space-separated after command:
```
> /mcp__github__pr_review 456
> /mcp__jira__create_issue "登录流中的错误" high
```

**Tips**:
* MCP prompts dynamically discovered from connected servers
* Parameters parsed per prompt's defined parameters
* Prompt results directly injected into conversation
* Server and prompt names normalized (spaces become underscores)

## Enterprise MCP Configuration

Organizations needing centralized MCP server control, Claude Code supports enterprise-managed configuration allowing IT administrators to:

* Control which MCP servers employees access
* Deploy standardized approved servers organization-wide
* Prevent unauthorized MCP servers
* Optionally restrict user-added servers
* Completely disable MCP if needed

### Setting Up Enterprise MCP Configuration

System administrators deploy enterprise MCP configuration file alongside managed settings:

* **macOS**: `/Library/Application Support/ClaudeCode/managed-mcp.json`
* **Windows**: `C:\ProgramData\ClaudeCode\managed-mcp.json`
* **Linux**: `/etc/claude-code/managed-mcp.json`

File uses same format as standard `.mcp.json`:

```json
{
  "mcpServers": {
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/"
    },
    "sentry": {
      "type": "http",
      "url": "https://mcp.sentry.dev/mcp"
    },
    "company-internal": {
      "type": "stdio",
      "command": "/usr/local/bin/company-mcp-server",
      "args": ["--config", "/etc/company/mcp-config.json"],
      "env": {
        "COMPANY_API_URL": "https://internal.company.com"
      }
    }
  }
}
```

### Restricting MCP Servers With Allow/Deny Lists

Administrators use `allowedMcpServers` and `deniedMcpServers` in `managed-settings.json` to control configurable servers:

* **macOS**: `/Library/Application Support/ClaudeCode/managed-settings.json`
* **Windows**: `C:\ProgramData\ClaudeCode\managed-settings.json`
* **Linux**: `/etc/claude-code/managed-settings.json`

```json
{
  "allowedMcpServers": [
    { "serverName": "github" },
    { "serverName": "sentry" },
    { "serverName": "company-internal" }
  ],
  "deniedMcpServers": [
    { "serverName": "filesystem" }
  ]
}
```

**Allow list behavior** (`allowedMcpServers`):
* `undefined` (default): No restrictions - users configure any server
* Empty array `[]`: Completely locked - users can't configure any servers
* Server name list: Users only configure specified servers

**Deny list behavior** (`deniedMcpServers`):
* `undefined` (default): No servers blocked
* Empty array `[]`: No servers blocked
* Server name list: Specified servers explicitly blocked in all scopes

**Important notes**:
* Restrictions apply across all scopes: user, project, local, even enterprise servers
* Deny list has absolute priority: servers in both lists get blocked

**Enterprise configuration priority**: Enterprise MCP configuration has highest priority, can't be overridden by user, local, or project configurations.

---

**End of Complete Content Extraction**
