# Hook 开发者指南

> **版本**: v22.0.0
> **最后更新**: 2025-11-15
> **适用对象**: Hook系统开发者、工作流定制者
> **架构版本**: v22.0 PreToolUse驱动强制工作流

本文档提供 NeteaseMod-Claude 工作流系统 Hook 机制的开发与定制指南。

---

## 📋 目录

1. [快速开始](#快速开始)
2. [自定义验证规则](#自定义验证规则)
3. [添加新的工作流阶段](#添加新的工作流阶段)
4. [修改专家触发条件](#修改专家触发条件)
5. [创建自定义Hook](#创建自定义hook)
6. [调试技巧](#调试技巧)
7. [测试方法](#测试方法)
8. [常见问题](#常见问题)
9. [最佳实践](#最佳实践)

---

## 快速开始

### 环境准备

1. **安装依赖**

```bash
cd D:\EcWork\基于Claude的MODSDK开发工作流
npm install
```

2. **全局部署**

```bash
npm link
```

3. **在目标项目中初始化**

```bash
cd D:\EcWork\NetEaseMapECBedWars
initmc
```

4. **验证部署**

```bash
# 检查core/模块是否存在
ls .claude/hooks/core/

# 预期输出：
#  __init__.py
#  tool_matrix.py
#  stage_validator.py
#  path_validator.py
#  semantic_analyzer.py
#  expert_trigger.py
#  state_manager.py

# 检查统一Hook是否存在
ls .claude/hooks/unified-*

# 预期输出：
#  unified-pretooluse-enforcer.py
#  unified-posttooluse-updater.py
```

### 测试Hook系统

创建测试脚本验证Hook工作正常：

```python
# test-hooks.py
import sys
import os

# 添加hooks路径
sys.path.insert(0, '.claude/hooks')

from core.stage_validator import StageValidator
from core.state_manager import StateManager

def test_layer1_validation():
    """测试第一层验证：阶段-工具基础验证"""
    validator = StageValidator(cwd=os.getcwd())

    # 测试：Step1禁止Write工具
    result = validator.validate(
        current_step="step1_understand",
        tool_name="Write",
        tool_input={"file_path": "test.py"},
        workflow_state={
            "current_step": "step1_understand",
            "steps": {"step0_context": {"status": "completed"}}
        }
    )

    assert not result["allowed"], "Step1应该禁止Write工具"
    print("✅ Layer 1测试通过: Step1禁止Write")

def test_layer2_preconditions():
    """测试第二层验证：前置条件检查"""
    validator = StageValidator(cwd=os.getcwd())

    # 测试：Step3需要Step1完成
    result = validator.validate(
        current_step="step3_execute",
        tool_name="Edit",
        tool_input={"file_path": "test.py"},
        workflow_state={
            "current_step": "step3_execute",
            "steps": {}  # Step1未完成
        }
    )

    assert not result["allowed"], "Step3应该检查Step1前置条件"
    print("✅ Layer 2测试通过: 前置条件检查")

def test_layer3_path_validation():
    """测试第三层验证：文件路径验证"""
    validator = StageValidator(cwd=os.getcwd())

    # 测试：Step1禁止Read代码文件
    result = validator.validate(
        current_step="step1_understand",
        tool_name="Read",
        tool_input={"file_path": "behavior_packs/main.py"},
        workflow_state={
            "current_step": "step1_understand",
            "steps": {"step0_context": {"status": "completed"}}
        }
    )

    assert not result["allowed"], "Step1应该禁止Read代码文件"
    print("✅ Layer 3测试通过: 路径验证")

if __name__ == "__main__":
    print("🧪 开始Hook系统测试...\n")

    test_layer1_validation()
    test_layer2_preconditions()
    test_layer3_path_validation()

    print("\n🎉 所有测试通过！Hook系统工作正常。")
```

运行测试：

```bash
python test-hooks.py
```

---

## 自定义验证规则

### 场景1: 添加路径黑名单

**需求**: 禁止在Step3阶段修改配置文件。

**修改文件**: `templates/.claude/hooks/core/tool_matrix.py`

```python
"step3_execute": {
    "path_rules": {
        "Write": {
            "whitelist_patterns": [
                "behavior_packs/**/*.py",
                "resource_packs/**/*.json",
                "scripts/**/*.js"
            ],
            "blacklist": [
                ".task-meta.json",
                "workflow-state.json",
                "**/*.config.json",  # ← 新增：禁止修改配置文件
                "settings.json",
                ".env"  # ← 新增：禁止修改环境变量文件
            ]
        }
    }
}
```

**测试**:

```python
# test_custom_path_rule.py
from core.stage_validator import StageValidator

validator = StageValidator()
result = validator.validate(
    current_step="step3_execute",
    tool_name="Write",
    tool_input={"file_path": "app.config.json"},
    workflow_state={
        "current_step": "step3_execute",
        "steps": {
            "step1_understand": {"status": "completed"},
            "step2_research": {"status": "completed"}
        }
    }
)

assert not result["allowed"], "应该拒绝修改配置文件"
print("✅ 自定义路径规则生效")
```

### 场景2: 添加语义规则

**需求**: 禁止在Step1使用WebSearch（避免AI偷懒不读文档）。

**修改文件**: `templates/.claude/hooks/core/tool_matrix.py`

```python
"step1_understand": {
    "allowed_tools": ["Read"],  # 不包括WebSearch
    "semantic_rules": {
        "WebSearch": {
            "forbidden": True,
            "reason": "理解任务需求阶段禁止使用WebSearch，请先阅读项目文档"
        }
    }
}
```

### 场景3: 添加危险命令检测

**需求**: 禁止使用curl下载外部脚本并执行。

**修改文件**: `templates/.claude/hooks/core/semantic_analyzer.py`

```python
class SemanticAnalyzer:
    def _is_dangerous_command(self, command) -> bool:
        """检测危险Bash命令"""
        dangerous_patterns = [
            r'rm\s+-rf\s+/',
            r'git\s+push\s+--force',
            r'sudo\b',
            r'mkfs\b',
            r'dd\s+if=',
            r'curl\s+.*\|\s*bash',  # ← 新增：禁止curl | bash
            r'wget\s+.*\|\s*sh',    # ← 新增：禁止wget | sh
            r'eval\s*\$\(',         # ← 新增：禁止eval命令替换
        ]
        return any(re.search(pattern, command) for pattern in dangerous_patterns)
```

---

## 添加新的工作流阶段

### 场景: 添加Step2.5设计方案阶段

**需求**: 在任务研究阶段后、执行实施前，增加一个设计方案阶段。

#### 1. 修改阶段顺序

**修改文件**: `templates/.claude/hooks/core/tool_matrix.py`

```python
# 修改STEP_ORDER
STEP_ORDER = [
    "step0_context",
    "step1_understand",
    "step2_research",
    "step2.5_design",  # ← 新增阶段
    "step3_execute",
    "step4_cleanup"
]
```

#### 2. 添加阶段配置

```python
# 在STAGE_TOOL_MATRIX中添加
"step2.5_design": {
    "display_name": "设计方案",
    "description": "设计技术方案，绘制架构图，编写设计文档",

    "allowed_tools": ["Read", "Write", "Grep", "Glob"],

    "preconditions": ["step2_completed"],

    "path_rules": {
        "Write": {
            "whitelist_patterns": [
                "docs/design/**/*.md",
                "docs/architecture/**/*.md",
                "tasks/*/design.md"
            ],
            "blacklist": [
                "behavior_packs/**/*",
                "resource_packs/**/*",
                ".task-meta.json"
            ],
            "description": "只能写入设计文档，禁止修改代码"
        },
        "Read": {
            "whitelist_patterns": ["**/*.md", "**/*.py", "**/*.js"],
            "description": "可以阅读代码和文档"
        }
    },

    "semantic_rules": {
        "Write": {
            "purpose": "design_documentation",
            "description": "编写设计文档，必须包含架构图、接口定义、数据流图"
        },
        "Edit": {
            "forbidden": True,
            "reason": "设计阶段禁止Edit代码文件"
        },
        "Bash": {
            "forbidden": True,
            "reason": "设计阶段禁止执行命令"
        }
    },

    "completion_condition": {
        "trigger_expr": "workflow_state.get('steps', {}).get('step2.5_design', {}).get('design_approved', False)",
        "auto_advance": True,
        "next_step": "step3_execute",
        "description": "AI完成设计文档并明确说明设计完成后推进到Step3"
    },

    "ai_guidance": """
## Step2.5: 设计方案阶段

你现在需要设计技术方案，输出设计文档。

### 设计内容

1. **架构设计**:
   - 模块划分
   - 接口定义
   - 数据流设计

2. **技术选型**:
   - 使用的技术栈
   - 第三方库选择
   - 性能考虑

3. **风险评估**:
   - 潜在风险
   - 降低风险的策略

### 输出要求

使用Write工具创建设计文档：

Write("docs/design/任务-XXX-设计方案.md", content=设计文档内容)

完成后明确说明"设计完成"。
"""
}
```

#### 3. 修改PostToolUse检测逻辑

**修改文件**: `templates/.claude/hooks/orchestrator/posttooluse_updater.py`

```python
def check_step_completion(current_step, workflow_state, task_meta, state_mgr):
    """检测步骤是否完成，自动推进工作流"""

    # ... 现有逻辑 ...

    # 特殊处理：Step2.5设计方案完成检测
    if current_step == "step2.5_design":
        # 检测AI回复中是否包含"设计完成"
        # 注意：这需要在UserPromptSubmit Hook中设置标志
        is_completed = workflow_state.get('steps', {}).get('step2.5_design', {}).get('design_approved', False)

        if is_completed:
            # 推进到Step3
            workflow_state['current_step'] = 'step3_execute'
            # ... 更新步骤状态 ...
```

#### 4. 修改UserPromptSubmit Hook

**修改文件**: `templates/.claude/hooks/orchestrator/user_prompt_handler.py`

```python
# 在任务初始化时添加Step2.5
def initialize_workflow_state(...):
    workflow_state = {
        # ...
        "steps": {
            "step0_context": {"status": "pending"},
            "step1_understand": {"status": "pending"},
            "step2_research": {"status": "pending"},
            "step2.5_design": {"status": "pending"},  # ← 新增
            "step3_execute": {"status": "pending"},
            "step4_cleanup": {"status": "pending"}
        }
    }

# 在用户输入检测中添加设计完成关键词
def detect_design_completion(user_input):
    """检测用户确认设计完成"""
    confirmation_keywords = [
        r'(?:设计完成|design\s+completed)',
        r'(?:方案设计好了|设计好了)',
        r'(?:/mc-design-confirm)'
    ]

    for pattern in confirmation_keywords:
        if re.search(pattern, user_input, re.IGNORECASE):
            return True

    return False

# 在UserPromptSubmit主逻辑中
if workflow_state.get('current_step') == 'step2.5_design':
    if detect_design_completion(user_input):
        workflow_state['steps']['step2.5_design']['design_approved'] = True
```

#### 5. 测试新阶段

```python
# test_step2.5_design.py
from core.stage_validator import StageValidator

validator = StageValidator()

# 测试1：Step2.5允许Write设计文档
result = validator.validate(
    current_step="step2.5_design",
    tool_name="Write",
    tool_input={"file_path": "docs/design/设计方案.md"},
    workflow_state={
        "current_step": "step2.5_design",
        "steps": {
            "step2_research": {"status": "completed"}
        }
    }
)
assert result["allowed"], "Step2.5应该允许Write设计文档"
print("✅ 测试1通过")

# 测试2：Step2.5禁止Write代码
result = validator.validate(
    current_step="step2.5_design",
    tool_name="Write",
    tool_input={"file_path": "behavior_packs/main.py"},
    workflow_state={
        "current_step": "step2.5_design",
        "steps": {
            "step2_research": {"status": "completed"}
        }
    }
)
assert not result["allowed"], "Step2.5应该禁止Write代码"
print("✅ 测试2通过")

# 测试3：Step2.5禁止Bash命令
result = validator.validate(
    current_step="step2.5_design",
    tool_name="Bash",
    tool_input={"command": "python test.py"},
    workflow_state={
        "current_step": "step2.5_design",
        "steps": {
            "step2_research": {"status": "completed"}
        }
    }
)
assert not result["allowed"], "Step2.5应该禁止Bash命令"
print("✅ 测试3通过")

print("\n🎉 Step2.5阶段测试全部通过！")
```

---

## 修改专家触发条件

### 场景1: 调整BUG修复循环阈值

**需求**: 降低专家触发阈值，更早介入帮助AI。

**修改文件**: `templates/.claude/hooks/core/expert_trigger.py`

```python
class ExpertTrigger:
    def _detect_bug_fix_loop(self, workflow_state) -> bool:
        """
        检测BUG修复循环
        触发条件: iterations≥2, negative≥2, same_file≥2
        """
        bug_tracking = workflow_state.get('bug_fix_tracking', {})
        iterations = bug_tracking.get('iterations', [])
        indicators = bug_tracking.get('loop_indicators', {})

        iterations_count = len(iterations)
        negative_count = indicators.get('negative_feedback_count', 0)
        same_file_count = indicators.get('same_file_edit_count', 0)

        # 原阈值: iterations≥2, negative≥2, same_file≥2
        # 新阈值: iterations≥1, negative≥1, same_file≥2（更早触发）
        return (
            iterations_count >= 1 and  # ← 修改: 2 → 1
            negative_count >= 1 and    # ← 修改: 2 → 1
            same_file_count >= 2
        )
```

### 场景2: 添加新的循环检测模式

**需求**: 检测"工具调用失败循环"（AI反复尝试失败的操作）。

**修改文件**: `templates/.claude/hooks/core/expert_trigger.py`

```python
class ExpertTrigger:
    def should_trigger(self, workflow_state) -> bool:
        """判断是否应该触发专家审查"""
        # 1. 检查是否已触发
        if workflow_state.get('expert_triggered', False):
            return False

        # 2. 只在Step3阶段触发
        if workflow_state.get('current_step') != 'step3_execute':
            return False

        # 3. 根据任务类型检测循环
        task_type = workflow_state.get('task_type', 'general')

        if task_type == 'bug_fix':
            return (self._detect_bug_fix_loop(workflow_state) or
                    self._detect_tool_failure_loop(workflow_state))  # ← 新增
        elif task_type == 'feature_development':
            return self._detect_feature_loop(workflow_state)

        return False

    def _detect_tool_failure_loop(self, workflow_state) -> bool:
        """
        检测工具调用失败循环
        触发条件: 工具调用失败次数≥3
        """
        metrics = workflow_state.get('metrics', {})
        failed_ops = metrics.get('failed_operations', [])

        # 统计最近5个操作中的失败次数
        recent_failures = failed_ops[-5:] if len(failed_ops) >= 5 else failed_ops
        failure_count = len(recent_failures)

        return failure_count >= 3

    def generate_prompt(self, workflow_state) -> str:
        """生成专家分析Prompt"""
        task_type = workflow_state.get('task_type', 'general')

        if task_type == 'bug_fix':
            # 判断是哪种循环
            if self._detect_tool_failure_loop(workflow_state):
                return self._generate_tool_failure_prompt(workflow_state)  # ← 新增
            else:
                return self._generate_bug_fix_prompt(workflow_state)
        # ...

    def _generate_tool_failure_prompt(self, workflow_state) -> str:
        """生成工具失败循环专家Prompt"""
        metrics = workflow_state.get('metrics', {})
        failed_ops = metrics.get('failed_operations', [])

        # 构建失败操作历史
        history = "## 失败操作历史\n\n"
        for i, op in enumerate(failed_ops[-5:], 1):
            history += f"### 失败操作 {i}\n"
            history += f"- **时间**: {op.get('timestamp', 'unknown')}\n"
            history += f"- **工具**: {op.get('tool', 'unknown')}\n"
            history += f"- **文件**: {op.get('file', 'unknown')}\n"
            history += f"- **错误**: {op.get('error', 'unknown')[:200]}\n\n"

        prompt = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 专家审查系统已触发
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 检测到的问题模式

**循环类型**: tool_failure_loop（工具调用失败循环）
**置信度**: 85%
**证据**:
- 失败操作次数: {len(failed_ops)}
- 问题模式: AI反复尝试失败的操作，未能调整策略

{history}

## 你的任务

分析为什么工具调用反复失败，找出根本原因。

1. **错误模式分析**: 失败操作有什么共同点？
2. **环境问题排查**: 是否存在环境配置问题？
3. **权限问题排查**: 是否存在文件权限问题？
4. **备选策略**: 如何规避这些失败？

请立即开始分析。
"""
        return prompt
```

---

## 创建自定义Hook

### 场景: 创建代码质量检查Hook

**需求**: 在PostToolUse阶段检查代码质量，发现问题时给AI提示。

#### 1. 创建Hook文件

**文件**: `templates/.claude/hooks/code-quality-checker.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Quality Checker - 代码质量检查Hook
触发时机: PostToolUse (Write/Edit)
职责: 检查代码质量，发现问题时给出改进建议
"""

import sys
import json
import re
from typing import Dict, List

def check_code_quality(file_path: str, content: str) -> Dict:
    """
    检查代码质量

    Returns:
        {
            "has_issues": bool,
            "issues": [{"severity": "warning|error", "message": str}]
        }
    """
    issues = []

    # 1. 检查DEBUG代码
    if re.search(r'print\s*\(.*debug', content, re.IGNORECASE):
        issues.append({
            "severity": "warning",
            "message": "检测到DEBUG代码（print调试），建议在生产环境前清理"
        })

    # 2. 检查硬编码密钥
    if re.search(r'(password|secret|token)\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE):
        issues.append({
            "severity": "error",
            "message": "检测到硬编码的密钥/密码，存在安全风险！请使用环境变量"
        })

    # 3. 检查过长函数
    lines = content.split('\n')
    in_function = False
    function_lines = 0
    function_name = ""

    for line in lines:
        # 检测函数定义
        func_match = re.match(r'\s*def\s+(\w+)\s*\(', line)
        if func_match:
            if in_function and function_lines > 50:
                issues.append({
                    "severity": "warning",
                    "message": f"函数 {function_name} 过长（{function_lines}行），建议拆分"
                })
            in_function = True
            function_lines = 0
            function_name = func_match.group(1)
        elif in_function:
            function_lines += 1

    # 4. 检查TODO/FIXME
    todo_count = len(re.findall(r'#\s*(TODO|FIXME)', content, re.IGNORECASE))
    if todo_count > 3:
        issues.append({
            "severity": "warning",
            "message": f"代码中有{todo_count}个TODO/FIXME标记，建议及时处理"
        })

    return {
        "has_issues": len(issues) > 0,
        "issues": issues
    }

def generate_suggestion(issues: List[Dict]) -> str:
    """生成改进建议消息"""
    if not issues:
        return ""

    message = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    message += "📝 代码质量检查\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    errors = [i for i in issues if i['severity'] == 'error']
    warnings = [i for i in issues if i['severity'] == 'warning']

    if errors:
        message += "❌ **严重问题**:\n"
        for issue in errors:
            message += f"   - {issue['message']}\n"
        message += "\n"

    if warnings:
        message += "⚠️ **警告**:\n"
        for issue in warnings:
            message += f"   - {issue['message']}\n"
        message += "\n"

    message += "建议在继续之前解决这些问题。\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

    return message

def main():
    """主入口"""
    # 1. 解析输入
    try:
        event_data = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        # 静默退出
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": ""
            },
            "suppressOutput": True
        }))
        sys.exit(0)

    tool_name = event_data.get("toolName", "")
    tool_input = event_data.get("toolInput", {})
    is_error = event_data.get("isError", False)

    # 2. 只处理Write/Edit工具，且成功的操作
    if tool_name not in ["Write", "Edit"] or is_error:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": ""
            },
            "suppressOutput": True
        }))
        sys.exit(0)

    # 3. 只检查Python代码文件
    file_path = tool_input.get("file_path", "")
    if not file_path.endswith('.py'):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": ""
            },
            "suppressOutput": True
        }))
        sys.exit(0)

    # 4. 获取文件内容
    content = ""
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        # Edit工具只有new_string，无法获取完整内容
        # 这里简化处理，只检查new_string
        content = tool_input.get("new_string", "")

    # 5. 检查代码质量
    result = check_code_quality(file_path, content)

    # 6. 输出建议
    if result["has_issues"]:
        suggestion = generate_suggestion(result["issues"])
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": suggestion
            },
            "suppressOutput": False
        }))
    else:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": ""
            },
            "suppressOutput": True
        }))

    sys.exit(0)

if __name__ == "__main__":
    main()
```

#### 2. 注册Hook

**修改文件**: `templates/.claude/settings.json.template`

```json
{
  "hooks": {
    "postToolUse": [
      {
        "command": ["python", ".claude/hooks/orchestrator/posttooluse_updater.py"],
        "applicableTools": ["Read", "Write", "Edit", "Bash", "Task", "Grep", "Glob"]
      },
      {
        "command": ["python", ".claude/hooks/code-quality-checker.py"],
        "applicableTools": ["Write", "Edit"]
      }
    ]
  }
}
```

#### 3. 测试自定义Hook

创建测试文件：

```python
# test_code_quality_hook.py
import subprocess
import json

def test_debug_code_detection():
    """测试DEBUG代码检测"""
    hook_input = {
        "toolName": "Write",
        "toolInput": {
            "file_path": "test.py",
            "content": """
def process_data(data):
    print("DEBUG: data =", data)
    return data * 2
"""
        },
        "isError": False
    }

    result = subprocess.run(
        ["python", ".claude/hooks/code-quality-checker.py"],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True
    )

    output = json.loads(result.stdout)
    context = output["hookSpecificOutput"]["additionalContext"]

    assert "DEBUG代码" in context, "应该检测到DEBUG代码"
    print("✅ DEBUG代码检测通过")

def test_hardcoded_password_detection():
    """测试硬编码密码检测"""
    hook_input = {
        "toolName": "Write",
        "toolInput": {
            "file_path": "test.py",
            "content": """
def connect_db():
    password = "mySecretPassword123"
    return connect(password)
"""
        },
        "isError": False
    }

    result = subprocess.run(
        ["python", ".claude/hooks/code-quality-checker.py"],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True
    )

    output = json.loads(result.stdout)
    context = output["hookSpecificOutput"]["additionalContext"]

    assert "硬编码" in context, "应该检测到硬编码密码"
    assert "严重问题" in context, "应该标记为严重问题"
    print("✅ 硬编码密码检测通过")

if __name__ == "__main__":
    print("🧪 测试代码质量检查Hook...\n")
    test_debug_code_detection()
    test_hardcoded_password_detection()
    print("\n🎉 所有测试通过！")
```

运行测试：

```bash
python test_code_quality_hook.py
```

---

## 调试技巧

### 1. 启用详细日志

在Hook文件开头添加调试日志：

```python
import sys
import os

# 创建日志目录
log_dir = os.path.join(os.getcwd(), '.claude', '.hook-logs')
os.makedirs(log_dir, exist_ok=True)

# 启用调试日志
DEBUG = True

def debug_log(message):
    """写入调试日志"""
    if DEBUG:
        log_file = os.path.join(log_dir, 'unified-pretooluse-enforcer.log')
        with open(log_file, 'a', encoding='utf-8') as f:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {message}\n")

# 在关键位置添加日志
def main():
    debug_log("=== PreToolUse Hook触发 ===")

    event_data = json.loads(sys.stdin.read())
    tool_name = event_data.get("toolName", "")

    debug_log(f"工具名称: {tool_name}")
    debug_log(f"工具输入: {event_data.get('toolInput', {})}")

    # ... 验证逻辑 ...

    debug_log(f"验证结果: {validation_result}")
```

查看日志：

```bash
cat .claude/.hook-logs/unified-pretooluse-enforcer.log
```

### 2. 使用stderr输出

```python
import sys

# stderr输出不会影响Hook的JSON输出
sys.stderr.write("[DEBUG] 当前步骤: step3_execute\n")
sys.stderr.write(f"[DEBUG] 工具: {tool_name}\n")
sys.stderr.write(f"[DEBUG] 验证结果: {result}\n")
```

### 3. 交互式调试

创建独立测试脚本，不依赖Claude Code环境：

```python
# debug_validator.py
import sys
sys.path.insert(0, '.claude/hooks')

from core.stage_validator import StageValidator

# 设置断点
import pdb

validator = StageValidator(cwd=".")

# 在这里设置断点
pdb.set_trace()

result = validator.validate(
    current_step="step1_understand",
    tool_name="Write",
    tool_input={"file_path": "test.py"},
    workflow_state={"current_step": "step1_understand", "steps": {}}
)

print(result)
```

运行调试：

```bash
python debug_validator.py
```

### 4. 单元测试驱动开发

创建完整的测试套件：

```python
# test_suite.py
import unittest
import sys
sys.path.insert(0, '.claude/hooks')

from core.stage_validator import StageValidator

class TestLayer1Validation(unittest.TestCase):
    """测试第一层验证"""

    def setUp(self):
        self.validator = StageValidator()

    def test_step1_deny_write(self):
        """Step1应该禁止Write工具"""
        result = self.validator.validate(
            current_step="step1_understand",
            tool_name="Write",
            tool_input={"file_path": "test.py"},
            workflow_state={
                "current_step": "step1_understand",
                "steps": {"step0_context": {"status": "completed"}}
            }
        )
        self.assertFalse(result["allowed"])

    def test_step3_allow_write(self):
        """Step3应该允许Write工具"""
        result = self.validator.validate(
            current_step="step3_execute",
            tool_name="Write",
            tool_input={"file_path": "behavior_packs/test.py"},
            workflow_state={
                "current_step": "step3_execute",
                "steps": {
                    "step1_understand": {"status": "completed"},
                    "step2_research": {"status": "completed"}
                }
            }
        )
        self.assertTrue(result["allowed"])

class TestLayer2Validation(unittest.TestCase):
    """测试第二层验证"""

    def setUp(self):
        self.validator = StageValidator()

    def test_step3_require_step1_completed(self):
        """Step3需要Step1完成"""
        result = self.validator.validate(
            current_step="step3_execute",
            tool_name="Edit",
            tool_input={"file_path": "test.py"},
            workflow_state={
                "current_step": "step3_execute",
                "steps": {}  # Step1未完成
            }
        )
        self.assertFalse(result["allowed"])
        self.assertIn("Step1", result["reason"])

if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)
```

运行测试套件：

```bash
python test_suite.py -v
```

---

## 测试方法

### 自动化测试脚本

创建完整的测试脚本验证所有验证层：

```python
# comprehensive_test.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hook系统综合测试
覆盖四层验证、五阶段工作流、专家触发
"""

import sys
import os
sys.path.insert(0, '.claude/hooks')

from core.stage_validator import StageValidator
from core.expert_trigger import ExpertTrigger
from core import tool_matrix

# 测试结果统计
test_results = {
    "passed": 0,
    "failed": 0,
    "errors": []
}

def test_case(name, condition, error_msg=""):
    """测试用例辅助函数"""
    global test_results
    if condition:
        print(f"✅ {name}")
        test_results["passed"] += 1
    else:
        print(f"❌ {name}")
        test_results["failed"] += 1
        if error_msg:
            test_results["errors"].append(f"{name}: {error_msg}")

def test_layer1_tool_type():
    """测试Layer 1: 工具类型验证"""
    print("\n" + "="*60)
    print("Layer 1: 工具类型验证")
    print("="*60)

    validator = StageValidator()

    # 测试1: Step1禁止Write
    result = validator.validate(
        "step1_understand", "Write", {"file_path": "test.py"},
        {"current_step": "step1_understand", "steps": {"step0_context": {"status": "completed"}}}
    )
    test_case("Step1禁止Write工具", not result["allowed"])

    # 测试2: Step1允许Read
    result = validator.validate(
        "step1_understand", "Read", {"file_path": "docs/test.md"},
        {"current_step": "step1_understand", "steps": {"step0_context": {"status": "completed"}}}
    )
    test_case("Step1允许Read工具", result["allowed"])

    # 测试3: Step3允许Write
    result = validator.validate(
        "step3_execute", "Write", {"file_path": "behavior_packs/test.py"},
        {"current_step": "step3_execute", "steps": {
            "step1_understand": {"status": "completed"},
            "step2_research": {"status": "completed"}
        }}
    )
    test_case("Step3允许Write工具", result["allowed"])

def test_layer2_preconditions():
    """测试Layer 2: 前置条件检查"""
    print("\n" + "="*60)
    print("Layer 2: 前置条件检查")
    print("="*60)

    validator = StageValidator()

    # 测试1: Step3需要Step1完成
    result = validator.validate(
        "step3_execute", "Edit", {"file_path": "test.py"},
        {"current_step": "step3_execute", "steps": {}}
    )
    test_case("Step3需要Step1完成", not result["allowed"])

    # 测试2: Step3需要Step2完成
    result = validator.validate(
        "step3_execute", "Edit", {"file_path": "test.py"},
        {"current_step": "step3_execute", "steps": {
            "step1_understand": {"status": "completed"}
        }}
    )
    test_case("Step3需要Step2完成", not result["allowed"])

    # 测试3: Step4需要用户确认
    result = validator.validate(
        "step4_cleanup", "Task", {"subagent_type": "general-purpose"},
        {"current_step": "step4_cleanup", "steps": {
            "step3_execute": {"user_confirmed": False}
        }}
    )
    test_case("Step4需要用户确认", not result["allowed"])

def test_layer3_path_validation():
    """测试Layer 3: 文件路径验证"""
    print("\n" + "="*60)
    print("Layer 3: 文件路径验证")
    print("="*60)

    validator = StageValidator()

    # 测试1: Step1禁止Read代码文件
    result = validator.validate(
        "step1_understand", "Read", {"file_path": "behavior_packs/main.py"},
        {"current_step": "step1_understand", "steps": {"step0_context": {"status": "completed"}}}
    )
    test_case("Step1禁止Read代码文件", not result["allowed"])

    # 测试2: Step1允许Read文档
    result = validator.validate(
        "step1_understand", "Read", {"file_path": "markdown/系统设计.md"},
        {"current_step": "step1_understand", "steps": {"step0_context": {"status": "completed"}}}
    )
    test_case("Step1允许Read文档", result["allowed"])

    # 测试3: Step3禁止修改元数据
    result = validator.validate(
        "step3_execute", "Write", {"file_path": ".task-meta.json"},
        {"current_step": "step3_execute", "steps": {
            "step1_understand": {"status": "completed"},
            "step2_research": {"status": "completed"}
        }}
    )
    test_case("Step3禁止修改元数据", not result["allowed"])

def test_expert_trigger():
    """测试专家触发系统"""
    print("\n" + "="*60)
    print("专家触发系统")
    print("="*60)

    expert = ExpertTrigger()

    # 测试1: 未达到阈值，不触发
    workflow_state = {
        "current_step": "step3_execute",
        "task_type": "bug_fix",
        "expert_triggered": False,
        "bug_fix_tracking": {
            "enabled": True,
            "iterations": [{"iteration_id": 1}],
            "loop_indicators": {
                "negative_feedback_count": 1,
                "same_file_edit_count": 1
            }
        }
    }
    result = expert.should_trigger(workflow_state)
    test_case("未达到阈值不触发专家", not result)

    # 测试2: 达到阈值，触发专家
    workflow_state["bug_fix_tracking"]["iterations"].append({"iteration_id": 2})
    workflow_state["bug_fix_tracking"]["loop_indicators"]["negative_feedback_count"] = 2
    workflow_state["bug_fix_tracking"]["loop_indicators"]["same_file_edit_count"] = 2
    result = expert.should_trigger(workflow_state)
    test_case("达到阈值触发专家", result)

    # 测试3: 已触发过，不重复触发
    workflow_state["expert_triggered"] = True
    result = expert.should_trigger(workflow_state)
    test_case("不重复触发专家", not result)

def test_step_order():
    """测试阶段顺序"""
    print("\n" + "="*60)
    print("阶段顺序")
    print("="*60)

    step_order = tool_matrix.STEP_ORDER
    test_case("阶段顺序正确", step_order == [
        "step0_context",
        "step1_understand",
        "step2_research",
        "step3_execute",
        "step4_cleanup"
    ])

    # 测试get_next_step
    test_case("Step0 → Step1", tool_matrix.get_next_step("step0_context") == "step1_understand")
    test_case("Step1 → Step2", tool_matrix.get_next_step("step1_understand") == "step2_research")
    test_case("Step2 → Step3", tool_matrix.get_next_step("step2_research") == "step3_execute")
    test_case("Step3 → Step4", tool_matrix.get_next_step("step3_execute") == "step4_cleanup")
    test_case("Step4无下一步", tool_matrix.get_next_step("step4_cleanup") is None)

def print_summary():
    """打印测试总结"""
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)

    total = test_results["passed"] + test_results["failed"]
    print(f"\n总测试数: {total}")
    print(f"✅ 通过: {test_results['passed']}")
    print(f"❌ 失败: {test_results['failed']}")
    print(f"成功率: {test_results['passed'] / total * 100:.1f}%")

    if test_results["failed"] > 0:
        print("\n失败的测试:")
        for error in test_results["errors"]:
            print(f"  - {error}")
        print("\n❌ 测试失败！")
        sys.exit(1)
    else:
        print("\n🎉 所有测试通过！")
        sys.exit(0)

if __name__ == "__main__":
    print("🧪 Hook系统综合测试")
    print("="*60)

    test_layer1_tool_type()
    test_layer2_preconditions()
    test_layer3_path_validation()
    test_expert_trigger()
    test_step_order()

    print_summary()
```

运行综合测试：

```bash
python comprehensive_test.py
```

---

## 常见问题

### Q1: Hook修改后如何生效？

**A**: Hook文件修改后需要重新部署：

```bash
# 方法1: 重新全局部署
cd D:\EcWork\基于Claude的MODSDK开发工作流
npm link

# 方法2: 直接复制Hook文件到目标项目
cp templates/.claude/hooks/core/tool_matrix.py D:\EcWork\NetEaseMapECBedWars\.claude\hooks\core\
```

### Q2: 如何调试Hook验证失败的原因？

**A**: 启用详细日志：

```python
# 在unified-pretooluse-enforcer.py中
import sys

# 在验证前输出
sys.stderr.write(f"[DEBUG] 验证: step={current_step}, tool={tool_name}\n")

# 在每层验证后输出
sys.stderr.write(f"[DEBUG] Layer 1 result: {layer1_result}\n")
```

### Q3: 如何临时禁用某个验证层？

**A**: 修改`stage_validator.py`，注释掉对应层的验证：

```python
def validate(self, current_step, tool_name, tool_input, workflow_state):
    # Layer 1: 工具类型验证
    layer1_result = self._validate_layer1_tool_type(...)
    if not layer1_result["allowed"]:
        return layer1_result

    # Layer 2: 前置条件检查（临时禁用）
    # layer2_result = self._validate_layer2_preconditions(...)
    # if not layer2_result["allowed"]:
    #     return layer2_result

    # ...其他层...

    return {"allowed": True, "reason": "验证通过"}
```

**注意**: 仅用于调试，不要在生产环境禁用验证。

### Q4: 如何重置工作流状态？

**A**: 删除状态文件：

```bash
# 删除运行时状态
rm .claude/workflow-state.json
rm .claude/.task-active.json

# 删除任务元数据（慎重！会丢失历史数据）
rm tasks/任务-XXX/.task-meta.json
```

### Q5: 专家系统不触发怎么办？

**A**: 检查触发条件：

```python
# 打印当前状态
import sys
sys.path.insert(0, '.claude/hooks')

from core.expert_trigger import ExpertTrigger
from core.state_manager import StateManager

state_mgr = StateManager(cwd=".")
current_step, workflow_state = state_mgr.load_current_state()

expert = ExpertTrigger()
print(f"当前步骤: {current_step}")
print(f"任务类型: {workflow_state.get('task_type')}")
print(f"迭代次数: {len(workflow_state.get('bug_fix_tracking', {}).get('iterations', []))}")
print(f"负面反馈: {workflow_state.get('bug_fix_tracking', {}).get('loop_indicators', {}).get('negative_feedback_count')}")
print(f"同文件编辑: {workflow_state.get('bug_fix_tracking', {}).get('loop_indicators', {}).get('same_file_edit_count')}")
print(f"应该触发: {expert.should_trigger(workflow_state)}")
```

---

## 最佳实践

### 1. 渐进式验证规则

**不推荐**: 一次性添加大量严格规则

```python
# ❌ 过于严格，可能阻碍正常开发
"step3_execute": {
    "path_rules": {
        "Write": {
            "whitelist": ["behavior_packs/player.py"],  # 只允许修改一个文件
            # ...
        }
    }
}
```

**推荐**: 先宽松，逐步收紧

```python
# ✅ 先允许修改整个目录，观察实际使用情况
"step3_execute": {
    "path_rules": {
        "Write": {
            "whitelist_patterns": ["behavior_packs/**/*.py"],
            # ...
        }
    }
}

# 后续根据实际问题收紧规则
```

### 2. 清晰的错误消息

**不推荐**: 简单的错误消息

```python
# ❌ 用户不知道该怎么做
return {"allowed": False, "reason": "不允许"}
```

**推荐**: 详细的错误消息 + 建议

```python
# ✅ 清楚说明原因和正确做法
return {
    "allowed": False,
    "reason": "Step1阶段禁止修改代码文件",
    "suggestion": """
请先完成以下步骤:
1. 阅读至少1个相关文档了解任务需求
2. 等待系统自动推进到Step3执行阶段
3. 在Step3阶段可以修改代码文件
"""
}
```

### 3. 幂等性设计

**原则**: Hook应该是幂等的，多次执行产生相同结果。

```python
# ✅ 幂等设计
def update_code_changes(file_path, workflow_state):
    """更新代码修改记录（幂等）"""
    metrics = workflow_state.setdefault('metrics', {})
    code_changes = metrics.setdefault('code_changes', [])

    # 检查是否已记录（避免重复）
    existing = [c for c in code_changes if c['file'] == file_path and c['timestamp'] == timestamp]
    if existing:
        return  # 已记录，跳过

    code_changes.append({...})
```

### 4. 文档同步

**原则**: 代码修改后立即更新文档。

```bash
# 修改core/tool_matrix.py后
# 1. 更新Hook状态机机制.md
# 2. 更新Hook开发者指南.md
# 3. 更新CHANGELOG.md
```

### 5. 版本控制

**原则**: 重大修改前先备份。

```bash
# 备份旧版本
cp core/tool_matrix.py core/tool_matrix.py.backup_v22.0.0

# 修改配置
vim core/tool_matrix.py

# 测试
python comprehensive_test.py

# 提交
git add core/tool_matrix.py
git commit -m "feat(hooks): 添加Step2.5设计方案阶段"
```

---

## 附录：快速参考

### Hook文件清单

| 文件 | 职责 | 触发时机 |
|------|------|---------|
| `unified-pretooluse-enforcer.py` | 四层验证强制拦截 | PreToolUse (所有工具) |
| `unified-posttooluse-updater.py` | 状态更新、专家触发、步骤推进 | PostToolUse (所有工具) |
| `session-start-hook.py` | 恢复任务状态 | SessionStart |
| `user-prompt-submit-hook.py` | 任务初始化/恢复 | UserPromptSubmit |
| `stop-hook.py` | 会话结束检查 | Stop |

### 核心模块清单

| 模块 | 职责 |
|------|------|
| `core/tool_matrix.py` | 工具矩阵配置 |
| `core/stage_validator.py` | 四层验证引擎 |
| `core/path_validator.py` | 文件路径验证 |
| `core/semantic_analyzer.py` | 操作语义分析 |
| `core/expert_trigger.py` | 专家触发器 |
| `core/state_manager.py` | 状态管理器 |

### 常用命令

```bash
# 全局部署
npm link

# 在项目中初始化
initmc

# 运行测试
python comprehensive_test.py

# 查看Hook日志
cat .claude/.hook-logs/unified-pretooluse-enforcer.log

# 重置工作流
rm .claude/workflow-state.json .claude/.task-active.json
```

---

**版本**: v22.0.0
**最后更新**: 2025-11-15
**维护者**: NeteaseMod-Claude 工作流团队
