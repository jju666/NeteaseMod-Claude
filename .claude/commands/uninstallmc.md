---
description: 从当前项目卸载 MODSDK 工作流，清理所有由 initmc 部署的文件
version: 16.0
---

# /uninstallmc - 卸载 MODSDK 工作流

**功能**: 从当前项目中移除所有由 `initmc` 部署的工作流文件，恢复项目到未部署状态。

---

## 📋 执行流程

### 步骤1: 加载卸载工具

```bash
node lib/uninstall-workflow.js --dry-run
```

### 步骤2: 预览将要删除的文件

AI会输出完整的文件清单，包括：
- 📋 命令文件（.claude/commands/）
- 📚 文档文件（markdown/）
- 🔧 工具库（lib/）
- ⚙️ 配置文件（CLAUDE.md、workflow-version.json等）

### 步骤3: 询问用户确认

使用 `AskUserQuestion` 工具询问用户：

```markdown
检测到以下工作流文件将被删除：

[文件清单]

⚠️ 重要提示：
- 所有文件会自动备份到 `.backup-uninstall-YYYY-MM-DD/`
- 用户文件（tasks/、markdown/systems/ 等）不会被删除
- 可从备份恢复

**问题1**: 是否删除 CLAUDE.md？
  - 选择"是"：连同 CLAUDE.md 一起删除
  - 选择"否"：保留 CLAUDE.md（推荐）

**问题2**: 确认执行卸载？
  - 输入"yes"继续
  - 输入"no"取消
```

### 步骤4: 执行卸载

根据用户回答：

```bash
# 如果用户选择删除 CLAUDE.md
node lib/uninstall-workflow.js --remove-claude-md

# 如果用户选择保留 CLAUDE.md
node lib/uninstall-workflow.js
```

### 步骤5: 输出卸载报告

显示：
- ✅ 已删除的文件数量
- 💾 释放的磁盘空间
- 📁 备份位置
- ✅ 保留的用户文件

---

## 🔒 安全机制

1. **自动备份**：所有文件删除前自动备份到 `.backup-uninstall-YYYY-MM-DD/`
2. **用户文件保护**：以下文件/目录永不删除
   - `tasks/` - 用户任务记录
   - `markdown/systems/` - 用户编写的组件文档
   - `markdown/states/` - 状态文档
   - `markdown/presets/` - 预设文档
   - `.claude/discovered-patterns.json` - 项目结构发现结果

3. **预览模式**：使用 `--dry-run` 仅预览，不执行删除

---

## 🎯 使用场景

| 场景 | 操作 |
|------|------|
| 彻底移除工作流 | `/uninstallmc` |
| 清理后重新部署 | `/uninstallmc` → `initmc` |
| 升级到新版本 | `initmc --sync`（推荐）或 `/uninstallmc` → `initmc` |
| 测试工作流 | `initmc` → 测试 → `/uninstallmc` |

---

## 💡 常见问题

### Q1: 卸载会删除我的代码吗？

**不会**。卸载只删除工作流文件，以下内容始终保留：
- ✅ 您的 Python 代码（modMain.py、各种 System 等）
- ✅ tasks/ 目录中的任务记录
- ✅ markdown/systems/ 等用户文档
- ✅ 项目配置（manifest.json 等）

### Q2: 误删了怎么办？

所有文件都备份在 `.backup-uninstall-YYYY-MM-DD/` 目录，直接复制回来即可。

### Q3: 能否只删除部分文件？

暂不支持。如需保留某些文件，请：
1. 先执行 `/uninstallmc`
2. 从备份中复制需要的文件

### Q4: 卸载后如何重新部署？

直接运行 `initmc` 即可重新部署工作流。

---

## 📝 注意事项

1. **CLAUDE.md 处理**：
   - 如果您在 CLAUDE.md 中添加了自定义内容，建议选择"保留"
   - 如果您想完全清理，可以选择"删除"

2. **备份清理**：
   - 备份目录不会自动删除
   - 确认卸载成功后，可手动删除备份目录释放空间

3. **升级建议**：
   - 如需升级工作流，推荐使用 `initmc --sync` 而非卸载重装
   - `--sync` 模式会保留用户内容，仅更新工作流文件

---

## 🔄 相关命令

- `initmc` - 部署/更新工作流
- `initmc --sync` - 同步更新工作流（推荐升级方式）
- `npm run uninstall` - 卸载全局工作流（从系统中移除 initmc 命令）
