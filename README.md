# NeteaseMod-Claude

> **🤖 AI-Powered MODSDK Development Workflow**
>
> Claude Code 驱动的网易我的世界 MODSDK 开发工作流
>
> 一次安装，到处使用 | 自适应项目结构 | 零配置部署

[![Version](https://img.shields.io/badge/version-15.0.0-blue.svg)](./CHANGELOG.md)
[![Node](https://img.shields.io/badge/node-%3E%3D12.0.0-green.svg)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](./LICENSE)

---

## 🎯 项目简介

**NeteaseMod-Claude** 是一个完整的 AI 辅助开发工作流系统，专为网易我的世界 MODSDK 项目设计。它将 Claude Code AI 能力与 MODSDK 开发最佳实践深度融合，通过智能文档系统、任务管理和自适应项目结构发现，大幅提升开发效率和代码质量。

### ✨ 核心特性

- **🧠 AI 驱动开发** - 集成 Claude Code，提供智能代码生成和问题排查
- **📚 完整文档体系** - 涵盖 MODSDK 核心概念、开发规范、API 速查和问题排查
- **🔍 自适应发现** - 自动识别项目结构，零配置适配任意 MODSDK 架构
- **⚡ 快速部署** - 一条命令全局安装，在任意项目中复用
- **📖 智能文档维护** - 自动生成和更新组件文档，保持文档同步
- **🎯 任务分级系统** - 三级任务分类（微任务/标准/复杂），智能评估执行策略

### 🎁 核心价值

✅ **防止 90% 的常见错误** - 内置 CRITICAL 规范，覆盖双端隔离、生命周期、序列化等关键问题
✅ **节省 70% 的文档编写时间** - AI 智能生成和维护组件文档
✅ **提升 3-5 倍开发效率** - 三步核心流程，从任务理解到代码实现的完整指导
✅ **100% 通用兼容** - 适配任意 MODSDK 项目架构（状态机、预设、管理器等）

> ⚠️ **适用范围**: 本项目专注于**网易 MODSDK 通用开发知识**，适用于任意基于网易 MODSDK 的 Mod 项目开发。

---

## 🚀 快速开始

### 📦 安装

```bash
# 1. 克隆项目
git clone https://github.com/jju666/NeteaseMod-Claude.git
cd NeteaseMod-Claude

# 2. 安装依赖（⚠️ 必须执行，不能跳过！）
npm install

# 3. 全局安装（仅需一次）
npm run install-global
```

> ⚠️ **重要提示**：
> - 步骤2的 `npm install` 是**必须的**，不能跳过
> - 跳过会导致运行 `initmc` 时报错：`Error: Cannot find module 'fs-extra'`
> - 从 v15.1 版本开始，`install-global` 脚本会自动检测并安装缺失的依赖

### ⚡ 在你的 MODSDK 项目中使用

```bash
# 1. 进入你的 MODSDK 项目目录
cd /path/to/your-modsdk-project

# 2. 初始化工作流（自动部署配置和文档）
initmc

# 3. 在 Claude Code 中打开项目，执行自适应发现
/discover

# 4. 开始你的第一个任务
/cc 创建一个简单的System，监听玩家加入游戏事件
```

### 🎯 5 分钟快速体验

1. **安装工作流** - 参考 [安装与配置.md](./安装与配置.md)（3分钟）
2. **了解基本概念** - 阅读 [快速开始.md](./markdown/快速开始.md)（5分钟）
3. **查看命令手册** - 参考 [Claude指令参考.md](./Claude指令参考.md)（速查）
4. **开始开发** - 直接使用 `/cc` 命令执行任务

> 💡 **提示**: `initmc` 是终端命令，`/discover` 和 `/cc` 是 Claude Code 中的 Slash 命令

---

## 📚 文档体系

### 📖 新手入门（5分钟起步）

| 文档 | 内容 | 时长 |
|------|------|------|
| [安装与配置.md](./安装与配置.md) | 工作流全局安装和部署指南 | 3分钟 |
| [快速开始.md](./markdown/快速开始.md) | 基本概念和第一个任务 | 5分钟 |
| [Claude指令参考.md](./Claude指令参考.md) | 所有命令的完整说明 | 速查 |

### ⚠️ 核心规范（防止90%错误）

| 文档 | 内容 | 重要性 |
|------|------|--------|
| [开发规范.md](./markdown/开发规范.md) | CRITICAL规范详解（双端隔离、生命周期等） | ⭐⭐⭐⭐⭐ |
| [问题排查.md](./markdown/问题排查.md) | 10个常见问题和解决方案 | ⭐⭐⭐⭐ |

### 🔧 开发参考

| 文档 | 内容 |
|------|------|
| [开发指南.md](./markdown/开发指南.md) | System/Component/Event/Entity 完整开发流程 |
| [API速查.md](./markdown/API速查.md) | 常用API代码片段，可直接复制 ⭐ |
| [MODSDK核心概念.md](./markdown/MODSDK核心概念.md) | System/Component/Event/Entity 速查表 ⭐ |
| [systems/](./markdown/systems/) | 各个 System 的详细实现文档 |

### 🤖 AI工作流（内部参考）

| 文档 | 内容 | 面向对象 |
|------|------|----------|
| [CLAUDE.md](./CLAUDE.md) | AI助手核心工作流配置 | Claude Code |
| [任务类型决策表.md](./markdown/ai/任务类型决策表.md) | 任务分级和执行策略 | AI参考 |
| [快速通道流程.md](./markdown/ai/快速通道流程.md) | 微任务快速执行流程 | AI参考 |
| [上下文管理规范.md](./markdown/ai/上下文管理规范.md) | Tasks 目录管理规范 | AI参考 |

---

## 💡 核心功能

### 🔍 自适应项目结构发现

**零配置，自动识别任意 MODSDK 项目架构**

```bash
# 在 Claude Code 中执行
/discover
```

**工作原理**：
- 🔎 自动扫描项目代码，识别所有 Python 类
- 🧠 区分 MODSDK 官方概念（System、Component）和自定义模式
- 📁 推断文档目录结构和命名规则
- 🗺️ 生成组件到文档路径的映射规则
- 💾 输出到 `.claude/discovered-patterns.json`

**适配能力**：
- ✅ 状态机模式（State 类）
- ✅ 预设模式（Preset 类）
- ✅ 管理器模式（Manager 类）
- ✅ 控制器模式（Controller 类）
- ✅ ...任意项目自定义架构

**性能**：5-10 秒完成，不消耗 Token

> 核心实现：[lib/adaptive-doc-discovery.js](lib/adaptive-doc-discovery.js)（约 500 行，完全基于代码分析）

---

### ⚡ 智能任务执行（/cc 命令）

**一条命令，从需求到实现**

```bash
# 添加新功能
/cc 创建一个计分板系统，显示玩家击杀数

# 修复BUG
/cc 修复玩家登录时的初始化错误

# 优化代码
/cc 优化Update方法，减少不必要的组件查询

# 重构代码
/cc 将商店逻辑从ServerSystem拆分到独立的Manager类
```

**工作流程**（三步核心流程）：
1. **理解任务** - AI 自动分级（微任务/标准/复杂），制定执行计划
2. **查阅文档** - 自动检索相关规范和API，防止常见错误
3. **执行收尾** - 代码实现 → 验证 → 文档更新 → Git commit

详见：[Claude指令参考.md](./Claude指令参考.md)

---

### 📖 智能文档维护

**文档与代码同步，告别文档滞后**

```bash
# 1. 验证文档覆盖率
/validate-docs

# 2. 批量生成文档内容
/enhance-docs
```

**功能**：
- 📊 自动分析代码，识别缺失文档的组件
- 🤖 AI 深度分析源代码，生成完整文档（1500-3000 字）
- 🔄 自动更新文档待补充清单
- 📝 动态适配项目组件类型（基于 `/discover` 结果）

**输出示例**：
- `markdown/系统名称.md` - System 文档
- `markdown/组件名称.md` - Component 文档
- `markdown/自定义模式名称.md` - 项目特定组件文档

---

### 🔍 智能文档检索

**快速找到你需要的信息**

```bash
# 全文搜索
/cc 搜索 双端通信

# 标签搜索
/cc 搜索 tag:性能优化

# 系统搜索
/cc 搜索 system:ShopSystem
```

查看完整索引：[索引.md](./markdown/索引.md)

---

### 🗂️ 任务归档系统

**保持项目整洁，积累开发经验**

```bash
/cc 归档 商店系统开发
# 自动移动到 tasks/completed/
```

**元数据自动提取**：
- 📅 完成时间
- 🏷️ 标签（功能、重构、BUG修复等）
- 📊 复杂度评分
- 🔗 关联的 System/Component

---

## ⚠️ CRITICAL 规范（防止 90% 错误）

**开发前必须了解的 4 条核心规范**：

### 1. 双端隔离原则
```python
# ❌ 错误：在服务端GetSystem获取客户端系统
shop_client = self.GetSystem("ShopClientSystem")  # 返回None!

# ✅ 正确：使用双端通信
self.NotifyToClient(playerId, "EventName", data)
```

### 2. System 生命周期
```python
# ✅ 必须在__init__中手动调用Create()
def __init__(self, namespace, systemName):
    super(MySystem, self).__init__(namespace, systemName)
    self.comp = None  # 只声明
    self.Create()     # 手动调用

def Create(self):
    self.comp = self.GetComponent(...)  # 安全访问
```

### 3. EventData 序列化限制
```python
# ❌ 错误：使用tuple
data["position"] = (100, 64, 100)  # 序列化失败!

# ✅ 正确：使用list
data["position"] = [100, 64, 100]
```

### 4. AOI 感应区范围限制
```python
# ❌ 错误：超过2000格限制
aoi_comp.AddAoi(pos, [3000, 3000, 3000])  # 不生效!

# ✅ 正确：每个维度≤2000
aoi_comp.AddAoi(pos, [2000, 2000, 2000])
```

> 完整规范详见：[开发规范.md](./markdown/开发规范.md)（1330 行，覆盖所有关键问题）

---

## 🏗️ 技术架构

### 核心模块

| 模块 | 文件 | 功能 | 代码行数 |
|------|------|------|---------|
| 自适应发现引擎 | `lib/adaptive-doc-discovery.js` | 扫描项目结构，生成映射规则 | ~500 |
| 工作流初始化器 | `lib/init-workflow.js` | 部署配置和文档到目标项目 | ~400 |
| 智能文档维护 | `lib/intelligent-doc-maintenance.js` | AI驱动的文档生成和更新 | ~600 |
| 文档索引引擎 | `lib/indexer.js` | 构建全局文档索引 | ~300 |
| 智能检索引擎 | `lib/search-engine.js` | 全文检索和相关度排序 | ~400 |
| 项目分析器 | `lib/analyzer.js` | 代码分析和复杂度评估 | ~500 |

**总计**: 约 5000 行纯 JavaScript 实现，零 Python 依赖

### 命令系统

| 命令 | 类型 | 功能 |
|------|------|------|
| `initmc` | 终端命令 | 全局部署工作流（Node.js 脚本） |
| `/discover` | Slash 命令 | 自适应项目结构发现 |
| `/cc` | Slash 命令 | AI 驱动的任务执行 |
| `/validate-docs` | Slash 命令 | 文档覆盖率验证 |
| `/enhance-docs` | Slash 命令 | 批量文档内容生成 |

---

## 🌐 官方资源

### 📚 内置文档（Git Submodule）

工作流内置了官方文档，通过 Git Submodule 管理：

- **网易 MODSDK 文档**: https://github.com/EaseCation/netease-modsdk-wiki
- **基岩版 Wiki**: https://github.com/Bedrock-OSS/bedrock-wiki

**自动部署**：
```bash
# 1. 安装工作流时自动下载文档
npm install  # 自动执行 git submodule update --init --recursive

# 2. 初始化下游项目时自动部署
initmc  # 自动创建 .claude/docs/ 软链接
```

**查询策略**（智能降级）：
1. **优先查询本地文档**（`.claude/docs/`）- 速度快（<1秒）、支持离线
2. **降级到在线查询**（本地文档不存在时）- 使用 WebFetch（5-10秒）

**手动更新文档**：
```bash
cd /path/to/NeteaseMod-Claude
git submodule update --remote  # 更新到最新版本
```

---

## 📊 项目状态

- **项目类型**: 通用 MODSDK 开发工作流
- **目标平台**: 网易我的世界（Python 2.7）
- **AI 引擎**: Claude Code
- **当前版本**: v15.0.0（内联式架构）
- **文档数量**: 14 篇核心文档（约 15000 行）
- **代码规模**: 约 5000 行 JavaScript

详见：[CHANGELOG.md](./CHANGELOG.md) | [项目状态.md](./markdown/项目状态.md)

---

## 🤝 贡献指南

欢迎贡献！请遵循以下原则：

1. **保持通用性** - 不添加项目特定内容
2. **遵循架构** - 维护内联式架构的三段式结构
3. **测试充分** - 确保跨平台兼容（Windows/Mac/Linux）
4. **文档同步** - 代码变更必须更新相关文档

---

## 📞 获取帮助

### 📖 文档资源
- **新手指南**: [快速开始.md](./markdown/快速开始.md)
- **命令手册**: [Claude指令参考.md](./Claude指令参考.md)
- **问题排查**: [问题排查.md](./markdown/问题排查.md)

### 💬 AI 辅助
```bash
# 在 Claude Code 中直接询问
/cc 我遇到了[描述问题]，如何解决？
```

### 🐛 报告问题
- GitHub Issues: [创建 Issue](../../issues)
- 请附上错误信息、项目结构和复现步骤

---

## 📄 许可证

MIT License

本项目遵循 MIT 开源协议，同时需遵守网易我的世界 MODSDK 开发协议。

---

## 🙏 致谢

- **Anthropic Claude** - 提供强大的 AI 能力
- **网易我的世界团队** - MODSDK 开发框架
- **EaseCation** - MODSDK 文档维护

---

<div align="center">

**NeteaseMod-Claude** - 让 AI 成为你的 MODSDK 开发伙伴

⭐ 如果这个项目对你有帮助，请给我们一个 Star！

[快速开始](./markdown/快速开始.md) • [完整文档](./markdown/) • [更新日志](./CHANGELOG.md)

_最后更新: 2025-11-10 | 版本: v15.0.0_

</div>
