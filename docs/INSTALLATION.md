# 安装指南

> NeteaseMod-Claude 完整安装教程

---

## 📋 目录

1. [前置要求](#前置要求)
2. [安装步骤](#安装步骤)
3. [验证安装](#验证安装)
4. [故障排查](#故障排查)

---

## 前置要求

在开始之前，请确保你的环境满足以下要求：

| 环境组件 | 版本要求 | 说明 |
|---------|---------|------|
| **Node.js** | ≥12.0.0 | 运行命令行工具 |
| **npm** | 随Node.js安装 | 包管理器 |
| **Git** | 任意版本 | 克隆仓库和子模块 |
| **Claude Code** | 最新版 | AI辅助开发工具 |
| **Python** | 2.7 | MODSDK项目运行环境（可选） |

**检查环境**：
```bash
node --version   # 应显示 v12.0.0 或更高
npm --version    # 应显示 npm 版本
git --version    # 应显示 git 版本
```

---

## 安装步骤

### 1. 从GitHub克隆（推荐）

```bash
# 1. 克隆仓库（包含子模块）
git clone --recursive https://github.com/jju666/NeteaseMod-Claude.git
cd NeteaseMod-Claude

# 2. 安装npm依赖
npm install

# 3. 全局安装命令行工具
npm run install-global

# 4. 验证安装
initmc --version
```

**说明**：
- `--recursive` 参数会自动初始化 Git Submodule（官方文档）
- 如果忘记使用 `--recursive`，可以手动执行：
  ```bash
  git submodule update --init --recursive
  ```

**⚠️ 重要提示**：
- `npm run install-global` 会自动下载官方文档（约50MB）
- 下载过程可能需要 **1-3 分钟**，取决于网络速度
- 请耐心等待，**不要关闭终端**
- 如果网络较慢，可能出现长时间无输出，这是正常现象

### 2. 使用npm全局安装（未来支持）

```bash
# 🚧 功能开发中，v16.2将支持
npm install -g netease-mod-claude
initmc --version
```

---

## 验证安装

### 检查命令是否可用

安装完成后，应该可以在任意目录执行以下命令：

```bash
# 检查命令是否可用
initmc --version          # 显示版本号
uninstallmc --help        # 显示帮助信息
merge-conflicts --help    # 覆盖层冲突检测工具
detect-obsolete --help    # 废弃文件检测工具
```

### 如果提示"命令未找到"

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

## 初始化MODSDK项目

### 自动检测项目结构

```bash
# 进入你的MODSDK项目目录
cd /path/to/your/modsdk-project

# 一键初始化工作流
initmc

# 输出示例：
# 🔍 检测到MODSDK项目结构:
#    - behavior_packs/behavior_pack_xxx/scripts/
# 📦 开始部署工作流 v16.1...
# ✅ 创建 .claude/ 目录
# ✅ 创建软连接: .claude/core-docs/ → [上游v16.1]
# ✅ 生成 CLAUDE.md（基于项目结构）
# ✅ 生成 /uninstallmc 命令
# ✅ 部署完成！
```

### 手动指定项目路径（可选）

```bash
# 如果项目结构特殊，可以手动指定路径
initmc --path /path/to/modsdk-project

# 强制重新初始化（覆盖已有配置）
initmc --force
```

### 初始化后的项目结构

```
your-modsdk-project/
├── behavior_packs/          # 你的原有项目
│   └── behavior_pack_xxx/
│       └── scripts/
│
├── .claude/                 # ✨ 新增：Claude Code配置
│   ├── commands/
│   │   └── uninstallmc.md  # Slash Command
│   ├── core-docs/           # 软连接到上游核心文档
│   └── docs/                # Git Submodule（官方文档）
│
├── CLAUDE.md                # ✨ 新增：AI工作流总入口
├── markdown/                # ✨ 新增：项目文档目录
└── tasks/                   # ✨ 新增：任务历史（自动创建）
```

---

## 配置Claude Code

### 启动Claude Code

```bash
# 在项目根目录启动Claude Code
cd /path/to/your/modsdk-project

# 方式1：使用VS Code扩展（推荐）
# 1. 安装Claude Code扩展
# 2. 在VS Code中打开项目
# 3. Ctrl+Shift+P → "Claude Code: Start Session"

# 方式2：命令行启动
claude-code
```

### 验证工作流部署

在Claude Code中输入：

```
你好，请确认你是否能看到CLAUDE.md文档
```

**正确响应示例**：
```
✅ 已读取 CLAUDE.md 文档
🎯 当前工作流版本: v16.1
📚 核心文档状态:
   - 开发规范.md: 📦 上游基线版本
   - 问题排查.md: 📦 上游基线版本
✅ 工作流已正确部署！
```

**如果Claude无法读取CLAUDE.md**，请检查：
1. 文件是否存在于项目根目录
2. Claude Code的工作目录是否正确

---

## 故障排查

### 问题1：`initmc` 命令未找到

见上方 [验证安装](#如果提示命令未找到) 章节。

### 问题2：Git Submodule初始化失败

**症状**：
```bash
git clone https://github.com/jju666/NeteaseMod-Claude.git
# ⚠️ 警告: 文档下载失败，将使用在线查询
```

**影响**：
- `.claude/docs/netease-modsdk-wiki/` 目录为空
- Claude会降级使用WebFetch在线查阅（需要联网）

**解决方案**：

**方式1：手动初始化子模块（推荐）**
```bash
cd NeteaseMod-Claude
git submodule update --init --recursive

# 验证
ls .claude/docs/netease-modsdk-wiki/docs
```

**方式2：使用降级策略（临时方案）**
```bash
# 跳过子模块初始化，Claude Code会自动降级到WebFetch
# 优点: 可立即使用
# 缺点: 需要联网，查阅速度较慢
```

**方式3：离线环境手动部署**
```bash
# 在有网络的环境准备
git clone --recursive https://github.com/jju666/NeteaseMod-Claude.git
tar -czf netease-mod-claude.tar.gz NeteaseMod-Claude/

# 在离线环境解压
tar -xzf netease-mod-claude.tar.gz
```

### 问题3：Windows软连接权限不足

**症状**：
```bash
npm run install-global
# ❌ 错误: EPERM: operation not permitted, copyfile ...
```

**解决方案**：

**方式1：以管理员身份运行PowerShell（推荐）**
```powershell
# 1. 右键点击 "Windows PowerShell" → "以管理员身份运行"

# 2. 切换到项目目录（⚠️ 注意：路径中有空格时必须使用引号）
cd "D:\EcWork\基于Claude的MODSDK开发工作流"

# 3. 运行安装命令
npm install
npm run install-global
```

**⚠️ 常见错误**：
```powershell
# ❌ 错误示例（路径有空格时不加引号）
cd D:\EcWork\基于Claude的MODSDK开发工作流
# 结果：只切换到 D:\EcWork\，导致找不到 package.json

# ✅ 正确示例（使用引号）
cd "D:\EcWork\基于Claude的MODSDK开发工作流"
```

**方式2：启用开发者模式（Windows 10+）**
```
设置 → 更新和安全 → 开发者选项 → 开发人员模式
# 重启终端后重试
```

---

## 下一步

- 📖 [快速开始](./markdown/快速开始.md) - 5分钟上手
- 📚 [完整文档](./README.md#-完整文档) - 文档导航
- 🐛 [故障排查](./TROUBLESHOOTING.md) - 更多问题解决

---

_安装指南 | 最后更新: 2025-11-11_
