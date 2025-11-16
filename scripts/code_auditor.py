#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代码审查工具 - 依赖图构建与废弃代码检测

职责:
1. 扫描 templates/ 目录下所有 Python 文件
2. 构建静态依赖关系图
3. 识别未被引用的文件和函数
4. 根据多维度验证进行置信度分级
5. 生成详细的审查报告

使用方式:
    python scripts/code_auditor.py

输出:
    - 标准输出: 进度和关键发现
    - 文件输出: audit-reports/YYYY-MM-DD-HHMMSS.json (结构化数据)
"""

import os
import re
import sys
import json
import ast
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import defaultdict

# Windows UTF-8 编码修复
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


class CodeAuditor:
    """代码审查器 - 依赖图分析与废弃代码检测"""

    def __init__(self, project_root: str):
        """初始化审查器

        Args:
            project_root: 项目根目录路径
        """
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "templates"
        self.hooks_dir = self.templates_dir / ".claude" / "hooks"

        # 数据结构
        self.all_files: List[Path] = []
        self.dependency_graph: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_graph: Dict[str, Set[str]] = defaultdict(set)
        self.entry_points: Set[str] = set()
        self.reachable_files: Set[str] = set()

        # 分析结果
        self.unreferenced_files: List[Path] = []
        self.confidence_high: List[Dict] = []
        self.confidence_medium: List[Dict] = []
        self.confidence_low: List[Dict] = []
        self.unused_functions: List[Dict] = []

        # 统计信息
        self.stats = {
            "total_files": 0,
            "entry_points": 0,
            "edges": 0,
            "unreferenced": 0
        }

    def run(self) -> Dict:
        """执行完整的代码审查流程

        Returns:
            审查结果字典
        """
        print("=" * 60)
        print("🔍 代码审查工具启动")
        print("=" * 60)
        print(f"项目根目录: {self.project_root}")
        print(f"审查目标: {self.templates_dir}")
        print()

        # 阶段 1: 文件扫描
        print("⏳ 阶段 1/5: 文件扫描...")
        self._scan_files()
        print(f"  ✅ 扫描完成: {self.stats['total_files']} 个文件\n")

        # 阶段 2: 依赖图构建
        print("⏳ 阶段 2/5: 依赖图构建...")
        self._build_dependency_graph()
        print(f"  ✅ 构建完成: {self.stats['edges']} 条依赖边\n")

        # 阶段 3: 入口点检测
        print("⏳ 阶段 3/5: 入口点检测...")
        self._detect_entry_points()
        print(f"  ✅ 检测完成: {self.stats['entry_points']} 个入口点\n")

        # 阶段 4: 可达性分析
        print("⏳ 阶段 4/5: 可达性分析...")
        self._analyze_reachability()
        print(f"  ✅ 分析完成: {len(self.reachable_files)} 个可达文件")
        print(f"  ⚠️ 未引用文件: {self.stats['unreferenced']} 个\n")

        # 阶段 5: 置信度分级
        print("⏳ 阶段 5/5: 置信度分级...")
        self._classify_by_confidence()
        print(f"  🔴 高置信度: {len(self.confidence_high)} 个")
        print(f"  🟡 中置信度: {len(self.confidence_medium)} 个")
        print(f"  🟢 低置信度: {len(self.confidence_low)} 个\n")

        # 生成报告
        print("📝 生成审查报告...")
        report = self._generate_report()
        print("  ✅ 报告生成完成\n")

        return report

    def _scan_files(self):
        """扫描所有 Python 文件"""
        if not self.hooks_dir.exists():
            print(f"❌ 错误: hooks 目录不存在: {self.hooks_dir}")
            sys.exit(1)

        # 递归扫描所有 .py 文件
        for py_file in self.hooks_dir.rglob("*.py"):
            # 排除 __pycache__ 等临时目录
            if "__pycache__" in py_file.parts:
                continue

            self.all_files.append(py_file)

        self.stats["total_files"] = len(self.all_files)

    def _build_dependency_graph(self):
        """构建依赖关系图"""
        for file_path in self.all_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                # 提取 import 语句
                imports = self._extract_imports(content, file_path)

                # 相对路径作为节点标识
                file_rel = self._get_relative_path(file_path)

                # 构建依赖边
                for imported_module in imports:
                    # 尝试将模块名解析为文件路径
                    imported_file = self._resolve_module_path(imported_module, file_path)
                    if imported_file:
                        imported_rel = self._get_relative_path(imported_file)
                        self.dependency_graph[file_rel].add(imported_rel)
                        self.reverse_graph[imported_rel].add(file_rel)
                        self.stats["edges"] += 1

            except Exception as e:
                print(f"  ⚠️ 警告: 读取文件失败 {file_path}: {e}")

    def _extract_imports(self, content: str, file_path: Path) -> Set[str]:
        """提取文件中的 import 语句

        Args:
            content: 文件内容
            file_path: 文件路径

        Returns:
            导入的模块名集合
        """
        imports = set()

        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)

                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                        # 同时添加 from X import Y 中的 Y（如果是子模块）
                        for alias in node.names:
                            if alias.name != "*":
                                full_name = f"{node.module}.{alias.name}"
                                imports.add(full_name)

        except SyntaxError as e:
            print(f"  ⚠️ 语法错误 {file_path}: {e}")

        return imports

    def _resolve_module_path(self, module_name: str, current_file: Path) -> Optional[Path]:
        """将模块名解析为文件路径

        Args:
            module_name: 模块名（如 "core.task_meta_manager"）
            current_file: 当前文件路径

        Returns:
            解析后的文件路径，如果无法解析则返回 None
        """
        # 处理相对导入（.module 或 ..module）
        if module_name.startswith("."):
            # 相对导入，基于当前文件位置
            current_dir = current_file.parent
            parts = module_name.split(".")

            # 计算向上的层数
            level = 0
            for part in parts:
                if part == "":
                    level += 1
                else:
                    break

            # 向上移动目录
            base_dir = current_dir
            for _ in range(level - 1):
                base_dir = base_dir.parent

            # 移除前导点号
            module_parts = [p for p in parts if p]

            # 构建路径
            if module_parts:
                module_path = base_dir / "/".join(module_parts)
            else:
                module_path = base_dir

        else:
            # 绝对导入，基于 hooks 目录
            module_parts = module_name.split(".")
            module_path = self.hooks_dir / "/".join(module_parts)

        # 尝试匹配文件
        candidates = [
            module_path.with_suffix(".py"),
            module_path / "__init__.py"
        ]

        for candidate in candidates:
            if candidate.exists() and candidate in self.all_files:
                return candidate

        return None

    def _detect_entry_points(self):
        """检测入口点（从 settings.json.template 读取已注册的 hooks）"""
        settings_file = self.templates_dir / ".claude" / "settings.json.template"

        if not settings_file.exists():
            print(f"  ⚠️ 警告: settings.json.template 不存在，无法检测入口点")
            return

        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)

            hooks = settings.get("hooks", {})

            for hook_name, hook_configs in hooks.items():
                for config in hook_configs:
                    for hook_def in config.get("hooks", []):
                        command = hook_def.get("command", "")

                        # 提取 Python 脚本路径（格式: python .claude/hooks/xxx.py）
                        match = re.search(r'python\s+\.claude/hooks/(.+\.py)', command)
                        if match:
                            hook_path = match.group(1).replace("/", os.sep)
                            entry_rel = str(Path(hook_path))
                            self.entry_points.add(entry_rel)

        except Exception as e:
            print(f"  ⚠️ 警告: 解析 settings.json.template 失败: {e}")

        self.stats["entry_points"] = len(self.entry_points)

    def _analyze_reachability(self):
        """分析可达性（从入口点出发 DFS）"""
        # DFS 遍历
        visited = set()

        def dfs(node: str):
            if node in visited:
                return
            visited.add(node)
            self.reachable_files.add(node)

            # 递归访问依赖
            for neighbor in self.dependency_graph.get(node, []):
                dfs(neighbor)

        # 从所有入口点出发
        for entry in self.entry_points:
            dfs(entry)

        # 识别未引用文件
        for file_path in self.all_files:
            file_rel = self._get_relative_path(file_path)
            if file_rel not in self.reachable_files:
                self.unreferenced_files.append(file_path)

        self.stats["unreferenced"] = len(self.unreferenced_files)

    def _classify_by_confidence(self):
        """根据多维度验证进行置信度分级"""
        for file_path in self.unreferenced_files:
            file_rel = self._get_relative_path(file_path)

            # 基础信息
            file_info = {
                "file": str(file_path.relative_to(self.project_root)),
                "file_rel": file_rel,
                "reasons": [],
                "risks": [],
                "suggestions": []
            }

            # 检查 1: deprecated 目录
            is_deprecated = "deprecated" in file_path.parts

            # 检查 2: Git 状态（需要外部调用 git status）
            # 这里暂时跳过，由 Claude 在运行时检查

            # 检查 3: 文件名模式
            filename = file_path.name
            is_test = filename.startswith("test_")
            is_init = filename == "__init__.py"
            has_deprecated_keyword = any(kw in filename.lower() for kw in ["deprecated", "obsolete", "old_"])

            # 检查 4: 注释标记（需要读取文件内容）
            has_deprecated_comment = False
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_lines = f.read(500)  # 读取前 500 字符
                    if re.search(r'#\s*(deprecated|obsolete|废弃)', first_lines, re.IGNORECASE):
                        has_deprecated_comment = True
            except:
                pass

            # 置信度分级逻辑
            if is_deprecated:
                file_info["reasons"].append("位于 deprecated/ 目录")
                file_info["suggestions"].append("安全删除")
                self.confidence_high.append(file_info)

            elif has_deprecated_keyword or has_deprecated_comment:
                file_info["reasons"].append("文件名或注释标记为废弃")
                file_info["suggestions"].append("建议删除")
                self.confidence_high.append(file_info)

            elif is_init and len(self._get_sibling_files(file_path)) == 0:
                file_info["reasons"].append("__init__.py 文件，但目录下无其他文件")
                file_info["suggestions"].append("建议删除（可能是空包）")
                self.confidence_medium.append(file_info)

            elif any(d in file_path.parts for d in ["core", "utils", "orchestrator"]):
                file_info["reasons"].append("位于核心模块目录，但未被引用")
                file_info["risks"].append("可能被外部脚本使用或动态引用")
                file_info["suggestions"].append("建议人工确认后删除")
                self.confidence_medium.append(file_info)

            elif is_test:
                file_info["reasons"].append("测试文件，但未被引用")
                file_info["suggestions"].append("建议保留或移至 tests/ 目录")
                self.confidence_low.append(file_info)

            else:
                # 默认：中置信度
                file_info["reasons"].append("静态分析未检测到引用")
                file_info["risks"].append("可能存在动态引用或配置引用")
                file_info["suggestions"].append("建议人工确认")
                self.confidence_medium.append(file_info)

    def _get_relative_path(self, file_path: Path) -> str:
        """获取相对于 hooks 目录的路径"""
        try:
            return str(file_path.relative_to(self.hooks_dir))
        except ValueError:
            return str(file_path)

    def _get_sibling_files(self, file_path: Path) -> List[Path]:
        """获取同目录下的其他 Python 文件"""
        parent = file_path.parent
        siblings = []
        for f in parent.glob("*.py"):
            if f != file_path and f.name != "__pycache__":
                siblings.append(f)
        return siblings

    def _generate_report(self) -> Dict:
        """生成审查报告"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "project_root": str(self.project_root),
            "audit_target": str(self.templates_dir),
            "statistics": self.stats,
            "entry_points": list(self.entry_points),
            "reachable_files": list(self.reachable_files),
            "unreferenced_files": [str(f.relative_to(self.project_root)) for f in self.unreferenced_files],
            "confidence_high": self.confidence_high,
            "confidence_medium": self.confidence_medium,
            "confidence_low": self.confidence_low,
            "unused_functions": self.unused_functions
        }

        # 保存到文件
        report_dir = self.project_root / "audit-reports"
        report_dir.mkdir(exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y-%m-%d-%H%M%S")
        report_file = report_dir / f"{timestamp_str}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"  ✅ 报告已保存: {report_file}")

        return report


def main():
    """主入口"""
    # 获取项目根目录（脚本位于 scripts/ 目录）
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # 创建审查器
    auditor = CodeAuditor(str(project_root))

    # 运行审查
    report = auditor.run()

    # 输出汇总
    print("=" * 60)
    print("✅ 审查完成")
    print("=" * 60)
    print(f"📊 统计:")
    print(f"  - 扫描文件: {report['statistics']['total_files']} 个")
    print(f"  - 入口点: {report['statistics']['entry_points']} 个")
    print(f"  - 依赖边: {report['statistics']['edges']} 条")
    print(f"  - 可达文件: {len(report['reachable_files'])} 个")
    print(f"  - 未引用文件: {report['statistics']['unreferenced']} 个")
    print()
    print(f"🔍 分级结果:")
    print(f"  🔴 高置信度: {len(report['confidence_high'])} 个")
    print(f"  🟡 中置信度: {len(report['confidence_medium'])} 个")
    print(f"  🟢 低置信度: {len(report['confidence_low'])} 个")
    print()
    print("📄 详细报告已保存到 audit-reports/ 目录")
    print("=" * 60)


if __name__ == "__main__":
    main()
