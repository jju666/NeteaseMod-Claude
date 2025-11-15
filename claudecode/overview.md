# Claude Code 概述

> 了解 Claude Code，Anthropic 的代理编码工具，它位于您的终端中,帮助您比以往任何时候都更快地将想法转化为代码。

## 30 秒快速开始

前置条件：

* 一个 [Claude.ai](https://claude.ai)（推荐）或 [Claude 控制台](https://console.anthropic.com/) 账户

**安装 Claude Code：**

**macOS/Linux:**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Homebrew:**
```bash
brew install --cask claude-code
```

**Windows:**
```powershell
irm https://claude.ai/install.ps1 | iex
```

**NPM:**
```bash
npm install -g @anthropic-ai/claude-code
```
需要 [Node.js 18+](https://nodejs.org/en/download/)

**开始使用 Claude Code：**

```bash
cd your-project
claude
```

首次使用时，系统会提示您登录。就这样！

> 查看[高级设置](/zh-CN/setup)了解安装选项，或者如果遇到问题，请查看[故障排除](/zh-CN/troubleshooting)。

> **新的 VS Code 扩展（测试版）**：更喜欢图形界面？新的 [VS Code 扩展](/zh-CN/vs-code)提供了易于使用的原生 IDE 体验，无需熟悉终端。

## Claude Code 为您做什么

* **从描述构建功能**：用纯英文告诉 Claude 您想构建什么。它将制定计划、编写代码并确保其正常工作。
* **调试和修复问题**：描述一个错误或粘贴一条错误消息。Claude Code 将分析您的代码库、识别问题并实施修复。
* **导航任何代码库**：询问关于您团队代码库的任何内容，并获得深思熟虑的答案。
* **自动化繁琐的任务**：修复棘手的 lint 问题、解决合并冲突并编写发布说明。

## 为什么开发者喜欢 Claude Code

* **在您的终端中工作**：Claude Code 在您已经工作的地方与您相遇，使用您已经喜欢的工具。
* **采取行动**：Claude Code 可以直接编辑文件、运行命令和创建提交。
* **Unix 哲学**：Claude Code 是可组合和可脚本化的。
* **企业就绪**：企业级[安全](/zh-CN/security)、[隐私](/zh-CN/data-usage)和[合规性](https://trust.anthropic.com/)是内置的。

## 后续步骤

* [快速入门](/zh-CN/quickstart) - 通过实际示例查看 Claude Code 的实际应用
* [常见工作流](/zh-CN/common-workflows) - 常见工作流的分步指南
* [故障排除](/zh-CN/troubleshooting) - Claude Code 常见问题的解决方案
* [IDE 设置](/zh-CN/vs-code) - 将 Claude Code 添加到您的 IDE

## 其他资源

* [使用 Agent SDK 构建](https://docs.claude.com/en/docs/agent-sdk/overview) - 使用 Claude Agent SDK 创建自定义 AI 代理
* [在 AWS 或 GCP 上托管](/zh-CN/third-party-integrations) - 使用 Amazon Bedrock 或 Google Vertex AI 配置 Claude Code
* [设置](/zh-CN/settings) - 为您的工作流自定义 Claude Code
* [命令](/zh-CN/cli-reference) - 了解 CLI 命令和控制
* [参考实现](https://github.com/anthropics/claude-code/tree/main/.devcontainer) - 克隆开发容器参考实现
* [安全](/zh-CN/security) - Claude Code 的保障措施和安全使用的最佳实践
* [隐私和数据使用](/zh-CN/data-usage) - Claude Code 如何处理您的数据
