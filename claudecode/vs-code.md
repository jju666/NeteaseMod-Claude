# Visual Studio Code

> 通过我们的原生扩展或 CLI 集成在 Visual Studio Code 中使用 Claude Code

![Claude Code VS Code 扩展界面](https://mintcdn.com/claude-code/-YhHHmtSxwr7W8gy/images/vs-code-extension-interface.jpg?fit=max&auto=format&n=-YhHHmtSxwr7W8gy&q=85&s=300652d5678c63905e6b0ea9e50835f8)

## VS Code 扩展（测试版）

VS Code 扩展（测试版）让您能够通过集成在 IDE 中的原生图形界面实时查看 Claude 的更改。VS Code 扩展使喜欢使用可视化界面而不是终端的用户更容易访问和交互 Claude Code。

### 功能

VS Code 扩展提供：

* **原生 IDE 体验**：通过 Spark 图标访问的专用 Claude Code 侧边栏面板
* **计划模式和编辑**：在接受之前查看和编辑 Claude 的计划
* **自动接受编辑模式**：在 Claude 进行更改时自动应用
* **文件管理**：使用 @-mention 文件或通过系统文件选择器附加文件和图像
* **MCP 服务器使用**：使用通过 CLI 配置的模型上下文协议服务器
* **对话历史**：轻松访问过去的对话
* **多个会话**：同时运行多个 Claude Code 会话
* **键盘快捷键**：支持 CLI 中的大多数快捷键
* **斜杠命令**：直接在扩展中访问大多数 CLI 斜杠命令

### 要求

* VS Code 1.98.0 或更高版本

### 安装

从 [Visual Studio Code 扩展市场](https://marketplace.visualstudio.com/items?itemName=anthropic.claude-code) 下载并安装扩展。

### 工作原理

安装后，您可以通过 VS Code 界面开始使用 Claude Code：

1. 点击编辑器侧边栏中的 Spark 图标打开 Claude Code 面板
2. 以与在终端中相同的方式提示 Claude Code
3. 观看 Claude 分析您的代码并建议更改
4. 直接在界面中查看和接受编辑
   * **提示**：将侧边栏拖宽以查看内联差异，然后点击它们以展开查看完整详情

### 使用第三方提供商（Vertex 和 Bedrock）

VS Code 扩展支持通过第三方提供商（如 Amazon Bedrock 和 Google Vertex AI）使用 Claude Code。当使用这些提供商配置时，扩展不会提示登录。要使用第三方提供商，请在 VS Code 扩展设置中配置环境变量：

1. 打开 VS Code 设置
2. 搜索"Claude Code: Environment Variables"
3. 添加所需的环境变量

#### 环境变量

| 变量 | 描述 | 必需 | 示例 |
| :--- | :--- | :--- | :--- |
| `CLAUDE_CODE_USE_BEDROCK` | 启用 Amazon Bedrock 集成 | Bedrock 必需 | `"1"` 或 `"true"` |
| `CLAUDE_CODE_USE_VERTEX` | 启用 Google Vertex AI 集成 | Vertex AI 必需 | `"1"` 或 `"true"` |
| `ANTHROPIC_API_KEY` | 第三方访问的 API 密钥 | 必需 | `"your-api-key"` |
| `AWS_REGION` | Bedrock 的 AWS 区域 |  | `"us-east-2"` |
| `AWS_PROFILE` | Bedrock 身份验证的 AWS 配置文件 |  | `"your-profile"` |
| `CLOUD_ML_REGION` | Vertex AI 的区域 |  | `"global"` 或 `"us-east5"` |
| `ANTHROPIC_VERTEX_PROJECT_ID` | Vertex AI 的 GCP 项目 ID |  | `"your-project-id"` |
| `ANTHROPIC_MODEL` | 覆盖主模型 | 覆盖模型 ID | `"us.anthropic.claude-sonnet-4-5-20250929-v1:0"` |
| `ANTHROPIC_SMALL_FAST_MODEL` | 覆盖小型/快速模型 | 可选 | `"us.anthropic.claude-3-5-haiku-20241022-v1:0"` |
| `CLAUDE_CODE_SKIP_AUTH_LOGIN` | 禁用所有登录提示 | 可选 | `"1"` 或 `"true"` |

有关详细的设置说明和其他配置选项，请参阅：

* [Amazon Bedrock 上的 Claude Code](/zh-CN/amazon-bedrock)
* [Google Vertex AI 上的 Claude Code](/zh-CN/google-vertex-ai)

### 尚未实现

VS Code 扩展中尚未提供以下功能：

* **完整 MCP 服务器配置**：您需要[首先通过 CLI 配置 MCP 服务器](/zh-CN/mcp)，然后扩展将使用它们
* **子代理配置**：[通过 CLI 配置子代理](/zh-CN/sub-agents)以在 VS Code 中使用它们
* **检查点**：在特定点保存和恢复对话状态
* **高级快捷键**：
  * `#` 快捷键添加到内存
  * `!` 快捷键直接运行 bash 命令
* **制表符补全**：使用制表符键进行文件路径补全

我们正在努力在未来的更新中添加这些功能。

## 安全考虑

当 Claude Code 在 VS Code 中运行且启用了自动编辑权限时，它可能能够修改 IDE 配置文件，这些文件可能被您的 IDE 自动执行。这可能会增加在自动编辑模式下运行 Claude Code 的风险，并允许绕过 Claude Code 对 bash 执行的权限提示。

在 VS Code 中运行时，请考虑：

* 为不受信任的工作区启用 [VS Code 受限模式](https://code.visualstudio.com/docs/editor/workspace-trust#_restricted-mode)
* 对编辑使用手动批准模式
* 特别小心确保 Claude 仅与受信任的提示一起使用

## 旧版 CLI 集成

我们发布的第一个 VS Code 集成允许在终端中运行的 Claude Code 与您的 IDE 交互。它提供选择上下文共享（当前选择/选项卡自动与 Claude Code 共享）、在 IDE 中而不是终端中查看差异、文件引用快捷键（Mac 上的 `Cmd+Option+K` 或 Windows/Linux 上的 `Alt+Ctrl+K` 以插入文件引用，如 @File#L1-99）和自动诊断共享（lint 和语法错误）。

旧版集成在您从 VS Code 的集成终端运行 `claude` 时自动安装。只需从终端运行 `claude`，所有功能都会激活。对于外部终端，使用 `/ide` 命令将 Claude Code 连接到您的 VS Code 实例。要配置，运行 `claude`，输入 `/config`，并将差异工具设置为 `auto` 以进行自动 IDE 检测。

扩展和 CLI 集成都适用于 Visual Studio Code、Cursor、Windsurf 和 VSCodium。

## 故障排除

### 扩展未安装

* 确保您有兼容版本的 VS Code（1.85.0 或更高版本）
* 检查 VS Code 是否有权限安装扩展
* 尝试直接从市场网站安装

### 旧版集成不工作

* 确保您从 VS Code 的集成终端运行 Claude Code
* 确保已安装您的 IDE 变体的 CLI：
  * VS Code：`code` 命令应该可用
  * Cursor：`cursor` 命令应该可用
  * Windsurf：`windsurf` 命令应该可用
  * VSCodium：`codium` 命令应该可用
* 如果命令未安装：
  1. 使用 `Cmd+Shift+P`（Mac）或 `Ctrl+Shift+P`（Windows/Linux）打开命令面板
  2. 搜索"Shell Command: Install 'code' command in PATH"（或您的 IDE 的等效命令）

如需更多帮助，请参阅我们的[故障排除指南](/zh-CN/troubleshooting)。
