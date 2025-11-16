#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证SubagentStop Hook修复效果

测试目标：
1. 验证修复后的代码能正确识别assistant消息
2. 验证能正确提取content字段
3. 验证LLM解析兜底是否被触发（如果没有标记）
"""

import json
import os
import sys

# 添加hooks目录到路径
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)
HOOK_DIR = os.path.join(PROJECT_ROOT, 'templates', '.claude', 'hooks')
sys.path.insert(0, HOOK_DIR)

from lifecycle.subagent_stop import extract_subagent_result

# 测试transcript文件路径
TRANSCRIPT_PATH = r"C:\Users\28114\.claude\projects\D--EcWork---Claude-MODSDK------tests\agent-fe27a7f6.jsonl"

def test_extract_subagent_result():
    """测试提取子代理结果功能"""
    print("=" * 80)
    print("测试SubagentStop Hook修复效果")
    print("=" * 80)

    # 检查文件是否存在
    if not os.path.exists(TRANSCRIPT_PATH):
        print(f"❌ 错误：transcript文件不存在")
        print(f"   路径：{TRANSCRIPT_PATH}")
        return False

    print(f"✓ transcript文件存在")
    print(f"  路径：{TRANSCRIPT_PATH}")

    # 统计文件信息
    with open(TRANSCRIPT_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        total_lines = len(lines)

        # 统计消息类型
        user_count = 0
        assistant_count = 0
        for line in lines:
            try:
                msg = json.loads(line)
                if msg.get('type') == 'user':
                    user_count += 1
                elif msg.get('type') == 'assistant':
                    assistant_count += 1
            except:
                pass

    print(f"\n文件统计：")
    print(f"  - 总行数：{total_lines}")
    print(f"  - user消息：{user_count}")
    print(f"  - assistant消息：{assistant_count}")

    # 调用extract_subagent_result
    print(f"\n开始提取子代理结果...")
    print("-" * 80)

    result = extract_subagent_result(TRANSCRIPT_PATH)

    print("-" * 80)

    # 检查结果
    if result:
        print(f"\n✅ 成功提取子代理结果！")
        print(f"\n结果内容：")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        # 检查必要字段
        required_fields = ['approved', 'issues', 'suggestions']
        missing_fields = [f for f in required_fields if f not in result]

        if missing_fields:
            print(f"\n⚠️ 警告：缺少必要字段：{missing_fields}")
            return False
        else:
            print(f"\n✓ 所有必要字段都存在")
            return True
    else:
        print(f"\n❌ 未能提取子代理结果")
        print(f"\n可能原因：")
        print(f"  1. 没有找到SUBAGENT_RESULT标记")
        print(f"  2. LLM解析兜底失败（检查ANTHROPIC_API_KEY环境变量）")
        print(f"  3. 消息格式解析错误（这个已经修复）")
        return False

def check_last_message():
    """检查最后一条assistant消息的内容"""
    print("\n" + "=" * 80)
    print("检查最后一条assistant消息")
    print("=" * 80)

    with open(TRANSCRIPT_PATH, 'r', encoding='utf-8') as f:
        messages = []
        for line in f:
            try:
                msg = json.loads(line)
                messages.append(msg)
            except:
                pass

    # 查找最后一条assistant消息
    for msg in reversed(messages):
        if msg.get('type') == 'assistant':
            message_data = msg.get('message', {})
            content = message_data.get('content', [])

            print(f"\n找到最后一条assistant消息：")
            print(f"  - UUID: {msg.get('uuid', 'N/A')}")
            print(f"  - 时间戳: {msg.get('timestamp', 'N/A')}")
            print(f"  - stop_reason: {message_data.get('stop_reason', 'N/A')}")
            print(f"  - content段数: {len(content) if isinstance(content, list) else 'N/A'}")

            # 提取文本内容
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))

                full_text = '\n'.join(text_parts)
                print(f"\n文本内容（前500字符）：")
                print(full_text[:500])

                # 检查是否包含SUBAGENT_RESULT标记
                if '<!-- SUBAGENT_RESULT' in full_text:
                    print(f"\n✓ 包含SUBAGENT_RESULT标记")
                else:
                    print(f"\n⚠️ 不包含SUBAGENT_RESULT标记")
                    print(f"   → 需要触发LLM解析兜底机制")

            break
    else:
        print(f"\n❌ 未找到任何assistant消息")

if __name__ == '__main__':
    print("\n🔍 SubagentStop Hook修复验证脚本\n")

    # 检查最后一条消息
    check_last_message()

    # 测试提取功能
    success = test_extract_subagent_result()

    print("\n" + "=" * 80)
    if success:
        print("✅ 验证通过：修复生效！")
        print("\n下一步：")
        print("  1. 重新运行原始的/mc命令测试工作流")
        print("  2. 检查expert_review_count是否正确更新")
        print("  3. 检查task-meta.json中的expert_review_completed字段")
    else:
        print("❌ 验证失败")
        print("\n排查步骤：")
        print("  1. 检查ANTHROPIC_API_KEY环境变量是否设置")
        print("  2. 检查anthropic库是否安装（pip install anthropic）")
        print("  3. 查看上方stderr输出中的详细错误信息")
    print("=" * 80)

    sys.exit(0 if success else 1)
