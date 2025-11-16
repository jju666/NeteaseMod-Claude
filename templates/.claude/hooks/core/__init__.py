"""
Core module for Hook State Machine (v2.0)

核心变更(v2.0):
- 移除 StateManager，使用 TaskMetaManager 替代
- task-meta.json 为唯一数据源
- 删除 workflow-state.json 相关逻辑

This module provides the core validation and state management
infrastructure for the unified hook architecture.
"""

__version__ = "21.0.0"
__author__ = "NeteaseMod-Claude Team"

# 导出核心类
from .stage_validator import StageValidator
from .task_meta_manager import TaskMetaManager
from .expert_trigger import ExpertTrigger

__all__ = [
    "StageValidator",
    "TaskMetaManager",
    "ExpertTrigger"
]
