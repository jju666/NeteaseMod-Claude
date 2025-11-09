# 更新日志

## v2.3.0 - 2025-11-09 (当前版本)

### MODSDK纯化重构 🎯

**核心文档完全重构** - 移除所有项目特定内容
- ✅ 开发规范.md (960→1330行, +38%) - 新增Component规范、Entity管理、EventData限制、AOI限制
- ✅ 开发指南.md (831→1636行, +97%) - 完整System/Component/Event/Entity开发流程
- ✅ 问题排查.md (232→712行, +206%) - 扩展到10个MODSDK常见问题
- ✅ 快速开始.md (216→327行, +51%) - 新增热重载机制、双端开发技巧
- ✅ CLAUDE.md (v13.0) - CRITICAL规范扩充为4条，快速索引14条

**移除项目特定内容**
- ❌ ECPreset/Preset系统（6处引用）
- ❌ GamingState状态机（5处引用）
- ❌ BedWars示例（替换为通用MyMod示例）

**CRITICAL规范扩充**
- ⛔ 规范3: EventData序列化限制（禁止tuple）
- ⛔ 规范4: AOI感应区范围限制（最大2000格）

**文档纯度**: 100%聚焦MODSDK通用开发知识

**补充文档（方案B）**
- ✅ MODSDK核心概念.md (新增，400行) - System/Component/Event/Entity速查
- ✅ API速查.md (新增，600行) - 常用API代码片段
- ✅ 任务类型决策表.md (v2.0) - 移除项目特定示例
- ✅ 快速通道流程.md (v2.0) - 移除商店相关示例
- ✅ Claude指令参考.md (v2.0) - 替换所有项目特定示例

---

## v2.2.0 - 2025-11-09

### 核心特性

**全局安装机制** - 一次安装，到处使用
- 通过 `npm run install-global` 安装到用户目录
- 使用 `modsdk-deploy` 命令快速部署到任意项目
- 跨平台支持 (Windows/Mac/Linux)

**智能检索与文档关联系统**
- 元数据标准化系统 (`lib/metadata-schema.js`)
- 全局文档索引 (`lib/indexer.js`)
- 智能检索引擎 (`lib/search-engine.js`)
- 新增 `/search` 和 `/archive` 命令

**纯JavaScript实现** - 无Python依赖
- `lib/analyzer.js` - 项目分析器
- `lib/generator.js` - 文档生成器
- `lib/init-workflow.js` - 工作流初始化器
- 完整的模板系统

### 核心功能

1. `/initmc` - 工作流初始化器
   - 自动分析项目类型和规模
   - 生成定制化的CLAUDE.md
   - 创建完整的文档结构

2. `/search` - 智能文档检索
   - 全文搜索、标签搜索、System搜索
   - 智能相关度排序

3. `/archive` - 任务归档
   - 一键归档已完成任务
   - 自动生成元数据

4. `modsdk-deploy` - 快速部署
   - 将工作流部署到任意项目

### 技术亮点

- 跨平台路径处理
- 智能复杂度评估
- 文档索引与检索
- 元数据自动提取

---

_最后更新: 2025-11-09 | 版本: v2.2.0_
