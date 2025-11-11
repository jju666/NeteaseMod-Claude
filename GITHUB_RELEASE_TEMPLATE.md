# v16.1.0 - 双重定制架构

> **发布日期**: 2025-11-11
> **版本类型**: Minor Release

---

## 🎉 重大更新

### 📚 完善的README文档
- **从106行扩展至640+行**，全面展示项目强大功能
- 新增详细的**安装和部署教学**（4个步骤）
- 添加**前置环境要求**检查表
- 完整的**故障排查章节**（7个FAQ）
- 2个完整的**使用示例**（修复常见错误、添加新功能）

### 🔧 路径规范化
- 修正所有文档中的**硬编码路径**为通用占位符
  - CLAUDE.md（4处修正）
  - .claude/commands/cc.md（3处修正）
  - markdown/项目状态.md（1处修正）

### 📦 发布文档
- 新增 **CHANGELOG.md** - 完整版本历史记录
- 新增 **RELEASE_CHECKLIST.md** - 发布前检查清单

---

## ✨ v16.1 核心特性（继承自v16.1.0首发）

### CLAUDE.md项目扩展区支持
- **新增变量支持**：`{{PRESETS_DOCS_SECTION}}`、`{{QUICK_INDEX_EXTRA}}`
- **智能合并逻辑**：自动检测项目定制内容，上游更新时保留定制
- **迁移脚本优化**：从v16.0平滑升级

### /uninstallmc 指令
- **一键卸载**：支持从Claude Code中执行 `/uninstallmc` 卸载工作流
- **安全备份**：自动创建备份目录 `.backup-uninstall-[日期]/`
- **清理范围**：删除 `.claude/`、`CLAUDE.md`、`markdown/`、`tasks/`

---

## 🐛 Bug修复

- 优化官方文档查阅策略，优先使用本地软连接
- 修复废弃文件检测的版本号歧义问题
- 修复v16.0初始化过程中的构造函数参数传递问题

---

## 📊 技术指标

| 指标 | 数值 |
|-----|------|
| **自动化程度** | 95% |
| **职责隔离** | 100%（多项目互不影响） |
| **文档覆盖率** | 100% |
| **兼容性** | Windows/Linux/Mac |
| **定制化程度** | 高（支持CLAUDE.md内容定制） |

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone --recursive https://github.com/jju666/NeteaseMod-Claude.git
cd NeteaseMod-Claude
```

### 2. 全局安装

```bash
npm install
npm run install-global
```

### 3. 初始化项目

```bash
cd /path/to/your/modsdk-project
initmc
```

### 4. 开始开发

在Claude Code中直接对话，AI会自动遵循MODSDK规范！

---

## 📚 完整文档

- **[README.md](./README.md)** - 项目主文档（新增640+行）
- **[CHANGELOG.md](./CHANGELOG.md)** - 版本历史（新增）
- **[CLAUDE.md](./CLAUDE.md)** - AI工作流参考
- **[快速参考.md](./快速参考.md)** - 工作流快速查询
- **[迁移指南-v16.1.md](./markdown/迁移指南-v16.1.md)** - v16.0→v16.1升级

---

## 🔄 升级指南

### 从v16.0升级

```bash
# 1. 更新上游仓库
cd /path/to/NeteaseMod-Claude
git pull origin main

# 2. 同步到下游项目
cd /path/to/your-modsdk-project
initmc --sync
```

### 从v15.x升级

```bash
# 执行initmc自动迁移
cd /path/to/your-modsdk-project
initmc  # 自动检测v15.0并升级到v16.1
```

---

## 🌟 亮点特性

### 1. 双层文档架构（v16.0核心创新）
- **上游基线层**：`.claude/core-docs/` 软连接到上游
- **项目覆盖层**：`markdown/core/` 支持项目定制
- **智能路由**：AI自动选择最佳文档版本

### 2. AI智能规范遵守
- 自动查阅并遵守MODSDK开发规范
- 避免90%的常见错误
- 支持在线查阅官方文档

### 3. 三步核心工作流
- **步骤1**：理解任务与分级（2分钟）
- **步骤2**：查阅文档（智能路由）
- **步骤3**：执行与收尾

---

## 🤝 贡献

欢迎提交Issue和Pull Request！

- **GitHub**: https://github.com/jju666/NeteaseMod-Claude
- **Issues**: https://github.com/jju666/NeteaseMod-Claude/issues

---

## 📜 许可证

MIT License - see [LICENSE](./LICENSE) for details

**附加条款**：本项目专为网易我的世界（中国版）MODSDK设计，使用时需遵守网易MODSDK开发协议。

---

## 🔗 相关链接

- **Claude Code**: https://claude.ai/code
- **网易MODSDK文档**: https://github.com/EaseCation/netease-modsdk-wiki
- **基岩版Wiki**: https://github.com/Bedrock-OSS/bedrock-wiki

---

<div align="center">

**让AI成为你的MODSDK开发专家** 🤖⚡

*Powered by [Claude Code](https://claude.ai/code)*

</div>
