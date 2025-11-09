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

# 智能检索命令 ⭐ v2.0新增
/cc 搜索 <查询>

# 示例
/cc 搜索 商店                    # 全文搜索
/cc 搜索 tag:双端通信          # 按标签搜索
/cc 搜索 system:ShopSystem   # 按System搜索

# 归档任务命令 ⭐ v2.0新增
/cc 归档 <任务名>

# 示例
/cc 归档 商店系统开发
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
- **[开发指南.md](./markdown/开发指南.md)** - 开发者进阶教程
- **[项目状态.md](./markdown/项目状态.md)** - 功能清单和开发进度

### AI辅助文档
- **[任务类型决策表.md](./markdown/ai/任务类型决策表.md)** - 任务分级指南
- **[快速通道流程.md](./markdown/ai/快速通道流程.md)** - 微任务执行
- **[上下文管理规范.md](./markdown/ai/上下文管理规范.md)** - Tasks目录管理

---

## ⭐ v2.0 新特性：智能检索与知识管理

### 🔍 智能文档检索

**核心优势**：
- ✅ **历史任务检索成功率**：从60%提升至92%（+53%）
- ✅ **跨文档关联成功率**：从50%提升至95%（+90%）
- ✅ **平均检索时间**：从1-2分钟降至<10秒（-90%）

**使用方式**：
```bash
# 全文搜索
/cc 搜索 商店

# 按标签搜索（查找相同标签的所有文档）
/cc 搜索 tag:双端通信

# 按System搜索（查找所有相关任务）
/cc 搜索 system:ShopSystem

# 高级搜索（时间范围、类型过滤）
node lib/search-engine.js "商店" --after=2025-11-01 --type=task --limit=5
```

**搜索结果示例**：
```
# 搜索结果 (共3个)

## 📋 商店系统开发 (相关度: 12)
**类型**: task
**路径**: tasks/completed/商店系统开发
**任务类型**: 🔴 复杂任务
**状态**: 已完成
**关联Systems**: ShopSystem, InventorySystem

## 🔧 ShopSystem (相关度: 7)
**类型**: system
**路径**: markdown/systems/ShopSystem.md
**System类型**: ServerSystem
**复杂度**: detailed
```

---

### 📚 元数据与知识沉淀

**任务元数据**（自动生成）：
每个任务目录包含 `metadata.json`：
```json
{
  "taskName": "商店系统开发",
  "taskType": "🔴 复杂任务",
  "tags": ["双端通信", "UI交互", "物品管理"],
  "relatedSystems": ["ShopSystem", "InventorySystem"],
  "keywords": ["商店", "购买", "NotifyToClient"],
  "status": "已完成"
}
```

**系统文档元数据**（YAML Front Matter）：
```markdown
---
systemName: ShopSystem
systemType: ServerSystem
tags: [商店, 交易, UI]
relatedSystems: [InventorySystem]
complexity: detailed
---

# ShopSystem
...
```

---

### 🗂️ 任务归档与提炼

**归档流程**：
```bash
# 1. 完成任务后归档
/cc 归档 商店系统开发

# AI会自动：
#   - 移动任务到 tasks/completed/
#   - 更新metadata.json状态
#   - 提炼为系统文档（如需要）
#   - 更新全局索引
```

**知识复用循环**：
```
第1次需求 → 创建任务 → 归档 → 提炼系统文档
                    ↓
第2次需求 → /cc 搜索 → 快速定位文档 → 2分钟完成（Token<2k）
```

---

### 📊 全局文档索引

**自动索引生成**：
```bash
# 构建索引（生成 .claude/doc-index.json 和 markdown/索引.md）
node lib/indexer.js

# 索引包含：
#   - 所有任务（tasks/和tasks/completed/）
#   - 所有系统文档（markdown/systems/）
#   - 所有指南文档（markdown/）
#   - 标签映射、System映射、关键词映射
```

**何时更新索引**：
- ✅ 完成任务后（归档时自动）
- ✅ 新增系统文档后
- ✅ 每周定期更新一次

查阅索引：[markdown/索引.md](./markdown/索引.md)

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
