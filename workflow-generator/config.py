# -*- coding: utf-8 -*-
"""
配置和常量
"""

from __future__ import print_function
import os

# 项目路径（动态获取，支持任意位置clone）
WORKFLOW_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(WORKFLOW_ROOT, "templates")
RULES_LIBRARY_DIR = os.path.join(WORKFLOW_ROOT, "rules-library")
DOC_TEMPLATES_DIR = os.path.join(WORKFLOW_ROOT, "doc-templates")

# 官方文档资源（在线）
MODSDK_WIKI_URL = "https://github.com/EaseCation/netease-modsdk-wiki"
BEDROCK_WIKI_URL = "https://github.com/Bedrock-OSS/bedrock-wiki"

# 参考项目路径（可选，仅用于本地测试和下载示例）
BEDWARS_PROJECT = r"D:\EcWork\NetEaseMapECBedWars"
RPG_PROJECT = r"D:\new-mg"

# 辅助函数
import os

def get_template_path(template_name, project_type="General"):
    """
    获取模板路径（使用内置模板）

    Args:
        template_name: 模板名称（如 "CLAUDE.md", "开发规范.md"）
        project_type: 项目类型（"RPG", "BedWars", "General"）

    Returns:
        str: 模板文件的绝对路径
    """
    if template_name == "CLAUDE.md":
        # CLAUDE.md：使用通用模板
        return os.path.join(TEMPLATES_DIR, "CLAUDE.md.template")
    elif template_name == "cc.md":
        # /cc命令模板
        return os.path.join(TEMPLATES_DIR, ".claude", "commands", "cc.md.template")
    elif template_name in ["开发规范.md", "问题排查.md", "快速开始.md"]:
        # 通用markdown模板
        return os.path.join(TEMPLATES_DIR, "markdown", template_name + ".template")
    elif template_name == "README.md":
        return os.path.join(TEMPLATES_DIR, "README.md.template")
    else:
        # 其他模板
        return os.path.join(TEMPLATES_DIR, template_name)

def has_reference_projects():
    """检测是否存在参考项目（用于可选的示例下载）"""
    return os.path.exists(BEDWARS_PROJECT) or os.path.exists(RPG_PROJECT)

# 文档详细度配置
DETAIL_LEVELS = {
    "simple": {
        "word_count": 500,
        "description": "简单文档（类结构、方法列表）"
    },
    "medium": {
        "word_count": 1500,
        "description": "中等详细度（架构、数据流、API）"
    },
    "detailed": {
        "word_count": 3000,
        "description": "详细文档（完整业务逻辑、示例）"
    }
}

# 复杂度评分阈值
COMPLEXITY_THRESHOLDS = {
    "detailed": 8,   # score >= 8 → detailed
    "medium": 5,     # score >= 5 → medium
    # score < 5 → simple
}

# 项目规模阈值
SCALE_THRESHOLDS = {
    "small": 10,     # ≤10 Systems
    "medium": 30,    # 11-30 Systems
    # >30 Systems → large
}

# 文档质量评估阈值
QUALITY_THRESHOLDS = {
    "high": 80,      # ≥80分 → 保留
    "medium": 50,    # 50-79分 → 重写
    # <50分 → 重新生成
}

# 占位符定义
PLACEHOLDERS = {
    "PROJECT_PATH": "{{PROJECT_PATH}}",
    "PROJECT_NAME": "{{PROJECT_NAME}}",
    "EXAMPLE_TASKS": "{{EXAMPLE_TASKS}}",
    "SDK_DOC_PATH": "{{SDK_DOC_PATH}}",
    "CRITICAL_RULES": "{{CRITICAL_RULES}}",
    "CORE_PATHS": "{{CORE_PATHS}}",
    "ARCHITECTURE_DOCS": "{{ARCHITECTURE_DOCS_SECTION}}",
    "BUSINESS_DOCS": "{{BUSINESS_DOCS_SECTION}}",
    "NBT_CHECK_SECTION": "{{NBT_CHECK_SECTION}}",
    "LOG_FILES": "{{LOG_FILES}}",
}

# CRITICAL规范映射（根据项目类型选择）
CRITICAL_RULES_MAP = {
    "general": [
        "System生命周期",
        "模块导入规范",
        "双端隔离",
        "Python2.7兼容性"
    ],
    "apollo": ["Apollo1.0架构"],
    "ecpreset": ["ECPreset数据存储"],
    "rpg": ["RPG-NBT兼容性"]
}

# 项目类型识别关键词
PROJECT_TYPE_KEYWORDS = {
    "RPG": ["rpg", "combat", "weapon", "armor", "skill"],
    "BedWars": ["bedwars", "bed", "generator", "team"],
    "PVP": ["pvp", "arena", "duel"],
    "Survival": ["survival", "hunger", "thirst"],
}
