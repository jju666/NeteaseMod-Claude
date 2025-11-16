#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SubagentStop Hook Unit Tests - 验证v3.0 transcript解析
测试范围:
1. extract_subagent_result() transcript解析
2. JSON/JSONL格式支持
3. SUBAGENT_RESULT标记提取
4. generate_user_message() 用户消息生成
"""

import sys
import os
import json
import tempfile
import unittest

# 添加templates/.claude/hooks到路径
HOOK_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'templates', '.claude', 'hooks'
)
sys.path.insert(0, HOOK_DIR)

from lifecycle.subagent_stop import extract_subagent_result, generate_user_message


class TestSubagentStopV3(unittest.TestCase):
    """v3.0 Final SubagentStop Hook测试"""

    def setUp(self):
        """创建临时文件用于测试"""
        self.temp_dir = tempfile.mkdtemp()

    def test_extract_from_json_transcript(self):
        """测试从标准JSON格式transcript提取结果"""
        transcript_content = {
            "messages": [
                {
                    "role": "user",
                    "content": "请审查这个方案"
                },
                {
                    "role": "assistant",
                    "content": """
## 专家审查结果

方案已通过审查，无CRITICAL违规。

### 合规性检查
- ✅ 无CRITICAL违规
- ⚠️ 建议添加物品掉落范围限制

<!-- SUBAGENT_RESULT
{
  "approved": true,
  "issues": [],
  "suggestions": ["建议添加物品掉落范围限制"]
}
-->
"""
                }
            ]
        }

        # 写入临时文件
        transcript_path = os.path.join(self.temp_dir, "transcript.json")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_content, f)

        # 提取结果
        result = extract_subagent_result(transcript_path)

        # 验证
        self.assertIsNotNone(result, "应成功提取结果")
        self.assertTrue(result["approved"])
        self.assertEqual(result["issues"], [])
        self.assertEqual(result["suggestions"], ["建议添加物品掉落范围限制"])

    def test_extract_from_jsonl_transcript(self):
        """测试从JSONL格式transcript提取结果"""
        transcript_lines = [
            json.dumps({"role": "user", "content": "请审查这个方案"}),
            json.dumps({
                "role": "assistant",
                "content": """审查完成\n\n<!-- SUBAGENT_RESULT\n{"approved": false, "issues": ["缺少错误处理"], "suggestions": []}\n-->"""
            })
        ]

        # 写入临时文件
        transcript_path = os.path.join(self.temp_dir, "transcript.jsonl")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(transcript_lines))

        # 提取结果
        result = extract_subagent_result(transcript_path)

        # 验证
        self.assertIsNotNone(result, "应成功提取结果")
        self.assertFalse(result["approved"])
        self.assertEqual(result["issues"], ["缺少错误处理"])

    def test_extract_with_multiline_json(self):
        """测试提取多行JSON格式的SUBAGENT_RESULT"""
        transcript_content = {
            "messages": [
                {
                    "role": "assistant",
                    "content": """
审查结果

<!-- SUBAGENT_RESULT
{
  "approved": true,
  "issues": [
    "问题1",
    "问题2"
  ],
  "suggestions": [
    "建议1",
    "建议2"
  ]
}
-->
"""
                }
            ]
        }

        transcript_path = os.path.join(self.temp_dir, "multiline.json")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_content, f)

        result = extract_subagent_result(transcript_path)

        self.assertIsNotNone(result)
        self.assertTrue(result["approved"])
        self.assertEqual(len(result["issues"]), 2)
        self.assertEqual(len(result["suggestions"]), 2)

    def test_extract_with_list_content(self):
        """测试处理content为数组的情况"""
        transcript_content = {
            "messages": [
                {
                    "role": "assistant",
                    "content": [
                        {"type": "text", "text": "审查结果"},
                        {
                            "type": "text",
                            "text": '<!-- SUBAGENT_RESULT {"approved": true, "issues": [], "suggestions": []} -->'
                        }
                    ]
                }
            ]
        }

        transcript_path = os.path.join(self.temp_dir, "list_content.json")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_content, f)

        result = extract_subagent_result(transcript_path)

        self.assertIsNotNone(result)
        self.assertTrue(result["approved"])

    def test_extract_returns_none_for_missing_marker(self):
        """测试缺少SUBAGENT_RESULT标记时返回None"""
        transcript_content = {
            "messages": [
                {
                    "role": "assistant",
                    "content": "普通回复，没有标记"
                }
            ]
        }

        transcript_path = os.path.join(self.temp_dir, "no_marker.json")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_content, f)

        result = extract_subagent_result(transcript_path)
        self.assertIsNone(result, "缺少标记应返回None")

    def test_extract_returns_none_for_invalid_json(self):
        """测试JSON格式错误时返回None"""
        transcript_content = {
            "messages": [
                {
                    "role": "assistant",
                    "content": '<!-- SUBAGENT_RESULT {invalid json} -->'
                }
            ]
        }

        transcript_path = os.path.join(self.temp_dir, "invalid_json.json")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_content, f)

        result = extract_subagent_result(transcript_path)
        self.assertIsNone(result, "JSON格式错误应返回None")

    def test_extract_returns_none_for_nonexistent_file(self):
        """测试文件不存在时返回None"""
        result = extract_subagent_result("/nonexistent/path.json")
        self.assertIsNone(result)

    def test_generate_user_message_expert_approved(self):
        """测试生成专家审查通过消息"""
        subagent_result = {
            "approved": True,
            "issues": [],
            "suggestions": ["建议添加物品掉落范围限制"]
        }

        message = generate_user_message("bug_fix", subagent_result, "expert_review")

        self.assertIn("✅ 专家审查通过", message)
        self.assertIn("💡 优化建议", message)
        self.assertIn("建议添加物品掉落范围限制", message)

    def test_generate_user_message_expert_rejected(self):
        """测试生成专家审查未通过消息"""
        subagent_result = {
            "approved": False,
            "issues": ["缺少错误处理", "未验证输入"],
            "suggestions": ["添加try-catch"]
        }

        message = generate_user_message("bug_fix", subagent_result, "expert_review")

        self.assertIn("⚠️ 专家审查发现问题", message)
        self.assertIn("缺少错误处理", message)
        self.assertIn("未验证输入", message)
        self.assertIn("💡 改进建议", message)
        self.assertIn("添加try-catch", message)

    def test_generate_user_message_doc_research(self):
        """测试生成文档查询消息"""
        subagent_result = {
            "summary": "已查询相关API文档",
            "findings": [
                "使用spawnItem()生成物品",
                "坐标范围限制在-100到100"
            ]
        }

        message = generate_user_message("feature_design", subagent_result, "doc_research")

        self.assertIn("📚 文档查询完成", message)
        self.assertIn("已查询相关API文档", message)
        self.assertIn("使用spawnItem()生成物品", message)
        self.assertIn("坐标范围限制在-100到100", message)

    def test_generate_user_message_other_subagent(self):
        """测试生成其他子代理类型消息"""
        subagent_result = {}
        message = generate_user_message("general", subagent_result, "unknown_type")

        self.assertIn("✅ 子代理完成", message)
        self.assertIn("unknown_type", message)


if __name__ == '__main__':
    unittest.main(verbosity=2)
