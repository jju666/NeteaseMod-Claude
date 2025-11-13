# 文档创建强制执行机制 (v20.1.1)

> **版本**: v20.1.1
> **创建日期**: 2025-11-13
> **功能**: 100%可靠的任务归档文档同步系统

---

## 📋 问题背景

在v20.0.3及之前版本中,任务归档后的文档同步存在以下问题:

1. ❌ AI可能以"无合适文档"为理由跳过文档创建
2. ❌ 依赖AI的系统约束("NEVER create new files"),不够可靠
3. ❌ 没有验证机制,无法确保文档已创建
4. ❌ 任务知识无法沉淀到项目文档体系

## 🎯 v20.1.1 解决方案

### 核心设计

采用**两阶段验证 + 增强提示词**的可靠方案:

```
阶段1: 归档前生成文档快照
  ├─ generate_doc_snapshot()  # 记录所有markdown文件的mtime和size
  └─ save_doc_snapshot()      # 保存到 .claude/.doc-snapshot.json

阶段2: 注入增强提示词
  ├─ generate_doc_sync_prompt()  # 明确要求"必须创建文档"
  └─ inject_doc_sync_task()      # 提供文档创建模板和决策树

阶段3: 归档后验证文档变更
  ├─ post-archive-doc-enforcer.py
  ├─ 对比快照前后的文档变更
  ├─ 如果无变更 → 阻断操作(exit 2)
  └─ 注入强制提示,要求AI创建/更新文档
```

### 关键特性

#### 1. 智能判断机制

```python
# 不会无脑强制创建,而是智能判断:
if is_test_task(task_desc):
    # 测试任务允许跳过
    pass
elif not has_markdown_docs:
    # 首次使用允许跳过
    pass
else:
    # 正常任务必须创建/更新文档
    enforce_doc_creation()
```

#### 2. 决策树引导

提示词提供清晰的决策树:

```
步骤1: 检查现有文档
  └─ Glob(pattern="markdown/**/*.md")

步骤2: 根据情况决策
  ├─ 情况A: 找到相关文档 → 使用Edit更新
  └─ 情况B: 没有相关文档 → 使用Write创建
```

#### 3. 文档创建模板

提供完整的文档模板:

```markdown
# {{功能名}}

> **创建时间**: 2025-11-13
> **关联任务**: task-1113-170514-xxx
> **任务描述**: xxx

## 概述
## 实现细节
## 相关代码
## 注意事项
```

---

## 🔧 技术实现

### 文件清单

| 文件 | 职责 | 版本 |
|------|------|------|
| `post-archive-hook.py` | 任务归档 + 快照生成 + 提示词注入 | v20.2.0 |
| `post-archive-doc-enforcer.py` | 文档变更验证 + 强制阻断 | v20.1.1 |
| `.doc-snapshot.json` | 归档前文档快照(临时文件) | - |

### Hook执行链

```
PostToolUse (任何工具使用后):
  1. unified-workflow-driver.py      # 工作流状态机
  2. post-archive-hook.py             # 检测step4完成 → 归档
     ├─ generate_doc_snapshot()       # 生成快照
     ├─ move_to_archive()             # 移动任务到已归档/
     └─ inject_doc_sync_task()        # 注入增强提示词
  3. post-archive-doc-enforcer.py     # 验证文档变更
     ├─ compare_snapshots()           # 对比快照
     ├─ 有变更 → exit 0 (放行)
     └─ 无变更 → exit 2 (阻断) + 注入强制提示
```

### 快照数据结构

```json
{
  "d:/project/markdown/systems/ShopSystem.md": {
    "mtime": 1699876543.123,
    "size": 2048
  },
  "d:/project/markdown/events/PurchaseEvent.md": {
    "mtime": 1699876540.456,
    "size": 1024
  }
}
```

---

## 📖 使用指南

### 对于AI

归档阶段会自动触发,AI需要:

1. **分析任务内容**
   - Read `tasks/已归档/task-xxx/context.md`
   - Read `tasks/已归档/task-xxx/solution.md`

2. **检查现有文档**
   - `Glob(pattern="markdown/**/*.md")`
   - 判断是否有相关文档

3. **执行文档操作**
   - 有相关文档 → 使用Edit更新1-2个文档
   - 无相关文档 → 使用Write创建新文档

4. **验证通过**
   - Enforcer检测到文档变更
   - 自动放行,任务完成

### 对于开发者

#### 安装

执行 `initmc` 时自动部署:

```bash
cd your-project/
initmc
# Hook系统会自动配置
```

#### 跳过文档验证(仅测试任务)

如果任务确实是纯测试性质:

```bash
# 方法1: 任务描述包含"测试"关键词
/mc 测试Hook功能

# 方法2: 手动删除快照
rm .claude/.doc-snapshot.json
```

#### 查看验证日志

```bash
# Enforcer的日志输出到stderr
# 可以在Claude Code输出中看到:
✅ 新建文档 (1 个):
  - ShopSystem.md
```

---

## 🚀 工作流程示例

### 场景1: 新功能开发(需要创建文档)

```
1. 用户: /mc 实现商店购买功能
2. AI完成实现,标记step4_cleanup完成
3. post-archive-hook触发:
   ├─ 生成快照: {现有2个文档}
   ├─ 移动任务到已归档/
   └─ 注入提示词: "必须创建/更新文档"
4. AI执行文档同步:
   ├─ Glob("markdown/**/*.md") → 找到现有文档
   ├─ 发现没有商店相关文档
   └─ Write("markdown/systems/商店系统.md") → 创建新文档
5. post-archive-doc-enforcer验证:
   ├─ 对比快照: 新增1个文档
   └─ 验证通过 ✅
```

### 场景2: Bug修复(更新现有文档)

```
1. 用户: /mc 修复商店购买BUG
2. AI完成修复,标记step4_cleanup完成
3. post-archive-hook触发:
   ├─ 生成快照
   └─ 注入提示词
4. AI执行文档同步:
   ├─ Glob → 找到"商店系统.md"
   └─ Edit("markdown/systems/商店系统.md") → 更新已知问题章节
5. post-archive-doc-enforcer验证:
   ├─ 对比快照: 修改1个文档
   └─ 验证通过 ✅
```

### 场景3: 测试任务(允许跳过)

```
1. 用户: /mc 测试Hook功能是否正常
2. AI完成测试,标记step4_cleanup完成
3. post-archive-hook触发
4. AI输出: "此任务为测试性质,无需文档化"
5. post-archive-doc-enforcer验证:
   ├─ 检测到任务描述包含"测试"
   └─ 允许跳过 ✅
```

### 场景4: AI忘记创建文档(触发阻断)

```
1. 用户: /mc 实现玩家排行榜功能
2. AI完成实现,标记step4_cleanup完成
3. post-archive-hook触发 → 注入提示词
4. AI误判: "无需更新文档" (错误!)
5. post-archive-doc-enforcer验证:
   ├─ 对比快照: 无任何变更
   └─ 阻断操作 ❌ + 注入强制提示
6. AI收到强制提示:
   "⚠️ 文档同步检查失败 - 请按决策树处理"
7. AI重新执行:
   ├─ Glob扫描markdown目录
   ├─ 发现没有排行榜文档
   └─ Write("markdown/systems/排行榜系统.md")
8. 验证通过 ✅
```

---

## 🔍 故障排查

### 问题1: 验证总是失败

**症状**: 每次归档都被阻断

**排查**:

```bash
# 1. 检查快照文件是否存在
ls .claude/.doc-snapshot.json

# 2. 查看快照内容
cat .claude/.doc-snapshot.json

# 3. 检查markdown目录
ls markdown/**/*.md

# 4. 手动删除快照重新生成
rm .claude/.doc-snapshot.json
```

### 问题2: 测试任务被强制要求创建文档

**原因**: 任务描述没有包含"测试"关键词

**解决**:

```bash
# 方法1: 任务描述明确包含"测试"
/mc 测试玩家移动功能

# 方法2: 手动跳过
rm .claude/.doc-snapshot.json
```

### 问题3: Enforcer没有触发

**排查**:

```bash
# 1. 检查Hook配置
cat .claude/settings.json | grep post-archive-doc-enforcer

# 2. 确认文件存在
ls .claude/hooks/post-archive-doc-enforcer.py

# 3. 测试Hook脚本
echo '{"cwd": ".", "eventName": "PostToolUse"}' | python .claude/hooks/post-archive-doc-enforcer.py
```

---

## 📊 性能影响

| 操作 | 耗时 | 说明 |
|------|------|------|
| 生成快照 | <50ms | 扫描markdown目录(通常<100个文件) |
| 保存快照 | <10ms | 写入JSON文件 |
| 对比快照 | <20ms | 字典对比操作 |
| Hook总耗时 | <100ms | 对用户体验无影响 |

---

## 🎓 设计原则

1. **确定性执行**: 不依赖AI判断,Hook强制验证
2. **智能容错**: 测试任务、首次使用允许跳过
3. **清晰引导**: 提供决策树和文档模板
4. **快照机制**: 精确对比文档变更
5. **阻断反馈**: 验证失败时注入详细提示

---

## 📝 版本历史

### v20.1.1 (2025-11-13)

- ✅ 新增文档快照生成功能
- ✅ 新增post-archive-doc-enforcer.py验证Hook
- ✅ 增强post-archive-hook.py提示词
- ✅ 添加智能跳过机制(测试任务/首次使用)
- ✅ 提供完整的决策树引导
- ✅ 提供文档创建模板

### v20.0.3 (之前版本)

- ⚠️ 依赖AI自觉性,不够可靠
- ⚠️ 无验证机制

---

## 🔗 相关文档

- [Hook机制完整技术文档](./Hook机制.md)
- [任务归档流程](./post-archive-hook.py)
- [工作流配置](../workflow-config.json)

---

**END**
