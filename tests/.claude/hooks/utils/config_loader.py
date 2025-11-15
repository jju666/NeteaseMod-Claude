#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
工作流配置加载器
提供统一的配置读取接口，支持默认值降级
"""

import os
import json

DEFAULT_CONFIG = {
    "task_naming": {
        "max_description_length": 16  # v20.2.7: 从8提升到16字符
    },
    "workflow_steps": {
        "step2_min_docs": 3
    },
    "cleanup": {
        "max_auto_update_docs": 3
    },
    "archive": {
        "enabled": True,
        "auto_move_to_archived": True,
        "auto_sync_docs": True
    }
}

def load_config(project_path=None):
    """
    加载工作流配置

    Args:
        project_path: 项目根目录路径，默认为当前工作目录

    Returns:
        dict: 配置字典
    """
    if project_path is None:
        project_path = os.getcwd()

    config_file = os.path.join(project_path, '.claude', 'workflow-config.json')

    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # 合并默认配置（填充缺失的键）
                return merge_config(DEFAULT_CONFIG, config)
        else:
            return DEFAULT_CONFIG.copy()
    except:
        return DEFAULT_CONFIG.copy()

def merge_config(default, custom):
    """递归合并配置字典"""
    result = default.copy()
    for key, value in custom.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result

def get_max_task_desc_length(project_path=None):
    """快速获取任务描述最大长度"""
    config = load_config(project_path)
    return config['task_naming']['max_description_length']
