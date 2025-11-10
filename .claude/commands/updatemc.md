# /updatemc - 智能合并CLAUDE.md备份差异

检测CLAUDE.md备份文件，智能合并用户修改到新版本。

---

## ⚠️ 重要提示

**建议开启计划模式**：

本命令会执行文件对比、智能分析、合并操作等多个步骤。
为了让您清楚了解整个合并流程，**强烈建议在计划模式下执行**：

1. 点击输入框左侧的 **"计划"** 按钮（或按 `Ctrl+Shift+P`）
2. 输入 `/updatemc`
3. 查看并确认合并计划
4. 退出计划模式，开始执行

这样可以：
- ✅ 提前预览完整的合并策略
- ✅ 确认哪些内容会被保留/替换
- ✅ 避免意外覆盖重要修改
- ✅ 节省Token（计划模式不消耗额外Token）

---

## 🎯 使用场景

当您执行 `initmc` 部署工作流后，如果看到备份提示：

```
📦 备份原文件: CLAUDE.md.backup.2025-11-10
```

说明您之前修改过 CLAUDE.md，现在可以使用 `/updatemc` 智能合并您的修改。

---

## 📋 执行流程

### 步骤1：检测备份文件

```bash
# 自动检测最新的备份文件
ls CLAUDE.md.backup.*
```

### 步骤2：对比差异

使用 `diff` 或 `Read` 工具对比：
- `CLAUDE.md.backup.YYYY-MM-DD` （旧版本 + 用户修改）
- `CLAUDE.md` （新版本模板）

### 步骤3：智能分析

AI 会分析差异，区分：
- ✅ **用户自定义内容** - 需要保留
  - 项目特定的AI指令
  - 自定义工作流程
  - 特殊开发规范
  - 项目路径调整

- ❌ **模板更新内容** - 应该使用新版本
  - 版本号更新
  - 新增功能说明
  - BUG修复
  - 文档结构优化

### 步骤4：智能合并

生成合并后的 CLAUDE.md：
1. 保留新版本的框架和系统章节
2. 插入用户自定义的章节
3. 合并冲突部分（AI智能判断）

### 步骤5：验证与确认

- 显示合并计划
- 询问用户是否应用
- 备份当前版本（CLAUDE.md.before-merge）
- 写入合并后的内容

---

## 🔍 实现逻辑

```python
# 伪代码示例
def updatemc():
    # 1. 检测备份文件
    backup_files = glob("CLAUDE.md.backup.*")
    if not backup_files:
        print("未找到备份文件，无需合并")
        return

    # 2. 选择最新备份
    latest_backup = sorted(backup_files)[-1]

    # 3. 读取三个版本
    backup_content = read_file(latest_backup)
    current_content = read_file("CLAUDE.md")

    # 4. AI分析差异
    diff = compare(backup_content, current_content)
    user_changes = extract_user_modifications(diff)

    # 5. 智能合并
    merged_content = merge_intelligently(
        base=current_content,
        user_changes=user_changes
    )

    # 6. 显示合并计划并确认
    show_merge_plan(merged_content)
    if user_confirms():
        backup("CLAUDE.md", "CLAUDE.md.before-merge")
        write_file("CLAUDE.md", merged_content)
        print("✅ 合并完成！")
```

---

## 💡 合并策略

### 保留用户修改的章节

如果用户添加了新章节：
```markdown
## 🎯 项目特定配置

- 项目名称：我的MOD项目
- 开发阶段：Alpha
- 特殊规范：使用State模式管理游戏状态
```

→ **完整保留**，插入到合适位置

### 合并冲突的章节

如果用户修改了系统章节（如CRITICAL规范）：
```diff
# 用户版本（备份）
- ⛔ 规范1: 双端隔离原则
+ ⛔ 规范1: 双端隔离原则（项目要求严格执行）

# 新版本（模板）
+ ⛔ 规范5: 新增的规范
```

→ **AI智能判断**：
- 保留用户的注释/强调
- 添加新版本的新规范
- 合并后：包含用户修改 + 新增内容

### 更新系统内容

如果是版本号、日期等系统内容：
```diff
# 备份：v13.0 | 2025-11-09
# 新版：v14.1 | 2025-11-10
```

→ **使用新版本**

---

## 🚨 注意事项

1. **自动备份**
   - 合并前会自动备份当前 CLAUDE.md 为 `CLAUDE.md.before-merge`
   - 如果合并结果不满意，可以恢复

2. **手动检查**
   - 合并后建议手动检查 CLAUDE.md
   - 确保没有遗漏重要的自定义内容

3. **多次备份**
   - 如果有多个备份文件，默认使用最新的
   - 可以指定合并特定备份：`/updatemc 2025-11-09`

---

## 📚 使用示例

### 示例1：标准合并流程

```bash
# 1. 部署工作流，发现有备份
> initmc
📦 备份原文件: CLAUDE.md.backup.2025-11-10
✅ CLAUDE.md - 15.2 KB

# 2. 在 Claude Code 中执行合并
> /updatemc

🔍 检测到备份文件: CLAUDE.md.backup.2025-11-10
📊 分析差异...

发现用户修改:
  1. 添加了 "## 项目特定配置" 章节
  2. 修改了项目路径：D:\MyProject
  3. 在CRITICAL规范中添加了注释

📋 合并计划:
  ✅ 保留新版本框架（v14.1）
  ✅ 插入 "项目特定配置" 章节
  ✅ 保留用户的路径配置
  ✅ 合并CRITICAL规范的注释
  ✅ 添加新版本的功能说明

是否应用合并？(yes/no): yes

📦 备份当前版本: CLAUDE.md.before-merge
✅ 合并完成！
```

### 示例2：指定备份文件合并

```bash
> /updatemc 2025-11-09

🔍 使用指定备份: CLAUDE.md.backup.2025-11-09
...（后续流程相同）
```

---

## 🔗 相关命令

- `initmc` - 部署工作流（会自动备份CLAUDE.md）
- `/cc` - 执行开发任务

---

**版本**: v2.1.0
**最后更新**: 2025-11-10
