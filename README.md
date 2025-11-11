# NeteaseMod-Claude

> **🤖 AI-Powered MODSDK Development Workflow**
>
> Claude Code 驱动的网易我的世界 MODSDK 开发工作流
>
> 一次安装，到处使用 | 自适应项目结构 | 零配置部署

[![Version](https://img.shields.io/badge/version-16.0.0-blue.svg)](./CLAUDE.md#📝-版本信息)
[![Node](https://img.shields.io/badge/node-%3E%3D12.0.0-green.svg)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen.svg)](./LICENSE)

---

## 🎯 项目简介

**NeteaseMod-Claude** 是一个完整的 AI 辅助开发工作流系统，专为网易我的世界 MODSDK 项目设计。通过智能文档系统、任务管理和自适应项目结构发现，大幅提升开发效率和代码质量。

### ✨ 核心特性

- **🧠 AI 驱动开发** - 集成 Claude Code，提供智能代码生成和问题排查
- **📚 双层文档架构** ⭐ v16.0 - 上游基线 + 项目覆盖层，零风险升级，按需定制
- **🔍 自适应发现** - 自动识别项目结构，零配置适配任意 MODSDK 架构
- **⚠️ CRITICAL 规范** - 内置4条高危规范，防止90%的常见错误
- **🎯 智能任务分级** - 三级任务分类（微任务/标准/复杂），自动评估执行策略

### 🎁 核心价值

✅ **防止 90% 的常见错误** - CRITICAL 规范覆盖双端隔离、生命周期、序列化等关键问题
✅ **节省 70% 的文档编写时间** - AI 智能生成和维护组件文档
✅ **提升 3-5 倍开发效率** - 三步核心流程，从任务理解到代码实现的完整指导
✅ **100% 通用兼容** - 适配任意 MODSDK 项目架构（状态机、预设、管理器等）

> ⚠️ **适用范围**: 本项目专注于**网易 MODSDK 通用开发知识**，适用于任意基于网易 MODSDK 的 Mod 项目开发。

---

## 🚀 5分钟快速上手

### 步骤1: 安装工作流（2分钟）

```bash
# 1. 克隆项目
git clone https://github.com/jju666/NeteaseMod-Claude.git
cd NeteaseMod-Claude

# 2. 安装依赖（⚠️ 必须执行，不能跳过！）
npm install

# 3. 全局安装（仅需一次）
npm run install-global
```

> ⚠️ **Windows用户特别注意**: 安装后需配置PATH环境变量才能使用 `initmc` 命令。
> 详见下方 [常见问题 → Q1: 找不到 initmc 命令](#q1-执行-initmc-提示-找不到命令)

### 步骤2: 部署到项目（30秒）

```bash
# 1. 进入你的 MODSDK 项目目录（包含 modMain.py 的目录）
cd /path/to/your-modsdk-project

# 2. 执行部署命令
initmc

# 3. 等待部署完成（约10-30秒）
```

### 步骤3: 开始开发（1分钟）

```bash
# 在 Claude Code 中执行以下命令

# 1. 自适应发现项目结构（5-10秒，零Token消耗）
/discover

# 2. 开始你的第一个任务
/cc 创建一个简单的System，监听玩家加入游戏事件
```

**🎉 完成！现在你可以使用AI辅助开发了！**

---

## 📚 文档导航

### 🚀 新手必读（5分钟起步）

| 文档 | 内容 | 时长 |
|------|------|------|
| [快速开始.md](./markdown/快速开始.md) | 基本概念和第一个任务 | 5分钟 |
| [指令速查表](#📝-指令速查表) | 常用命令快速参考 | 1分钟 |

### ⚠️ 核心规范（防止90%错误）

| 文档 | 内容 | 重要性 |
|------|------|--------|
| [CRITICAL规范速览](#⚠️-critical规范速览) | 4条高危规范代码示例 | ⭐⭐⭐⭐⭐ |
| [开发规范.md](./markdown/开发规范.md) | CRITICAL规范详解（双端隔离、生命周期等） | ⭐⭐⭐⭐⭐ |
| [问题排查.md](./markdown/问题排查.md) | 10个常见问题和解决方案 | ⭐⭐⭐⭐ |

### 🔧 开发参考

| 文档 | 内容 |
|------|------|
| [API速查.md](./markdown/API速查.md) | 常用API代码片段，可直接复制 ⭐ |
| [MODSDK核心概念.md](./markdown/MODSDK核心概念.md) | System/Component/Event/Entity 速查表 ⭐ |
| [开发指南.md](./markdown/开发指南.md) | System/Component/Event/Entity 完整开发流程 |

### 🤖 AI工作流（内部参考）

| 文档 | 内容 | 面向对象 |
|------|------|----------|
| [CLAUDE.md](./CLAUDE.md) | AI助手核心工作流配置 | Claude Code |
| [任务类型决策表.md](./markdown/ai/任务类型决策表.md) | 任务分级和执行策略 | AI参考 |
| [上下文管理规范.md](./markdown/ai/上下文管理规范.md) | Tasks 目录管理规范 | AI参考 |

### 🔧 技术细节

| 文档 | 内容 |
|------|------|
| [快速参考.md](./快速参考.md) | 技术架构、命令系统、官方资源 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本更新日志 |

---

## 💡 核心功能

### 1️⃣ 自适应项目结构发现 ⭐ v16.0

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

**性能**：5-10 秒完成，不消耗 Token

---

### 2️⃣ 智能任务执行

**一条命令，从需求到实现**

```bash
# 添加新功能
/cc 创建一个计分板系统，显示玩家击杀数

# 修复BUG
/cc 修复玩家登录时的初始化错误

# 优化代码
/cc 优化Update方法，减少不必要的组件查询
```

**工作流程**（三步核心流程）：
1. **理解任务** - AI 自动分级（微任务/标准/复杂），制定执行计划
2. **查阅文档** - 自动检索相关规范和API，防止常见错误
3. **执行收尾** - 代码实现 → 验证 → 文档更新 → Git commit

---

### 3️⃣ 智能文档维护

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

---

## ⚠️ CRITICAL规范速览

**开发前必须了解的 4 条核心规范**

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

## 📝 指令速查表

| 指令 | 功能 | 示例 |
|------|------|------|
| `initmc` | 全局部署工作流（终端命令） | `initmc` |
| `initmc --sync` | 同步更新工作流 ⭐ v16.0 | `initmc --sync` |
| `/discover` | 自适应项目结构发现 | `/discover` |
| `/cc [任务]` | 执行任务 | `/cc 修复BUG` |
| `/validate-docs` | 验证文档完整性 | `/validate-docs` |
| `/enhance-docs` | 批量生成文档内容 | `/enhance-docs` |

完整命令说明：[Claude指令参考.md](./Claude指令参考.md)

---

## ❓ 常见问题

### Q1: 执行 `initmc` 提示 "找不到命令"

**原因**: Windows用户目录未添加到PATH环境变量中

**解决方案（Windows）**:

1. 按 `Win+R`，输入 `sysdm.cpl`，回车
2. 点击"高级"选项卡 → "环境变量"
3. 在"用户变量"区域找到"Path"，双击编辑
4. 点击"新建"，添加：`C:\Users\你的用户名`
5. 点击"确定"保存
6. **重新打开终端**（必须重启终端才能生效）

验证是否生效：
```bash
where initmc
# 应显示: C:\Users\你的用户名\initmc.cmd
```

### Q2: 执行 `initmc` 提示 "Error: Cannot find module 'fs-extra'"

**原因**: 跳过了 `npm install` 步骤

**解决方案**:
```bash
# 1. 进入工作流项目目录
cd <工作流项目目录>

# 2. 安装依赖
npm install

# 3. 重新执行全局安装
npm run install-global
```

### Q3: 如何更新工作流到最新版本？

**方案1: 同步更新（推荐）** ⭐ v16.0
```bash
# 在任意 MODSDK 项目中执行
initmc --sync
```

**方案2: 手动更新**
```bash
# 1. 拉取最新代码
cd <工作流项目目录>
git pull

# 2. 安装新依赖
npm install

# 3. 重新全局安装
npm run install-global

# 4. 在MODSDK项目中重新部署
cd <MODSDK项目目录>
initmc
```

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

## 🤝 贡献指南

欢迎贡献！请遵循以下原则：

1. **保持通用性** - 不添加项目特定内容
2. **遵循架构** - 维护双层文档架构
3. **测试充分** - 确保跨平台兼容（Windows/Mac/Linux）
4. **文档同步** - 代码变更必须更新相关文档

---

## 📝 版本信息

> **当前版本**: v16.0 (双层文档架构)
> **最后更新**: 2025-11-11
> **项目状态**: 生产就绪 (Production Ready)

### v16.0 更新亮点 ⚡

**双层文档架构（全新升级）**：
- ✅ **上游基线层**: `.claude/core-docs/` 软连接到上游，自动同步更新
- ✅ **项目覆盖层**: `markdown/core/` 支持项目定制，互不干扰
- ✅ **智能路由**: AI自动选择项目定制版或上游基线版
- ✅ **自动迁移**: v15.x项目执行 `initmc` 自动升级到v16.0
- ✅ **完全隔离**: 多项目共用上游时，职责100%隔离

**用户体验改进**：
- 📁 下游项目文档从10+个文件减少到3-5个（-67%）
- 🔄 一键同步：`initmc --sync` 自动更新工作流
- 📝 按需定制：需要编辑核心文档时，AI自动创建覆盖层

详见：[CHANGELOG.md](./CHANGELOG.md)

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

_最后更新: 2025-11-11 | 版本: v16.0_

</div>
