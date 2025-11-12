# 📂 项目文档导航

> 📚 **基于Claude的MODSDK开发工作流** - MODSDK项目文档中心
>
> 基于 NeteaseMod-Claude 工作流 v18.1.0

**最后更新**: 2025-11-12

---

## 📊 文档组织结构

本项目采用**双层文档架构**：上游工作流提供基线文档，项目可按需定制。

```
项目文档/
├── .claude/core-docs/       # 上游工作流文档（软连接/只读副本）
│   ├── 核心工作流文档/      # L1必读：开发规范、问题排查、快速开始
│   ├── 概念参考/            # L1速查：MODSDK核心概念、API速查
│   ├── 深度指南/            # L2进阶：完整参考文档
│   └── ai/                  # L3 AI工作流：任务模式策略
├── markdown/core/           # 项目定制文档（覆盖上游基线）
├── markdown/systems/        # 项目System实现文档
└── markdown/                # 项目特定文档（索引、项目状态等）
```

---

## 🚀 快速导航

### L1 核心文档（上游提供 - 必读）

**核心工作流文档** - 防止90%错误

| 文档 | 路径 | 描述 |
|------|------|------|
| ⭐⭐⭐ **开发规范** | [.claude/core-docs/核心工作流文档/开发规范.md](../.claude/core-docs/核心工作流文档/开发规范.md) | 4个CRITICAL规范（双端隔离、System生命周期等） |
| ⭐⭐⭐ **问题排查** | [.claude/core-docs/核心工作流文档/问题排查.md](../.claude/core-docs/核心工作流文档/问题排查.md) | 11个常见问题速查（AttributeError、跨端通信等） |
| ⭐⭐ **快速开始** | [.claude/core-docs/核心工作流文档/快速开始.md](../.claude/core-docs/核心工作流文档/快速开始.md) | 5分钟快速上手、环境搭建 |
| ⭐⭐ **官方文档查询指南** | [.claude/core-docs/核心工作流文档/官方文档查询指南.md](../.claude/core-docs/核心工作流文档/官方文档查询指南.md) | WebFetch使用、网易Wiki导航 |

**概念参考** - 核心概念速查

| 文档 | 路径 | 描述 |
|------|------|------|
| ⭐⭐⭐ **MODSDK核心概念** | [.claude/core-docs/概念参考/MODSDK核心概念.md](../.claude/core-docs/概念参考/MODSDK核心概念.md) | System、Component、Event概念速查 |
| ⭐⭐ **API速查** | [.claude/core-docs/概念参考/API速查.md](../.claude/core-docs/概念参考/API速查.md) | 常用API代码片段 |

---

### L2 深度指南（上游提供 - 按需查阅）

**完整参考文档** - 深入理解高级话题

| 文档 | 适用场景 |
|------|---------|
| [深入理解ECS架构](../.claude/core-docs/深度指南/深入理解ECS架构.md) | 架构设计、系统重构 |
| [事件系统完整参考](../.claude/core-docs/深度指南/事件系统完整参考.md) | 复杂交互、跨端通信 |
| [网络架构与通信](../.claude/core-docs/深度指南/网络架构与通信.md) | 网络同步、多人游戏 |
| [性能优化完整指南](../.claude/core-docs/深度指南/性能优化完整指南.md) | 性能瓶颈、卡顿优化 |
| [数据持久化指南](../.claude/core-docs/深度指南/数据持久化指南.md) | 存档系统、数据存储 |
| [业务系统实现案例](../.claude/core-docs/深度指南/业务系统实现案例.md) | 学习参考、快速开发 |
| [反模式识别清单](../.claude/core-docs/深度指南/反模式识别清单.md) | 代码审查、质量保证 |
| [调试工具与命令](../.claude/core-docs/深度指南/调试工具与命令.md) | 问题调试、性能分析 |
| [配置系统参考](../.claude/core-docs/深度指南/配置系统参考.md) | 配置管理、模块化 |

**完整深度指南索引**: [查看所有深度指南](../.claude/core-docs/深度指南/)

---

### L3 AI辅助文档（上游提供 - AI助手参考）

**AI工作流策略** - 任务执行模式

| 文档 | 描述 |
|------|------|
| [任务模式策略表](../.claude/core-docs/ai/任务模式策略表.md) | Bug修复、新功能、代码理解、性能优化四种模式 |
| [任务类型决策表](../.claude/core-docs/ai/任务类型决策表.md) | 微任务、标准任务、复杂任务三级分类 |
| [快速通道流程](../.claude/core-docs/ai/快速通道流程.md) | 微任务快速执行流程 |
| [上下文管理规范](../.claude/core-docs/ai/上下文管理规范.md) | Tasks目录管理、5章/9章模板 |
| [方案自检清单](../.claude/core-docs/ai/方案自检清单.md) | CRITICAL规范检查、设计评审 |

---

## 🔧 项目特定文档（本地维护）

### Systems文档
- **位置**: `./systems/`
- **职责**: 记录本项目各System的实现细节、架构设计、数据流
- **维护**: 由AI在开发过程中自动生成和更新

**示例**:
- `./systems/ShopServerSystem.md` - 商店系统服务端实现
- `./systems/ExpClientSystem.md` - 经验系统客户端UI

### 项目定制文档（可选）
- **位置**: `./core/`
- **职责**: 覆盖上游基线文档，添加项目特定规范
- **使用场景**: 当上游`开发规范.md`不满足项目需求时

**智能降级机制**:
```
AI查阅"开发规范.md"时:
  1. 优先读取: markdown/core/开发规范.md（项目定制版）
  2. 降级读取: .claude/core-docs/核心工作流文档/开发规范.md（上游基线）
```

**如何定制**:
```bash
# 复制上游文档到项目定制层
cp .claude/core-docs/核心工作流文档/开发规范.md markdown/core/开发规范.md

# 编辑项目定制版本
code markdown/core/开发规范.md

# AI会自动优先读取项目定制版本
```

---

## 💡 使用建议

### 对于新手开发者
1. 阅读 [快速开始](../.claude/core-docs/核心工作流文档/快速开始.md)（5分钟）
2. 理解 [MODSDK核心概念](../.claude/core-docs/概念参考/MODSDK核心概念.md)
3. 遵守 [开发规范](../.claude/core-docs/核心工作流文档/开发规范.md) 中的4个CRITICAL规范
4. 遇到问题查 [问题排查](../.claude/core-docs/核心工作流文档/问题排查.md)

### 对于AI助手
1. 执行任务前先查阅 [任务模式策略表](../.claude/core-docs/ai/任务模式策略表.md)
2. 根据任务类型选择查阅深度:
   - 🟢 微任务: 可选查阅L1核心文档
   - 🟡 标准任务: 必须查阅L1核心 + L2按需
   - 🔴 复杂任务: 完整查阅L1+L2+L3
3. 始终验证 [开发规范](../.claude/core-docs/核心工作流文档/开发规范.md) 中的CRITICAL规范

---

## 🔍 文档搜索

### 使用Grep工具

```bash
# 搜索上游核心文档
Grep("双端隔离", path=".claude/core-docs/", output_mode="content")

# 搜索项目System文档
Grep("商店系统", path="markdown/systems/", output_mode="files_with_matches")

# 搜索所有文档
Grep("性能优化", path="markdown/", output_mode="content", -C=3)
```

### 使用Glob工具

```bash
# 查找项目System文档
Glob("markdown/systems/**/*.md")

# 查找上游深度指南
Glob(".claude/core-docs/深度指南/**/*.md")

# 查找特定主题
Glob("**/Shop*.md")
```

---

## 📈 文档查阅优先级

```
用户任务
  ↓
┌────────────────────────────────────┐
│ 1. 查阅 L1 核心文档                │ → 防止90%错误
│    - 开发规范.md（CRITICAL规范）   │
│    - 问题排查.md（常见问题）       │
├────────────────────────────────────┤
│ 2. 查阅 项目System文档             │ → 理解现有实现
│    - markdown/systems/XXXSystem.md│
├────────────────────────────────────┤
│ 3. 查阅 L2 深度指南（按需）        │ → 深入理解
│    - 深度指南/事件系统完整参考.md │
│    - 深度指南/性能优化完整指南.md │
├────────────────────────────────────┤
│ 4. 查阅 官方文档（按需）           │ → API详细说明
│    - .claude/docs/modsdk-wiki/    │
│    - 或使用WebFetch在线查询        │
└────────────────────────────────────┘
```

---

## 🔄 工作流更新

### 检查更新

```bash
# 执行同步命令
initmc --sync

# 自动完成:
# - 检测上游版本更新
# - 同步上游文档（更新软连接）
# - 智能检测冲突
# - 清理废弃文件（带备份）
```

### 查看上游更新

```bash
# 对比上游与项目定制版
diff .claude/core-docs/核心工作流文档/开发规范.md markdown/core/开发规范.md

# 在VSCode中可视化对比
code --diff .claude/core-docs/核心工作流文档/开发规范.md markdown/core/开发规范.md
```

### 重置到上游版本

```bash
# 删除项目定制版，回退到上游基线
rm markdown/core/开发规范.md

# AI会自动回退到.claude/core-docs/版本
```

---

## 🌟 双层架构优势

| 优势 | 说明 |
|------|------|
| **零风险升级** | 上游更新不影响项目定制 |
| **清晰分层** | 核心工作流 vs 项目特定，一目了然 |
| **按需定制** | 只定制需要的文档，其他保持同步 |
| **完全隔离** | 多项目共用时，互不干扰 |
| **智能降级** | 项目定制 → 上游基线，自动回退 |

---

## 📚 相关资源

- **工作流仓库**: [NeteaseMod-Claude](https://github.com/jju666/NeteaseMod-Claude)
- **官方文档**: [网易MODSDK Wiki](https://github.com/EaseCation/netease-modsdk-wiki)
- **基岩版Wiki**: [Bedrock Wiki](https://github.com/Bedrock-OSS/bedrock-wiki)

---

**文档版本**: v18.1.0
**项目名称**: 基于Claude的MODSDK开发工作流
**最后更新**: 2025-11-12
