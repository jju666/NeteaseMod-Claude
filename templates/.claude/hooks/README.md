# Claude Code Hooks - 工作流强制执行系统

本目录包含多个Hook脚本，实现**工作流强制执行**和**任务全生命周期追踪**。

## 🆕 v18.5.0 重要更新: 符合官方Hook格式

本版本所有Hooks已更新为**Claude Code官方Hook格式规范**:

- ✅ **PreToolUse**: 使用 `hookSpecificOutput.permissionDecision` 格式 (`allow`/`deny`/`ask`)
- ✅ **PostToolUse/Stop/SubagentStop**: 使用标准 `decision: "block"` 格式
- ✅ **settings.json**: 采用官方推荐的嵌套 `hooks` 数组结构
- ✅ **兼容性**: 向后兼容旧格式,平滑升级

官方文档: https://docs.claude.com/en/hooks-reference

## 🔔 桌面通知支持 (v18.4+)

Hooks 支持**跨平台桌面通知**,在屏幕右下角弹出提示:

- ✅ **VSCode**: 原生右下角通知(开箱即用)
- ✅ **PyCharm/IntelliJ**: 系统通知中心(需安装 `plyer`: `pip install plyer`)
- ✅ **其他编辑器**: 彩色终端输出(自动降级)

详见: [通知系统文档](../../../docs/developer/通知系统.md)

---

## 📋 Hook清单

| Hook | 文件 | 触发时机 | 职责 |
|------|------|---------|------|
| **Hook 1** | `user-prompt-submit-hook.py` | 用户提交提示词后 | 检测 `/mc` 命令，自动初始化任务追踪 |
| **Hook 2** | `stop-hook.py` | 会话结束前 | 验证任务完成，失败时阻止结束 |
| **Hook 3** | `subagent-stop-hook.py` | 子代理结束时 | 验证专家审核评分，<8分阻止结束 |

---

## 🎯 核心机制

### Hook 1: 任务初始化拦截

**检测条件**: 用户提示词以 `/mc ` 开头

**自动操作**:
1. 创建任务目录 `tasks/task-{timestamp}/`
2. 初始化 `context.md`（工作记录模板）
3. 初始化 `solution.md`（方案记录模板）
4. 创建 `.task-meta.json`（机器可读元数据）
5. 注入任务追踪提醒到对话

**元数据结构** (`.task-meta.json`):
```json
{
  "task_id": "task-20250113-143022",
  "task_description": "修复商店购买BUG",
  "created_at": "2025-01-13T14:30:22",
  "status": "in_progress",
  "failure_count": 0,
  "failure_history": [],
  "expert_review_triggered": false,
  "expert_review_score": null,
  "user_confirmed_fixed": false,
  "archived_at": null
}
```

---

### Hook 2: 完成验证与重试强制

**检测条件**: 会话尝试结束时

**验证逻辑**:
1. 查找最新的活跃任务（`status: "in_progress"`）
2. 检查 `context.md` 中是否包含用户确认关键词：
   - `已修复`、`修复成功`、`问题解决`
   - `fixed`、`resolved`
   - `用户确认: 是`

**失败处理**:
- **失败次数 < 2**: 
  - 失败计数器 +1
  - 阻止会话结束（exit 2）
  - 强制要求继续分析
  
- **失败次数 ≥ 2**:
  - 失败计数器 +1
  - 标记 `expert_review_triggered: true`
  - 阻止会话结束（exit 2）
  - 强制要求调用 `/mc-review` 专家审核

**成功处理**:
- 检测到用户确认后，允许会话结束
- 更新任务状态为 `completed`
- 记录归档时间

---

### Hook 3: 专家审核质量保障

**检测条件**: 子代理任务包含 `/mc-review`

**评分提取**:
使用正则表达式匹配审核报告中的评分：
- `**总分**: X/10`
- `总分: X/10`
- `Score: X/10`

**质量验证**:
- **评分 < 8分**:
  - 阻止审核结束（exit 2）
  - 强制要求修改方案并重新审核
  - 更新元数据中的 `expert_review_score`
  
- **评分 ≥ 8分**:
  - 允许审核结束
  - 记录评分到元数据
  - 继续实施方案

---

## 🔧 配置方法

Hook系统通过 `.claude/settings.json` 配置 (官方格式):

```json
{
  "$schema": "https://code.claude.com/schemas/settings.json",
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/user-prompt-submit-hook.py",
            "timeout": 5
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-critical-rules.py",
            "timeout": 10
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/enforce-cleanup.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

**关键要点**:
- 使用 `$CLAUDE_PROJECT_DIR` 环境变量引用项目路径
- 每个hook事件包含 `hooks` 数组
- PreToolUse/PostToolUse需要 `matcher` 字段匹配工具名
- `timeout` 设置单个hook超时时间(秒)

**自动配置**: 执行 `initmc` 时会自动生成此配置。

---

## 📊 任务生命周期流程

```
1. 用户输入 /mc "修复BUG"
   ↓
2. Hook 1 自动创建 tasks/task-{id}/
   ↓
3. Claude 执行任务（步骤1→2→2.5→3）
   ↓
4. 第一次尝试失败
   ↓
5. Hook 2 阻止会话结束，失败计数=1
   ↓
6. 强制继续分析
   ↓
7. 第二次尝试失败
   ↓
8. Hook 2 阻止会话结束，失败计数=2
   ↓
9. 触发专家审核提醒
   ↓
10. Claude 调用 /mc-review
    ↓
11. Hook 3 检测审核评分
    ↓
    ├─ 评分<8 → 阻止结束，要求修改
    └─ 评分≥8 → 允许继续
    ↓
12. 继续实施方案
    ↓
13. 用户测试后在 context.md 中记录"已修复"
    ↓
14. Hook 2 检测到确认，允许会话结束
    ↓
15. 任务归档，状态更新为 completed
```

---

## 🐛 故障排查

### 问题1: Hook未执行

**症状**: `/mc` 命令后未创建 `tasks/` 目录

**排查步骤**:
1. 检查 `.claude/settings.json` 是否存在且配置正确
2. 检查 Python 是否可用：`python --version`
3. 检查Hook脚本权限：`ls -la .claude/hooks/`
4. 查看Hook执行日志（stderr输出）

**解决方案**:
```bash
# 重新生成Hook配置
initmc --sync

# 给Hook脚本添加执行权限（Linux/Mac）
chmod +x .claude/hooks/*.py
```

---

### 问题2: Hook阻止了正常操作

**症状**: 会话无法结束，即使任务已完成

**原因**: Hook 2 未检测到用户确认关键词

**解决方案**:
在 `tasks/{task_id}/context.md` 的"用户反馈"部分添加确认：

```markdown
### 用户反馈
用户确认: 是
已修复，功能正常
```

或者使用这些关键词之一：
- `已修复`
- `修复成功`
- `问题解决`
- `fixed`
- `resolved`

---

### 问题3: 审核评分无法提取

**症状**: Hook 3 输出"无法提取审核评分"

**原因**: `/mc-review` 输出格式不匹配

**解决方案**:
确保审核报告包含以下格式之一：
- `**总分**: 8.5/10`
- `总分: 8.5/10`
- `Score: 8.5/10`

---

### 问题4: Python兼容性问题

**症状**: Hook执行时报错 `SyntaxError` 或编码错误

**原因**: Python 2/3 兼容性问题

**解决方案**:
Hook脚本已兼容Python 2.7和3.x，如仍有问题：
1. 检查Python版本：`python --version`
2. 尝试显式使用Python 3：修改 `.claude/settings.json`
   ```json
   {
     "hooks": {
       "userPromptSubmit": "python3 .claude/hooks/user-prompt-submit-hook.py",
       ...
     }
   }
   ```

---

## 📖 相关文档

- **Claude Code Hooks技术文档**: `docs/Claude-Code-Hooks完整技术文档.md`
- **工作流主文档**: `CLAUDE.md`
- **命令系统**: `.claude/commands/mc.md`

---

## 🔒 安全说明

1. **Hook脚本是可信代码**: 由工作流系统部署，不应手动修改
2. **元数据文件保护**: `.task-meta.json` 由系统管理，不要手动编辑
3. **退出码规范**: 
   - `exit(0)` = 成功，允许继续
   - `exit(2)` = 阻止操作
   - `exit(1)` = 非阻塞错误
4. **错误处理**: 所有Hook脚本都有异常捕获，不会导致Claude Code崩溃

---

## 📊 统计数据

- **Hook脚本数量**: 3个
- **总代码行数**: ~370行
- **支持的Python版本**: 2.7+ / 3.x
- **配置复杂度**: 低（自动生成）
- **维护成本**: 极低（零配置）
- **Windows兼容性**: ✅ v18.4.1修复UTF-8编码问题

---

**版本**: v18.5.0
**最后更新**: 2025-11-13

### 🔧 版本更新历史

#### v18.5.0 (2025-11-13)
- ✅ 全面升级为Claude Code官方Hook格式
- ✅ PreToolUse使用 `hookSpecificOutput.permissionDecision` 格式
- ✅ settings.json采用官方嵌套结构
- ✅ 移除弃用的 `decision: "approve"` 格式
- ✅ 添加 `suppressOutput` 控制输出显示
- 📚 更新README配置示例

#### v18.4.1 (2025-11-13)
- 修复Windows平台GBK编码问题
- 所有hooks强制使用UTF-8输出
- 文件操作统一指定encoding='utf-8'
- 支持emoji和Unicode字符正常显示
