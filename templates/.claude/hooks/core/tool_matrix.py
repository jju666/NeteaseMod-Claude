"""
Tool Matrix - 工具矩阵配置
定义：阶段-工具-路径-语义 四维验证规则

Version: v20.3.0 - 重新引入Step2任务流路由阶段
"""

# ============== 核心矩阵配置 ==============

STAGE_TOOL_MATRIX = {
    # ========== Step0: 理解项目上下文 ==========
    "step0_context": {
        "display_name": "理解项目上下文",
        "description": "阅读CLAUDE.md了解项目结构和工作流规范",

        "allowed_tools": ["Read"],

        "preconditions": [],  # 无前置条件，初始阶段

        "path_rules": {
            "Read": {
                "whitelist": ["CLAUDE.md", "README.md"],
                "blacklist": [],
                "description": "只能阅读项目根目录的CLAUDE.md和README.md"
            }
        },

        "semantic_rules": {
            "Read": {
                "purpose": "understand_project",
                "max_reads": 2,
                "description": "理解项目上下文，最多读2个文件"
            }
        },

        "completion_condition": {
            "trigger_expr": "any('CLAUDE.md'.upper() in doc.upper() for doc in task_meta.get('metrics', {}).get('docs_read', []))",
            "auto_advance": True,
            "next_step": "step1_understand",
            "description": "检测到CLAUDE.md被读取后自动推进到step1"
        }
    },

    # ========== Step1: 理解任务需求 ==========
    "step1_understand": {
        "display_name": "理解任务需求",
        "description": "阅读用户提供的需求描述、相关文档或问题说明",

        "allowed_tools": ["Read"],

        "preconditions": ["step0_completed"],

        "path_rules": {
            "Read": {
                "whitelist_patterns": [
                    "docs/**/*.md",
                    "markdown/**/*.md",
                    "*.md",
                    "tasks/*/context.md",
                    "tasks/*/solution.md"
                ],
                "blacklist_patterns": [
                    "behavior_packs/**/*",
                    "resource_packs/**/*",
                    "scripts/**/*.py",
                    "scripts/**/*.js",
                    "*.py",
                    "*.js"
                ],
                "description": "只能阅读文档，禁止阅读代码文件"
            }
        },

        "semantic_rules": {
            "Read": {
                "purpose": "understand_requirements",
                "min_reads": 1,
                "forbidden_content_types": ["code"],
                "description": "理解需求文档，至少读1个文档"
            }
        },

        "completion_condition": {
            "trigger_expr": "task_meta.get('metrics', {}).get('docs_read_count', 0) >= 1",
            "auto_advance": True,
            "next_step": "step2_research",
            "description": "至少阅读1个文档后自动推进到step2_research"
        }
    },

    # ========== Step2: 任务研究阶段 (v22.0 PreToolUse强制驱动) ==========
    "step2_research": {
        "display_name": "任务研究阶段（强制）",
        "description": "深度研究问题根因和技术约束，禁止修改任何文件",

        "allowed_tools": ["Read", "Grep", "Glob"],

        "preconditions": ["step1_completed"],

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
                "description": "可以阅读文档和代码，但禁止修改"
            },
            "Grep": {
                "allowed": True,
                "description": "允许搜索代码，了解现有实现"
            },
            "Glob": {
                "allowed": True,
                "description": "允许查找文件"
            }
        },

        "semantic_rules": {
            "Read": {
                "purpose": "deep_research",
                "min_reads": 3,  # ⭐ v22.0: 强制最少文档数
                "description": "必须查阅至少3个相关文档（玩法包模式降为2个）"
            },
            "Write": {
                "forbidden": True,
                "reason": "研究阶段严禁修改任何文件"
            },
            "Edit": {
                "forbidden": True,
                "reason": "研究阶段严禁修改任何文件"
            },
            "Bash": {
                "forbidden": True,
                "reason": "研究阶段禁止执行命令"
            }
        },

        "completion_condition": {
            "type": "ai_explicit_confirm",  # ⭐ v22.0: AI必须明确确认
            "confirmation_keywords": [
                "研究完成",
                "已理解问题根因",
                "开始实施",
                "准备修改",
                "可以开始编码"
            ],
            "min_doc_count": 3,  # 最少文档数（由task-meta.json的required_doc_count动态覆盖）
            "auto_advance": False,  # ⭐ v22.0: 不自动推进，需AI明确确认
            "next_step": "step3_execute",
            "description": "查阅至少3个文档并明确说明研究结论后，Hook检测关键词并推进到step3"
        },

        "ai_guidance": """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ 当前阶段: 任务研究（Step2 - 强制）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

你现在处于强制研究阶段，需要完成：

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
Hook会检测你的确认关键词，自动推进到step3执行阶段。
"""
    },

    # ========== Step3: 执行实施 ==========
    "step3_execute": {
        "display_name": "执行实施",
        "description": "代码修改、测试、迭代，直到用户确认完成",

        "allowed_tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob", "WebFetch", "WebSearch"],

        "preconditions": ["step1_completed", "step2_completed"],

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
                "description": "可以写入代码文件，但禁止直接修改元数据"
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
                "description": "可以修改代码文件，但禁止直接修改元数据"
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
                "description": "允许测试命令和安全的git命令，禁止危险操作"
            }
        },

        "semantic_rules": {
            "Write": {
                "purpose": "implement_solution",
                "requires_read_first": True,
                "description": "实现解决方案，写入新代码前必须先Read目标文件"
            },
            "Edit": {
                "purpose": "modify_code",
                "max_same_file_edits": 5,
                "description": "修改代码，同一文件修改超过5次将触发专家审查"
            },
            "Bash": {
                "purpose": "test_execution",
                "description": "执行测试命令验证修改"
            }
        },

        "completion_condition": {
            "trigger_expr": "workflow_state.get('steps', {}).get('step3_execute', {}).get('user_confirmed', False)",
            "auto_advance": False,  # 需要用户明确确认
            "next_step": "step4_cleanup",
            "description": "用户明确确认修复完成（输入'/mc-confirm'或'已修复'）后推进到step4",
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

    # ========== Step4: 收尾归档 ==========
    "step4_cleanup": {
        "display_name": "收尾归档",
        "description": "文档更新、DEBUG清理、任务归档（强制子代理执行）",

        # 父代理只能Task，子代理可以全部工具
        "allowed_tools": ["Task", "Read"],

        "preconditions": ["user_confirmed"],

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
                "description": "启动收尾子代理，创建锁文件"
            },
            "Write": {
                "forbidden_in_parent": True,
                "reason": "父代理禁止直接Write，必须通过子代理"
            },
            "Edit": {
                "forbidden_in_parent": True,
                "reason": "父代理禁止直接Edit，必须通过子代理"
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
                            "field": "workflow_state.steps.step4_cleanup.status",
                            "value": "completed",
                            "description": "子代理必须标记step4_cleanup为completed"
                        }
                    }
                }
            }
        },

        "completion_condition": {
            "trigger_expr": "workflow_state.get('steps', {}).get('step4_cleanup', {}).get('status') == 'completed'",
            "auto_advance": False,  # 完成后自动归档
            "next_step": None,
            "description": "子代理标记step4_cleanup.status=completed后，post-archive-hook自动归档任务"
        }
    }
}


# ============== 辅助函数 ==============

def get_stage_config(stage_name: str) -> dict:
    """获取阶段配置"""
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
    """获取下一个步骤"""
    step_order = ["step0_context", "step1_understand", "step2_route", "step3_execute", "step4_cleanup"]

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
    "step0_context",
    "step1_understand",
    "step2_research",   # v22.0 PreToolUse强制驱动
    "step3_execute",
    "step4_cleanup"
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
