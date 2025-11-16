# BUGFIX v22.3.8 - 专家审查状态更新修复

**日期**: 2025-11-17
**影响版本**: v22.3.6 及之前所有版本
**修复版本**: v22.3.8

---

## 问题描述

### BUG 现象

在下游项目使用 `/mc` 启动标准工作流后,专家子代理虽然成功启动并完成审查,但 `task-meta.json` 中以下字段未能正确更新:

```json
{
  "steps": {
    "planning": {
      "expert_review_completed": false,  // ❌ 应为 true
      "expert_review_count": 0,          // ❌ 应为 1+
      "expert_review_result": null       // ❌ 应有审查结果
    }
  },
  "metrics": {
    "expert_review_triggered": false     // ❌ 应为 true
  },
  "bug_fix_tracking": {
    "expert_triggered": false            // ❌ 应为 true
  }
}
```

### 影响范围

- 专家审查结果无法被正确记录
- 审查次数统计错误
- metrics 和 bug_fix_tracking 字段未同步更新
- 影响后续工作流决策(依赖这些字段的逻辑)

### 根本原因分析

通过分析调试日志发现了真正的根本原因:

#### 原因 1: SubagentStop Hook 读取错误的 transcript 文件 (关键BUG)

**代码位置**: `templates/.claude/hooks/lifecycle/subagent_stop.py` 第401行

**错误代码**:
```python
# ❌ BUG: 读取主会话transcript,而非子代理transcript
transcript_path = hook_input.get('transcript_path')
```

**问题分析**:
- Hook 接收的参数中包含两个路径:
  - `transcript_path`: 主会话的 transcript 文件
  - `agent_transcript_path`: 子代理的 transcript 文件
- 专家审查结果(SUBAGENT_RESULT标记)只存在于**子代理的transcript**中
- Hook错误地读取了主会话文件,导致无法找到结果标记,提前退出

**日志证据** (`subagent-stop-debug.log`):
```
完整输入: {
  "transcript_path": "...\\6bf79c20-9a87-460a-93a1-9cfbefc68a25.jsonl",  // 主会话
  "agent_transcript_path": "...\\agent-8f91bbfe.jsonl",                 // 子代理 ✅
}
[02:14:06.079] transcript_path = '...\\6bf79c20...jsonl'                // ❌ 读取错误路径
[02:14:06.082] Extract result: None                                     // 提取失败,提前退出
```

#### 原因 2: metrics 字段未同步更新 (次要问题)

**代码位置**: `templates/.claude/hooks/lifecycle/subagent_stop.py` 第525-545行

**缺失逻辑**:
`update_expert_review` 回调函数只更新了 `steps.planning` 下的字段,未更新:
- `metrics.expert_review_triggered`
- `bug_fix_tracking.expert_triggered`

---

## 修复方案

### 修复 1: 使用正确的 transcript 路径

**修改文件**:
- `templates/.claude/hooks/lifecycle/subagent_stop.py`
- `tests/.claude/hooks/lifecycle/subagent_stop.py`

**修改位置**: 第400-416行

**修复后代码**:
```python
# 2. 获取子代理transcript路径(v22.3.8关键修复)
# 🔥 BUG修复: 必须使用agent_transcript_path,而非transcript_path
# transcript_path是主会话的记录,agent_transcript_path才是子代理的记录
transcript_path = hook_input.get('agent_transcript_path')
log_to_file(f"agent_transcript_path = {repr(transcript_path)}")

# 兜底:如果agent_transcript_path不存在,尝试使用transcript_path(向后兼容)
if not transcript_path:
    transcript_path = hook_input.get('transcript_path')
    log_to_file(f"[WARN] agent_transcript_path不存在,降级使用transcript_path: {repr(transcript_path)}")

if not transcript_path:
    sys.stderr.write("[WARN] 未提供agent_transcript_path或transcript_path,跳过\n")
    log_to_file("退出: 两个路径都为空")
    print(json.dumps({}, ensure_ascii=False))
    sys.exit(0)
```

**关键变更**:
1. ✅ 优先使用 `agent_transcript_path` 而非 `transcript_path`
2. ✅ 添加降级逻辑,保持向后兼容
3. ✅ 改进日志输出,便于调试

### 修复 2: 同步更新 metrics 字段

**修改文件**:
- `templates/.claude/hooks/lifecycle/subagent_stop.py`
- `tests/.claude/hooks/lifecycle/subagent_stop.py`

**修改位置**: 第525-554行 (`update_expert_review` 函数)

**新增代码**:
```python
def update_expert_review(meta_data):
    # ... 原有代码 ...

    # 🔥 v22.3.8新增:同步更新metrics和bug_fix_tracking字段
    if 'metrics' not in meta_data:
        meta_data['metrics'] = {}
    meta_data['metrics']['expert_review_triggered'] = True

    if 'bug_fix_tracking' not in meta_data:
        meta_data['bug_fix_tracking'] = {}
    meta_data['bug_fix_tracking']['expert_triggered'] = True

    log_to_file(f"atomic_update更新字段: ..., metrics.expert_review_triggered=True, bug_fix_tracking.expert_triggered=True")
    return meta_data
```

**关键变更**:
1. ✅ 添加 `metrics.expert_review_triggered = True`
2. ✅ 添加 `bug_fix_tracking.expert_triggered = True`
3. ✅ 更新日志输出包含新字段

---

## 验证方法

### 测试步骤

1. **清理旧数据**:
   ```bash
   cd tests
   rm -rf tasks/任务-*
   rm .task-active.json
   ```

2. **启动新任务**:
   ```bash
   /mc
   # 输入任务描述(触发bug_fix类型的任务)
   ```

3. **等待专家审查完成**

4. **检查 task-meta.json**:
   ```bash
   cat tests/tasks/任务-*/\.task-meta.json
   ```

### 预期结果

```json
{
  "steps": {
    "planning": {
      "expert_review_completed": true,        // ✅ 应为 true
      "expert_review_count": 1,               // ✅ 应 >= 1
      "expert_review_result": "pass",         // ✅ 应有结果
      "expert_review": {                      // ✅ 应包含完整审查结果
        "approved": true,
        "review": "...",
        "suggestions": []
      }
    }
  },
  "metrics": {
    "expert_review_triggered": true           // ✅ 新增字段
  },
  "bug_fix_tracking": {
    "expert_triggered": true                  // ✅ 新增字段
  }
}
```

### 日志验证

**检查 `subagent-stop-debug.log`**:
```
[时间] agent_transcript_path = '...\\agent-xxxxxxxx.jsonl'  // ✅ 使用正确路径
[时间] Extract result: {"approved": true, ...}              // ✅ 成功提取
[时间] atomic_update更新字段: expert_review_completed=True, expert_review_count=1, expert_review_result=pass, metrics.expert_review_triggered=True, bug_fix_tracking.expert_triggered=True
```

---

## 相关问题

### 为什么之前没发现这个BUG?

1. **误诊问题**: 最初错误地认为是 `subagent_type: undefined` 导致子代理启动失败
2. **日志误读**: 没有仔细检查 `agent_transcript_path` 和 `transcript_path` 的区别
3. **测试不完整**: 之前的测试只验证了子代理启动,未深入检查元数据更新

### v22.3.7 修复了什么?

v22.3.7 修复的是 PreToolUse Hook 的 `updatedInput` 参数丢失问题:
- **问题**: 使用 `updatedInput` 时只保留了 `prompt` 字段,丢失了 `subagent_type` 等参数
- **修复**: 保留所有原始参数,只修改需要更新的字段

虽然这个修复是必要的,但**不是导致专家审查状态未更新的根本原因**。

### 与 v22.3.7 的关系

- **v22.3.7**: 确保子代理能正确启动(参数传递修复)
- **v22.3.8**: 确保子代理结果能被正确提取和记录(路径修复 + 字段同步)

两者都是必要的,相互独立但配合工作。

---

## 技术细节

### SubagentStop Hook 执行流程

1. ✅ 检查 `stop_hook_active` (防止重复触发)
2. 🔥 **读取子代理 transcript** (v22.3.8修复点)
3. ✅ 提取 SUBAGENT_RESULT 标记
4. ✅ 获取活跃任务ID
5. ✅ 加载 task-meta.json
6. 🔥 **使用 atomic_update 更新状态** (v22.3.8增强点)
7. ✅ 生成用户消息

### SUBAGENT_RESULT 标记格式

子代理在完成审查后会在其 transcript 中写入:
```html
<!-- SUBAGENT_RESULT {
  "approved": true,
  "review": "审查通过",
  "suggestions": []
} -->
```

### atomic_update 并发安全

使用 `TaskMetaManager.atomic_update()` 方法确保并发安全:
```python
def atomic_update(task_id, callback):
    """
    1. 加载最新的 task-meta.json
    2. 调用 callback(meta_data) 进行修改
    3. 保存修改后的数据
    4. 内置文件锁防止竞态条件
    """
```

---

## 版本历史

### v22.3.8 (2025-11-17) ✅

**新增**:
- SubagentStop Hook 使用 `agent_transcript_path` 读取子代理记录
- `update_expert_review` 回调同步更新 `metrics.expert_review_triggered`
- `update_expert_review` 回调同步更新 `bug_fix_tracking.expert_triggered`

**修复**:
- 修复专家审查结果提取失败的根本原因(读取错误文件)
- 修复 `expert_review_count` 等字段未更新问题
- 改进日志输出,增强可调试性

**向后兼容**:
- 保留对 `transcript_path` 的降级支持
- 不影响非专家审查的工作流

### v22.3.7 (2025-11-17)

**修复**:
- PreToolUse Hook `updatedInput` 参数丢失问题
- 确保 `subagent_type` 等参数正确传递

### v22.3.6 及之前

**问题**:
- SubagentStop Hook 读取错误的 transcript 文件
- 专家审查状态字段未能正确更新

---

## 相关文件

### 修改的文件
- [templates/.claude/hooks/lifecycle/subagent_stop.py](templates/.claude/hooks/lifecycle/subagent_stop.py) (L400-416, L525-554)
- [tests/.claude/hooks/lifecycle/subagent_stop.py](tests/.claude/hooks/lifecycle/subagent_stop.py) (同上)

### 备份文件
- [templates/.claude/hooks/lifecycle/subagent_stop.py.backup-v22.3.8](templates/.claude/hooks/lifecycle/subagent_stop.py.backup-v22.3.8)

### 调试日志示例
- [tests/subagent-stop-debug.log](tests/subagent-stop-debug.log)
- [tests/2025-11-17-command-messagemc-is-runningcommand-message.txt](tests/2025-11-17-command-messagemc-is-runningcommand-message.txt)

### 参考文档
- [Hook状态机功能文档](docs/developer/hooks状态机功能文档.md)
- [Claude Code Hook 官方文档](docs/claudecode/hook.md)

---

## 总结

这次修复解决了一个**关键但隐蔽**的BUG:

1. **根本原因**: Hook读取了错误的transcript文件,导致无法提取审查结果
2. **连带问题**: metrics和bug_fix_tracking字段未同步更新
3. **修复策略**:
   - 使用正确的 `agent_transcript_path` (关键修复)
   - 同步更新所有相关字段 (完善修复)
   - 保持向后兼容 (稳健性)

**影响**: 修复后,专家审查工作流将完全可用,所有状态字段正确更新,支持后续决策逻辑。

---

**作者**: Claude
**审核**: 待人工审核
**状态**: ✅ 已实施,待测试验证
