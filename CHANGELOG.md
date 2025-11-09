# 更新日志

## v2.2.0 - 2025-11-09 (当前版本)

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
