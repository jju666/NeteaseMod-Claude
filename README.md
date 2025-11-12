# 基于Claude的MODSDK开发工作流

> **网易我的世界MODSDK项目**
>
> 基于Claude Code AI辅助开发

---

## 🎯 项目简介

General类型MODSDK项目

---

## 🚀 5分钟快速上手

MODSDK开发只需一个核心命令: **`/mc`**

### 场景1: 修复BUG
```bash
/mc 商店购买时返回None错误
```
AI自动: 查问题排查 → 验证CRITICAL规范 → 提供修复方案

### 场景2: 添加新功能
```bash
/mc 添加VIP系统,玩家可以购买VIP获得移动速度加成
```
AI自动: 需求分析 → 设计事件流 → 生成完整代码框架

### 场景3: 性能优化
```bash
/mc 服务器卡顿,优化性能
```
AI自动: 扫描代码 → 检测性能瓶颈 → 提供优化方案

### 场景4: 代码理解
```bash
/mc 解释ShopServerSystem的代码逻辑
```
AI自动: 分析代码 → 绘制数据流 → 输出详细解释

---

## 📚 完整命令列表

**核心命令**:
- `/mc <任务>` - MODSDK开发主命令(90%场景)

**专项工具**:
- `/mc-review` - 方案审查
- `/mc-perf` - 性能分析
- `/mc-docs [--gen]` - 文档验证/生成
- `/mc-why <规范>` - 原理解释
- `/mc-discover` - 项目结构发现

详见: [CLAUDE.md](./CLAUDE.md)

---

## 📚 文档导航

### 核心文档
- **[CLAUDE.md](./CLAUDE.md)** - AI工作流程参考（必读）
- **[开发规范.md](./markdown/开发规范.md)** - CRITICAL规范，防止90%错误
- **[问题排查.md](./markdown/问题排查.md)** - 已知问题和调试技巧

### 系统文档
- **[systems/](./markdown/systems/)** - 系统实现文档

- **[开发指南.md](./markdown/开发指南.md)** - 待补充

### AI辅助文档
- **[任务类型决策表.md](./markdown/ai/任务类型决策表.md)** - 任务分级指南
- **[快速通道流程.md](./markdown/ai/快速通道流程.md)** - 微任务执行
- **[上下文管理规范.md](./markdown/ai/上下文管理规范.md)** - Tasks目录管理

---

## 🔗 关键路径

- **项目根目录**: `d:/EcWork/基于Claude的MODSDK开发工作流`

---

## 📝 开发规范

详见 [开发规范.md](./markdown/开发规范.md)

**CRITICAL规范**（必须遵守）：
1. **双端隔离原则**：使用NotifyToClient/NotifyToServer通信
2. **System生命周期**：在__init__中手动调用self.Create()
3. **模块导入规范**：子目录使用完整路径导入
{{EXTRA_CRITICAL_RULES}}

---

## 🌐 官方资源

### 网易MODSDK文档
- GitHub: https://github.com/EaseCation/netease-modsdk-wiki
- 查询API用法、事件说明、组件文档

### 基岩版Wiki
- GitHub: https://github.com/Bedrock-OSS/bedrock-wiki
- 查询NBT结构、实体属性、原版机制

---

## 📊 项目状态

生产就绪 (Production Ready)

---

## 📄 许可证

本项目遵循网易我的世界MODSDK开发协议。

---

_最后更新: 2025-11-12 | 项目版本: {{PROJECT_VERSION}}_
