"""
Tool Matrix - 工具矩阵配置
定义：阶段-工具-路径-语义 四维验证规则

Version: v3.0 Final - 完整4步语义化状态机
"""

# ============== 核心矩阵配置 ==============

STAGE_TOOL_MATRIX = {
    # ========== Activation: 任务激活与类型识别 (v3.0新增) ==========
    "activation": {
        "display_name": "任务激活",
        "description": "任务初始化与类型识别（自动执行，AI无需关注）",

        "allowed_tools": [],  # 此阶段由UserPromptSubmit Hook自动完成，AI不介入

        "preconditions": [],  # 起始阶段，无前置条件

        "path_rules": {},

        "semantic_rules": {},

        "completion_condition": {
            "type": "automatic",
            "auto_advance": True,  # 自动推进到planning
            "next_step": "planning",
            "description": "UserPromptSubmit Hook识别任务类型后自动推进到planning"
        },

        "ai_guidance": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 任务激活阶段
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

此阶段由系统自动完成任务类型识别：
- BUG修复任务
- 功能设计任务

你无需执行任何操作，系统将自动推进到Planning阶段。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    },

    # ========== Planning: 方案制定阶段 (v3.0差异化流程) ==========
    "planning": {
        "display_name": "方案制定",
        "description": "深度研究问题根因和技术约束,制定解决方案,禁止修改任何文件",

        # ✅ Phase 5: 完整的白名单定义（默认拒绝原则）
        # 注意: Update/Patch等工具别名会被StageValidator归一化为Edit，因此无需在此列出
        "allowed_tools": [
            "Read",        # 阅读文件（代码/文档）
            "Grep",        # 搜索代码关键词
            "Glob",        # 查找文件模式匹配
            "Task",        # 启动子代理（专家审查/文档查询）
            "WebFetch",    # 获取在线文档（如官方Wiki）
            "WebSearch"    # 搜索技术资料
        ],

        "preconditions": ["activation_completed"],  # v3.0: 需要activation完成

        "path_rules": {
            "Read": {
                "whitelist_patterns": [
                    "**/*.md",
                    "**/*.py",
                    "**/*.js",
                    "**/*.json"
                ],
                "blacklist": [
                    ".task-meta.json",
                    "workflow-state.json"
                ],
                "description": "可以阅读文档和代码,但禁止修改"
            },
            "Grep": {
                "allowed": True,
                "description": "允许搜索代码,了解现有实现"
            },
            "Glob": {
                "allowed": True,
                "description": "允许查找文件"
            }
        },

        "semantic_rules": {
            "Read": {
                "purpose": "deep_research",
                "min_reads": 3,  # v3.0: 功能设计强制3个，BUG修复可选（动态判断）
                "min_reads_bug_fix": 0,  # v3.0新增: BUG修复无强制文档要求
                "description": "功能设计必须查阅至少3个文档，BUG修复可选"
            },
            "Write": {
                "forbidden": True,
                "reason": "方案制定阶段严禁修改任何文件"
            },
            "Edit": {
                "forbidden": True,
                "reason": "方案制定阶段严禁修改任何文件"
            },
            # ✅ Phase 4 Bug Fix: 添加Update和NotebookEdit禁止规则（Claude Code v2.0）
            "Update": {
                "forbidden": True,
                "reason": "方案制定阶段严禁修改任何文件"
            },
            "NotebookEdit": {
                "forbidden": True,
                "reason": "方案制定阶段严禁修改任何文件"
            },
            "Bash": {
                "forbidden": True,
                "reason": "方案制定阶段禁止执行命令"
            },
            "Task": {
                "purpose": "launch_subagent",
                "allowed_subagent_types": ["expert_review", "doc_research"],
                "description": "启动专家审查或文档查询子代理"
            }
        },

        "completion_condition": {
            "type": "ai_explicit_confirm",  # ⭐ v3.0 Final: AI必须明确确认
            "confirmation_keywords": [
                "研究完成",
                "已理解问题根因",
                "开始实施",
                "准备修改",
                "可以开始编码"
            ],
            "min_doc_count": 3,  # 最少文档数（由task-meta.json的required_doc_count动态覆盖）
            "auto_advance": False,  # ⭐ v3.0 Final: 不自动推进,需AI明确确认
            "next_step": "implementation",
            "description": "查阅至少3个文档并明确说明研究结论后,Hook检测关键词并推进到implementation"
        },

        "ai_guidance": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 当前阶段: 方案制定（Planning - 强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你现在处于强制方案制定阶段,需要完成：

1. **查阅文档**（至少3个）：
   - 理解问题根因和技术约束
   - 查阅CRITICAL规范相关文档
   - 研究相关系统实现

2. **明确说明研究结论**：
   - 包含关键词："研究完成"或"已理解问题根因"
   - 说明你对问题的理解和解决思路

**禁止操作**：
- ❌ Write/Edit任何文件（PreToolUse会拦截）
- ❌ Bash执行命令
- ❌ 尝试跳过研究直接修改

**允许操作**：
- ✅ Read阅读文档和代码
- ✅ Grep搜索相关实现
- ✅ Glob查找文件

**完成研究后**：
Hook会检测你的确认关键词,自动推进到implementation执行阶段。
"""
    },

    # ========== Implementation: 代码实施 ==========
    "implementation": {
        "display_name": "代码实施",
        "description": "代码修改、测试、迭代,直到用户确认完成",

        # ✅ Phase 5: 完整的白名单定义（默认拒绝原则）
        # 注意: Update/Patch/NotebookEdit等别名会被StageValidator归一化，无需在此列出
        "allowed_tools": [
            "Read",         # 阅读文件
            "Write",        # 写入新文件
            "Edit",         # 修改现有文件（包括Update/Patch别名）
            "NotebookEdit", # 修改Jupyter Notebook
            "Bash",         # 执行测试命令
            "Grep",         # 搜索代码
            "Glob",         # 查找文件
            "WebFetch",     # 获取在线文档
            "WebSearch",    # 搜索技术资料
            "Task"          # 启动子代理（如需专家审查）
        ],

        "preconditions": ["planning_completed"],

        "path_rules": {
            "Write": {
                "whitelist_patterns": [
                    "behavior_packs/**/*.py",
                    "resource_packs/**/*.json",
                    "scripts/**/*.js",
                    "scripts/**/*.py"
                ],
                "blacklist": [
                    ".task-meta.json",
                    "workflow-state.json",
                    ".task-active.json",
                    ".cleanup-subagent.lock"
                ],
                "description": "可以写入代码文件,但禁止直接修改元数据"
            },
            "Edit": {
                "whitelist_patterns": [
                    "behavior_packs/**/*.py",
                    "resource_packs/**/*.json",
                    "scripts/**/*.js",
                    "scripts/**/*.py"
                ],
                "blacklist": [
                    ".task-meta.json",
                    "workflow-state.json",
                    ".task-active.json"
                ],
                "description": "可以修改代码文件,但禁止直接修改元数据"
            },
            "Bash": {
                "allowed_commands_patterns": [
                    r"^pytest\b",
                    r"^python\b",
                    r"^node\b",
                    r"^npm\s+(test|run)\b",
                    r"^git\s+(status|diff|log)\b"
                ],
                "forbidden_commands_patterns": [
                    r"rm\s+-rf\s+/",
                    r"git\s+push\s+--force",
                    r"sudo\b",
                    r"mkfs\b",
                    r"dd\s+if="
                ],
                "description": "允许测试命令和安全的git命令,禁止危险操作"
            }
        },

        "semantic_rules": {
            "Write": {
                "purpose": "implement_solution",
                "requires_read_first": True,
                "description": "实现解决方案,写入新代码前必须先Read目标文件"
            },
            "Edit": {
                "purpose": "modify_code",
                "max_same_file_edits": 5,
                "description": "修改代码,同一文件修改超过5次将触发专家审查"
            },
            "Bash": {
                "purpose": "test_execution",
                "description": "执行测试命令验证修改"
            }
        },

        "completion_condition": {
            "trigger_expr": "workflow_state.get('steps', {}).get('implementation', {}).get('user_confirmed', False)",
            "auto_advance": False,  # 需要用户明确确认
            "next_step": "finalization",
            "description": "用户明确确认修复完成（输入'/mc-confirm'或'已修复'）后推进到finalization",
            "confirmation_keywords": [
                "/mc-confirm",
                "已修复",
                "修复完成",
                "已解决",
                "解决了",
                "好了",
                "可以了",
                "没问题了",
                "work了"
            ]
        }
    },

    # ========== Finalization: 收尾归档 ==========
    "finalization": {
        "display_name": "收尾归档",
        "description": "文档更新、DEBUG清理、任务归档（强制子代理执行）",

        # 父代理只能Task,子代理可以全部工具
        "allowed_tools": ["Task", "Read"],

        "preconditions": ["planning_completed", "user_confirmed"],

        "path_rules": {
            "Task": {
                "required_params": {
                    "subagent_type": "general-purpose",
                    "description_pattern": r".*文档更新.*收尾.*"
                },
                "description": "父代理只能通过Task工具启动收尾子代理"
            },
            "Read": {
                "whitelist": [
                    ".claude/.agent-doc-update.txt",
                    ".task-meta.json"
                ],
                "description": "父代理可以读取子代理任务描述和元数据"
            }
        },

        "semantic_rules": {
            "Task": {
                "purpose": "launch_cleanup_subagent",
                "max_launches": 1,
                "creates_lock": True,
                "description": "启动收尾子代理,创建锁文件"
            },
            "Write": {
                "forbidden_in_parent": True,
                "reason": "父代理禁止直接Write,必须通过子代理"
            },
            "Edit": {
                "forbidden_in_parent": True,
                "reason": "父代理禁止直接Edit,必须通过子代理"
            },
            "Bash": {
                "forbidden_in_parent": True,
                "reason": "父代理禁止执行Bash命令"
            }
        },

        # 子代理规则（检测到锁文件后生效）
        "subagent_rules": {
            "allowed_tools": ["Read", "Write", "Edit", "Grep", "Glob"],
            "path_rules": {
                "Write": {
                    "whitelist": [
                        ".task-meta.json",
                        "markdown/**/*.md",
                        "docs/**/*.md"
                    ],
                    "description": "子代理可以更新元数据和文档"
                },
                "Edit": {
                    "whitelist_patterns": [
                        "markdown/**/*.md",
                        "docs/**/*.md",
                        "behavior_packs/**/*.py",
                        "resource_packs/**/*.json"
                    ],
                    "description": "子代理可以编辑文档和清理DEBUG代码"
                }
            },
            "semantic_rules": {
                "Write": {
                    "purpose": "update_metadata_and_docs",
                    "required_updates": {
                        ".task-meta.json": {
                            "field": "workflow_state.steps.finalization.status",
                            "value": "completed",
                            "description": "子代理必须标记finalization为completed"
                        }
                    }
                }
            }
        },

        "completion_condition": {
            "trigger_expr": "workflow_state.get('steps', {}).get('finalization', {}).get('status') == 'completed'",
            "auto_advance": False,  # 完成后自动归档
            "next_step": None,
            "description": "子代理标记finalization.status=completed后,post-archive-hook自动归档任务"
        }
    }
}


# ============== 辅助函数 ==============

def get_stage_config(stage_name: str) -> dict:
    """
    获取阶段配置 (v3.0 Final: 语义化命名)

    Args:
        stage_name: 阶段名称 (activation, planning, implementation, finalization)

    Returns:
        阶段配置字典
    """
    return STAGE_TOOL_MATRIX.get(stage_name, {})


def get_allowed_tools(stage_name: str) -> list:
    """获取阶段允许的工具列表"""
    config = get_stage_config(stage_name)
    return config.get('allowed_tools', [])


def get_preconditions(stage_name: str) -> list:
    """获取阶段前置条件"""
    config = get_stage_config(stage_name)
    return config.get('preconditions', [])


def get_path_rules(stage_name: str, tool_name: str) -> dict:
    """获取工具的路径规则"""
    config = get_stage_config(stage_name)
    path_rules = config.get('path_rules', {})
    return path_rules.get(tool_name, {})


def get_semantic_rules(stage_name: str, tool_name: str) -> dict:
    """获取工具的语义规则"""
    config = get_stage_config(stage_name)
    semantic_rules = config.get('semantic_rules', {})
    return semantic_rules.get(tool_name, {})


def get_next_step(current_step: str) -> str:
    """
    获取下一个步骤 (v3.0: 完整4步语义化)

    Args:
        current_step: 当前步骤(activation, planning, implementation, finalization)

    Returns:
        下一个步骤名称,如果已是最后一步则返回None
    """
    # v3.0: 完整4步顺序
    step_order = ["activation", "planning", "implementation", "finalization"]

    try:
        current_idx = step_order.index(current_step)
        if current_idx < len(step_order) - 1:
            return step_order[current_idx + 1]
    except ValueError:
        pass

    return None


def is_auto_advance(stage_name: str) -> bool:
    """检查阶段是否自动推进"""
    config = get_stage_config(stage_name)
    completion = config.get('completion_condition', {})
    return completion.get('auto_advance', False)


# ============== 步骤顺序配置 ==============

STEP_ORDER = [
    "activation",        # v3.0: 任务激活阶段（自动完成）
    "planning",          # v3.0: 方案制定阶段（差异化流程）
    "implementation",    # v3.0: 代码实施阶段（轮次循环）
    "finalization"       # v3.0: 收尾归档阶段（子代理执行）
]


# ============== 策略类型定义 ==============

STRATEGY_TYPES = {
    "bug_fix": {
        "display_name": "BUG修复",
        "description": "修复系统功能异常、错误或不符合预期的行为",
        "loop_detection_enabled": True,
        "expert_trigger_threshold": {
            "iterations": 2,
            "negative_feedback": 2,
            "same_file_edits": 2
        }
    },
    "feature_development": {
        "display_name": "功能开发",
        "description": "新增功能、添加新特性",
        "loop_detection_enabled": True,
        "expert_trigger_threshold": {
            "iterations": 3,
            "dissatisfied_count": 2
        }
    },
    "optimization": {
        "display_name": "优化改进",
        "description": "性能优化、代码优化、体验优化",
        "loop_detection_enabled": False
    },
    "refactoring": {
        "display_name": "重构",
        "description": "代码结构调整、架构优化",
        "loop_detection_enabled": False
    }
}


# ============== v3.0新增: 差异化流程配置 ==============

DIFFERENTIATED_WORKFLOWS = {
    "bug_fix": {
        "planning": {
            "min_doc_count": 0,  # BUG修复无需强制文档
            "expert_review_required": True,  # 必须触发专家审查
            "expert_review_auto_trigger": True,  # 方案制定完成后自动触发
            "doc_query_subagent": False,  # 不启动文档查询子代理
            "ai_guidance_template": "ai_guidance_bug_fix"  # 使用BUG修复专属引导
        },
        "implementation": {
            "test_after_each_round": True,  # 每轮建议测试
            "max_rounds_before_expert": 3  # 3轮未修复触发专家审查
        }
    },
    "feature_design": {
        "planning": {
            "min_doc_count": 3,  # 功能设计强制3个文档
            "expert_review_required": False,  # 不强制专家审查
            "gameplay_pack_matching": True,  # 启用玩法包匹配
            "doc_query_subagent": True,  # 可选启动文档查询子代理
            "ai_guidance_template": "ai_guidance_feature_design"  # 使用功能设计专属引导
        },
        "implementation": {
            "test_after_each_round": False,  # 不强制每轮测试
            "max_rounds_before_expert": 5  # 5轮触发专家审查
        }
    }
}


def get_workflow_config(task_type: str, stage: str) -> dict:
    """
    获取差异化流程配置 (v3.0新增)

    Args:
        task_type: 任务类型（bug_fix/feature_design）
        stage: 当前阶段（activation/planning/implementation/finalization）

    Returns:
        差异化配置字典
    """
    workflows = DIFFERENTIATED_WORKFLOWS.get(task_type, DIFFERENTIATED_WORKFLOWS["feature_design"])
    return workflows.get(stage, {})


def get_min_doc_count(task_type: str) -> int:
    """
    获取最少文档数要求 (v3.0差异化)

    Args:
        task_type: 任务类型（bug_fix/feature_design）

    Returns:
        最少文档数
    """
    config = get_workflow_config(task_type, "planning")
    return config.get("min_doc_count", 0)  # v3.0: 默认0（未知类型不强制文档）
