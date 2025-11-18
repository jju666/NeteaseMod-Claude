#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v24.0 部署验证脚本 (不依赖真实 API)

验证所有组件是否正确部署和集成
"""

import os
import sys
import io
import json

# 修复 Windows 编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加父目录到路径
HOOK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HOOK_DIR)

def print_header(title):
    print("\n" + "="*70)
    print(title)
    print("="*70)

def check_file(file_path, description):
    """检查文件是否存在"""
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        print(f"[OK] {description}")
        print(f"     路径: {file_path}")
        print(f"     大小: {size} 字节")
        return True
    else:
        print(f"[ERROR] {description} - 文件不存在")
        print(f"        路径: {file_path}")
        return False

def check_import(module_name, class_names):
    """检查模块导入"""
    try:
        module = __import__(module_name, fromlist=class_names)
        print(f"[OK] 模块导入成功: {module_name}")
        for cls_name in class_names:
            cls = getattr(module, cls_name)
            print(f"     - {cls_name}: {cls}")
        return True
    except Exception as e:
        print(f"[ERROR] 模块导入失败: {module_name}")
        print(f"        错误: {e}")
        return False

def check_function_in_file(file_path, function_names):
    """检查文件中是否包含指定函数"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        found = []
        not_found = []
        for func_name in function_names:
            pattern = f"def {func_name}("
            if pattern in content:
                found.append(func_name)
            else:
                not_found.append(func_name)

        if found:
            print(f"[OK] 函数检测通过: {file_path}")
            for func in found:
                print(f"     - {func}")

        if not_found:
            print(f"[WARN] 缺少函数:")
            for func in not_found:
                print(f"       - {func}")
            return False

        return True
    except Exception as e:
        print(f"[ERROR] 文件读取失败: {e}")
        return False

def main():
    print_header("v24.0 LLM语义分析 - 部署验证")

    results = {
        'passed': 0,
        'failed': 0,
        'total': 0
    }

    # 1. 检查核心文件
    print_header("1. 核心文件检查")

    files_to_check = [
        ("core/feedback_analyzer.py", "FeedbackAnalyzer 核心模块"),
        ("core/test_feedback_analyzer.py", "测试套件"),
        ("prompts/feedback_analysis_v1.txt", "提示词模板"),
        ("config/feedback_analyzer.json", "配置文件"),
        ("orchestrator/user_prompt_handler.py", "工作流集成"),
    ]

    for file_path, description in files_to_check:
        results['total'] += 1
        full_path = os.path.join(HOOK_DIR, file_path)
        if check_file(full_path, description):
            results['passed'] += 1
        else:
            results['failed'] += 1

    # 2. 检查模块导入
    print_header("2. 模块导入检查")

    results['total'] += 1
    if check_import("core.feedback_analyzer", ["FeedbackAnalyzer", "FeedbackAnalysis", "create_feedback_analyzer"]):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # 3. 检查集成函数
    print_header("3. 集成函数检查")

    results['total'] += 1
    user_prompt_handler_path = os.path.join(HOOK_DIR, "orchestrator", "user_prompt_handler.py")
    if check_function_in_file(user_prompt_handler_path, ["_handle_llm_analysis"]):
        results['passed'] += 1
    else:
        results['failed'] += 1

    # 4. 检查配置文件格式
    print_header("4. 配置文件验证")

    results['total'] += 1
    config_path = os.path.join(HOOK_DIR, "config", "feedback_analyzer.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        required_keys = ['version', 'enabled', 'model']
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            print(f"[WARN] 配置文件缺少必需字段: {missing_keys}")
            results['failed'] += 1
        else:
            print(f"[OK] 配置文件格式正确")
            print(f"     版本: {config['version']}")
            print(f"     启用: {config['enabled']}")
            print(f"     模型: {config['model']}")
            results['passed'] += 1
    except Exception as e:
        print(f"[ERROR] 配置文件解析失败: {e}")
        results['failed'] += 1

    # 5. 测试 FeedbackAnalyzer 基本功能（不调用 API）
    print_header("5. 基本功能测试（无 API 调用）")

    results['total'] += 1
    try:
        from core.feedback_analyzer import FeedbackAnalyzer

        # 测试初始化（不提供 API key，应该失败但不崩溃）
        analyzer = FeedbackAnalyzer(api_key="fake-key-for-testing")

        # 测试 fallback 行为
        analysis = analyzer._fallback_analysis("测试反馈", "测试错误")

        if analysis.overall_status == "needs_clarification":
            print("[OK] Fallback 机制正常工作")
            print(f"     fallback_status: {analysis.overall_status}")
            print(f"     confidence: {analysis.confidence}")
            results['passed'] += 1
        else:
            print("[ERROR] Fallback 机制异常")
            results['failed'] += 1
    except Exception as e:
        print(f"[ERROR] 基本功能测试失败: {e}")
        results['failed'] += 1

    # 6. 总结
    print_header("部署验证总结")

    print(f"总检查项: {results['total']}")
    print(f"通过: {results['passed']}")
    print(f"失败: {results['failed']}")
    print(f"成功率: {results['passed'] / results['total'] * 100:.1f}%")

    if results['failed'] == 0:
        print("\n[SUCCESS] 所有检查通过！v24.0 已成功部署到 tests 目录。")
        print("\n下一步:")
        print("1. 在实际 Hook 环境中测试（需要 Claude Code CLI）")
        print("2. 配置环境变量: ANTHROPIC_API_KEY 或 ANTHROPIC_AUTH_TOKEN")
        print("3. 在真实任务中使用并收集反馈")
        return 0
    else:
        print("\n[WARNING] 部分检查未通过，请检查上述错误。")
        return 1

if __name__ == '__main__':
    sys.exit(main())
