# Claude Code 设置完整内容提取

## 主要标题和导言

> 使用全局和项目级设置以及环境变量配置 Claude Code。

Claude Code 提供了多种设置来配置其行为以满足您的需求。您可以在使用交互式 REPL 时运行 `/config` 命令来配置 Claude Code,这会打开一个选项卡式设置界面,您可以在其中查看状态信息并修改配置选项。

## 设置文件

`settings.json` 文件是我们通过分层设置配置 Claude Code 的官方机制:

* **用户设置**在 `~/.claude/settings.json` 中定义,适用于所有项目。
* **项目设置**保存在您的项目目录中:
  * `.claude/settings.json` 用于检入源代码控制并与您的团队共享的设置
  * `.claude/settings.local.json` 用于未检入的设置,适用于个人偏好和实验。Claude Code 将在创建 `.claude/settings.local.json` 时配置 git 以忽略它。
* 对于 Claude Code 的企业部署,我们还支持**企业托管策略设置**。这些优先于用户和项目设置。系统管理员可以将策略部署到:
  * macOS: `/Library/Application Support/ClaudeCode/managed-settings.json`
  * Linux 和 WSL: `/etc/claude-code/managed-settings.json`
  * Windows: `C:\ProgramData\ClaudeCode\managed-settings.json`
* 企业部署还可以配置**托管 MCP 服务器**,这些服务器会覆盖用户配置的服务器。请参阅企业 MCP 配置:
  * macOS: `/Library/Application Support/ClaudeCode/managed-mcp.json`
  * Linux 和 WSL: `/etc/claude-code/managed-mcp.json`
  * Windows: `C:\ProgramData\ClaudeCode\managed-mcp.json`

### 示例 settings.json

```JSON
{
  "permissions": {
    "allow": [
      "Bash(npm run lint)",
      "Bash(npm run test:*)",
      "Read(~/.zshrc)"
    ],
    "deny": [
      "Bash(curl:*)",
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)"
    ]
  },
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "OTEL_METRICS_EXPORTER": "otlp"
  },
  "companyAnnouncements": [
    "Welcome to Acme Corp! Review our code guidelines at docs.acme.com",
    "Reminder: Code reviews required for all PRs",
    "New security policy in effect"
  ]
}
```

### 可用设置

`settings.json` 支持多个选项:

| 键                            | 描述                                                                                                                                          | 示例                                                                      |
| :--------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------ | :---------------------------------------------------------------------- |
| `apiKeyHelper`               | 自定义脚本,在 `/bin/sh` 中执行,用于生成身份验证值。此值将作为 `X-Api-Key` 和 `Authorization: Bearer` 标头发送用于模型请求                                                      | `/bin/generate_temp_api_key.sh`                                         |
| `cleanupPeriodDays`          | 基于最后活动日期本地保留聊天记录的时长(默认:30 天)                                                                                                                | `20`                                                                    |
| `companyAnnouncements`       | 在启动时显示给用户的公告。如果提供多个公告,它们将随机循环显示。                                                                                                            | `["Welcome to Acme Corp! Review our code guidelines at docs.acme.com"]` |
| `env`                        | 将应用于每个会话的环境变量                                                                                                                               | `{"FOO": "bar"}`                                                        |
| `includeCoAuthoredBy`        | 是否在 git 提交和拉取请求中包含 `co-authored-by Claude` 署名(默认:`true`)                                                                                    | `false`                                                                 |
| `permissions`                | 请参阅下表了解权限结构。                                                                                                                                |                                                                         |
| `hooks`                      | 配置自定义命令以在工具执行前后运行。请参阅钩子文档                                                                                                   | `{"PreToolUse": {"Bash": "echo 'Running command..'"}}`                  |
| `disableAllHooks`            | 禁用所有钩子                                                                                                                      | `true`                                                                  |
| `model`                      | 覆盖 Claude Code 使用的默认模型                                                                                                                      | `"claude-sonnet-4-5-20250929"`                                          |
| `statusLine`                 | 配置自定义状态行以显示上下文。请参阅 statusLine 文档                                                                                        | `{"type": "command", "command": "~/.claude/statusline.sh"}`             |
| `outputStyle`                | 配置输出样式以调整系统提示。请参阅输出样式文档                                                                                             | `"Explanatory"`                                                         |
| `forceLoginMethod`           | 使用 `claudeai` 限制登录到 Claude.ai 账户,使用 `console` 限制登录到 Claude Console(API 使用计费)账户                                                              | `claudeai`                                                              |
| `forceLoginOrgUUID`          | 指定组织的 UUID 以在登录期间自动选择它,绕过组织选择步骤。需要设置 `forceLoginMethod`                                                                                     | `"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`                                |
| `enableAllProjectMcpServers` | 自动批准项目 `.mcp.json` 文件中定义的所有 MCP 服务器                                                                                                         | `true`                                                                  |
| `enabledMcpjsonServers`      | 要批准的 `.mcp.json` 文件中特定 MCP 服务器的列表                                                                                                           | `["memory", "github"]`                                                  |
| `disabledMcpjsonServers`     | 要拒绝的 `.mcp.json` 文件中特定 MCP 服务器的列表                                                                                                           | `["filesystem"]`                                                        |
| `allowedMcpServers`          | 在 managed-settings.json 中设置时,用户可以配置的 MCP 服务器的允许列表。未定义 = 无限制,空数组 = 锁定。适用于所有范围。拒绝列表优先。请参阅企业 MCP 配置 | `[{ "serverName": "github" }]`                                          |
| `deniedMcpServers`           | 在 managed-settings.json 中设置时,明确阻止的 MCP 服务器的拒绝列表。适用于所有范围,包括企业服务器。拒绝列表优先于允许列表。请参阅企业 MCP 配置         | `[{ "serverName": "filesystem" }]`                                      |
| `awsAuthRefresh`             | 修改 `.aws` 目录的自定义脚本(请参阅高级凭证配置)                                                    | `aws sso login --profile myprofile`                                     |
| `awsCredentialExport`        | 输出包含 AWS 凭证的 JSON 的自定义脚本(请参阅高级凭证配置)                                              | `/bin/generate_aws_grant.sh`                                            |

### 权限设置

| 键                              | 描述                                                                                                                                                                         | 示例                                                                     |
| :----------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------------------------- |
| `allow`                        | 权限规则数组以允许工具使用。**注意:** Bash 规则使用前缀匹配,而不是正则表达式                                                                                         | `[ "Bash(git diff:*)" ]`                                               |
| `ask`                          | 权限规则数组以在工具使用时请求确认。                                                                                                                   | `[ "Bash(git push:*)" ]`                                               |
| `deny`                         | 权限规则数组以拒绝工具使用。使用此选项也可以排除敏感文件不被 Claude Code 访问。**注意:** Bash 模式是前缀匹配,可能被绕过(请参阅 Bash 权限限制) | `[ "WebFetch", "Bash(curl:*)", "Read(./.env)", "Read(./secrets/**)" ]` |
| `additionalDirectories`        | Claude 可以访问的其他工作目录                                                                                                                       | `[ "../docs/" ]`                                                       |
| `defaultMode`                  | 打开 Claude Code 时的默认权限模式                                                                                                                     | `"acceptEdits"`                                                        |
| `disableBypassPermissionsMode` | 设置为 `"disable"` 以防止激活 `bypassPermissions` 模式。这会禁用 `--dangerously-skip-permissions` 命令行标志。请参阅托管策略设置                        | `"disable"`                                                            |

### 沙箱设置

配置高级沙箱行为。沙箱将 bash 命令与您的文件系统和网络隔离。有关详细信息,请参阅沙箱文档。

**文件系统和网络限制**通过读取、编辑和 WebFetch 权限规则配置,而不是通过这些沙箱设置。

| 键                           | 描述                                                                                                                                                            | 示例                        |
| :-------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------------------------ |
| `enabled`                   | 启用 bash 沙箱(仅限 macOS/Linux)。默认值:false                                                                                                                          | `true`                    |
| `autoAllowBashIfSandboxed`  | 沙箱化时自动批准 bash 命令。默认值:true                                                                                                                                     | `true`                    |
| `excludedCommands`          | 应在沙箱外运行的命令                                                                                                                                                    | `["git", "docker"]`       |
| `allowUnsandboxedCommands`  | 允许命令通过 `dangerouslyDisableSandbox` 参数在沙箱外运行。设置为 `false` 时,`dangerouslyDisableSandbox` 逃生舱完全禁用,所有命令必须沙箱化运行(或在 `excludedCommands` 中)。对于需要严格沙箱化的企业策略很有用。默认值:true | `false`                   |
| `network.allowUnixSockets`  | 沙箱中可访问的 Unix 套接字路径(用于 SSH 代理等)                                                                                                                                | `["~/.ssh/agent-socket"]` |
| `network.allowLocalBinding` | 允许绑定到 localhost 端口(仅限 MacOS)。默认值:false                                                                                                                        | `true`                    |
| `network.httpProxyPort`     | 如果您想使用自己的代理,则使用的 HTTP 代理端口。如果未指定,Claude 将运行自己的代理。                                                                                                             | `8080`                    |
| `network.socksProxyPort`    | 如果您想使用自己的代理,则使用的 SOCKS5 代理端口。如果未指定,Claude 将运行自己的代理。                                                                                                           | `8081`                    |
| `enableWeakerNestedSandbox` | 为无特权 Docker 环境启用较弱的沙箱(仅限 Linux)。**降低安全性。** 默认值:false                                                                                                          | `true`                    |

### 沙箱配置示例

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "excludedCommands": ["docker"],
    "network": {
      "allowUnixSockets": [
        "/var/run/docker.sock"
      ],
      "allowLocalBinding": true
    }
  },
  "permissions": {
    "deny": [
      "Read(.envrc)",
      "Read(~/.aws/**)"
    ]
  }
}
```

**文件系统访问**通过读取/编辑权限控制:

* 读取拒绝规则阻止沙箱中的文件读取
* 编辑允许规则允许文件写入(除了默认值,例如当前工作目录)
* 编辑拒绝规则阻止在允许的路径内写入

**网络访问**通过 WebFetch 权限控制:

* WebFetch 允许规则允许网络域
* WebFetch 拒绝规则阻止网络域

### 设置优先级

设置按优先级顺序应用(从高到低):

1. **企业托管策略**(`managed-settings.json`)
   * 由 IT/DevOps 部署
   * 无法被覆盖

2. **命令行参数**
   * 特定会话的临时覆盖

3. **本地项目设置**(`.claude/settings.local.json`)
   * 个人项目特定设置

4. **共享项目设置**(`.claude/settings.json`)
   * 源代码控制中的团队共享项目设置

5. **用户设置**(`~/.claude/settings.json`)
   * 个人全局设置

此层次结构确保企业安全策略始终得到执行,同时仍允许团队和个人自定义其体验。

### 配置系统的关键要点

* **内存文件 (CLAUDE.md)**:包含 Claude 在启动时加载的说明和上下文
* **设置文件 (JSON)**:配置权限、环境变量和工具行为
* **斜杠命令**:可在会话期间使用 `/command-name` 调用的自定义命令
* **MCP 服务器**:使用其他工具和集成扩展 Claude Code
* **优先级**:更高级别的配置(企业)覆盖更低级别的配置(用户/项目)
* **继承**:设置被合并,更具体的设置添加到或覆盖更广泛的设置

### 系统提示可用性

<Note>
  与 claude.ai 不同,我们不在本网站上发布 Claude Code 的内部系统提示。使用 CLAUDE.md 文件或 `--append-system-prompt` 向 Claude Code 的行为添加自定义说明。
</Note>

### 排除敏感文件

要防止 Claude Code 访问包含敏感信息的文件(例如 API 密钥、机密、环境文件),请在 `.claude/settings.json` 文件中使用 `permissions.deny` 设置:

```json
{
  "permissions": {
    "deny": [
      "Read(./.env)",
      "Read(./.env.*)",
      "Read(./secrets/**)",
      "Read(./config/credentials.json)",
      "Read(./build)"
    ]
  }
}
```

这替代了已弃用的 `ignorePatterns` 配置。匹配这些模式的文件将完全对 Claude Code 不可见,防止任何意外泄露敏感数据。

## 子代理配置

Claude Code 支持可在用户和项目级别配置的自定义 AI 子代理。这些子代理存储为带有 YAML 前置事项的 Markdown 文件:

* **用户子代理**:`~/.claude/agents/` - 在所有项目中可用
* **项目子代理**:`.claude/agents/` - 特定于您的项目,可与您的团队共享

子代理文件定义具有自定义提示和工具权限的专门 AI 助手。在子代理文档中了解有关创建和使用子代理的更多信息。

## 插件配置

Claude Code 支持一个插件系统,允许您使用自定义命令、代理、钩子和 MCP 服务器扩展功能。插件通过市场分发,可在用户和存储库级别配置。

### 插件设置

`settings.json` 中的插件相关设置:

```json
{
  "enabledPlugins": {
    "formatter@company-tools": true,
    "deployer@company-tools": true,
    "analyzer@security-plugins": false
  },
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": "github",
      "repo": "company/claude-plugins"
    }
  }
}
```

#### `enabledPlugins`

控制启用哪些插件。格式:`"plugin-name@marketplace-name": true/false`

**范围**:

* **用户设置**(`~/.claude/settings.json`):个人插件偏好
* **项目设置**(`.claude/settings.json`):与团队共享的项目特定插件
* **本地设置**(`.claude/settings.local.json`):每台机器的覆盖(未提交)

**示例**:

```json
{
  "enabledPlugins": {
    "code-formatter@team-tools": true,
    "deployment-tools@team-tools": true,
    "experimental-features@personal": false
  }
}
```

#### `extraKnownMarketplaces`

定义应为存储库提供的其他市场。通常在存储库级别设置中使用,以确保团队成员可以访问所需的插件源。

**当存储库包含 `extraKnownMarketplaces` 时**:

1. 当团队成员信任该文件夹时,系统会提示他们安装市场
2. 然后提示团队成员从该市场安装插件
3. 用户可以跳过不需要的市场或插件(存储在用户设置中)
4. 安装遵守信任边界并需要明确同意

**示例**:

```json
{
  "extraKnownMarketplaces": {
    "company-tools": {
      "source": {
        "source": "github",
        "repo": "company-org/claude-plugins"
      }
    },
    "security-plugins": {
      "source": {
        "source": "git",
        "url": "https://git.company.com/security/plugins.git"
      }
    }
  }
}
```

**市场源类型**:

* `github`:GitHub 存储库(使用 `repo`)
* `git`:任何 git URL(使用 `url`)
* `directory`:本地文件系统路径(使用 `path`,仅用于开发)

### 管理插件

使用 `/plugin` 命令以交互方式管理插件:

* 浏览市场中的可用插件
* 安装/卸载插件
* 启用/禁用插件
* 查看插件详细信息(提供的命令、代理、钩子)
* 添加/删除市场

在插件文档中了解有关插件系统的更多信息。

## 环境变量

Claude Code 支持以下环境变量来控制其行为:

<Note>
  所有环境变量也可以在 [`settings.json`](#available-settings) 中配置。这是自动为每个会话设置环境变量或为整个团队或组织推出一组环境变量的有用方式。
</Note>

| 变量                                         | 目的                                                                                                                                                                                                             |
| :----------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY`                        | 作为 `X-Api-Key` 标头发送的 API 密钥,通常用于 Claude SDK(对于交互式使用,运行 `/login`)                                                                                                                                                               |
| `ANTHROPIC_AUTH_TOKEN`                     | `Authorization` 标头的自定义值(您在此处设置的值将以 `Bearer ` 为前缀)                                                                                                                                                                              |
| `ANTHROPIC_CUSTOM_HEADERS`                 | 您想添加到请求的自定义标头(采用 `Name: Value` 格式)                                                                                                                                                                                             |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL`            | 请参阅模型配置                                                                                                                                                                                                                   |
| `ANTHROPIC_DEFAULT_OPUS_MODEL`             | 请参阅模型配置                                                                                                                                                                                                                   |
| `ANTHROPIC_DEFAULT_SONNET_MODEL`           | 请参阅模型配置                                                                                                                                                                                                                   |
| `ANTHROPIC_MODEL`                          | 要使用的模型设置的名称(请参阅模型配置)                                                                                                                                                                                        |
| `ANTHROPIC_SMALL_FAST_MODEL`               | \[已弃用] Haiku 级模型用于后台任务的名称                                                                                                                                                                                        |
| `ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION`    | 使用 Bedrock 时覆盖 Haiku 级模型的 AWS 区域                                                                                                                                                                                               |
| `AWS_BEARER_TOKEN_BEDROCK`                 | Bedrock API 密钥用于身份验证(请参阅 Bedrock API 密钥)                                                                                                                                                                             |
| `BASH_DEFAULT_TIMEOUT_MS`                  | 长时间运行的 bash 命令的默认超时                                                                                                                                                                                                            |
| `BASH_MAX_OUTPUT_LENGTH`                   | bash 输出中的最大字符数,超过此数量后将进行中间截断                                                                                                                                                                                                   |
| `BASH_MAX_TIMEOUT_MS`                      | 模型可以为长时间运行的 bash 命令设置的最大超时                                                                                                                                                                                                     |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR` | 每个 Bash 命令后返回到原始工作目录                                                                                                                                                                                                           |
| `CLAUDE_CODE_API_KEY_HELPER_TTL_MS`        | 应刷新凭证的间隔(以毫秒为单位)(使用 `apiKeyHelper` 时)                                                                                                                                                                                          |
| `CLAUDE_CODE_CLIENT_CERT`                  | 用于 mTLS 身份验证的客户端证书文件的路径                                                                                                                                                                                                        |
| `CLAUDE_CODE_CLIENT_KEY_PASSPHRASE`        | 加密 CLAUDE_CODE_CLIENT_KEY 的密码短语(可选)                                                                                                                                                                                         |
| `CLAUDE_CODE_CLIENT_KEY`                   | 用于 mTLS 身份验证的客户端私钥文件的路径                                                                                                                                                                                                        |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` | 等同于设置 `DISABLE_AUTOUPDATER`、`DISABLE_BUG_COMMAND`、`DISABLE_ERROR_REPORTING` 和 `DISABLE_TELEMETRY`                                                                                                                              |
| `CLAUDE_CODE_DISABLE_TERMINAL_TITLE`       | 设置为 `1` 以禁用基于对话上下文的自动终端标题更新                                                                                                                                                                                                    |
| `CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL`        | 跳过 IDE 扩展的自动安装                                                                                                                                                                                                                 |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS`            | 为大多数请求设置最大输出令牌数                                                                                                                                                                                                                |
| `CLAUDE_CODE_SKIP_BEDROCK_AUTH`            | 跳过 Bedrock 的 AWS 身份验证(例如使用 LLM 网关时)                                                                                                                                                                                            |
| `CLAUDE_CODE_SKIP_VERTEX_AUTH`             | 跳过 Vertex 的 Google 身份验证(例如使用 LLM 网关时)                                                                                                                                                                                          |
| `CLAUDE_CODE_SUBAGENT_MODEL`               | 请参阅模型配置                                                                                                                                                                                                                 |
| `CLAUDE_CODE_USE_BEDROCK`                  | 使用 Bedrock                                                                                                                                                                                                                   |
| `CLAUDE_CODE_USE_VERTEX`                   | 使用 Vertex                                                                                                                                                                                                                    |
| `DISABLE_AUTOUPDATER`                      | 设置为 `1` 以禁用自动更新。这优先于 `autoUpdates` 配置设置。                                                                                                                                                                                       |
| `DISABLE_BUG_COMMAND`                      | 设置为 `1` 以禁用 `/bug` 命令                                                                                                                                                                                                          |
| `DISABLE_COST_WARNINGS`                    | 设置为 `1` 以禁用成本警告消息                                                                                                                                                                                                              |
| `DISABLE_ERROR_REPORTING`                  | 设置为 `1` 以选择退出 Sentry 错误报告                                                                                                                                                                                                      |
| `DISABLE_NON_ESSENTIAL_MODEL_CALLS`        | 设置为 `1` 以禁用非关键路径(如风味文本)的模型调用                                                                                                                                                                                                   |
| `DISABLE_PROMPT_CACHING`                   | 设置为 `1` 以禁用所有模型的提示缓存(优先于每个模型的设置)                                                                                                                                                                                               |
| `DISABLE_PROMPT_CACHING_HAIKU`             | 设置为 `1` 以禁用 Haiku 模型的提示缓存                                                                                                                                                                                                      |
| `DISABLE_PROMPT_CACHING_OPUS`              | 设置为 `1` 以禁用 Opus 模型的提示缓存                                                                                                                                                                                                       |
| `DISABLE_PROMPT_CACHING_SONNET`            | 设置为 `1` 以禁用 Sonnet 模型的提示缓存                                                                                                                                                                                                     |
| `DISABLE_TELEMETRY`                        | 设置为 `1` 以选择退出 Statsig 遥测(请注意,Statsig 事件不包括用户数据,如代码、文件路径或 bash 命令)                                                                                                                                                              |
| `HTTP_PROXY`                               | 为网络连接指定 HTTP 代理服务器                                                                                                                                                                                                             |
| `HTTPS_PROXY`                              | 为网络连接指定 HTTPS 代理服务器                                                                                                                                                                                                            |
| `MAX_MCP_OUTPUT_TOKENS`                    | MCP 工具响应中允许的最大令牌数。当输出超过 10,000 个令牌时,Claude Code 显示警告(默认值:25000)                                                                                                                                                                |
| `MAX_THINKING_TOKENS`                      | 启用扩展思考并为思考过程设置令牌预算。扩展思考改进了复杂推理和编码任务的性能,但影响提示缓存效率。默认禁用。 |
| `MCP_TIMEOUT`                              | MCP 服务器启动的超时时间(以毫秒为单位)                                                                                                                                                                                                         |
| `MCP_TOOL_TIMEOUT`                         | MCP 工具执行的超时时间(以毫秒为单位)                                                                                                                                                                                                          |
| `NO_PROXY`                                 | 将直接发出请求的域和 IP 列表,绕过代理                                                                                                                                                                                                          |
| `SLASH_COMMAND_TOOL_CHAR_BUDGET`           | 显示给 SlashCommand 工具的斜杠命令元数据的最大字符数(默认值:15000)                                                                                                                                        |
| `USE_BUILTIN_RIPGREP`                      | 设置为 `0` 以使用系统安装的 `rg` 而不是 Claude Code 附带的 `rg`                                                                                                                                                                                 |
| `VERTEX_REGION_CLAUDE_3_5_HAIKU`           | 使用 Vertex AI 时覆盖 Claude 3.5 Haiku 的区域                                                                                                                                                                                          |
| `VERTEX_REGION_CLAUDE_3_7_SONNET`          | 使用 Vertex AI 时覆盖 Claude 3.7 Sonnet 的区域                                                                                                                                                                                         |
| `VERTEX_REGION_CLAUDE_4_0_OPUS`            | 使用 Vertex AI 时覆盖 Claude 4.0 Opus 的区域                                                                                                                                                                                           |
| `VERTEX_REGION_CLAUDE_4_0_SONNET`          | 使用 Vertex AI 时覆盖 Claude 4.0 Sonnet 的区域                                                                                                                                                                                           |
| `VERTEX_REGION_CLAUDE_4_1_OPUS`            | 使用 Vertex AI 时覆盖 Claude 4.1 Opus 的区域                                                                                                                                                                                           |

## Claude 可用的工具

Claude Code 可以访问一组强大的工具,帮助它理解和修改您的代码库:

| 工具               | 描述                                                   | 需要权限 |
| :--------------- | :--------------------------------------------------- | :--- |
| **Bash**         | 在您的环境中执行 shell 命令                                    | 是    |
| **Edit**         | 对特定文件进行有针对性的编辑                                       | 是    |
| **Glob**         | 基于模式匹配查找文件                                           | 否    |
| **Grep**         | 在文件内容中搜索模式                                           | 否    |
| **NotebookEdit** | 修改 Jupyter 笔记本单元格                                    | 是    |
| **NotebookRead** | 读取和显示 Jupyter 笔记本内容                                  | 否    |
| **Read**         | 读取文件的内容                                              | 否    |
| **SlashCommand** | 运行自定义斜杠命令                                             | 是    |
| **Task**         | 运行子代理以处理复杂的多步骤任务                                     | 否    |
| **TodoWrite**    | 创建和管理结构化任务列表                                         | 否    |
| **WebFetch**     | 从指定的 URL 获取内容                                        | 是    |
| **WebSearch**    | 执行具有域过滤的网络搜索                                         | 是    |
| **Write**        | 创建或覆盖文件                                              | 是    |

权限规则可以使用 `/allowed-tools` 或在权限设置中配置。另请参阅工具特定权限规则。

### 使用钩子扩展工具

您可以使用 Claude Code 钩子在任何工具执行前后运行自定义命令。

例如,您可以在 Claude 修改 Python 文件后自动运行 Python 格式化程序,或通过阻止对某些路径的写入操作来防止修改生产配置文件。

## 另请参阅

* 身份和访问管理 - 了解 Claude Code 的权限系统
* IAM 和访问控制 - 企业策略管理
* 故障排除 - 常见配置问题的解决方案
