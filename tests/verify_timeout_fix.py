#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Hook timeout修复
"""
import json
import sys
import os

print("=" * 60)
print("验证Hook timeout配置")
print("=" * 60)

# 读取settings.json
settings_path = os.path.join(os.path.dirname(__file__), '.claude', 'settings.json')
with open(settings_path, 'r', encoding='utf-8') as f:
    settings = json.load(f)

# 读取claude_semantic_config.json
config_path = os.path.join(os.path.dirname(__file__), '.claude', 'hooks', 'config', 'claude_semantic_config.json')
with open(config_path, 'r', encoding='utf-8') as f:
    llm_config = json.load(f)

hook_timeout = settings['hooks']['UserPromptSubmit'][0]['hooks'][0]['timeout']
llm_timeout = llm_config['timeout_seconds']

print(f"\n配置检查:")
print(f"  Hook timeout: {hook_timeout}秒")
print(f"  LLM API timeout: {llm_timeout}秒")

if hook_timeout > llm_timeout:
    print(f"\n✅ 配置正确: Hook timeout ({hook_timeout}s) > LLM timeout ({llm_timeout}s)")
    print(f"   余量: {hook_timeout - llm_timeout}秒")
else:
    print(f"\n❌ 配置错误: Hook timeout ({hook_timeout}s) <= LLM timeout ({llm_timeout}s)")
    print(f"   LLM可能超时导致Hook被强制终止！")
    sys.exit(1)

# 推荐配置
recommended_hook_timeout = llm_timeout + 5
if hook_timeout < recommended_hook_timeout:
    print(f"\n⚠️  建议增加Hook timeout到{recommended_hook_timeout}秒（LLM超时+5秒余量）")
else:
    print(f"\n✅ Hook timeout配置充足")

print("\n" + "=" * 60)
print("验证完成")
print("=" * 60)
