# 基于Claude的MODSDK开发工作流

> **网易我的世界MODSDK项目**
>
> 基于Claude Code AI辅助开发

---

## 🎯 项目简介

General类型MODSDK项目

---

## 🚀 快速开始

### 开发环境

- Python 2.7
- 网易我的世界开发者工具
- MODSDK

### 使用Claude Code开发

**核心命令**：
```bash
# 快速执行任务
/cc [任务描述]

# 示例
/cc 修复System初始化错误
/cc 添加新功能模块
/cc 优化代码性能
/cc 日志显示错误
```

**工作流程**：
1. 查阅 [CLAUDE.md](./CLAUDE.md) 了解AI工作流程
2. 使用 `/cc` 命令快速创建/继续任务
3. AI会自动查阅文档、遵循规范、记录修改

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

- **项目根目录**: `{{PROJECT_ROOT}}`

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

{{PROJECT_STATUS}}

---

## 📄 许可证

本项目遵循网易我的世界MODSDK开发协议。

---

_最后更新: 2025-11-09 | 项目版本: {{PROJECT_VERSION}}_
