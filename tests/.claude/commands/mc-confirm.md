---
description: 显式确认BUG修复任务已完成，触发工作流状态更新
---

# /mc-confirm 命令

**用户明确确认BUG修复任务已经完成。**

## 作用

- 设置 `workflow_state.steps.step3_execute.user_confirmed = true`
- 触发工作流推进到收尾阶段（step4_cleanup）
- 作为自然语言确认识别失败时的备用方案

## 使用场景

当你输入"已修复"、"修复完成"等确认语句后，如果系统未正确识别并推进工作流，可以使用此命令显式确认。

## 响应

确认收到，BUG修复任务已完成确认。

**✓ 已设置 user_confirmed = true**

工作流将在下一轮推进到收尾阶段。
