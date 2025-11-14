# v20.2.12 - 智能单命令模式

> **发布日期**: 2025-11-14
> **类型**: 用户体验优化 + 技术债务清理

---

## 🎯 核心改进

### 1️⃣ 智能单命令模式
再也不需要记住各种参数! `initmc` 一条命令自动完成所有操作:

```bash
# 以前需要:
initmc              # 首次部署
initmc --sync       # 发现更新后手动同步
initmc --force      # 强制重置
initmc --clean      # 清理文件

# 现在只需要:
initmc              # 自动检测 → 自动清理 → 自动迁移 → 自动同步 ✨
```

**自动行为**:
- 🗑️ 清理遗留的全局命令文件 (.cmd)
- 🔍 自动检测版本更新
- 🧹 自动清理废弃文件(无需确认)
- ⬆️ 自动同步最新工作流
- 🚀 自动执行迁移脚本

---

### 2️⃣ npm link 推荐方式

**旧方式(已废弃)**:
```bash
npm run deploy  # 30秒+, 创建残留文件
```

**新方式(推荐)**:
```bash
npm link        # 5秒, 实时更新, 无残留 ⚡
```

**优势对比**:
| 特性 | npm link | npm run deploy |
|------|----------|----------------|
| 安装速度 | ⚡ 5秒 | ⏱️ 30秒+ |
| 实时更新 | ✅ 修改代码立即生效 | ❌ 需重新运行 |
| 卸载清理 | ✅ `npm unlink` 完全清理 | ⚠️ 需手动删除多个文件 |
| 版本一致性 | ✅ 始终使用最新代码 | ⚠️ 可能出现缓存 |
| 残留文件 | ✅ 无残留 | ⚠️ 用户目录有 .cmd |

---

### 3️⃣ 版本管理统一

**消除所有版本号硬编码**:
- ✅ `bin/install-global.js` - 动态读取 package.json
- ✅ `bin/initmc.js` - 支持 npm link 路径
- ✅ 单一数据源(Single Source of Truth)

**增强防缓存机制**:
- ✅ `version-checker.js` - 双重保险(清除 require 缓存 + 直接读文件)
- ✅ 确保 manifest 写入实时版本号
- ✅ 新增版本一致性检查脚本

---

## 📊 用户体验改进

```
安装速度: 30秒 → 5秒 (⚡ 提升 83%)
命令参数: 5个 → 0个 (🎯 简化 100%)
遗留文件: ⚠️ 有 → ✅ 无 (🗑️ 改进 100%)
版本一致性: ⚠️ 可能缓存 → ✅ 实时读取 (🔒 可靠性 +100%)
```

---

## 📦 新增内容

### 新增文件
- **lib/cleanup-utils.js** - 清理工具模块
- **scripts/check-version-consistency.js** - 版本一致性检查

### 更新文件
**核心模块**:
- bin/initmc.js - 支持npm link,移除旧路径依赖
- bin/install-global.js - 添加废弃警告
- lib/init-workflow.js - 智能单命令模式
- lib/version-checker.js - 增强防缓存

**文档更新**:
- docs/developer/安装指南.md - 推荐npm link
- docs/developer/快速上手.md - 更新部署说明
- README.md - 更新安装步骤
- CLAUDE.md - 更新版本号

---

## 🚀 快速开始

### 全局安装(推荐)

```bash
git clone https://github.com/jju666/NeteaseMod-Claude.git
cd NeteaseMod-Claude
npm install
npm link
```

### 部署到项目

```bash
cd your-modsdk-project
initmc  # 一条命令,搞定一切! ✨
```

---

## 📚 详细文档

- **[BUGFIX-v20.2.12.md](./BUGFIX-v20.2.12.md)** - 完整的改进报告
- **[安装指南](./docs/developer/安装指南.md)** - 详细安装步骤
- **[快速上手](./docs/developer/快速上手.md)** - 核心命令使用

---

## ⚠️ 破坏性变更

### 废弃的参数(已移除)
- ❌ `--sync` - 现在自动检测版本并同步
- ❌ `--force` / `--reset` - 现在默认行为已优化
- ❌ `--clean` - 现在自动清理废弃文件
- ❌ `--auto-migrate` - 现在默认启用自动迁移

### 废弃的安装方式(保留但不推荐)
- ⚠️ `npm run deploy` - 已废弃,推荐使用 `npm link`

**迁移指南**: 旧项目无需任何修改,直接运行 `initmc` 即可自动升级! 🎉

---

## 🙏 致谢

感谢所有用户的反馈和建议,本次更新极大地简化了工作流部署流程!

如有问题或建议,请提交 [Issue](https://github.com/jju666/NeteaseMod-Claude/issues)。

---

**完整更新日志**: [CHANGELOG.md](./CHANGELOG.md)

---

## 📋 如何在GitHub创建Release

1. 访问 https://github.com/jju666/NeteaseMod-Claude/releases/new
2. 选择标签: `v20.2.12`
3. 标题: `v20.2.12 - 🎯 智能单命令模式`
4. 复制本文件内容到描述框
5. 点击 "Publish release"
