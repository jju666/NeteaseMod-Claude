# Claude Code 安全性页面 - 完整原始内容

## 标题
# 安全性

> 了解 Claude Code 的安全防护措施和安全使用的最佳实践。

## 主要章节

### 我们如何处理安全性

#### 安全基础
您的代码安全至关重要。Claude Code 以安全为核心构建，按照 Anthropic 的全面安全计划开发。了解更多信息并访问资源（SOC 2 Type 2 报告、ISO 27001 证书等），请访问 [Anthropic 信任中心](https://trust.anthropic.com)。

#### 基于权限的架构
Claude Code 默认使用严格的只读权限。当需要额外操作时（编辑文件、运行测试、执行命令），Claude Code 会请求明确的权限。用户可以控制是否批准一次性操作或自动允许操作。

我们设计 Claude Code 以实现透明和安全。例如，我们要求在执行 bash 命令之前获得批准，让您直接控制。这种方法使用户和组织能够直接配置权限。

有关详细的权限配置，请参阅[身份和访问管理](/zh-CN/iam)。

#### 内置保护
为了降低代理系统中的风险：

* **沙箱化 bash 工具**：使用文件系统和网络隔离的[沙箱](/zh-CN/sandboxing) bash 命令，减少权限提示同时保持安全性。使用 `/sandbox` 启用以定义 Claude Code 可以自主工作的边界
* **写入访问限制**：Claude Code 只能写入启动它的文件夹及其子文件夹——它不能在没有明确权限的情况下修改父目录中的文件。虽然 Claude Code 可以读取工作目录外的文件（对于访问系统库和依赖项很有用），但写入操作严格限制在项目范围内，创建了清晰的安全边界
* **提示疲劳缓解**：支持按用户、按代码库或按组织的白名单常用安全命令
* **接受编辑模式**：批量接受多个编辑，同时为具有副作用的命令保持权限提示

#### 用户责任
Claude Code 仅具有您授予它的权限。您有责任在批准前审查建议的代码和命令的安全性。

### 防止提示注入

提示注入是一种技术，攻击者试图通过插入恶意文本来覆盖或操纵 AI 助手的指令。Claude Code 包括针对这些攻击的多项防护措施：

#### 核心保护
* **权限系统**：敏感操作需要明确批准
* **上下文感知分析**：通过分析完整请求来检测潜在有害指令
* **输入清理**：通过处理用户输入来防止命令注入
* **命令黑名单**：默认阻止从网络获取任意内容的风险命令，如 \`curl\` 和 \`wget\`。显式允许时，请注意[权限模式限制](/zh-CN/iam#tool-specific-permission-rules)

#### 隐私保护措施
我们已实施多项保护措施来保护您的数据，包括：

* 敏感信息的有限保留期（请参阅[隐私中心](https://privacy.anthropic.com/en/articles/10023548-how-long-do-you-store-my-data)了解更多信息）
* 对用户会话数据的受限访问
* 用户对数据培训偏好的控制。消费者用户可以随时更改其[隐私设置](https://claude.ai/settings/privacy)。

有关完整详情，请查阅我们的[商业服务条款](https://www.anthropic.com/legal/commercial-terms)（适用于 Team、Enterprise 和 API 用户）或[消费者条款](https://www.anthropic.com/legal/consumer-terms)（适用于 Free、Pro 和 Max 用户）以及[隐私政策](https://www.anthropic.com/legal/privacy)。

#### 额外保护措施
* **网络请求批准**：进行网络请求的工具默认需要用户批准
* **隔离的上下文窗口**：Web 获取使用单独的上下文窗口以避免注入潜在恶意提示
* **信任验证**：首次代码库运行和新 MCP 服务器需要信任验证
  * 注意：使用 \`-p\` 标志以非交互方式运行时，信任验证被禁用
* **命令注入检测**：即使之前已列入白名单，可疑的 bash 命令也需要手动批准
* **故障关闭匹配**：不匹配的命令默认需要手动批准
* **自然语言描述**：复杂的 bash 命令包括用户理解的解释
* **安全凭证存储**：API 密钥和令牌已加密。请参阅[凭证管理](/zh-CN/iam#credential-management)

**警告框：**
> **Windows WebDAV 安全风险**：在 Windows 上运行 Claude Code 时，我们建议不要启用 WebDAV 或允许 Claude Code 访问可能包含 WebDAV 子目录的路径，如 \`\*\`。[WebDAV 已被 Microsoft 弃用](https://learn.microsoft.com/en-us/windows/whats-new/deprecated-features#:~:text=The%20Webclient%20\(WebDAV\)%20service%20is%20deprecated)，原因是安全风险。启用 WebDAV 可能允许 Claude Code 触发对远程主机的网络请求，绕过权限系统。

**处理不受信任内容的最佳实践**：
1. 在批准前审查建议的命令
2. 避免直接将不受信任的内容通过管道传输到 Claude
3. 验证对关键文件的建议更改
4. 使用虚拟机 (VM) 运行脚本并进行工具调用，特别是在与外部 Web 服务交互时
5. 使用 \`/bug\` 报告可疑行为

**警告框：**
> 虽然这些保护措施大大降低了风险，但没有任何系统完全免疫所有攻击。在使用任何 AI 工具时，始终保持良好的安全实践。

### MCP 安全性
Claude Code 允许用户配置模型上下文协议 (MCP) 服务器。允许的 MCP 服务器列表在您的源代码中配置，作为 Claude Code 设置的一部分，工程师将其检入源代码控制。

我们鼓励编写您自己的 MCP 服务器或使用来自您信任的提供商的 MCP 服务器。您可以为 MCP 服务器配置 Claude Code 权限。Anthropic 不管理或审计任何 MCP 服务器。

### IDE 安全性
有关在 IDE 中运行 Claude Code 的安全性的更多信息，请参阅[此处](/zh-CN/vs-code#security)。

### 云执行安全性
使用[网络上的 Claude Code](/zh-CN/claude-code-on-the-web) 时，会实施额外的安全控制：

* **隔离的虚拟机**：每个云会话在隔离的、由 Anthropic 管理的 VM 中运行
* **网络访问控制**：网络访问默认受限，可配置为禁用或仅允许特定域
* **凭证保护**：身份验证通过安全代理处理，该代理在沙箱内使用作用域凭证，然后转换为您的实际 GitHub 身份验证令牌
* **分支限制**：Git push 操作限制在当前工作分支
* **审计日志**：云环境中的所有操作都被记录以用于合规和审计目的
* **自动清理**：会话完成后，云环境会自动终止

有关云执行的更多详情，请参阅[网络上的 Claude Code](/zh-CN/claude-code-on-the-web)。

### 安全最佳实践

#### 处理敏感代码
* 在批准前审查所有建议的更改
* 为敏感存储库使用项目特定的权限设置
* 考虑使用[开发容器](/zh-CN/devcontainer)以获得额外隔离
* 使用 \`/permissions\` 定期审计您的权限设置

#### 团队安全
* 使用[企业管理策略](/zh-CN/iam#enterprise-managed-policy-settings)来执行组织标准
* 通过版本控制共享已批准的权限配置
* 培训团队成员了解安全最佳实践
* 通过 [OpenTelemetry 指标](/zh-CN/monitoring-usage)监控 Claude Code 使用情况

#### 报告安全问题
如果您在 Claude Code 中发现安全漏洞：

1. 不要公开披露
2. 通过我们的 [HackerOne 计划](https://hackerone.com/anthropic-vdp/reports/new?type=team\&report_type=vulnerability)报告
3. 包括详细的复现步骤
4. 在公开披露前给我们时间来解决问题

## 相关资源
* [沙箱](/zh-CN/sandboxing) - bash 命令的文件系统和网络隔离
* [身份和访问管理](/zh-CN/iam) - 配置权限和访问控制
* [监控使用情况](/zh-CN/monitoring-usage) - 跟踪和审计 Claude Code 活动
* [开发容器](/zh-CN/devcontainer) - 安全、隔离的环境
* [Anthropic 信任中心](https://trust.anthropic.com) - 安全认证和合规
