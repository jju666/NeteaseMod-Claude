# NeteaseMod-Claude

<div align="center">

**🚀 网易我的世界MODSDK × Claude Code = 开发效率革命**

[![Version](https://img.shields.io/badge/version-20.2.9-blue.svg)](https://github.com/jju666/NeteaseMod-Claude)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Node](https://img.shields.io/badge/node-%3E%3D12.0.0-brightgreen.svg)](https://nodejs.org/)

**一条命令，AI全自动完成从需求分析到代码实现**

[快速开始](#-快速开始) • [核心特性](#-核心特性) • [使用场景](#-使用场景) • [文档](#-文档)

</div>

---

## 🎯 这是什么？

**NeteaseMod-Claude** 是基于 Claude Code AI 的智能MODSDK开发工作流系统。

### 💥 颠覆传统开发流程

**传统方式**：查文档 → 写代码 → 调试 → 改bug → 重复N次 ⏰ **耗时数小时**

**使用本工具**：一条命令 → AI自动完成 ✨ **仅需几分钟**

```bash
/mc 添加VIP系统，玩家购买VIP后获得移动速度加成
```

**AI自动执行**：
1. ✅ 分析需求，设计事件流
2. ✅ 生成完整ServerSystem代码框架
3. ✅ 配置组件、事件监听、数据持久化
4. ✅ 验证CRITICAL规范（双端通信、生命周期等）
5. ✅ 生成详细文档和使用说明

---

## 🔥 核心特性

### 1️⃣ 智能工作流驱动器（v20.x 重大升级）

**统一工作流引擎** - 自动识别任务类型，选择最优执行路径：

| 任务类型 | 识别关键词 | AI行为 |
|---------|----------|--------|
| 🐛 **BUG修复** | "修复"、"报错"、"不工作" | 智能诊断 → 定位问题 → 验证规范 → 提供修复方案 |
| ✨ **新功能** | "添加"、"实现"、"创建" | 需求分析 → 架构设计 → 生成代码 → 文档归档 |
| 📖 **代码理解** | "解释"、"是什么"、"怎么工作" | 代码扫描 → 流程分析 → 可视化说明 |
| ⚡ **性能优化** | "卡顿"、"慢"、"优化" | 性能分析 → 瓶颈检测 → 优化建议 |

### 2️⃣ 智能任务隔离系统（Hook机制）

**多层Hook系统** - 每个任务独立上下文，互不干扰：

- ✅ **自动创建任务目录**：`tasks/任务-1114-修复商店BUG/`
- ✅ **完整会话历史**：`.conversation.jsonl` 记录所有工具调用
- ✅ **跨会话归档**：压缩会话后自动生成 `context.md` + `solution.md`
- ✅ **失败追踪**：自动记录失败原因，支持重试和专家审核

### 3️⃣ CRITICAL规范守护者

**防止90%常见错误** - AI自动验证代码是否遵守关键规范：

1. **双端隔离原则**：禁止直接调用对端代码，强制使用 `NotifyToClient/Server`
2. **System生命周期**：检查 `__init__` 中是否调用 `self.Create()`
3. **模块导入规范**：子目录模块必须使用完整路径导入
4. **数据持久化**：提醒使用 `persistentData.modData` 存储玩家数据

### 4️⃣ 智能文档维护（自适应）

**文档永不过时** - AI根据代码变更自动更新文档：

- 📋 **三层文档架构**：核心规范 → 系统实现 → AI策略
- 🔍 **智能发现模式**：自动扫描项目，识别未记录的模块
- 🎯 **质量评分系统**：根据复杂度、重要性自动排序文档优先级
- 🔄 **增量更新**：只更新变化部分，保留人工编辑内容

### 5️⃣ 会话历史持久化（v20.2.8）

**解决归档上下文丢失问题**：

- ✅ 所有工具调用记录到 `.conversation.jsonl`
- ✅ 支持压缩会话后从历史重建归档文档
- ✅ 跨会话审计和回溯
- ✅ 子代理可访问完整上下文

---

## 🚀 快速开始

### 步骤1：安装工作流（上游项目维护者）

```bash
git clone https://github.com/jju666/NeteaseMod-Claude.git
cd NeteaseMod-Claude
npm install
npm run deploy
```

安装完成后，`initmc` 命令会自动添加到系统PATH。

### 步骤2：部署到MODSDK项目（下游用户）

```bash
cd your-modsdk-project
initmc
```

**工作流自动部署**：
- ✅ 复制 `.claude/` 目录（Hooks、配置、命令）
- ✅ 复制 `markdown/` 文档库（开发规范、问题排查）
- ✅ 创建 `tasks/` 任务目录
- ✅ 创建 `templates/` 任务模板

### 步骤3：开始使用

在Claude Code中输入：

```bash
/mc 添加商店系统，玩家可以花金币购买道具
```

**AI全自动完成**：需求分析 → 代码生成 → 规范验证 → 文档归档

---

## 💡 使用场景

### 场景1：修复BUG（智能诊断）

```bash
/mc 玩家死亡时背包物品没有掉落
```

**AI执行流程**：
1. 🔍 扫描 `问题排查.md` - 查找"物品掉落"相关已知问题
2. 📖 定位代码文件 - 分析事件监听逻辑
3. ✅ 验证规范 - 检查是否违反双端隔离原则
4. 🛠️ 提供修复方案 - 给出完整代码和解释

### 场景2：添加新功能（架构设计）

```bash
/mc 添加VIP系统，玩家购买VIP后移动速度+20%
```

**AI生成内容**：
- 📁 `VIPServerSystem.py` - 完整ServerSystem代码
- 📄 VIP数据结构设计（`persistentData.modData['vip_data']`）
- ⚡ 事件流设计（购买事件 → 速度组件修改 → 效果应用）
- 📋 使用文档（如何配置VIP等级、价格、权益）

### 场景3：性能优化（瓶颈检测）

```bash
/mc 服务器卡顿，优化性能
```

**AI分析步骤**：
1. 扫描所有 `*ServerSystem.py` 文件
2. 检测高频事件监听（如 `ServerPlayerTryDestroyBlockEvent`）
3. 分析是否存在不必要的全局遍历
4. 提供优化建议（事件过滤、缓存、异步处理）

### 场景4：代码理解（可视化说明）

```bash
/mc 解释ShopServerSystem的工作原理
```

**AI输出**：
- 📊 Mermaid流程图 - 可视化展示购买流程
- 🔗 数据流分析 - 客户端 → 服务端 → 数据持久化
- 💡 关键代码解释 - 逐行注释核心逻辑
- ⚠️ 潜在风险提示 - 并发问题、数据校验

---

## 📚 文档

### 用户文档
- **[快速开始](./docs/developer/快速上手.md)** - 5分钟上手，核心命令使用
- **[安装指南](./docs/developer/安装指南.md)** - 环境搭建、常见问题

### 开发者文档
- **[CLAUDE.md](./CLAUDE.md)** - AI工作流程参考（必读）
- **[技术架构](./docs/developer/技术架构.md)** - 系统设计、模块划分
- **[Hook机制](./docs/developer/Hook机制.md)** - 任务隔离、上下文管理
- **[数据流设计](./docs/developer/数据流设计.md)** - 工作流执行流程
- **[贡献指南](./docs/developer/贡献指南.md)** - 如何参与项目开发

### 完整文档索引
查看 [docs/developer/README.md](./docs/developer/README.md) - 19篇文档，80,000字，30+流程图

---

## 🎮 核心命令

| 命令 | 说明 | 使用频率 |
|------|------|---------|
| `/mc <任务>` | MODSDK开发主命令 | ⭐⭐⭐⭐⭐ (90%场景) |
| `/mc-review` | 方案审查（代码质量检查） | ⭐⭐⭐ |
| `/mc-perf` | 性能分析（瓶颈检测） | ⭐⭐ |
| `/mc-docs` | 文档验证/生成 | ⭐⭐ |
| `/mc-why <规范>` | 规范原理解释 | ⭐ |
| `/mc-discover` | 项目结构发现 | ⭐ |

---

## 📊 项目数据

### 核心统计

| 指标 | 数值 |
|------|------|
| **总代码行数** | ~15,000+ 行 |
| **Hook脚本** | 9个Python脚本 |
| **核心模块** | 23个JavaScript模块 |
| **开发者文档** | 19篇，80,000字 |
| **流程图** | 30+ Mermaid图表 |
| **版本迭代** | v1.0 → v20.2.8（20个大版本） |

### 技术栈

- **运行时**: Node.js ≥12.0.0
- **AI引擎**: Claude Code (Claude Sonnet 4.5)
- **Hook系统**: Python 3.6+
- **文档格式**: Markdown + Mermaid
- **配置格式**: JSON + JSONL

---

## 🌟 为什么选择 NeteaseMod-Claude？

### ✅ 开发效率提升 5-10倍

**传统开发**：查文档1小时 + 写代码2小时 + 调试2小时 = **5小时**
**使用本工具**：一条命令 + AI自动完成 = **30分钟**

### ✅ 代码质量有保障

- 自动验证CRITICAL规范，防止90%常见错误
- AI生成的代码经过最佳实践验证
- 完整的文档和注释，便于维护

### ✅ 知识沉淀和传承

- 所有任务自动归档到 `tasks/` 目录
- 完整的会话历史可追溯
- 文档自动更新，永不过时

### ✅ 多人协作友好

- 任务隔离机制，避免上下文污染
- 统一的代码规范和文档格式
- Git友好的版本管理

---

## 🔗 相关资源

### 官方文档

- **网易MODSDK Wiki**: [GitHub](https://github.com/EaseCation/netease-modsdk-wiki) - API用法、事件说明
- **Bedrock Wiki**: [GitHub](https://github.com/Bedrock-OSS/bedrock-wiki) - NBT结构、实体属性
- **Claude Code**: [文档](https://docs.claude.com/claude-code) - Hook系统、工具使用

### 社区支持

- **GitHub Issues**: [问题反馈](https://github.com/jju666/NeteaseMod-Claude/issues)
- **更新日志**: [CHANGELOG.md](./CHANGELOG.md)

---

## 📄 许可证

本项目采用 **MIT License** 开源协议。

网易我的世界MODSDK遵循网易官方开发协议。

---

## 🙏 致谢

感谢以下项目和团队：

- **Anthropic** - Claude AI 和 Claude Code 平台
- **网易游戏** - 我的世界MODSDK开发工具
- **开源社区** - Node.js、Python、Mermaid等工具

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**

**💬 有问题或建议？欢迎提Issue或PR！**

---

_最后更新: 2025-11-14 | 当前版本: v20.2.9_

Made with ❤️ by NeteaseMod-Claude Contributors

</div>
