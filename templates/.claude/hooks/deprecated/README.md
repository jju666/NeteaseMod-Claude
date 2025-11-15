# 废弃Hook文件存档

> **废弃时间**: 2025-11-15
> **废弃原因**: v20.3.0 架构重构 - 统一PreToolUse/PostToolUse机制

---

## 架构重构说明

v20.3.0 版本对Hook状态机进行了完整重构，从"自然语言提示引导AI"转向"四层验证强制拦截"模式。

### 核心变更

1. **PreToolUse统一化**: 所有PreToolUse强制逻辑整合到 `unified-pretooluse-enforcer.py`
2. **PostToolUse简化**: 所有PostToolUse状态更新逻辑整合到 `unified-posttooluse-updater.py`
3. **四层验证架构**: 工具类型 → 前置条件 → 文件路径 → 操作语义
4. **Step2重新引入**: 任务流路由阶段（bug_fix vs feature_development）

---

## 废弃文件清单

### 被 unified-pretooluse-enforcer.py 替代

| 文件名 | 原功能 | 替代方案 |
|--------|--------|---------|
| `enforce-step2.py` | Step2前置检查 | `core/stage_validator.py` Layer 2 (前置条件检查) |
| `workflow-stage-enforcer.py` | 阶段强制器 | `core/stage_validator.py` 四层验证 |
| `prevent-git-history-confusion.py` | Git历史混淆防护 | `core/semantic_analyzer.py` Bash危险命令检测 |
| `doc-sync-enforcer.py` | 文档同步强制器 | `core/semantic_analyzer.py` Write语义分析 |
| `enforce-cleanup.py` | Step4收尾强制 | `core/stage_validator.py` + 子代理规则 |
| `create-cleanup-lock.py` | 创建收尾锁文件 | `core/state_manager.py` create_subagent_lock() |

### 被 unified-posttooluse-updater.py 替代

| 文件名 | 原功能 | 替代方案 |
|--------|--------|---------|
| `unified-workflow-driver.py` | 核心工作流驱动（1079行） | `unified-posttooluse-updater.py` (300行精简版) |
| `iteration-tracker-hook.py` | 迭代追踪 | `unified-posttooluse-updater.py` update_code_changes() |
| `post-tool-use-hook.py` | 旧PostToolUse逻辑 | `unified-posttooluse-updater.py` 完全替代 |
| `track-doc-reading.py` | 文档阅读追踪 | `unified-posttooluse-updater.py` update_docs_read() |

---

## 新架构模块

### Core模块 (templates/.claude/hooks/core/)

```
core/
├── __init__.py                  # 模块初始化
├── state_manager.py             # 三文件状态同步管理器
├── tool_matrix.py               # 四维配置矩阵（阶段-工具-路径-语义）
├── path_validator.py            # 路径验证器（白名单/黑名单）
├── semantic_analyzer.py         # 语义分析器（最细粒度）
├── stage_validator.py           # 四层验证引擎（整合）
└── expert_trigger.py            # 专家触发器（循环检测）
```

### 统一Hook

- **unified-pretooluse-enforcer.py**: 零容忍拦截器，四层验证，违规立即DENY
- **unified-posttooluse-updater.py**: 纯粹状态更新器，专家触发，步骤推进

---

## 迁移指南

如果您需要恢复某个废弃Hook的功能，请参考以下映射关系：

### 1. PreToolUse拦截逻辑

**旧方式** (enforce-step2.py):
```python
if current_step == "step2_route":
    if tool_name == "Write":
        deny(...)
```

**新方式** (core/tool_matrix.py):
```python
"step2_route": {
    "semantic_rules": {
        "Write": {"forbidden": True, "reason": "研究阶段禁止修改文件"}
    }
}
```

### 2. PostToolUse状态更新

**旧方式** (unified-workflow-driver.py):
```python
def handle_posttooluse():
    if tool_name == "Read":
        metrics['docs_read'].append(file_path)
    # ... 1079行复杂逻辑
```

**新方式** (unified-posttooluse-updater.py):
```python
def update_state_by_tool(tool_name, ...):
    if tool_name == "Read":
        update_docs_read(file_path, workflow_state)
    # ... 300行精简逻辑，职责单一
```

### 3. 循环检测与专家触发

**旧方式** (iteration-tracker-hook.py + unified-workflow-driver.py):
```python
# 分散在多个文件中的检测逻辑
if same_file_edit_count > 2:
    # 生成专家Prompt
```

**新方式** (core/expert_trigger.py):
```python
expert_trigger = ExpertTrigger()
if expert_trigger.should_trigger(workflow_state):
    expert_prompt = expert_trigger.generate_prompt(workflow_state)
```

---

## 保留的Hook文件

以下Hook未废弃，仍在使用中：

- `session-start-hook.py` - 会话开始初始化
- `user-prompt-submit-hook.py` - 用户提示提交处理
- `stop-hook.py` - 会话停止清理
- `subagent-stop-hook.py` - 子代理停止处理
- `cleanup-subagent-stop.py` - 收尾子代理特殊处理
- `post-archive-hook.py` - 归档后处理
- `post-archive-doc-enforcer.py` - 归档后文档强制
- `session-end-hook.py` - 会话结束处理
- `conversation-recorder.py` - 对话记录
- 其他工具类Hook (hook_logger.py, vscode_notify.py, etc.)

---

## 参考文档

- [Hook状态机机制](../../../docs/developer/Hook状态机机制.md) - v20.2.17 完整说明
- [四层验证架构](../core/stage_validator.py) - 新架构实现

---

_最后更新: 2025-11-15 | 架构版本: v20.3.0_
