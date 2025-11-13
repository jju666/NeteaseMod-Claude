#!/usr/bin/env python
"""
v20.2 Intelligent BUG Diagnosis Helper Functions
"""

def analyze_bug_symptom(task_desc):
    """
    Analyze BUG symptom type (v20.2) - Bilingual support
    Returns: (symptom_type, symptom_description)
    """
    import re
    task_lower = task_desc.lower()

    # Detection features (English + Chinese)
    has_error_log = bool(re.search(r'(error|exception|traceback|stack|报错|错误|异常|崩溃)', task_lower))
    has_none_return = bool(re.search(r'(none|null|empty|返回none|返回空)', task_lower))
    has_api_mention = bool(re.search(r'(getsystem|getcomponent|listenforevent|createentity|getattr|setattr)', task_lower))
    has_init_mention = bool(re.search(r'(__init__|init|initialize|初始化)', task_lower))
    has_cross_end = bool(re.search(r'(server.*client|client.*server|cross|跨端|服务端.*客户端|客户端.*服务端)', task_lower))
    has_business_desc = bool(re.search(r'(not working|no effect|not trigger|logic.*error|function.*error|incorrect|abnormal|不生效|没有效果|没有触发|逻辑.*错误|功能.*错误|不正确|异常)', task_lower))
    has_performance = bool(re.search(r'(lag|delay|slow|tps|memory|leak|usage|卡顿|延迟|慢|内存|泄漏)', task_lower))

    # Classification by priority
    if has_none_return and has_init_mention and has_api_mention:
        return "lifecycle_error", "Lifecycle problem"
    elif has_cross_end or (has_error_log and 'getsystem' in task_lower):
        return "critical_violation", "CRITICAL rule violation"
    elif has_error_log and has_api_mention and not has_business_desc:
        return "api_error", "API/Event usage error"
    elif has_business_desc and not has_error_log:
        return "business_logic", "Business logic error"
    elif has_performance:
        return "performance", "Performance issue"
    else:
        return "unknown", "Need further analysis"

def extract_business_keywords(task_desc):
    """
    Extract business keywords for searching markdown docs (v20.2)
    Returns: list of matched keywords
    """
    business_terms = {
        'shop': ['shop', 'buy', 'sell', 'purchase'],
        'team': ['team', 'group', 'party'],
        'quest': ['quest', 'task', 'mission'],
        'skill': ['skill', 'ability', 'spell'],
        'inventory': ['inventory', 'bag', 'item'],
        'combat': ['combat', 'damage', 'attack', 'defense'],
        'economy': ['economy', 'coin', 'currency', 'money'],
        'permission': ['permission', 'admin', 'privilege'],
        'teleport': ['teleport', 'portal', 'warp'],
        'map': ['map', 'zone', 'region', 'area'],
        'social': ['friend', 'chat', 'party'],
        'achievement': ['achievement', 'title', 'reward'],
        'ui': ['ui', 'interface', 'button', 'menu']
    }

    task_lower = task_desc.lower()
    matched = []

    for domain, keywords in business_terms.items():
        for kw in keywords:
            if kw in task_lower:
                matched.append(domain)
                break

    return matched

def route_knowledge_sources(symptom_type, task_desc):
    """
    Route knowledge sources based on symptom type (v20.2)
    Returns: routing strategy dict
    """
    routes = {
        "api_error": {
            "strategy": "Fast match common errors",
            "primary_docs": [
                (".claude/core-docs/trouble-shooting.md", 1, 150, "11 common issues"),
            ],
            "skip_markdown": True,
            "extract_keywords": False,
            "markdown_priority": False
        },
        "lifecycle_error": {
            "strategy": "Verify CRITICAL rules",
            "primary_docs": [
                (".claude/core-docs/dev-guide.md", 20, 150, "CRITICAL rule 2"),
            ],
            "skip_markdown": True,
            "extract_keywords": False,
            "markdown_priority": False
        },
        "critical_violation": {
            "strategy": "Verify CRITICAL rules",
            "primary_docs": [
                (".claude/core-docs/dev-guide.md", 20, 150, "CRITICAL rule 1"),
            ],
            "skip_markdown": True,
            "extract_keywords": False,
            "markdown_priority": False
        },
        "business_logic": {
            "strategy": "Docs first + Code verification",
            "primary_docs": [],
            "skip_markdown": False,
            "extract_keywords": True,
            "markdown_priority": True
        },
        "performance": {
            "strategy": "Bottleneck identification",
            "primary_docs": [
                (".claude/core-docs/performance-guide.md", 1, 200, "Perf guide"),
            ],
            "skip_markdown": True,
            "extract_keywords": False,
            "markdown_priority": False
        },
        "unknown": {
            "strategy": "General exploration",
            "primary_docs": [
                (".claude/core-docs/trouble-shooting.md", 1, 150, "Try common errors"),
            ],
            "skip_markdown": False,
            "extract_keywords": True,
            "markdown_priority": False
        }
    }

    return routes.get(symptom_type, routes["unknown"])
