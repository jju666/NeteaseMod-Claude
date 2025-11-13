# -*- coding: utf-8 -*-
"""
测试v20.2.4 BUG修复指引生成功能
验证4个新增函数是否正常工作
"""
import sys
import os

# 直接加载Hook文件并执行
hook_file_path = os.path.join(
    os.path.dirname(__file__),
    '..',
    'templates',
    '.claude',
    'hooks',
    'user-prompt-submit-hook.py'
)

# 读取并执行Hook文件，提取函数
with open(hook_file_path, 'r', encoding='utf-8') as f:
    hook_code = f.read()

# 创建命名空间并执行
hook_namespace = {}
exec(hook_code, hook_namespace)

# 提取需要测试的函数
is_bugfix_task = hook_namespace['is_bugfix_task']
analyze_bug_symptom = hook_namespace['analyze_bug_symptom']
route_knowledge_sources = hook_namespace['route_knowledge_sources']
extract_business_keywords = hook_namespace['extract_business_keywords']
format_bugfix_guide = hook_namespace['format_bugfix_guide']

def test_is_bugfix_task():
    """测试BUG检测函数"""
    print(u"\n=== 测试1: BUG任务检测 ===")

    test_cases = [
        (u"/mc 修复tests目录中的玩家重生位置BUG", True),
        (u"/mc 修复AttributeError问题", True),
        (u"/mc 实现传送门功能", False),
        (u"/mc 玩家死亡后背包掉落BUG", True),
    ]

    for task_desc, expected in test_cases:
        result = is_bugfix_task(task_desc)
        status = u"✅" if result == expected else u"❌"
        print(u"{} '{}' → {}".format(status, task_desc, result))

def test_analyze_bug_symptom():
    """测试症状分析函数"""
    print(u"\n=== 测试2: BUG症状分析 ===")

    test_cases = [
        (u"修复玩家重生位置BUG", "business_logic"),
        (u"修复AttributeError问题", "api_error"),
        (u"修复生命周期初始化错误", "lifecycle_error"),
        (u"解决卡顿性能问题", "performance"),
    ]

    for task_desc, expected_type in test_cases:
        symptom_type, symptom_desc = analyze_bug_symptom(task_desc)
        status = u"✅" if symptom_type == expected_type else u"❌"
        print(u"{} '{}' → {} ({})".format(
            status, task_desc, symptom_type, symptom_desc
        ))

def test_route_knowledge_sources():
    """测试知识源路由函数"""
    print(u"\n=== 测试3: 知识源路由 ===")

    symptom_types = [
        "business_logic",
        "api_error",
        "lifecycle_error",
        "performance"
    ]

    for symptom_type in symptom_types:
        route = route_knowledge_sources(symptom_type, u"测试任务")
        print(u"✅ {} → {}".format(symptom_type, route["strategy"]))

def test_extract_business_keywords():
    """测试关键词提取函数"""
    print(u"\n=== 测试4: 业务关键词提取 ===")

    test_cases = [
        u"修复tests目录中的玩家重生位置BUG",
        u"玩家死亡后背包掉落不正确",
        u"NPC对话系统触发异常",
    ]

    for task_desc in test_cases:
        keywords = extract_business_keywords(task_desc)
        print(u"✅ '{}' → {}".format(task_desc, u', '.join(keywords)))

def test_format_bugfix_guide():
    """测试BUG修复指引生成"""
    print(u"\n=== 测试5: BUG修复指引生成 ===")

    test_cases = [
        u"修复tests目录中的玩家重生位置BUG",
        u"修复AttributeError: 'NoneType' object has no attribute 'get'",
    ]

    for task_desc in test_cases:
        try:
            guide = format_bugfix_guide(task_desc)
            if u"智能BUG修复系统 v20.2" in guide:
                print(u"✅ '{}' → 指引生成成功 ({} 字符)".format(
                    task_desc[:30] + u"...", len(guide)
                ))
                # 打印指引预览
                lines = guide.split(u'\n')[:10]
                for line in lines:
                    print(u"  {}".format(line))
                print(u"  ...")
            else:
                print(u"❌ '{}' → 指引格式异常".format(task_desc))
        except Exception as e:
            print(u"❌ '{}' → 生成失败: {}".format(task_desc, e))

if __name__ == '__main__':
    print(u"=" * 50)
    print(u"v20.2.4 BUG修复指引功能测试")
    print(u"=" * 50)

    try:
        test_is_bugfix_task()
        test_analyze_bug_symptom()
        test_route_knowledge_sources()
        test_extract_business_keywords()
        test_format_bugfix_guide()

        print(u"\n" + u"=" * 50)
        print(u"✅ 所有测试完成")
        print(u"=" * 50)
    except Exception as e:
        print(u"\n❌ 测试失败: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
