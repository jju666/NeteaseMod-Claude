#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MVP2: Claude API 语义分析验证

目标: 验证通过Claude API调用进行意图识别的可行性
技术栈: anthropic SDK, Claude Haiku模型
评估指标: 准确率、延迟、Token用量、成本
"""

import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 设置Windows控制台UTF-8编码支持
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

try:
    import anthropic
except ImportError:
    print("❌ 缺少依赖: anthropic")
    print("请运行: pip install anthropic")
    sys.exit(1)

# ===== 配置 =====
MODEL_NAME = "claude-3-5-haiku-20241022"
# 支持两种环境变量名称
API_KEY = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
TEST_CASES_FILE = Path(__file__).parent / 'test_cases.json'
OUTPUT_FILE = Path(__file__).parent / 'results' / 'mvp_claude_api_results.json'

# Claude Haiku 定价 (2024年11月)
PRICING = {
    'input_per_mtok': 0.80,   # $0.80 per million tokens
    'output_per_mtok': 4.00   # $4.00 per million tokens
}

# ===== 核心函数 =====
def load_test_cases() -> List[Tuple[str, str]]:
    """加载测试数据集"""
    if not TEST_CASES_FILE.exists():
        raise FileNotFoundError(f"测试数据集不存在: {TEST_CASES_FILE}")

    with open(TEST_CASES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = []
    for case in data['test_cases']:
        test_cases.append((case['input'], case['expected_intent']))

    return test_cases


def analyze_via_api(client: anthropic.Anthropic, user_input: str, context: Dict = None) -> Dict:
    """
    使用 Claude API 分析用户意图

    Args:
        client: Anthropic客户端
        user_input: 用户输入文本
        context: 任务上下文信息

    Returns:
        {
            'intent': 识别的意图,
            'confidence': 置信度,
            'reasoning': 判断理由,
            'latency_ms': 延迟(毫秒),
            'tokens_used': Token用量,
            'input_tokens': 输入Token数,
            'output_tokens': 输出Token数
        }
    """
    if context is None:
        context = {'current_step': 'implementation', 'code_changes': 0}

    prompt = f"""你是一个任务状态分析专家。请分析用户的反馈，判断任务应该转移到哪个状态。

**当前任务上下文**:
- 当前阶段: {context.get('current_step', 'implementation')}
- 代码修改次数: {context.get('code_changes', 0)}

**用户反馈**: "{user_input}"

**请判断用户意图（只输出JSON，不要其他内容）**:

可选意图类型:
- complete_success: 任务完全成功，所有问题已解决
- partial_success: 部分成功，还有一些问题需要继续修复
- failure: 修复失败或出现新问题
- planning_required: 需要重新设计方案或思路

输出格式:
{{
  "intent": "意图类型",
  "confidence": 0.0-1.0,
  "reasoning": "一句话说明判断理由"
}}
"""

    start_time = time.time()
    try:
        response = client.messages.create(
            model=MODEL_NAME,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        latency = time.time() - start_time

        # 解析响应
        response_text = response.content[0].text.strip()

        # 尝试提取JSON（可能包含markdown代码块）
        if '```json' in response_text:
            json_start = response_text.find('```json') + 7
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()
        elif '```' in response_text:
            json_start = response_text.find('```') + 3
            json_end = response_text.find('```', json_start)
            response_text = response_text[json_start:json_end].strip()

        result = json.loads(response_text)

        return {
            'intent': result.get('intent', 'error'),
            'confidence': result.get('confidence', 0.0),
            'reasoning': result.get('reasoning', ''),
            'latency_ms': latency * 1000,
            'tokens_used': response.usage.input_tokens + response.usage.output_tokens,
            'input_tokens': response.usage.input_tokens,
            'output_tokens': response.usage.output_tokens,
            'success': True
        }

    except json.JSONDecodeError as e:
        latency = time.time() - start_time
        return {
            'intent': 'error',
            'confidence': 0.0,
            'reasoning': f'JSON解析失败: {str(e)}',
            'latency_ms': latency * 1000,
            'tokens_used': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'success': False,
            'raw_response': response_text if 'response_text' in locals() else ''
        }

    except Exception as e:
        latency = time.time() - start_time
        return {
            'intent': 'error',
            'confidence': 0.0,
            'reasoning': f'API调用失败: {str(e)}',
            'latency_ms': latency * 1000,
            'tokens_used': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'success': False
        }


def evaluate(client: anthropic.Anthropic, test_cases: List[Tuple[str, str]]) -> Dict:
    """
    评估准确率、延迟、成本

    Returns:
        {
            'accuracy': 准确率,
            'avg_latency_ms': 平均延迟,
            'avg_tokens': 平均Token用量,
            'estimated_cost_per_call': 预估单次成本,
            'results': 详细结果列表
        }
    """
    correct = 0
    total = len(test_cases)
    results = []
    total_latency = 0
    total_input_tokens = 0
    total_output_tokens = 0
    api_errors = 0

    print(f"开始测试 {total} 个用例...")

    for idx, (user_input, expected_intent) in enumerate(test_cases, 1):
        # 模拟真实上下文
        context = {
            'current_step': 'implementation',
            'code_changes': 3
        }

        result = analyze_via_api(client, user_input, context)

        is_correct = result['intent'] == expected_intent and result['success']
        if is_correct:
            correct += 1

        if not result['success']:
            api_errors += 1

        total_latency += result['latency_ms']
        total_input_tokens += result['input_tokens']
        total_output_tokens += result['output_tokens']

        results.append({
            'id': idx,
            'input': user_input,
            'expected': expected_intent,
            'predicted': result['intent'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning'],
            'latency_ms': result['latency_ms'],
            'tokens_used': result['tokens_used'],
            'input_tokens': result['input_tokens'],
            'output_tokens': result['output_tokens'],
            'correct': is_correct,
            'success': result['success']
        })

        # 进度显示
        if idx % 10 == 0 or idx == total:
            print(f"  进度: {idx}/{total} ({idx/total*100:.0f}%)")

        # 延迟控制（避免触发速率限制）
        time.sleep(0.1)

    # 计算统计数据
    successful_calls = total - api_errors
    accuracy = correct / total if total > 0 else 0.0
    avg_latency = total_latency / successful_calls if successful_calls > 0 else 0.0
    avg_input_tokens = total_input_tokens / successful_calls if successful_calls > 0 else 0.0
    avg_output_tokens = total_output_tokens / successful_calls if successful_calls > 0 else 0.0
    avg_total_tokens = avg_input_tokens + avg_output_tokens

    # 成本计算
    estimated_cost_per_call = (
        (avg_input_tokens * PRICING['input_per_mtok'] +
         avg_output_tokens * PRICING['output_per_mtok']) / 1_000_000
    )

    return {
        'accuracy': accuracy,
        'avg_latency_ms': avg_latency,
        'avg_input_tokens': avg_input_tokens,
        'avg_output_tokens': avg_output_tokens,
        'avg_total_tokens': avg_total_tokens,
        'estimated_cost_per_call': estimated_cost_per_call,
        'total_input_tokens': total_input_tokens,
        'total_output_tokens': total_output_tokens,
        'total_cost': (total_input_tokens * PRICING['input_per_mtok'] +
                       total_output_tokens * PRICING['output_per_mtok']) / 1_000_000,
        'api_errors': api_errors,
        'results': results
    }


# ===== 主函数 =====
def main():
    print("=" * 60)
    print("  MVP2: Claude API 语义分析验证")
    print("=" * 60)
    print()

    # 检查API密钥
    if not API_KEY:
        print("❌ 错误: 未设置环境变量 ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN")
        print("\n请执行(二选一):")
        print('  export ANTHROPIC_API_KEY="your-api-key"       # Linux/Mac')
        print('  export ANTHROPIC_AUTH_TOKEN="your-api-key"    # Linux/Mac (alternative)')
        print('  set ANTHROPIC_API_KEY=your-api-key           # Windows CMD')
        print('  $env:ANTHROPIC_API_KEY="your-api-key"        # Windows PowerShell')
        sys.exit(1)

    # 1. 加载测试数据
    print("[1/3] 加载测试数据...")
    test_cases = load_test_cases()
    print(f"✅ 加载完成: {len(test_cases)} 个测试用例")

    # 2. 初始化客户端
    print(f"\n[2/3] 初始化 Anthropic 客户端...")
    print(f"      模型: {MODEL_NAME}")
    client = anthropic.Anthropic(api_key=API_KEY)
    print(f"✅ 客户端初始化完成")

    # 3. 评估
    print(f"\n[3/3] 评估准确率、延迟、成本...")
    print(f"      (预计耗时: {len(test_cases) * 0.5:.0f}-{len(test_cases) * 1.5:.0f}秒)")
    eval_result = evaluate(client, test_cases)

    # ===== 输出结果 =====
    print("\n" + "=" * 60)
    print("  评估结果")
    print("=" * 60)
    print(f"\n📊 总体指标:")
    print(f"  准确率: {eval_result['accuracy']:.2%} ({sum(r['correct'] for r in eval_result['results'])}/{len(test_cases)})")
    print(f"  平均延迟: {eval_result['avg_latency_ms']:.0f}ms")
    print(f"  平均Token用量: {eval_result['avg_total_tokens']:.1f} (输入:{eval_result['avg_input_tokens']:.1f}, 输出:{eval_result['avg_output_tokens']:.1f})")
    print(f"  预估单次成本: ${eval_result['estimated_cost_per_call']:.6f}")
    print(f"  本次测试总成本: ${eval_result['total_cost']:.4f}")
    if eval_result['api_errors'] > 0:
        print(f"  ⚠️  API错误: {eval_result['api_errors']} 次")

    # 统计各意图的准确率
    intent_stats = {}
    for r in eval_result['results']:
        intent = r['expected']
        if intent not in intent_stats:
            intent_stats[intent] = {'correct': 0, 'total': 0}
        intent_stats[intent]['total'] += 1
        if r['correct']:
            intent_stats[intent]['correct'] += 1

    print(f"\n📊 各意图准确率:")
    for intent, stats in intent_stats.items():
        acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
        print(f"  {intent:<20} {acc:>6.1%}  ({stats['correct']}/{stats['total']})")

    # 显示错误案例
    errors = [r for r in eval_result['results'] if not r['correct']]
    if errors:
        print(f"\n❌ 错误案例 ({len(errors)}个):")
        for r in errors[:10]:  # 只显示前10个
            print(f"  [{r['id']}] {r['input']}")
            print(f"      预期: {r['expected']}, 识别: {r['predicted']}, 置信度: {r['confidence']:.2f}")
            print(f"      理由: {r['reasoning']}")
            print(f"      延迟: {r['latency_ms']:.0f}ms, Tokens: {r['tokens_used']}")
            print()

    # ===== 保存结果 =====
    print("=" * 60)
    print("  保存结果")
    print("=" * 60)

    output_data = {
        'meta': {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model': MODEL_NAME,
            'test_cases_count': len(test_cases),
            'pricing': PRICING
        },
        'performance': {
            'avg_latency_ms': eval_result['avg_latency_ms'],
            'avg_input_tokens': eval_result['avg_input_tokens'],
            'avg_output_tokens': eval_result['avg_output_tokens'],
            'avg_total_tokens': eval_result['avg_total_tokens'],
            'total_input_tokens': eval_result['total_input_tokens'],
            'total_output_tokens': eval_result['total_output_tokens'],
            'api_errors': eval_result['api_errors']
        },
        'cost': {
            'estimated_cost_per_call': eval_result['estimated_cost_per_call'],
            'total_cost': eval_result['total_cost']
        },
        'accuracy': {
            'overall': eval_result['accuracy'],
            'by_intent': {
                intent: stats['correct'] / stats['total'] if stats['total'] > 0 else 0
                for intent, stats in intent_stats.items()
            }
        },
        'results': eval_result['results'],
        'errors': errors
    }

    # 确保输出目录存在
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 结果已保存到: {OUTPUT_FILE}")

    # ===== 总结 =====
    print("\n" + "=" * 60)
    print("  总结")
    print("=" * 60)
    print(f"✅ 总体准确率: {eval_result['accuracy']:.2%}")
    print(f"⏱️  平均延迟: {eval_result['avg_latency_ms']:.0f}ms")
    print(f"💰 预估单次成本: ${eval_result['estimated_cost_per_call']:.6f}")
    print(f"🎯 成功标准: 准确率>=95%, 延迟<=300ms, 成本<=$0.002")

    # 判断是否达标
    meets_accuracy = eval_result['accuracy'] >= 0.95
    meets_latency = eval_result['avg_latency_ms'] <= 300
    meets_cost = eval_result['estimated_cost_per_call'] <= 0.002

    if meets_accuracy and meets_latency and meets_cost:
        print("\n🎉 方案3(Claude API)达到所有成功标准!")
    else:
        print("\n⚠️  方案3未完全达标:")
        if not meets_accuracy:
            print(f"   - 准确率 {eval_result['accuracy']:.2%} < 95%")
        if not meets_latency:
            print(f"   - 延迟 {eval_result['avg_latency_ms']:.0f}ms > 300ms")
        if not meets_cost:
            print(f"   - 成本 ${eval_result['estimated_cost_per_call']:.6f} > $0.002")

    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
