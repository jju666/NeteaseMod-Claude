# /initmc - 初始化网易MODSDK工作流

自动部署完整的AI辅助开发工作流到当前项目。

## 描述

分析当前MODSDK项目并生成定制化的工作流文档，包括：
- CLAUDE.md（AI工作流程）
- /cc 命令（快速任务执行器）
- 开发规范、问题排查等文档
- Systems技术文档

## 用法

```bash
/initmc
```

---

## 执行流程

你需要执行以下Node.js脚本来初始化工作流：

### 步骤1：运行初始化脚本

```bash
node ~/.claude-modsdk-workflow/lib/init-workflow.js
```

### 步骤2：等待完成

脚本将自动执行以下操作：

1. **分析项目**
   - 检测项目类型（RPG/BedWars/General）
   - 扫描所有Systems和Presets
   - 计算复杂度和项目规模
   - 生成分析报告

2. **生成文档**
   - Layer 1（通用层）: CLAUDE.md、开发规范.md等
   - Layer 2（架构层）: Systems技术文档
   - Layer 3（业务层）: 业务文档框架
   - 生成定制化的 /cc 命令

3. **输出报告**
   - 显示生成统计
   - 列出可用命令
   - 提示后续步骤

### 步骤3：验证结果

检查是否生成以下文件：

```
✅ CLAUDE.md
✅ .claude/commands/cc.md
✅ markdown/开发规范.md
✅ markdown/问题排查.md
✅ markdown/systems/ （多个系统文档）
```

---

## 错误处理

### 错误1：未检测到modMain.py

```
❌ 错误: 当前目录不是MODSDK项目
```

**解决方案**：在项目根目录执行 /initmc

### 错误2：全局工作流未安装

```
❌ 错误: 无法找到全局工作流
```

**解决方案**：
1. 确认已运行全局安装
2. 检查 `~/.claude-modsdk-workflow/` 是否存在

---

## 注意事项

- ⏱️ 首次执行耗时：小项目5分钟，大项目可能需要15分钟
- 📝 Layer 1文档直接可用，Layer 2需补充，Layer 3是框架
- 🔄 AI会在后续开发中逐步完善文档

---

现在执行 /initmc 命令！
