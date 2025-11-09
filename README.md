# 基于Claude的MODSDK开发工作流

> **网易我的世界MODSDK项目**
>
> 基于Claude Code AI辅助开发

---

## 🎯 项目简介

General类型MODSDK项目，使用AI辅助开发工作流，提升开发效率和代码质量。

> ⚠️ **文档说明**: 本项目文档专注于**网易MODSDK通用开发知识**，适用于任意MODSDK项目开发。文档不包含特定游戏项目的实现细节。

---

## 🚀 快速上手

### 🔰 新手三步走

1. **[安装与配置](./安装与配置.md)** - 全局安装工作流（5分钟）
2. **[快速开始](./markdown/快速开始.md)** - 了解基本流程（5分钟）
3. **[Claude指令参考](./Claude指令参考.md)** - 掌握常用命令（速查）

### ⚡ 立即开始

```bash
# 1. 全局安装工作流（仅需一次）
npm run install-global

# 2. 在任意MODSDK项目中初始化
/initmc

# 3. 执行第一个任务
/cc 创建一个简单的System，监听玩家加入游戏事件
```

---

## 📚 完整文档导航

### 📖 入门文档（必读）

| 文档 | 用途 | 阅读时间 |
|------|------|----------|
| **[安装与配置.md](./安装与配置.md)** | 全局安装与部署 | 5分钟 |
| **[快速开始.md](./markdown/快速开始.md)** | 快速入门教程 | 5分钟 |
| **[Claude指令参考.md](./Claude指令参考.md)** | 指令完整说明 | 速查 |

### ⚠️ 核心规范（必学）

| 文档 | 用途 | 重要性 |
|------|------|--------|
| **[开发规范.md](./markdown/开发规范.md)** | CRITICAL规范详解 | ⭐⭐⭐⭐⭐ |
| **[CLAUDE.md](./CLAUDE.md)** | AI工作流程配置 | ⭐⭐⭐⭐⭐ |

### 🔧 开发文档

| 文档 | 用途 |
|------|------|
| **[开发指南.md](./markdown/开发指南.md)** | 进阶开发教程 |
| **[问题排查.md](./markdown/问题排查.md)** | 调试和问题解决 |
| **[项目状态.md](./markdown/项目状态.md)** | 功能清单和进度 |

### 📁 系统文档

- **[systems/](./markdown/systems/)** - 各系统的详细实现文档

### 🤖 AI辅助文档

| 文档 | 用途 | 面向对象 |
|------|------|----------|
| **[任务类型决策表.md](./markdown/ai/任务类型决策表.md)** | 任务分级指南 | AI参考 |
| **[快速通道流程.md](./markdown/ai/快速通道流程.md)** | 微任务流程 | AI参考 |
| **[上下文管理规范.md](./markdown/ai/上下文管理规范.md)** | Tasks管理 | AI参考 |

---

## 💡 核心功能

### ⚡ 智能任务执行

使用 `/cc` 命令执行任何开发任务：

```bash
# 修复BUG
/cc 修复System初始化错误

# 添加功能
/cc 添加玩家死亡事件监听

# 优化代码
/cc 优化Update方法性能
```

详见：[Claude指令参考.md](./Claude指令参考.md)

### 🔍 智能文档检索

快速查找相关文档和历史任务：

```bash
/cc 搜索 双端通信          # 全文搜索
/cc 搜索 tag:性能优化      # 按标签搜索
/cc 搜索 system:ShopSystem # 按System搜索
```

### 🗂️ 任务归档

一键归档已完成任务，保持项目整洁：

```bash
/cc 归档 商店系统开发
# 自动移动到 tasks/completed/
```

---

## ⚠️ CRITICAL规范速览

开发前必须了解：

1. **双端隔离原则** - 禁止跨端GetSystem，使用NotifyToClient/NotifyToServer
2. **System生命周期** - 在__init__中手动调用self.Create()
3. **模块导入规范** - 子目录使用完整路径导入

详见：[开发规范.md](./markdown/开发规范.md)

---

## 🌐 官方资源

- **网易MODSDK文档**: https://github.com/EaseCation/netease-modsdk-wiki
- **基岩版Wiki**: https://github.com/Bedrock-OSS/bedrock-wiki

Claude会自动使用WebFetch查询在线文档，保证信息最新。

---

## 📊 项目信息

- **项目类型**: General MODSDK
- **Python版本**: 2.7
- **AI辅助**: Claude Code
- **文档版本**: v12.0

详见：[项目状态.md](./markdown/项目状态.md)

---

## 📞 获取帮助

### 文档资源
- **快速入门**: [快速开始.md](./markdown/快速开始.md)
- **指令速查**: [Claude指令参考.md](./Claude指令参考.md)
- **问题排查**: [问题排查.md](./markdown/问题排查.md)

### AI辅助
```bash
# 遇到问题直接询问
/cc 我遇到了[描述问题]，如何解决？
```

---

## 📄 许可证

本项目遵循网易我的世界MODSDK开发协议。

---

_最后更新: 2025-11-09 | 文档版本: v12.0_
