# -*- coding: utf-8 -*-
"""
项目分析器
负责扫描MODSDK项目，识别项目类型、代码结构、现有文档
"""

from __future__ import print_function
import os
import re
from collections import defaultdict
import config

class ProjectAnalyzer:
    """项目分析器"""

    def __init__(self, project_path):
        self.project_path = project_path
        self.metadata = ProjectMetadata()
        self.code_structure = CodeStructure()
        self.doc_coverage = DocumentationCoverage()

    def analyze(self):
        """执行完整分析"""
        print("[分析器] 开始分析项目...")
        print("[分析器] 项目路径: {}".format(self.project_path))

        # 步骤1: 检测项目类型
        self._detect_project_type()

        # 步骤2: 扫描代码结构
        self._scan_code_structure()

        # 步骤3: 检查现有文档
        self._check_documentation()

        # 步骤4: 计算项目规模
        self._calculate_project_scale()

        print("[分析器] 分析完成")
        return self.generate_report()

    def _detect_project_type(self):
        """检测项目类型"""
        print("[分析器] 检测项目类型...")

        # 检查是否为MODSDK项目
        mod_main_path = self._find_file("modMain.py")
        if not mod_main_path:
            raise Exception("未检测到modMain.py，不是有效的MODSDK项目")

        self.metadata.is_modsdk = True
        self.metadata.mod_main_path = mod_main_path

        # 获取项目名称（从modMain.py所在目录）
        self.metadata.project_name = os.path.basename(os.path.dirname(mod_main_path))

        print("[分析器] 检测到MODSDK项目: {}".format(self.metadata.project_name))

        # 检测架构特征
        self.metadata.uses_apollo = self._detect_apollo()
        self.metadata.uses_ecpreset = self._detect_ecpreset()

        # 推断业务类型
        self.metadata.business_type = self._infer_business_type()

        print("[分析器] 项目类型: {}".format(self.metadata.business_type))
        if self.metadata.uses_apollo:
            print("[分析器] 检测到Apollo架构")
        if self.metadata.uses_ecpreset:
            print("[分析器] 检测到ECPreset框架")

    def _scan_code_structure(self):
        """扫描代码结构"""
        print("[分析器] 扫描代码结构...")

        # 扫描所有Python文件
        python_files_count = 0
        for root, dirs, files in os.walk(self.project_path):
            # 跳过一些常见的非代码目录
            if any(skip_dir in root for skip_dir in ['.git', '__pycache__', 'venv', 'node_modules']):
                continue

            for file in files:
                if file.endswith('.py'):
                    python_files_count += 1
                    file_path = os.path.join(root, file)
                    try:
                        self._analyze_python_file(file_path)
                    except Exception as e:
                        print("[分析器] 警告: 分析文件失败 {} - {}".format(file_path, str(e)))

        print("[分析器] 发现 {} 个Python文件".format(python_files_count))
        print("[分析器] 发现 {} 个Systems".format(len(self.code_structure.systems)))
        print("[分析器] 发现 {} 个Presets".format(len(self.code_structure.presets)))

    def _analyze_python_file(self, file_path):
        """分析单个Python文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            # 尝试使用其他编码
            try:
                with open(file_path, 'r', encoding='gbk') as f:
                    content = f.read()
            except:
                return  # 无法读取，跳过

        # 检测System类
        system_matches = re.findall(
            r'class\s+(\w+)\s*\(\s*(ServerSystem|ClientSystem)\s*\)',
            content
        )
        for class_name, base_class in system_matches:
            self.code_structure.add_system(
                name=class_name,
                file_path=file_path,
                type=base_class,
                content=content
            )

        # 检测Preset类
        preset_matches = re.findall(
            r'class\s+(\w+)\s*\(\s*ECPresetDefinition\s*\)',
            content
        )
        for class_name in preset_matches:
            self.code_structure.add_preset(
                name=class_name,
                file_path=file_path,
                content=content
            )

    def _check_documentation(self):
        """检查现有文档"""
        print("[分析器] 检查现有文档...")

        markdown_dir = os.path.join(self.project_path, "markdown")
        if not os.path.exists(markdown_dir):
            print("[分析器] markdown/目录不存在")
            return

        # 扫描所有markdown文件
        for root, dirs, files in os.walk(markdown_dir):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    self.doc_coverage.add_existing_doc(file_path)

        print("[分析器] 发现 {} 个现有文档".format(len(self.doc_coverage.existing_docs)))

    def _calculate_project_scale(self):
        """计算项目规模"""
        systems_count = len(self.code_structure.systems)

        if systems_count <= config.SCALE_THRESHOLDS["small"]:
            self.metadata.scale = "small"
        elif systems_count <= config.SCALE_THRESHOLDS["medium"]:
            self.metadata.scale = "medium"
        else:
            self.metadata.scale = "large"

        print("[分析器] 项目规模: {} ({} Systems)".format(self.metadata.scale, systems_count))

    def generate_report(self):
        """生成分析报告"""
        return AnalysisReport(
            metadata=self.metadata,
            code_structure=self.code_structure,
            doc_coverage=self.doc_coverage
        )

    # 辅助方法
    def _find_file(self, filename):
        """在项目中查找文件"""
        for root, dirs, files in os.walk(self.project_path):
            if filename in files:
                return os.path.join(root, filename)
        return None

    def _detect_apollo(self):
        """检测是否使用Apollo"""
        # 搜索import apollo相关代码
        mod_main_path = self.metadata.mod_main_path
        if mod_main_path:
            try:
                with open(mod_main_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'apollo' in content.lower():
                        return True
            except:
                pass
        return False

    def _detect_ecpreset(self):
        """检测是否使用ECPreset"""
        return len(self.code_structure.presets) > 0

    def _infer_business_type(self):
        """推断业务类型"""
        # 根据System名称推断
        system_names_lower = [s.name.lower() for s in self.code_structure.systems.values()]

        # 计算每种类型的匹配分数
        scores = {}
        for business_type, keywords in config.PROJECT_TYPE_KEYWORDS.items():
            score = sum(1 for name in system_names_lower
                       if any(keyword in name for keyword in keywords))
            scores[business_type] = score

        # 选择得分最高的类型
        if scores:
            max_type = max(scores, key=scores.get)
            if scores[max_type] > 0:
                return max_type

        return "General"


class ProjectMetadata:
    """项目元数据"""
    def __init__(self):
        self.is_modsdk = False
        self.project_name = ""
        self.mod_main_path = ""
        self.uses_apollo = False
        self.uses_ecpreset = False
        self.business_type = "General"
        self.scale = "small"  # small / medium / large


class CodeStructure:
    """代码结构"""
    def __init__(self):
        self.systems = {}  # {system_name: SystemInfo}
        self.presets = {}  # {preset_name: PresetInfo}
        self.dependencies = defaultdict(list)  # {system_name: [依赖的system]}

    def add_system(self, name, file_path, type, content):
        self.systems[name] = SystemInfo(name, file_path, type, content)

    def add_preset(self, name, file_path, content):
        self.presets[name] = PresetInfo(name, file_path, content)


class SystemInfo:
    """System信息"""
    def __init__(self, name, file_path, type, content):
        self.name = name
        self.file_path = file_path
        self.type = type  # ServerSystem / ClientSystem
        self.content = content

        # 分析代码复杂度
        self.lines_of_code = len(content.split('\n'))
        self.method_count = len(re.findall(r'def\s+\w+\s*\(', content))
        self.event_listeners = len(re.findall(r'ListenForEvent', content))

        # 计算复杂度分数
        self.complexity_score = self._calculate_complexity()

    def _calculate_complexity(self):
        """计算复杂度分数（用于决定文档详细度）"""
        score = 0

        # 因素1: 代码行数
        if self.lines_of_code > 500:
            score += 3
        elif self.lines_of_code > 200:
            score += 2
        else:
            score += 1

        # 因素2: 方法数量
        if self.method_count > 15:
            score += 2
        elif self.method_count > 5:
            score += 1

        # 因素3: 事件监听数量
        if self.event_listeners > 5:
            score += 1

        # 因素4: 核心System判断
        core_keywords = ['core', 'manager', 'game', 'state', 'main']
        if any(keyword in self.name.lower() for keyword in core_keywords):
            score += 2

        # 因素5: 依赖关系（通过import数量估算）
        import_count = len(re.findall(r'from\s+\w+\s+import', self.content))
        if import_count > 5:
            score += 2
        elif import_count > 2:
            score += 1

        return score

    def get_detail_level(self):
        """获取推荐的文档详细度"""
        if self.complexity_score >= config.COMPLEXITY_THRESHOLDS["detailed"]:
            return "detailed"  # 3000字
        elif self.complexity_score >= config.COMPLEXITY_THRESHOLDS["medium"]:
            return "medium"    # 1500字
        else:
            return "simple"    # 500字


class PresetInfo:
    """Preset信息"""
    def __init__(self, name, file_path, content):
        self.name = name
        self.file_path = file_path
        self.content = content


class DocumentationCoverage:
    """文档覆盖率"""
    def __init__(self):
        self.existing_docs = []  # 现有文档列表
        self.missing_docs = []   # 缺失文档列表
        self.low_quality_docs = []  # 低质量文档列表

    def add_existing_doc(self, doc_path):
        self.existing_docs.append(doc_path)


class AnalysisReport:
    """分析报告"""
    def __init__(self, metadata, code_structure, doc_coverage):
        self.metadata = metadata
        self.code_structure = code_structure
        self.doc_coverage = doc_coverage

    def to_markdown(self):
        """生成Markdown格式报告"""
        report = []
        report.append("# 📊 项目分析报告\n")

        # 项目概况
        report.append("## 🎯 项目概况\n")
        report.append("- **项目名称**: {}".format(self.metadata.project_name))
        report.append("- **项目类型**: {}".format(self.metadata.business_type))
        report.append("- **项目规模**: {}".format(self.metadata.scale))
        report.append("- **架构特征**:")
        report.append("  - Apollo架构: {}".format('✅' if self.metadata.uses_apollo else '❌'))
        report.append("  - ECPreset框架: {}".format('✅' if self.metadata.uses_ecpreset else '❌'))
        report.append("")

        # 代码结构
        report.append("## 📐 代码结构\n")
        report.append("- **Systems数量**: {}".format(len(self.code_structure.systems)))
        report.append("- **Presets数量**: {}".format(len(self.code_structure.presets)))
        report.append("")

        # Systems列表（按复杂度排序，只显示前10个）
        report.append("### Systems清单（按复杂度排序，前10个）\n")
        report.append("| System名称 | 类型 | 代码行数 | 方法数 | 复杂度 | 推荐详细度 |")
        report.append("|-----------|------|---------|--------|--------|-----------|")
        sorted_systems = sorted(self.code_structure.systems.values(),
                               key=lambda s: s.complexity_score, reverse=True)
        for system in sorted_systems[:10]:
            report.append("| {} | {} | {} | {} | {}/10 | {} |".format(
                system.name,
                system.type,
                system.lines_of_code,
                system.method_count,
                system.complexity_score,
                system.get_detail_level()
            ))

        if len(sorted_systems) > 10:
            report.append("| ... | ... | ... | ... | ... | ... |")
            report.append("| *共{}个Systems* | | | | | |".format(len(sorted_systems)))
        report.append("")

        # 文档覆盖率
        report.append("## 📚 文档覆盖率\n")
        report.append("- **现有文档**: {} 个".format(len(self.doc_coverage.existing_docs)))
        report.append("- **Systems缺失文档**: {} 个".format(
            len([s for s in self.code_structure.systems.values()])
        ))
        report.append("")

        # 预计生成
        report.append("## 📝 预计生成文档\n")
        report.append("- **Layer 1（通用层）**: 约13个文件")
        report.append("  - CLAUDE.md、开发规范.md、问题排查.md等")
        report.append("  - .claude/commands/cc.md ⭐")
        report.append("  - markdown/ai/（4个AI补充文档）")
        report.append("- **Layer 2（架构层）**: {}个系统文档".format(len(self.code_structure.systems)))
        if self.code_structure.presets:
            report.append("  - {}个Preset文档".format(len(self.code_structure.presets)))
        report.append("- **Layer 3（业务层）**: 框架文档（待后续补充）")
        report.append("")

        # 预估消耗
        systems_count = len(self.code_structure.systems)
        estimated_tokens = 30000  # 基础
        estimated_tokens += systems_count * 1000  # 每个System约1000 tokens
        estimated_time = max(5, systems_count // 3)  # 至少5分钟，每3个System增加1分钟

        report.append("## ⏱️ 预估消耗\n")
        report.append("- **预计Token消耗**: 约{}k tokens".format(estimated_tokens // 1000))
        report.append("- **预计执行时间**: 约{}分钟".format(estimated_time))
        report.append("")

        return "\n".join(report)
