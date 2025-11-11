# 项目文档导航

> 📚 本项目使用"基于Claude的MODSDK开发工作流 v{{VERSION}}"

---

## 📂 文档组织结构

### 核心工作流文档（上游提供）

存储位置：`.claude/core-docs/`（隐藏目录）

这些文档由工作流上游维护，默认只读：
- [开发规范.md](../.claude/core-docs/开发规范.md) - CRITICAL规范和最佳实践
- [问题排查.md](../.claude/core-docs/问题排查.md) - 常见问题解决方案
- [快速开始.md](../.claude/core-docs/快速开始.md) - 5分钟快速上手
- [MODSDK核心概念.md](../.claude/core-docs/MODSDK核心概念.md) - System/Component/Event概念速查
- [API速查.md](../.claude/core-docs/API速查.md) - 常用API代码片段
- [官方文档查询指南.md](../.claude/core-docs/官方文档查询指南.md) - 官方文档使用指南
- [ai/](../.claude/core-docs/ai/) - AI辅助工作流文档

**💡 如何定制核心文档？**

如果需要针对本项目定制（如添加非MODSDK规范）：
1. 将文档复制到 `markdown/core/`
2. 编辑 `markdown/core/[文档名].md`
3. AI会自动优先读取项目定制版本

---

### 项目特定文档（本地维护）

#### 系统文档
- [systems/](./systems/) - 本项目的System实现文档（AI自动生成）

#### 文档跟踪
- [文档待补充清单.md](./文档待补充清单.md) - 待完善的文档清单

#### 项目定制（可选）
- [core/](./core/) - 覆盖上游核心文档的项目定制版本

---

## 🔄 工作流更新

当工作流上游发布新版本时：

```bash
# 检查更新并同步
initmc --sync

# 自动执行：
# - 同步上游文档（更新软连接）
# - 检测版本更新
# - 智能检测冲突
# - 清理废弃文件（带备份）
```

---

## 📖 常用操作

### 查阅文档
Claude会自动按优先级查找：
1. `markdown/core/` (项目定制版) ⭐ 最高优先级
2. `.claude/core-docs/` (上游基线)
3. `markdown/systems/` (项目System文档)

### 定制核心文档
```bash
# 示例：定制开发规范
cp .claude/core-docs/开发规范.md markdown/core/开发规范.md

# 然后编辑
code markdown/core/开发规范.md

# Claude会自动读取项目定制版本
```

### 查看上游更新
```bash
# 对比上游与项目定制版
diff .claude/core-docs/开发规范.md markdown/core/开发规范.md

# 或在VSCode中对比
code --diff .claude/core-docs/开发规范.md markdown/core/开发规范.md
```

### 重置到上游版本
```bash
# 删除项目定制版，回退到上游基线
rm markdown/core/开发规范.md

# Claude会自动回退到.claude/core-docs/版本
```

---

## 💡 架构优势

**双层文档架构**让你获得：
- ✅ **零风险升级**: 上游更新不影响项目定制
- ✅ **清晰分层**: 核心工作流 vs 项目特定，一目了然
- ✅ **按需定制**: 只定制需要的文档，其他保持同步
- ✅ **完全隔离**: 多项目共用时，互不干扰

---

_文档版本: v{{VERSION}} | 更新时间: 2025-11-11_
