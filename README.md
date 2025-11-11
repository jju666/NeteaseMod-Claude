# NeteaseMod-Claude 🤖⚡

<div align="center">

**AI驱动的网易我的世界MODSDK开发工作流**

[![Version](https://img.shields.io/badge/version-16.1.0-blue.svg)](https://github.com/jju666/NeteaseMod-Claude)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Claude Code](https://img.shields.io/badge/Powered%20by-Claude%20Code-8A2BE2.svg)](https://claude.ai/code)
[![Node](https://img.shields.io/badge/node-%3E%3D12.0.0-brightgreen.svg)](https://nodejs.org)

*让Claude AI成为你的MODSDK开发专家*

[快速开始](#-快速开始) • [核心特性](#-核心特性) • [架构设计](#-架构设计) • [使用示例](#-使用示例) • [文档](#-完整文档)

</div>

---

## 🎯 项目简介

**NeteaseMod-Claude** 是一套专为网易我的世界MODSDK设计的**AI辅助开发工作流**。通过与Claude Code深度集成，让AI助手：
- ✅ **精通MODSDK开发规范**，自动避免90%常见错误
- ✅ **智能查阅官方文档**，无需手动搜索API
- ✅ **自动化任务管理**，从规划到实施全程追踪
- ✅ **双层文档架构**，项目定制与上游更新互不干扰

**一句话概括**：让Claude Code像一个**拥有3年MODSDK开发经验的专家**一样辅助你的项目开发。

---

## 🚀 快速开始

### 前置要求

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

### 1. 安装工作流（全局命令）

#### 方式1：从GitHub克隆（推荐）

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

#### 方式2：使用npm全局安装（未来支持）

```bash
# 🚧 功能开发中，v16.2将支持
npm install -g netease-mod-claude
initmc --version
```

#### 验证安装成功

安装完成后，应该可以在任意目录执行以下命令：

```bash
# 检查命令是否可用
initmc --version          # 显示版本号
uninstallmc --help        # 显示帮助信息
merge-conflicts --help    # 覆盖层冲突检测工具
detect-obsolete --help    # 废弃文件检测工具
```

如果提示"命令未找到"，请检查：
- **Windows**: 检查 `%APPDATA%\npm` 是否在PATH中
- **Linux/Mac**: 检查 `~/.npm-global/bin` 是否在PATH中

---

### 2. 初始化你的MODSDK项目

#### 自动检测项目结构

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

#### 手动指定项目路径（可选）

```bash
# 如果项目结构特殊，可以手动指定路径
initmc --path /path/to/modsdk-project

# 强制重新初始化（覆盖已有配置）
initmc --force
```

#### 初始化后的项目结构

```
your-modsdk-project/
├── behavior_packs/          # 你的原有项目
│   └── behavior_pack_xxx/
│       └── scripts/
│           ├── xxxServerSystem.py
│           └── xxxClientSystem.py
│
├── .claude/                 # ✨ 新增：Claude Code配置
│   ├── commands/
│   │   └── uninstallmc.md  # Slash Command
│   ├── core-docs/           # 软连接到上游核心文档
│   │   ├── 开发规范.md
│   │   ├── 问题排查.md
│   │   └── ...
│   └── docs/                # Git Submodule（官方文档）
│       └── netease-modsdk-wiki/
│
├── CLAUDE.md                # ✨ 新增：AI工作流总入口
├── markdown/                # ✨ 新增：项目文档目录
│   ├── core/                # 项目覆盖层（按需创建）
│   ├── systems/             # System技术文档
│   └── 文档待补充清单.md
│
└── tasks/                   # ✨ 新增：任务历史（自动创建）
```

---

### 3. 配置Claude Code（首次使用必读）

#### 3.1 启动Claude Code

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

#### 3.2 验证工作流部署

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
   - MODSDK核心概念.md: 📦 上游基线版本
✅ 工作流已正确部署！
```

如果Claude无法读取CLAUDE.md，请检查：
1. 文件是否存在于项目根目录
2. Claude Code的工作目录是否正确

---

### 4. 开始使用Claude Code开发

在你的项目中，直接与Claude Code对话：

```
你：修复商店系统点击无响应的问题

Claude：
✅ 已查阅文档: 开发规范.md (📝项目定制版), 问题排查.md (📦上游基线)
🎯 提取原则: ⛔禁止在服务端GetSystem获取客户端系统
📄 文档依据: 开发规范.md:32-45
🔍 定位问题: ShopServerSystem:78 错误使用 GetSystem("ShopClientSystem")
✅ 修复方案: 使用 NotifyToClient 发送事件到客户端
```

---

## ✨ 核心特性

### 1. 🧠 AI智能规范遵守

Claude Code会**自动查阅并遵守**MODSDK开发规范，避免90%的常见错误：

| 规范类型 | 自动检测能力 | 错误示例 |
|---------|------------|---------|
| **双端隔离原则** | ✅ 阻止跨端GetSystem | `ShopServerSystem`中调用`GetSystem("ShopClientSystem")` |
| **System生命周期** | ✅ 强制在`Create()`中初始化 | `__init__`中调用`GetComponent` |
| **模块导入规范** | ✅ 检查相对路径 | 子目录使用`from ..presets import X` |

详见：[开发规范.md](./markdown/开发规范.md)

---

### 2. 📚 双层文档架构（v16.0核心创新）

#### 架构设计

```
项目根目录/
├── .claude/
│   ├── core-docs/        ← 📦 上游基线层（只读，软连接）
│   │   ├── 开发规范.md
│   │   ├── 问题排查.md
│   │   └── ...
│   └── docs/            ← 官方文档（Git Submodule）
│       └── netease-modsdk-wiki/
│
└── markdown/
    ├── core/            ← 📝 项目覆盖层（可编辑）
    │   ├── 开发规范.md  ← 项目定制版（覆盖上游）
    │   └── ...
    ├── systems/         ← 项目System文档
    └── 文档待补充清单.md
```

#### 智能文档路由

当Claude Code查阅文档时，自动执行优先级路由：

```python
# 伪代码示例
if exists("markdown/core/开发规范.md"):
    Read("markdown/core/开发规范.md")  # 优先项目定制版
    标记: "📝 项目定制版"
else:
    Read(".claude/core-docs/开发规范.md")  # 回退到上游基线
    标记: "📦 上游基线版本"
```

#### 优势对比

| 特性 | v16.0双层架构 | v15.0单层架构 |
|-----|-------------|-------------|
| **职责隔离** | ✅ 100%（多项目互不影响） | ❌ 混杂在一起 |
| **上游更新** | ✅ 一键同步（`initmc --sync`） | ❌ 手动复制 |
| **项目定制** | ✅ 按需覆盖（自动创建） | ❌ 直接修改原文件 |
| **文档数量** | ✅ 3-5个（只存差异） | ❌ 10+个（全量复制） |
| **冲突风险** | ✅ 自动检测+备份 | ⚠️ 手动合并 |

---

### 3. 🔄 三步核心工作流

Claude Code按照**标准化流程**执行每个任务：

```
步骤1: 理解任务与分级（2分钟）
   ├─ 🟢 微任务 (<30行)  → 快速通道（直接Edit）
   ├─ 🟡 标准任务 (3-8文件) → 5章模板（父代理探索）
   └─ 🔴 复杂任务 (>8文件)  → 9章模板（可选并行）

步骤2: 查阅文档（智能路由）⭐
   ├─ 层级1: 项目覆盖层（markdown/core/）
   ├─ 层级2: 上游基线（.claude/core-docs/）
   ├─ 层级3: 项目文档（markdown/systems/）
   └─ 层级4: 官方文档（在线查阅 WebFetch）

步骤3: 执行与收尾
   ├─ 实施修改（Edit/Write）
   ├─ 验证测试
   ├─ 更新文档
   └─ Git commit（附带任务历史）
```

详见：[CLAUDE.md](./CLAUDE.md)

---

### 4. 🌐 智能官方文档查阅

Claude Code可以**自动在线查阅**最新官方文档，无需手动搜索：

```python
# AI自动执行
WebFetch(
    url="https://raw.githubusercontent.com/EaseCation/netease-modsdk-wiki/main/docs/...",
    prompt="提取NotifyToClient的参数说明和使用示例"
)
```

支持的文档源：
- ✅ [网易MODSDK开发文档](https://github.com/EaseCation/netease-modsdk-wiki)
- ✅ [基岩版Wiki](https://github.com/Bedrock-OSS/bedrock-wiki)（NBT/实体/原版机制）

---

### 5. 🛠️ 可选优化工具

v16.0新增两个可选工具，提升开发体验：

#### 覆盖层冲突合并工具
```bash
# 检测项目覆盖层与上游更新的冲突
merge-conflicts

# 输出示例
✅ 无冲突: markdown/core/问题排查.md (上游v16.0 → v16.1)
⚠️  有冲突: markdown/core/开发规范.md
    - 项目修改: 2025-11-10 (添加自定义规范3条)
    - 上游修改: v16.1 (新增CRITICAL规范4)
    🔧 建议: 手动合并，备份已创建到 .backup-docs-v16/
```

#### 废弃文件检测工具
```bash
# 检测上游已删除、但项目仍保留的过期文件
detect-obsolete

# 输出示例
⚠️  检测到3个废弃文件:
  - markdown/core/旧版开发规范.md (上游v15.0已删除)
    📦 备份: .obsolete-backup/markdown/core/旧版开发规范.md
    ❌ 自动删除
```

详见：[可选工具说明.md](./markdown/可选工具说明.md)

---

## 🏗️ 架构设计

### 项目结构

```
NeteaseMod-Claude/
├── bin/                    # 全局命令行工具
│   ├── initmc.js          # 初始化项目工作流
│   ├── uninstallmc.js     # 卸载工作流
│   ├── merge-conflicts.js # 覆盖层冲突检测
│   └── detect-obsolete.js # 废弃文件检测
│
├── lib/                    # 核心库
│   ├── init-workflow.js   # 工作流初始化引擎
│   ├── migration-v16.1.js # v16.1迁移脚本
│   ├── symlink-manager.js # 软连接管理
│   ├── generator.js       # 文档生成器
│   ├── analyzer.js        # 项目结构分析器
│   └── config.js          # 配置管理
│
├── templates/              # 文档模板
│   ├── CLAUDE.md.template
│   ├── README.md.template
│   └── .claude/
│       ├── core-docs/     # 核心文档基线（软连接源）
│       └── docs/          # 官方文档（Git Submodule）
│
├── example-project/        # 示例MODSDK项目
│   └── behavior_packs/
│       └── behavior_pack_test/
│           └── scripts/
│               ├── ShopServerSystem.py
│               ├── TeamServerSystem.py
│               ├── states/
│               └── presets/
│
├── markdown/               # 上游文档（供软连接使用）
│   ├── core/              # 核心工作流文档
│   │   ├── 开发规范.md
│   │   ├── 问题排查.md
│   │   └── ...
│   ├── ai/                # AI工作流文档
│   └── systems/           # System技术文档（示例）
│
├── CLAUDE.md              # AI工作流总入口
├── README.md              # 项目说明（本文件）
├── LICENSE                # MIT许可证
└── package.json           # npm包配置
```

---

## 💡 使用示例

### 示例1：修复常见错误（双端隔离）

**用户输入**：
```
修复ShopServerSystem中点击商店按钮无响应的问题
```

**Claude Code执行流程**：

```markdown
## 步骤1: 理解任务
🎯 任务级别: 🟡 标准任务（涉及3个文件）

## 步骤2: 查阅文档
✅ 已查阅: 开发规范.md (📝项目定制版), ShopServerSystem.md (项目文档)
🎯 提取原则:
  ⛔ 禁止: 服务端GetSystem获取客户端系统
  ✅ 应该: 使用NotifyToClient通信
  📚 原因: Server和Client进程分离，跨端GetSystem返回None

## 步骤3: 定位问题
📄 文件: behavior_packs/behavior_pack_test/scripts/ShopServerSystem.py:78
❌ 错误代码:
   ```python
   shop_client = self.GetSystem("ShopClientSystem")  # 运行时返回None!
   shop_client.ShowUI(playerId)
   ```

## 步骤4: 修复方案
✅ 使用事件通信:
   ```python
   # 服务端发送事件
   self.NotifyToClient(playerId, "ShowShopUI", {"shopId": shopId})

   # 客户端监听事件（ShopClientSystem.py）
   @Listen("ShowShopUI")
   def OnShowShopUI(self, args):
       shopId = args["shopId"]
       self.ShowUI(shopId)
   ```

## 步骤5: 验证
✅ 编译通过
✅ 功能测试通过
✅ Git commit完成
```

---

### 示例2：添加新功能（排行榜系统）

**用户输入**：
```
添加一个排行榜系统，显示玩家击杀数Top10
```

**Claude Code执行流程**：

```markdown
## 步骤1: 理解任务
🎯 任务级别: 🔴 复杂任务（需要创建6个新文件）

## 步骤2: 查阅文档
✅ 已查阅: 开发规范.md, API速查.md, MODSDK核心概念.md
🌐 官方文档查阅:
   - WebFetch: netease-modsdk-wiki/UI组件文档
   - WebFetch: bedrock-wiki/记分板系统

## 步骤3: 创建任务（9章模板）
📁 tasks/添加排行榜系统_20251111/
   ├── 1-需求分析.md
   ├── 2-技术方案.md
   ├── 3-架构设计.md
   ├── 4-实施计划.md
   ├── 5-代码实现.md
   ├── 6-测试验证.md
   ├── 7-文档更新.md
   ├── 8-总结反思.md
   └── 9-知识沉淀.md

## 步骤4: 分阶段实施
阶段1: 数据存储（RankServerSystem.py）✅
阶段2: UI显示（RankClientSystem.py）✅
阶段3: 数据更新（监听PlayerKillEvent）✅
阶段4: 排序算法（Top10计算）✅
阶段5: 集成测试 ✅

## 步骤5: 更新文档
✅ 创建: markdown/systems/RankSystem.md
✅ 更新: markdown/文档待补充清单.md
✅ Git commit完成
```

---

## 📚 完整文档

### 核心文档（必读）

| 文档 | 说明 | 读者 |
|-----|------|------|
| [CLAUDE.md](./CLAUDE.md) | AI工作流总入口 | 🤖 Claude必读 |
| [快速参考.md](./快速参考.md) | 工作流快速查询手册 | 👨‍💻 开发者必读 |
| [Claude指令参考.md](./Claude指令参考.md) | Slash Command使用说明 | 👨‍💻 开发者参考 |

### 开发规范

| 文档 | 说明 |
|-----|------|
| [开发规范.md](./markdown/开发规范.md) | CRITICAL规范，防止90%错误 |
| [问题排查.md](./markdown/问题排查.md) | 已知问题和调试技巧 |
| [MODSDK核心概念.md](./markdown/MODSDK核心概念.md) | System、Component、Event全解析 |
| [API速查.md](./markdown/API速查.md) | 常用API速查表 |

### 工作流文档

| 文档 | 说明 |
|-----|------|
| [快速开始.md](./markdown/快速开始.md) | 5分钟上手指南 |
| [任务类型决策表.md](./markdown/ai/任务类型决策表.md) | 任务分级指南 |
| [快速通道流程.md](./markdown/ai/快速通道流程.md) | 微任务执行流程 |

### 版本迁移

| 文档 | 说明 |
|-----|------|
| [迁移指南-v16.1.md](./markdown/迁移指南-v16.1.md) | v16.0 → v16.1升级 |
| [迁移指南-v16.0.md](./markdown/迁移指南-v16.0.md) | v15.x → v16.0升级 |
| [可选工具说明.md](./markdown/可选工具说明.md) | 覆盖层冲突合并、废弃文件检测 |

---

## 🔧 高级用法

### 自定义文档覆盖

当你需要为项目定制核心文档时，Claude Code会自动创建覆盖层：

```bash
# AI检测到需要编辑核心文档
你：我们项目需要添加一条自定义规范：禁止在Tick事件中使用循环

Claude：
📝 检测到需要编辑核心文档: 开发规范.md
🔄 自动创建项目覆盖层...
   复制: .claude/core-docs/开发规范.md
      → markdown/core/开发规范.md
   添加标记: <!-- 📝 项目定制版本 - 基于上游 v16.0 -->
✅ 覆盖层创建完成，开始编辑...

✅ 已添加自定义规范（第4条）:
   ⛔ 规范4: Tick事件性能优化
      - 禁止在OnEntityTick中使用循环
      - 禁止在OnServerTick中操作大量实体
```

之后，Claude Code会**优先读取**项目定制版 `markdown/core/开发规范.md`。

---

### 同步上游更新

当上游工作流更新时，一键同步：

```bash
# 检测新版本、更新软连接、清理废弃文件
initmc --sync

# 输出示例
🔍 检测到新版本: v16.0 → v16.1
📦 更新软连接: .claude/core-docs/ → [上游v16.1]
🔍 检测项目覆盖层冲突...
   ✅ 无冲突: markdown/core/问题排查.md
   ⚠️  有冲突: markdown/core/开发规范.md
      💡 建议执行: merge-conflicts
🧹 检测废弃文件...
   ❌ 删除: markdown/core/旧版开发规范.md (备份已创建)
✅ 同步完成！
```

---

### 卸载工作流

如果需要从项目中移除工作流：

```bash
# 方式1: 使用Slash Command（推荐）
在Claude Code中输入: /uninstallmc

# 方式2: 手动执行
uninstallmc

# 卸载内容
✅ 删除 .claude/ 目录
✅ 删除 CLAUDE.md
✅ 删除 markdown/ 目录
✅ 删除 tasks/ 目录
✅ 保留 README.md（如果存在）
✅ 创建备份: .backup-uninstall-20251111/
```

---

## 🔧 故障排查

### 安装问题

#### 问题1：`initmc` 命令未找到

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

#### 问题2：Git Submodule初始化失败

**症状**：
```bash
git clone https://github.com/jju666/NeteaseMod-Claude.git
# ⚠️ 警告: 文档下载失败，将使用在线查询
```

**解决方案**：
```bash
# 手动初始化子模块
cd NeteaseMod-Claude
git submodule update --init --recursive

# 如果网络问题，可以跳过子模块
# Claude Code会自动使用WebFetch在线查阅文档
```

---

#### 问题3：Windows软连接权限不足

**症状**：
```bash
initmc
# ❌ 错误: 无法创建软连接，权限不足
```

**解决方案**：
```powershell
# 方式1: 以管理员身份运行PowerShell
# 右键 PowerShell → "以管理员身份运行"
initmc

# 方式2: 启用开发者模式（Windows 10+）
# 设置 → 更新和安全 → 开发者选项 → 开发人员模式
# 重启终端后重试
```

---

### 使用问题

#### 问题4：Claude Code未读取CLAUDE.md

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

#### 问题5：软连接指向错误

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

### 常见问题 (FAQ)

#### Q1：是否支持多个MODSDK项目共用一个上游仓库？

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

#### Q2：如何更新到最新版本的工作流？

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

#### Q3：如何定制核心文档（如开发规范.md）？

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

#### Q4：如何检测项目覆盖层与上游的冲突？

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

#### Q5：如何卸载工作流？

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

#### Q6：Claude Code是否需要联网？

**A**：部分功能需要联网。

| 功能 | 是否需要联网 | 说明 |
|-----|------------|------|
| 读取本地文档 | ❌ 不需要 | CLAUDE.md、开发规范等 |
| 查阅官方文档 | ✅ 需要 | WebFetch查询GitHub |
| 代码编辑 | ❌ 不需要 | Edit/Write工具 |
| Git操作 | ❌ 不需要 | Git commit本地操作 |

**离线模式**：
- 确保 `git submodule` 已初始化（包含官方文档）
- Claude会优先使用本地文档
- 仅在本地找不到时才使用WebFetch

---

#### Q7：如何在团队中共享工作流配置？

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

## 🌟 技术亮点

### 1. 自动化程度：95%

| 操作 | 自动化程度 | 说明 |
|-----|----------|------|
| 项目初始化 | ✅ 100% | `initmc` 一键部署 |
| 文档路由 | ✅ 100% | AI自动选择项目定制版/上游基线 |
| 上游同步 | ✅ 95% | `initmc --sync` 自动更新（冲突需手动合并） |
| 规范遵守 | ✅ 90% | AI自动查阅规范，阻止常见错误 |
| 任务追踪 | ✅ 100% | 自动创建tasks历史 |
| 文档生成 | ✅ 100% | 自动生成System文档 |

### 2. 职责隔离：100%

多个项目可以共用上游仓库，互不影响：

```
上游仓库: NeteaseMod-Claude/
└── markdown/core/        # 核心文档基线

项目A: my-pvp-mod/
├── .claude/core-docs/ → [软连接到上游]
└── markdown/core/        # 项目A的定制（覆盖上游）
    └── 开发规范.md       # 添加PVP相关规范

项目B: my-rpg-mod/
├── .claude/core-docs/ → [软连接到上游]
└── markdown/core/        # 项目B的定制（覆盖上游）
    └── 问题排查.md       # 添加RPG相关问题
```

**优势**：
- ✅ 项目A和项目B的定制**完全独立**
- ✅ 上游更新时，`initmc --sync` **分别同步**
- ✅ 冲突检测**只影响各自项目**

### 3. 兼容性：全平台

| 平台 | 软连接方式 | 支持状态 |
|-----|-----------|---------|
| Windows | Junction/Symlink | ✅ 已测试 |
| Linux | Symlink | ✅ 已测试 |
| macOS | Symlink | ✅ 理论支持 |

---

## 📊 版本历史

### v16.1 (2025-11-11) - 双重定制架构

**核心升级**：
- ✨ **CLAUDE.md项目扩展区**：支持 `{{PRESETS_DOCS_SECTION}}`、`{{QUICK_INDEX_EXTRA}}` 变量
- ✨ **智能合并逻辑**：自动检测项目定制内容，上游更新时保留定制
- 🔧 **迁移脚本优化**：从v16.0平滑升级

**技术指标**：
- 职责隔离：100%（多项目互不影响）
- 定制化程度：高（支持CLAUDE.md内容定制）
- 向后兼容：v16.0项目自动迁移

详见：[迁移指南-v16.1.md](./markdown/迁移指南-v16.1.md)

---

### v16.0 (2025-11-10) - 双层文档架构

**核心创新**：
- ✨ **双层文档架构**：上游基线层 + 项目覆盖层
- ✨ **软连接管理**：`.claude/core-docs/` 自动软连接到上游
- ✨ **智能文档路由**：AI自动选择项目定制版或上游基线
- ✨ **自动迁移v15.x**：执行 `initmc` 自动升级

**新增工具**：
- 🔧 `merge-conflicts`：覆盖层冲突检测与合并
- 🔧 `detect-obsolete`：废弃文件自动清理（带备份）

**用户体验**：
- 📁 下游项目文档从10+个减少到3-5个
- 🔄 一键同步：`initmc --sync` 自动更新
- 📝 按需定制：需要编辑时AI自动创建覆盖层

详见：[迁移指南-v16.0.md](./markdown/迁移指南-v16.0.md)

---

### v15.0 (2025-11-09) - 单层文档架构（已废弃）

**特性**：
- ✅ CRITICAL规范前置
- ✅ 三步工作流程
- ✅ 三级任务分类

**问题**：
- ❌ 上游更新需要手动复制
- ❌ 项目定制会污染原文件
- ❌ 多项目维护困难

---

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

### 贡献类型

| 类型 | 说明 | 标签 |
|-----|------|------|
| 🐛 Bug修复 | 修复工作流错误 | `bug` |
| ✨ 新功能 | 添加新工具或优化 | `enhancement` |
| 📚 文档改进 | 完善核心文档 | `documentation` |
| 🔧 工具增强 | 优化命令行工具 | `tool` |

### 提交规范

```bash
git commit -m "feat: 添加xxx功能"
git commit -m "fix: 修复xxx问题"
git commit -m "docs: 更新xxx文档"
```

---

## 📜 许可证

本项目采用 [MIT License](./LICENSE)。

**附加条款**：
- 本项目专为**网易我的世界（中国版）MODSDK**设计
- 使用时需遵守[网易MODSDK开发协议](https://mc.163.com/dev/)

---

## 🔗 相关链接

- **GitHub仓库**：https://github.com/jju666/NeteaseMod-Claude
- **问题反馈**：https://github.com/jju666/NeteaseMod-Claude/issues
- **Claude Code官网**：https://claude.ai/code
- **网易MODSDK文档**：https://github.com/EaseCation/netease-modsdk-wiki
- **基岩版Wiki**：https://github.com/Bedrock-OSS/bedrock-wiki

---

## 💬 社区与支持

- 📧 **邮件支持**：通过GitHub Issues提问
- 📖 **文档问题**：提交PR改进文档
- 🐛 **Bug报告**：使用Issue模板提交

---

<div align="center">

**让AI成为你的MODSDK开发专家** 🤖⚡

Made with ❤️ by NeteaseMod-Claude Contributors

*Powered by [Claude Code](https://claude.ai/code)*

</div>
