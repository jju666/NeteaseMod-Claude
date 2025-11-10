# 更新日志

## v2.1.0 - 2025-11-10 (当前版本)

### 真·自适应机制实现 🎯

**核心引擎完成（方案A）**
- ✅ **lib/adaptive-doc-discovery.js** - 自动扫描项目结构的核心引擎
- ✅ **Windows兼容** - 使用Node.js原生API替代grep/find命令
- ✅ **零配置** - 完全基于代码分析，无需手动配置

**新增命令**
- ✅ **/discover** - 自适应项目结构发现
  - 自动识别MODSDK官方概念（System、Component）
  - 智能推断项目自定义模式（State、Preset、Manager等）
  - 推断文档目录结构
  - 生成 `.claude/discovered-patterns.json` 映射文件
  - 5-10秒完成，不消耗Token

**集成到现有工具**
- ✅ **/validate-docs** - 动态读取discovered-patterns.json
- ✅ **/enhance-docs** - 自适应生成文档路径和选项

**文档更新**
- ✅ CLAUDE.md (v14.1) - 添加/discover命令说明和工作流程
- ✅ 安装与配置.md - 补充首次配置的/discover步骤
- ✅ README.md - 添加/discover功能说明

**技术亮点**
- 📦 自动识别任意项目架构
- 🔮 智能推断文档路径映射规则
- 📁 适配任意MODSDK项目（状态机、预设、管理器等任意模式）
- 🗺️ 完全通用，100%零配置

---

## v2.0.0 - 2025-11-09

### MODSDK纯化重构 🎯

**核心文档完全重构** - 移除所有项目特定内容
- ✅ 开发规范.md (960→1330行, +38%) - 新增Component规范、Entity管理、EventData限制、AOI限制
- ✅ 开发指南.md (831→1636行, +97%) - 完整System/Component/Event/Entity开发流程
- ✅ 问题排查.md (232→712行, +206%) - 扩展到10个MODSDK常见问题
- ✅ 快速开始.md (216→327行, +51%) - 新增热重载机制、双端开发技巧
- ✅ CLAUDE.md (v13.0→v14.0) - CRITICAL规范扩充为4条，快速索引14条

**移除项目特定内容**
- ❌ ECPreset/Preset系统（6处引用）
- ❌ GamingState状态机（5处引用）
- ❌ BedWars示例（替换为通用MyMod示例）

**CRITICAL规范扩充**
- ⛔ 规范3: EventData序列化限制（禁止tuple）
- ⛔ 规范4: AOI感应区范围限制（最大2000格）

**文档纯度**: 100%聚焦MODSDK通用开发知识

**补充文档**
- ✅ MODSDK核心概念.md (新增，400行) - System/Component/Event/Entity速查
- ✅ API速查.md (新增，600行) - 常用API代码片段
- ✅ 任务类型决策表.md (v2.0) - 移除项目特定示例
- ✅ 快速通道流程.md (v2.0) - 移除商店相关示例
- ✅ Claude指令参考.md (v2.0) - 替换所有项目特定示例

---

## v1.0.0 - 2025-11-09

### 全局安装机制与部署脚本

**废弃AI驱动的/initmc** - 使用独立脚本替代
- ❌ 废弃 `/initmc` slash command（可靠性问题、执行时间长）
- ✅ 新增全局命令 `initmc`（使用Node.js脚本，10-30秒完成）
- ✅ 100%可靠的文件复制（自动验证，防止空文件）

**全局安装机制** - 一次安装，到处使用
- 通过 `npm run install-global` 安装到用户目录
- 使用 `initmc` 命令快速部署到任意项目
- 跨平台支持 (Windows/Mac/Linux)

**智能检索与文档关联系统**
- 元数据标准化系统 (`lib/metadata-schema.js`)
- 全局文档索引 (`lib/indexer.js`)
- 智能检索引擎 (`lib/search-engine.js`)
- AI辅助搜索和归档功能

**纯JavaScript实现** - 无Python依赖
- `lib/analyzer.js` - 项目分析器
- `lib/generator.js` - 文档生成器
- `lib/init-workflow.js` - 工作流初始化器
- `scripts/initmc.js` - 部署脚本（核心逻辑）
- `bin/initmc.js` - 全局命令入口

### 核心功能

1. 全局命令 `initmc` - 快速部署脚本
   - 使用Node.js脚本（不是slash command）
   - 10-30秒完成部署
   - 自动验证文件复制
   - 定制化配置（自动替换项目路径占位符）

2. AI辅助搜索 - 智能文档检索
   - 通过 `/cc 搜索 [关键词]` 使用
   - 全文搜索、标签搜索、System搜索
   - 智能相关度排序（需先构建索引）

3. AI辅助归档 - 任务归档
   - 通过 `/cc 归档 [任务名]` 使用
   - 一键归档已完成任务
   - 自动生成元数据

### 技术亮点

- 跨平台路径处理
- 智能复杂度评估
- 文档索引与检索
- 元数据自动提取

---

_最后更新: 2025-11-10 | 版本: v2.1.0_
