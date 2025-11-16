# NeteaseMod-Claude v3.0 Final 单元测试

## 概述

本目录包含v3.0 Final版本的完整自动化测试套件,用于验证Hook重构计划书的所有实现。

## 测试范围

### 1. Tool Matrix测试 (`test_tool_matrix.py`)

验证核心状态机配置:

- ✅ 4步语义化状态机 (activation/planning/implementation/finalization)
- ✅ STEP_ORDER顺序正确性
- ✅ 差异化工作流配置 (bug_fix vs feature_design)
- ✅ get_next_step()状态推进逻辑
- ✅ get_workflow_config()函数
- ✅ get_min_doc_count()函数
- ✅ 向后兼容STEP_MAPPING

**测试用例数**: 13个

### 2. SubagentStop Hook测试 (`test_subagent_stop.py`)

验证v3.0 transcript解析实现:

- ✅ extract_subagent_result() 从JSON格式transcript提取
- ✅ extract_subagent_result() 从JSONL格式transcript提取
- ✅ 多行JSON格式支持
- ✅ content为数组的处理
- ✅ 缺少SUBAGENT_RESULT标记的边界情况
- ✅ JSON格式错误的容错处理
- ✅ 文件不存在的容错处理
- ✅ generate_user_message() 专家审查通过消息
- ✅ generate_user_message() 专家审查未通过消息
- ✅ generate_user_message() 文档查询消息
- ✅ generate_user_message() 其他子代理类型

**测试用例数**: 11个

### 3. YAML规则测试 (`test_yaml_rules.py`)

验证4个YAML规则文件:

#### activation.yaml
- ✅ 文件存在性
- ✅ display_name正确
- ✅ task_type_detection配置
- ✅ bug_fix关键词 (BUG/修复/bug/fix)
- ✅ feature_design关键词 (实现/添加/功能/feature)
- ✅ 自动推进到planning配置

#### planning.yaml
- ✅ 文件存在性
- ✅ display_name正确
- ✅ allowed_tools (Task/Read/Grep/Glob)
- ✅ bug_fix_rules (min_doc_count=0, expert_review_required=true)
- ✅ feature_design_rules (min_doc_count=3, gameplay_pack_matching=true)
- ✅ 用户确认推进到implementation

#### implementation.yaml
- ✅ 文件存在性
- ✅ display_name正确
- ✅ allowed_tools (Write/Edit/Bash)
- ✅ round_based_iteration配置 (enabled=true, max_rounds=10, round_boundary="Stop")
- ✅ metrics_tracking (code_changes/user_feedback)
- ✅ expert_review_trigger (same_file_edits_threshold=5, consecutive_failures=3)
- ✅ completion_keywords (/mc-confirm/已修复/修复完成)

#### finalization.yaml
- ✅ 文件存在性
- ✅ display_name正确
- ✅ 父代理allowed_tools只有Task和Read
- ✅ 子代理allowed_tools (Write/Edit/Read/Grep)
- ✅ archiving配置
- ✅ 子代理完成触发条件 (steps.finalization.status == 'completed')

**测试用例数**: 22个

## 快速开始

### 运行所有测试

```bash
# Windows
python unit_tests\run_all_tests.py

# Linux/macOS
python3 unit_tests/run_all_tests.py
```

### 运行单个测试模块

```bash
# 测试Tool Matrix
python -m unittest unit_tests.test_tool_matrix

# 测试SubagentStop
python -m unittest unit_tests.test_subagent_stop

# 测试YAML规则
python -m unittest unit_tests.test_yaml_rules
```

### 运行单个测试用例

```bash
# 测试4步状态机
python -m unittest unit_tests.test_tool_matrix.TestToolMatrixV3.test_step_order_is_4_steps

# 测试JSON transcript提取
python -m unittest unit_tests.test_subagent_stop.TestSubagentStopV3.test_extract_from_json_transcript

# 测试BUG修复规则
python -m unittest unit_tests.test_yaml_rules.TestPlanningYAML.test_bug_fix_rules
```

## 测试报告

运行`run_all_tests.py`后会生成以下输出:

1. **控制台输出**: 彩色实时测试进度
   - ✓ (绿色): 测试通过
   - F (黄色): 测试失败
   - E (红色): 测试错误
   - S (蓝色): 测试跳过

2. **test_report.txt**: 详细测试报告
   - 测试统计
   - 失败测试详情
   - 错误测试详情

## 测试覆盖率

| 模块 | 测试用例 | 覆盖功能 |
|------|---------|---------|
| tool_matrix.py | 13 | 状态机配置、差异化流程、状态推进 |
| subagent_stop.py | 11 | Transcript解析、结果提取、用户消息生成 |
| activation.yaml | 6 | 任务类型检测、自动推进 |
| planning.yaml | 5 | 差异化规则、专家审查、文档查询 |
| implementation.yaml | 5 | 轮次循环、专家审查触发、用户反馈 |
| finalization.yaml | 6 | 子代理权限、归档配置 |

**总计**: 46个测试用例

## CI/CD集成

可以将测试集成到CI/CD流程:

```yaml
# .github/workflows/test.yml
name: Unit Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.8'
      - name: Install dependencies
        run: |
          pip install pyyaml
      - name: Run tests
        run: |
          python unit_tests/run_all_tests.py
```

## 依赖

- Python 3.6+
- pyyaml (用于YAML测试)

安装依赖:

```bash
pip install pyyaml
```

## 故障排查

### 常见问题

**问题1: ImportError: No module named 'core.tool_matrix'**

**解决方案**: 确保从项目根目录运行测试:
```bash
cd D:\EcWork\基于Claude的MODSDK开发工作流
python unit_tests\run_all_tests.py
```

**问题2: FileNotFoundError: [Errno 2] No such file or directory: '.../activation.yaml'**

**解决方案**: 确认YAML文件已创建:
```bash
dir templates\.claude\rules\*.yaml
```

**问题3: 测试失败 "STEP_ORDER必须是4步语义化状态机"**

**解决方案**: 检查tool_matrix.py中的STEP_ORDER是否为:
```python
STEP_ORDER = ["activation", "planning", "implementation", "finalization"]
```

## 开发者指南

### 添加新测试

1. **创建测试类**:
```python
class TestNewFeature(unittest.TestCase):
    def test_feature_works(self):
        # 测试逻辑
        self.assertTrue(feature_works())
```

2. **在run_all_tests.py中注册**:
```python
from unit_tests.test_new_feature import TestNewFeature

test_classes = [
    # ... 现有测试 ...
    TestNewFeature,
]
```

### 测试命名规范

- 测试文件: `test_<模块名>.py`
- 测试类: `Test<功能名>`
- 测试方法: `test_<具体测试内容>`

### 断言方法

常用unittest断言:

```python
self.assertEqual(a, b)        # a == b
self.assertNotEqual(a, b)     # a != b
self.assertTrue(x)            # x is True
self.assertFalse(x)           # x is False
self.assertIn(a, b)           # a in b
self.assertIsNone(x)          # x is None
self.assertIsNotNone(x)       # x is not None
```

## 版本历史

- **v3.0 Final** (2025-11-15): 完整测试套件覆盖所有v3.0实现
  - 46个测试用例
  - 3个测试模块
  - 彩色输出和详细报告

## 许可证

MIT License - 与主项目保持一致

---

**最后更新**: 2025-11-15
**维护者**: NeteaseMod-Claude 团队
