# NeteaseMod-Claude 工作流生成器

> **AI驱动的MODSDK开发工作流系统**
>
> 本项目为网易我的世界MODSDK提供智能开发辅助工具链

---

## 🎯 项目定位

**NeteaseMod-Claude** 是基于 **Claude Code Hooks 机制** 的工业级智能开发工作流系统：

- **🤖 Claude LLM语义分析**: 96.15%用户意图识别准确率（vs 传统关键词85%）
- **🔧 4步状态机架构**: Activation → Planning → Implementation → Finalization
- **🛡️ Hook强制规则系统**: 8个Hook协同工作，强制执行工作流规则
- **📊 单数据源设计**: task-meta.json统一管理任务状态（v21.0架构）

---

## ⚠️ Hook开发重要说明

### 开发依赖Hook功能时的标准流程

当你需要进行以下操作时：
- 🔨 开发新的Hook功能
- 🔧 调整现有Hook行为
- 🐛 修复Hook相关BUG

**请严格遵循以下查阅顺序**：

1. **首选参考**: [HOOK正确用法文档](./docs/developer/HOOK正确用法文档.md) ⭐
   - 包含所有Hook类型的标准实现方式
   - 实战案例和最佳实践
   - 已验证的代码示例（可直接复制）

2. **深度搜索**: [Claude Code 官方文档](https://code.claude.com/docs/zh-CN/overview)
   - 如果HOOK正确用法文档中找不到答案
   - 访问官方文档及其提及的相关网页
   - 深入了解Hook机制的底层原理

3. **最后手段**: 直接询问用户
   - 仅当上述两个资源都无法解决问题时
   - 明确说明已查阅的文档内容
   - 具体描述遇到的问题

**关键要点**：
- ✅ HOOK正确用法文档是项目的**唯一Hook开发标准**
- ✅ 所有Hook实现均已与Claude Code官方文档对齐验证
- ✅ 文档包含v24.0/v25.0实战验证的代码示例
- ❌ 禁止猜测或假设Hook行为，必须基于文档实现

---

## 📚 文档导航

### 🚀 快速开始
- [安装指南](./docs/developer/安装指南.md) - 5分钟快速部署
- [快速上手](./docs/developer/快速上手.md) - 核心命令与使用场景

### 🏗️ 核心架构
- [技术架构](./docs/developer/技术架构.md) - 系统设计与模块划分
- [数据流设计](./docs/developer/数据流设计.md) - 工作流执行流程
- [Hook状态机功能实现](./docs/developer/Hook状态机功能实现.md) - Hook系统完整实现说明
- [通知系统](./docs/developer/通知系统.md) - 跨平台桌面通知(v18.4+)

### 🤖 Claude LLM集成（v25.0核心）
- [HOOK正确用法文档](./docs/developer/HOOK正确用法文档.md) ⭐ **开发必读**
- [Claude语义分析器使用指南](./docs/developer/Claude语义分析器使用指南.md) - LLM语义分析系统
- [子代理结果注入与提取-完整实现指南](./docs/developer/子代理结果注入与提取-完整实现指南.md) - Subagent集成

### 📦 核心模块
- [项目分析器](./docs/developer/项目分析器.md) - ProjectAnalyzer 模块
- [文档生成器](./docs/developer/文档生成器.md) - DocumentGenerator 模块
- [智能文档维护](./docs/developer/智能文档维护.md) - 自适应文档系统
- [版本管理](./docs/developer/版本管理.md) - 迁移与同步机制

### 🎯 任务管理
- [任务模板使用指南](./docs/developer/任务模板使用指南.md) - 任务模板配置与使用
- [任务命名配置](./docs/developer/任务命名配置.md) - 任务命名规则与自定义

### 🔧 开发指南
- [贡献指南](./docs/developer/贡献指南.md) - 如何参与项目开发
- [测试指南](./docs/developer/测试指南.md) - 手动测试方法与验证脚本
- [通知功能安装指南](./docs/developer/通知功能安装指南.md) - 桌面通知功能部署
- [Windows-UTF8-升级指南](./docs/developer/Windows-UTF8-升级指南.md) - Windows 平台编码配置

### 📖 用户文档
- [README.md](./README.md) - 项目概述
- [CHANGELOG.md](./CHANGELOG.md) - 版本更新记录
- [开发者文档总览](./docs/developer/README.md) - 开发者文档入口

---

## 🤖 Claude Code 官方文档

本目录包含 Claude Code 的官方文档，用于深入理解 Claude Code 的功能和最佳实践。

### 📘 基础指南
- [概述](./claudecode/overview.md) - Claude Code 功能概览
- [快速开始](./claudecode/quickstart.md) - 快速上手指南
- [安装配置](./claudecode/setup.md) - 详细安装步骤

### 🔨 进阶使用
- [常见工作流](./claudecode/common-workflows.md) - 典型使用场景
- [VS Code 集成](./claudecode/vs-code.md) - VS Code 扩展使用
- [Hooks 机制](./claudecode/hooks.md) - Hook 系统详解
- [MCP 协议](./claudecode/mcp.md) - Model Context Protocol

### ⚙️ 配置与集成
- [设置选项](./claudecode/settings.md) - 完整配置参考
- [第三方集成](./claudecode/third-party-integrations.md) - 外部工具集成
- [CLI 命令参考](./claudecode/cli-reference.md) - 命令行接口

### 🛡️ 安全与隐私
- [安全指南](./claudecode/security.md) - 安全最佳实践
- [数据使用](./claudecode/data-usage.md) - 数据处理说明

### 🔍 故障排查
- [故障排查](./claudecode/troubleshooting.md) - 常见问题解决

---

## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

## 📝 版本历史

### v25.0 (2025-11-19~20) - Claude LLM语义分析系统 ✅

**核心突破**: 从传统关键词匹配升级到**Claude Sonnet 4.5驱动的语义分析**

**关键成果**:
1. **准确率提升**: 85% → 96.15% (+11.15%)
   - `complete_success`: 64.3% → 100%
   - `partial_success`: 64.3% → 100%
   - 完美识别转折语义（"基本正确,但还有BUG"）

2. **零维护成本**: 自动理解新表达（如"都正确了"），无需手动添加关键词

3. **状态机100%安全**: 硬编码合法转移表 + 运行时强制验证

**技术实现**:
- ✅ `ClaudeSemanticAnalyzer`: LLM语义分析器（Claude Sonnet 4.5）
- ✅ `StateTransitionValidator`: 状态转移验证器（防止状态机脱离）
- ✅ `UserPromptHandler`: 全面LLM集成（Planning/Implementation阶段）
- ✅ 2025-11-20迁移到Claude Sonnet 4.5（原3.5 Sonnet已退役）

**性能指标**:
- 延迟: P50 3-5秒, P95 8-12秒
- 成本: ~$0.36/年（可忽略）
- 超时: 15秒（友好降级提示）

**文档新增**:
- [HOOK正确用法文档](./docs/developer/HOOK正确用法文档.md) - Hook开发唯一标准
- [Claude语义分析器使用指南](./docs/developer/Claude语义分析器使用指南.md) - LLM集成完整文档

---

### v3.0 Final (2025-11-15) - 4步状态机完整实现 ✅

**架构重构**: 统一命名，完整实现4步语义化状态机

**核心实现**:
1. **4步状态机**: Activation → Planning → Implementation → Finalization
2. **YAML规则系统**: 声明式配置（4个阶段规则文件）
3. **SubagentStop重写**: transcript解析机制（替代stdin读取）
4. **差异化工作流**: BUG修复 vs 功能设计（自动路由）

**测试验证**:
- ✅ 48个自动化测试用例（100%通过）
- ✅ 13个文件版本统一（v3.0 Final）
- ✅ 完全向后兼容v21.0

**关键文件**:
- `tool_matrix.py`: 状态机核心配置
- `templates/.claude/rules/*.yaml`: 4个阶段规则文件
- `lifecycle/subagent_stop.py`: Subagent结果解析

---

### v21.1.2 (2025-11-15) - 文档规范全面审计 ✅

**质量保障**: 修复11个文档-代码不一致问题

**核心修复**:
- ✅ task-meta.json字段结构补全（steps.description/prompt等）
- ✅ 统一architecture_version格式（"v21.0"）
- ✅ 重写示例JSON（区分初始化 vs 运行时）
- ✅ 验证工具v21.0.2（Windows兼容性修复）

**验证结果**: 0个错误，0个警告，完全通过 ✅

---

### v21.1.0 (2025-11-14) - 单一数据源架构 ✅

**架构重构**: 移除workflow-state.json，统一使用task-meta.json

**核心变更**:
- ✅ 单数据源设计（task-meta.json唯一真实来源）
- ✅ TaskMetaManager统一管理（portalocker文件锁）
- ✅ Hook系统重构（8个Hook标准化路径）
- ✅ 玩法包模式自动跳过step0/step1

**破坏性变更**:
- ⚠️ v20.x任务无法在v21.0环境继续执行
- ⚠️ 需使用`initmc`自动迁移

---

### 版本说明

- **当前稳定版**: v25.0（Claude LLM语义分析）
- **架构版本**: v21.x（单一数据源task-meta.json）
- **状态机版本**: v3.0 Final（4步语义化状态机）

**升级建议**:
```bash
# 自动迁移v20.x → v21.0 → v25.0
initmc
```

---

_最后更新: 2025-11-20 | v25.0 (Claude LLM集成完成)_
