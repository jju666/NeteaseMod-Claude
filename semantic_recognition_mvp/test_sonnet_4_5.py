#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Claude Sonnet 4.5模型可用性
"""
import os
import sys

# Windows编码修复
if sys.platform == 'win32':
    import io
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        except (AttributeError, ValueError):
            pass

try:
    import anthropic
except ImportError:
    print("[FAIL] 缺少依赖: anthropic")
    print("请运行: pip install anthropic")
    sys.exit(1)

# 获取API密钥
API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
if not API_KEY:
    print("[FAIL] 未设置API密钥")
    print("请设置环境变量: ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN")
    sys.exit(1)

print("=" * 60)
print("测试Claude Sonnet 4.5模型可用性")
print("=" * 60)

# 测试模型列表
models_to_test = [
    "claude-sonnet-4-5",  # 别名（自动指向最新版本）
    "claude-sonnet-4-5-20250929",  # 具体版本
]

client = anthropic.Anthropic(api_key=API_KEY)

for model in models_to_test:
    print(f"\n测试模型: {model}")
    try:
        response = client.messages.create(
            model=model,
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": "请回复'测试成功'三个字"
                }
            ]
        )

        result = response.content[0].text
        print(f"  [OK] 模型可用")
        print(f"  响应: {result}")
        print(f"  输入tokens: {response.usage.input_tokens}")
        print(f"  输出tokens: {response.usage.output_tokens}")

    except anthropic.NotFoundError as e:
        print(f"  [FAIL] 模型不存在 (404)")
        print(f"  错误: {e}")

    except Exception as e:
        print(f"  [FAIL] 其他错误")
        print(f"  错误: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
