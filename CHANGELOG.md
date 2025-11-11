# Changelog

All notable changes to NeteaseMod-Claude will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [16.2.1] - 2025-11-11

### 🐛 Fixed - 下游命令部署和文档路径修复

#### 命令部署完整性
- **discover.md部署**：修复`/discover`命令未部署到下游项目的问题
- **review-design.md部署**：修复`/review-design`命令未部署到下游项目的问题
- **路径映射修复**：在`lib/config.js`的`getTemplatePath()`添加这两个命令的路径映射

#### 文档路径引用错误修复
- **markdown/软连接创建**：新增`SymlinkManager.createMarkdownSymlinks()`方法
- **双层架构实现**：在`markdown/`目录创建指向`.claude/core-docs/`的软连接
- **路径兼容性**：解决`/cc`命令引用`markdown/开发规范.md`但实际文档在`.claude/core-docs/`的问题
- **用户文件保护**：如果`markdown/`已有用户文件则跳过创建软连接

#### 官方文档部署优化
- **环境变量降级**：修复`_deployOfficialDocs()`依赖`NETEASE_CLAUDE_HOME`环境变量的问题
- **自动路径推断**：使用`upstreamPath`作为降级方案，无需手动设置环境变量
- **文档可用性**：确保官方MODSDK和基岩版Wiki文档自动部署到`.claude/docs/`

### 📚 Documentation

#### 命令模板改进
- **智能降级机制**：优先读取项目定制版（`markdown/core/`），降级到上游基线（`.claude/core-docs/`）
- **本地文档优先**：优化官方文档查阅策略，优先使用本地离线文档，降级到在线WebFetch
- **路径引用灵活化**：移除硬编码的`markdown/`路径前缀，支持灵活的文档组织

### 🎯 Impact

此版本修复了工作流部署的核心问题，确保下游项目：
- ✅ 获得完整的5个命令（从3个增加到5个）
- ✅ /cc命令可正确访问核心工作流文档
- ✅ 官方文档自动部署供本地快速查询
- ✅ 支持完整的双层文档架构

---

## [16.2.0] - 2025-11-11

### ✨ Added - Windows安装体验优化

#### 友好的错误提示
- **权限错误提示**：Windows安装时遇到权限问题，提供清晰的解决方案
- **路径处理说明**：提示用户正确使用引号处理空格路径
- **Git Submodule下载提示**：明确提示正在下载官方文档，告知预期时间

#### 文档完善
- **README.md**：添加Windows用户特别注意事项
- **INSTALLATION.md**：补充常见错误对比说明
- **上游CLAUDE.md**：重写为工作流开发指南（从449行精简到261行）

### 🐛 Fixed

#### 符号链接权限问题
- **跳过符号链接复制**：在 `install-global.js` 中跳过符号链接，避免Windows权限错误
- **普通PowerShell安装**：无需管理员权限即可完成全局安装
- **开发者模式支持**：优先使用Windows开发者模式

#### 下游产物清理
- **删除错误的.claude/core-docs/**：清理误部署到上游仓库的12个符号链接
- **添加.gitignore规则**：防止再次误添加下游产物

### 🔄 Changed

#### 文档架构重构
- **上游CLAUDE.md**：从MODSDK开发指南改为工作流开发指南
- **职责划分明确**：
  - `CLAUDE.md` → 指导工作流开发（工作流开发者使用）
  - `templates/CLAUDE.md.template` → 指导MODSDK开发（游戏开发者使用）
- **内容精简**：减少42%内容（449行 → 261行）

### 📚 Documentation

- 新增工作流架构说明（bin/, lib/, templates/, markdown/）
- 新增常见开发任务指南
- 新增问题排查章节
- 新增发布流程检查清单

### 🚀 Impact

- **Windows用户体验**：✅ 大幅改善（友好的错误提示，无需管理员权限）
- **安装成功率**：✅ 提升（自动跳过符号链接复制）
- **文档清晰度**：✅ 提升（角色定位明确，不再混淆）
- **Token节省**：✅ 42%（CLAUDE.md从449行降到261行）

---

## [16.1.0] - 2025-11-11

### ✨ Added - 双重定制架构

#### CLAUDE.md项目扩展区支持
- **新增变量支持**：`{{PRESETS_DOCS_SECTION}}`、`{{QUICK_INDEX_EXTRA}}`
- **智能合并逻辑**：自动检测项目定制内容，上游更新时保留定制
- **迁移脚本优化**：从v16.0平滑升级

#### /uninstallmc 指令
- **一键卸载**：支持从Claude Code中执行 `/uninstallmc` 卸载工作流
- **安全备份**：自动创建备份目录 `.backup-uninstall-[日期]/`
- **清理范围**：删除 `.claude/`、`CLAUDE.md`、`markdown/`、`tasks/`

### 🐛 Fixed

- 优化官方文档查阅策略，优先使用本地软连接
- 修复废弃文件检测的版本号歧义问题
- 修复v16.0初始化过程中的构造函数参数传递问题

### 📚 Documentation

- 完善迁移指南-v16.1.md
- 更新可选工具说明文档

### 🔧 Technical

- **定制化程度**：高（支持CLAUDE.md内容定制）
- **向后兼容**：v16.0项目自动迁移
- **职责隔离**：100%（多项目互不影响）

---

## [16.0.0] - 2025-11-10

### ✨ Added - 双层文档架构（核心创新）

#### 双层文档架构
- **上游基线层**：`.claude/core-docs/` 软连接到上游核心文档
- **项目覆盖层**：`markdown/core/` 支持项目定制，互不干扰
- **智能文档路由**：AI自动选择项目定制版或上游基线
- **自动迁移v15.x**：执行 `initmc` 自动升级

#### 可选优化工具
- **覆盖层冲突合并**：`merge-conflicts` 命令检测项目覆盖层与上游的冲突
- **废弃文件检测**：`detect-obsolete` 命令自动清理过期文件（带备份）

#### 命令行工具
- `initmc`：一键初始化MODSDK项目工作流
- `initmc --sync`：同步上游更新
- `initmc --force`：强制重新初始化
- `uninstallmc`：卸载工作流

### 🔄 Changed

- **文档数量优化**：下游项目从10+个文档减少到3-5个（只存差异）
- **软连接管理**：自动创建和维护软连接
- **迁移策略**：v15.x项目自动备份到 `.backup-docs-v15/`

### 🐛 Fixed

- 修复v16.0架构不一致问题，使initmc正确调用lib/init-workflow.js
- 修复migration-v16.js迁移时未更新命令文件
- 修复review-design.md文件大小检查阈值并支持v16.0双层架构验证
- 将markdown/README.md设置为可选验证项（v15项目兼容）

### 📚 Documentation

- 新增迁移指南-v16.0.md
- 新增可选工具说明.md
- 更新CLAUDE.md至v16.0标准

### 🚀 Performance

- **自动化程度**：95%（仅覆盖层冲突需手动合并）
- **职责隔离**：100%（多项目共用上游时互不影响）
- **兼容性**：Windows/Linux/Mac全平台

---

## [15.0.0] - 2025-11-09

### ✨ Added - 单层文档架构（已废弃）

#### CRITICAL规范前置
- **双端隔离原则**：禁止跨端GetSystem
- **System生命周期**：强制在Create()中初始化
- **模块导入规范**：使用完整路径导入

#### 三步核心工作流
- **步骤1**：理解任务与分级（2分钟）
- **步骤2**：查阅文档（智能路由）
- **步骤3**：执行与收尾

#### 三级任务分类
- 🟢 **微任务**：单文件<30行，直接Edit
- 🟡 **标准任务**：3-8文件，5章模板
- 🔴 **复杂任务**：>8文件/架构，9章模板

### 📚 Documentation

- 开发规范.md（1158行）
- 问题排查.md（1122行）
- 快速开始.md（217行）
- 开发指南.md
- 任务类型决策表.md
- 快速通道流程.md
- 上下文管理规范.md

### ⚠️ Deprecated

- **v15.0架构问题**：
  - 上游更新需要手动复制
  - 项目定制会污染原文件
  - 多项目维护困难
  - v16.0已完全重构解决

---

## [Unreleased]

### 🚧 Planned

#### v16.2 计划
- [ ] npm全局安装支持：`npm install -g netease-mod-claude`
- [ ] GitHub Actions CI/CD集成
- [ ] 自动化测试套件
- [ ] 多语言支持（英文版文档）

#### v17.0 计划
- [ ] Web管理界面（可视化项目配置）
- [ ] 插件系统（支持自定义扩展）
- [ ] 协作功能（团队共享配置）

---

## Version History Summary

| 版本 | 发布日期 | 核心特性 | 状态 |
|------|---------|---------|------|
| **v16.1** | 2025-11-11 | 双重定制架构、/uninstallmc指令 | ✅ 当前版本 |
| **v16.0** | 2025-11-10 | 双层文档架构、可选优化工具 | ✅ 稳定版 |
| **v15.0** | 2025-11-09 | CRITICAL规范、三步工作流 | ⚠️ 已废弃 |

---

## Migration Guide

### v15.0 → v16.0

**自动迁移**：
```bash
cd your-modsdk-project
initmc  # 自动检测v15.0并升级到v16.0
```

**变更**：
- 文档从 `markdown/` 迁移到双层架构
- 自动创建 `.claude/core-docs/` 软连接
- 备份原文档到 `.backup-docs-v15/`

详见：[迁移指南-v16.0.md](./markdown/迁移指南-v16.0.md)

### v16.0 → v16.1

**自动迁移**：
```bash
cd /path/to/NeteaseMod-Claude
git pull origin main

cd your-modsdk-project
initmc --sync  # 同步到v16.1
```

**变更**：
- CLAUDE.md支持项目扩展区变量
- 新增 `/uninstallmc` Slash Command
- 优化官方文档查阅策略

详见：[迁移指南-v16.1.md](./markdown/迁移指南-v16.1.md)

---

## Breaking Changes

### v16.0

- **文档路径变更**：核心文档从 `markdown/` 移动到 `.claude/core-docs/`（软连接）
- **CLAUDE.md格式变更**：新增"文档架构说明"章节
- **initmc行为变更**：默认创建双层架构

### v15.0

- **初次发布**：建立CRITICAL规范和三步工作流

---

## Acknowledgments

### Contributors

- [@jju666](https://github.com/jju666) - 项目维护者
- Claude Code Team - AI辅助开发工具

### Special Thanks

- 网易我的世界MODSDK团队 - 提供官方文档和API
- 基岩版Wiki社区 - 提供原版机制参考
- Claude Code用户社区 - 反馈和建议

---

## License

MIT License - see [LICENSE](./LICENSE) for details

**附加条款**：
- 本项目专为网易我的世界（中国版）MODSDK设计
- 使用时需遵守[网易MODSDK开发协议](https://mc.163.com/dev/)

---

## Links

- **GitHub**: https://github.com/jju666/NeteaseMod-Claude
- **Issues**: https://github.com/jju666/NeteaseMod-Claude/issues
- **Documentation**: [README.md](./README.md)
- **Quick Start**: [快速开始.md](./markdown/快速开始.md)

---

_Last Updated: 2025-11-11_
