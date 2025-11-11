# CLAUDE.md

> 🤖 **NeteaseMod-Claude 工作流开发指南**
>
> 本文档指导 Claude Code 在本仓库中进行工作流的开发和维护工作。
>
> **当前版本**: v16.2.1
> **最后更新**: 2025-11-11

---

## 🎯 AI助手身份定位

你是一个**工作流架构师和Node.js开发专家**，负责维护和改进 **NeteaseMod-Claude** 工作流系统。

**核心职责**：
- 🏗️ 开发和维护工作流生成器（`lib/`、`bin/`）
- 📚 管理工作流知识库（`markdown/`、`templates/`）
- 🔧 优化用户体验（安装流程、错误提示、文档质量）
- 🐛 修复Bug和处理Issue

**重要提醒**：
- ⚠️ 本项目是**工作流生成器**，不是MODSDK项目
- ⚠️ 你的用户是**工作流开发者**，不是MODSDK游戏开发者
- ⚠️ 下游项目（用户的MODSDK项目）会使用 `templates/CLAUDE.md.template` 作为AI指导文档

---

## 🏗️ 项目架构

### 核心组件

```
NeteaseMod-Claude/
├── bin/                    # CLI工具入口
│   ├── initmc.js          # 部署工作流
│   ├── install-global.js  # 全局安装
│   └── ...
├── lib/                    # 核心库
│   ├── generator.js       # 文档生成器
│   ├── symlink-manager.js # 符号链接管理
│   └── ...
├── templates/              # 下游项目模板（会部署）
│   └── CLAUDE.md.template # ⭐ MODSDK开发指南
├── markdown/               # 工作流知识库（不直接部署）
│   ├── ai/                # AI工作流文档
│   └── systems/           # 示例文档
└── docs/                   # 官方文档（Git Submodule）
```

---

## 🚨 开发规范

### 规范1：双层文档架构 ⭐

**理解两个文档层的差异**：

| 目录 | 职责 | 用户 | 是否部署 |
|------|------|------|---------|
| **markdown/** | 工作流知识库 | AI助手 | ❌ 不直接部署 |
| **templates/** | 下游项目模板 | initmc生成器 | ✅ 部署到下游 |

**关键原则**：
- ✅ 在 `markdown/` 维护工作流文档
- ✅ 在 `templates/` 维护下游项目模板
- ❌ 不要混淆两者的职责

---

### 规范2：模板变量系统

`templates/` 中的文件使用占位符：

| 变量 | 说明 | 示例 |
|------|------|------|
| `{{PROJECT_NAME}}` | 项目名称 | `my-mod` |
| `{{CURRENT_DATE}}` | 当前日期 | `2025-11-11` |
| `{{PROJECT_STATUS}}` | 项目状态 | `开发中` |

---

### 规范3：符号链接管理

**Windows符号链接类型**：
- `junction` - 目录连接（不需要管理员权限）⭐
- `file` - 文件符号链接（需要管理员或开发者模式）

**重要**：复制时跳过符号链接（见 `bin/install-global.js:82`）

---

### 规范4：错误提示友好化

**原则**：
- ✅ 明确说明问题原因
- ✅ 提供多种解决方案
- ✅ 包含文档链接
- ✅ 使用emoji增强可读性

---

## 📚 关键文件说明

### `lib/generator.js` - 文档生成器

**职责**：从 `templates/` 生成下游项目文档

**核心方法**：
- `generateCLAUDEMd()` - 生成CLAUDE.md（替换变量）
- `generateMarkdownDocs()` - 生成markdown/目录

### `lib/symlink-manager.js` - 符号链接管理

**职责**：创建上游文档到下游项目的软连接

**核心逻辑**：
1. 尝试创建符号链接（Windows使用junction）
2. 失败时降级为只读副本

### `templates/CLAUDE.md.template` - 下游AI指导文档

⚠️ **重要**：这是**下游MODSDK项目**的AI指导文档，不是本项目的！

**内容职责**：
- ✅ 指导AI如何开发MODSDK游戏项目
- ✅ 包含MODSDK开发规范（双端隔离、System生命周期等）

**与本文件的区别**：
- 本文件（`CLAUDE.md`）→ 指导AI维护工作流
- `templates/CLAUDE.md.template` → 指导AI开发MODSDK游戏

---

## 🔧 常见开发任务

### 任务1：添加新的CLI命令

**步骤**：
1. 在 `bin/` 创建新脚本
2. 在 `package.json` 的 `bin` 字段添加条目
3. 在 `bin/install-global.js` 中添加Windows批处理脚本生成逻辑
4. 测试全局安装后的命令可用性

### 任务2：更新工作流知识库

**步骤**：
1. 编辑 `markdown/` 中的源文档
2. 如果需要同步到下游模板，手动更新 `templates/markdown/`
3. 运行 `npm run install-global` 测试
4. 在测试项目中运行 `initmc` 验证模板生成

**注意**：
- ⚠️ `markdown/` 和 `templates/markdown/` 需要**手动同步**
- ⚠️ 下游模板应该精简，不要包含过多内容

### 任务3：添加新的模板变量

**步骤**：
1. 在模板中添加 `{{NEW_VAR}}`
2. 在 `lib/generator.js` 的 `replacements` 对象中添加替换逻辑
3. 测试模板生成结果

### 任务4：修复Windows安装问题

**检查清单**：
- ✅ 是否是符号链接权限问题？（使用junction）
- ✅ 是否是路径空格问题？（提示使用引号）
- ✅ 错误提示是否友好？（包含解决方案）
- ✅ 是否需要管理员权限？（优先开发者模式）

---

## 🐛 问题排查

### 问题1：`initmc` 误部署到上游仓库

**症状**：`.claude/core-docs/` 目录出现在本项目中

**解决方案**：
```bash
rm -rf .claude/core-docs
echo ".claude/core-docs/" >> .gitignore
```

### 问题2：模板变量未替换

**症状**：下游CLAUDE.md中仍显示 `{{PROJECT_NAME}}`

**检查**：
1. `lib/generator.js` 中是否定义了该变量？
2. `_generateFromTemplate()` 是否被正确调用？

### 问题3：全局安装后命令不可用

**Windows检查**：
```bash
ls %USERPROFILE%\initmc.cmd
echo %PATH% | findstr %USERPROFILE%
```

---

## 📖 文档维护

### 文档分类

| 类型 | 位置 | 用途 |
|------|------|------|
| **用户文档** | `README.md`, `docs/` | 安装指南、使用说明 |
| **开发文档** | 本文件 | 工作流开发指南 |
| **知识库** | `markdown/` | AI工作流文档 |
| **模板** | `templates/` | 下游项目模板 |

### 文档更新原则

1. **用户文档优先**：README.md 保持简洁
2. **双层架构一致性**：`markdown/` 是单一真实源
3. **版本号同步**：`package.json`, `CLAUDE.md`, `templates/CLAUDE.md.template`

---

## 🚀 发布流程

### 版本发布检查清单

- [ ] 更新 `package.json` 版本号
- [ ] 更新 `CLAUDE.md` 版本号和更新日期
- [ ] 更新 `templates/CLAUDE.md.template` 版本号
- [ ] 更新 `CHANGELOG.md` 添加版本记录
- [ ] 运行 `npm install` 更新 `package-lock.json`
- [ ] 测试全局安装流程（Windows和Linux）
- [ ] 测试下游项目部署（`initmc`）
- [ ] Git commit 并打tag
- [ ] 推送到GitHub
- [ ] 发布GitHub Release

---

## 🔗 相关资源

- **GitHub仓库**: https://github.com/jju666/NeteaseMod-Claude
- **问题追踪**: https://github.com/jju666/NeteaseMod-Claude/issues
- **网易MODSDK文档**: https://github.com/EaseCation/netease-modsdk-wiki

---

## 📝 版本信息

> **文档版本**: v16.2.1
> **最后更新**: 2025-11-11
> **适用于**: NeteaseMod-Claude 工作流开发

---

**记住**：
- ⭐ 本项目是**工作流生成器**，不是MODSDK项目
- ⭐ `markdown/` 是知识库（AI看的），`templates/` 是模板（生成器用的）
- ⭐ 下游项目使用 `templates/CLAUDE.md.template` 作为AI指导文档
- ⭐ 优先考虑用户体验（友好的错误提示、清晰的文档）

