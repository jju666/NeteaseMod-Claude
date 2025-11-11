# 故障排查指南

> NeteaseMod-Claude 常见问题与解决方案

---

## 📋 目录

1. [安装问题](#安装问题)
2. [使用问题](#使用问题)
3. [常见问题FAQ](#常见问题faq)

---

## 安装问题

### 问题1：`initmc` 命令未找到

**症状**：
```bash
initmc --version
bash: initmc: command not found
```

**解决方案**：

**Windows**:
```powershell
# 1. 检查npm全局目录
npm config get prefix
# 输出示例: C:\Users\YourName\AppData\Roaming\npm

# 2. 将该目录添加到PATH
# 系统属性 → 环境变量 → Path → 新建 → 添加上述路径

# 3. 重启终端，验证
initmc --version
```

**Linux/Mac**:
```bash
# 1. 检查npm全局目录
npm config get prefix
# 输出示例: /usr/local 或 ~/.npm-global

# 2. 添加到PATH（~/.bashrc 或 ~/.zshrc）
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# 3. 验证
initmc --version
```

---

### 问题2：Git Submodule初始化失败

见 [INSTALLATION.md - 问题2](./INSTALLATION.md#问题2git-submodule初始化失败)

---

### 问题3：Windows软连接权限不足

见 [INSTALLATION.md - 问题3](./INSTALLATION.md#问题3windows软连接权限不足)

---

## 使用问题

### 问题4：Claude Code未读取CLAUDE.md

**症状**：
- Claude响应通用内容，未遵守MODSDK规范
- 无法识别`/uninstallmc`命令

**解决方案**：
```bash
# 1. 确认文件存在
ls -la CLAUDE.md
ls -la .claude/commands/uninstallmc.md

# 2. 确认Claude Code工作目录
# 在Claude Code中输入：
你的当前工作目录是什么？

# 3. 如果目录不正确，手动切换
cd /path/to/your/modsdk-project

# 4. 强制Claude重新读取CLAUDE.md
请重新读取CLAUDE.md文档
```

---

### 问题5：软连接指向错误

**症状**：
```bash
ls -la .claude/core-docs/
# 显示: 指向无效路径
```

**解决方案**：
```bash
# 重新初始化工作流
initmc --force

# 或手动创建软连接（高级用户）
# Windows:
mklink /J .claude\core-docs D:\path\to\NeteaseMod-Claude\markdown\core

# Linux/Mac:
ln -s /path/to/NeteaseMod-Claude/markdown/core .claude/core-docs
```

---

## 常见问题（FAQ）

### Q1：是否支持多个MODSDK项目共用一个上游仓库？

**A**：✅ 完全支持！这是v16.0双层架构的核心优势。

```bash
# 上游仓库（只需克隆一次）
/path/to/NeteaseMod-Claude/

# 项目A
cd /path/to/project-A
initmc  # 自动软连接到上游

# 项目B
cd /path/to/project-B
initmc  # 自动软连接到上游

# 项目A和项目B完全独立，互不影响
```

---

### Q2：如何更新到最新版本的工作流？

**A**：分两种情况：

**情况1：更新上游仓库**
```bash
cd /path/to/NeteaseMod-Claude
git pull origin main
git submodule update --recursive
```

**情况2：同步到下游项目**
```bash
cd /path/to/your-modsdk-project
initmc --sync

# 输出示例：
# 🔍 检测到新版本: v16.1 → v16.2
# 📦 更新软连接: .claude/core-docs/ → [上游v16.2]
# ✅ 同步完成！
```

---

### Q3：如何定制核心文档（如开发规范.md）？

**A**：Claude Code会自动创建项目覆盖层。

**方式1：通过Claude自动创建（推荐）**
```
你：我们项目需要添加一条自定义规范：禁止在Tick事件中使用循环

Claude：
📝 检测到需要编辑核心文档: 开发规范.md
🔄 自动创建项目覆盖层...
   复制: .claude/core-docs/开发规范.md
      → markdown/core/开发规范.md
✅ 覆盖层创建完成，开始编辑...
```

**方式2：手动创建**
```bash
# 从上游复制到项目覆盖层
cp .claude/core-docs/开发规范.md markdown/core/开发规范.md

# 编辑项目副本
vim markdown/core/开发规范.md

# 之后Claude会优先读取项目定制版
```

---

### Q4：如何检测项目覆盖层与上游的冲突？

**A**：使用覆盖层冲突检测工具。

```bash
merge-conflicts

# 输出示例：
# ✅ 无冲突: markdown/core/问题排查.md
# ⚠️  有冲突: markdown/core/开发规范.md
#    - 项目修改: 2025-11-10 (添加自定义规范3条)
#    - 上游修改: v16.1 (新增CRITICAL规范4)
#    🔧 建议: 手动合并，备份已创建到 .backup-docs-v16/
```

---

### Q5：如何卸载工作流？

**A**：两种方式。

**方式1：Slash Command（推荐）**
```
在Claude Code中输入: /uninstallmc
```

**方式2：命令行**
```bash
uninstallmc

# 卸载内容：
# ✅ 删除 .claude/ 目录
# ✅ 删除 CLAUDE.md
# ✅ 删除 markdown/ 目录
# ✅ 删除 tasks/ 目录
# ✅ 创建备份: .backup-uninstall-20251111/
```

---

### Q6：Claude Code是否需要联网？

**A**：可完全离线使用（推荐部署方式）。

| 功能 | 是否需要联网 | 说明 |
|-----|------------|------|
| 读取本地文档 | ❌ 不需要 | CLAUDE.md、开发规范等 |
| 查阅官方文档 | ❌ 不需要 | `.claude/docs/`已在npm install时拉取 |
| 代码编辑 | ❌ 不需要 | Edit/Write工具 |
| Git操作 | ❌ 不需要 | Git commit本地操作 |
| 在线查阅（降级） | ✅ 需要 | 仅在本地文档缺失时触发 |

**离线模式（默认）**：
- `npm install` 自动初始化 Git Submodule（官方文档）
- Claude优先使用本地文档（`.claude/docs/`）
- WebFetch仅作为降级策略（本地缺失时）
- **95%场景可完全离线使用**

---

### Q7：如何在团队中共享工作流配置？

**A**：推荐方式：

```bash
# 1. 将工作流配置提交到Git（推荐提交）
git add .claude/ CLAUDE.md markdown/ tasks/
git commit -m "chore: 添加Claude工作流配置"

# 2. 团队成员克隆项目后，自动拥有工作流配置
git clone your-team-repo.git
cd your-team-repo

# 3. 只需全局安装命令行工具（一次性）
npm install -g netease-mod-claude  # v16.2将支持

# 4. 直接使用Claude Code开发
# 无需执行 initmc，因为配置已在Git仓库中
```

**不推荐提交**：
- `.claude/settings.local.json`（个人配置，已在.gitignore中）
- `tasks/`（个人任务历史，可选提交）

---

## 更多资源

- 📖 [安装指南](./INSTALLATION.md) - 详细安装步骤
- 📚 [完整文档](./README.md#-完整文档) - 文档导航
- 💡 [使用示例](./EXAMPLES.md) - 实际案例
- 🐛 [问题排查](./markdown/问题排查.md) - MODSDK开发问题

---

_故障排查指南 | 最后更新: 2025-11-11_
