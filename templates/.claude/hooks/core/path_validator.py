"""
Path Validator - 路径验证器
职责:
1. 文件路径白名单/黑名单验证
2. 通配符模式匹配
3. 路径规范化
"""

import os
import re
from pathlib import Path, PurePath
from typing import Dict, List, Optional


class PathValidator:
    """路径验证器 - 第三层验证"""

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd or os.getcwd()

    def validate(self, stage_name: str, tool_name: str, file_path: str, path_rules: Dict) -> Dict:
        """
        验证文件路径是否符合规则

        Args:
            stage_name: 当前阶段
            tool_name: 工具名称
            file_path: 文件路径
            path_rules: 路径规则配置

        Returns:
            {"allowed": bool, "reason": str, "suggestion": str}
        """
        # ✅ DEBUG诊断模式
        DEBUG = os.getenv("CLAUDE_HOOK_DEBUG", "0") == "1"

        if not file_path:
            return {"allowed": True, "reason": "无文件路径参数"}

        # 规范化路径
        normalized_path = self._normalize_path(file_path)

        # ✅ DEBUG诊断日志
        if DEBUG:
            import sys
            sys.stderr.write(f"[PathValidator] 原始路径: {file_path}\n")
            sys.stderr.write(f"[PathValidator] 归一化后: {normalized_path}\n")
            sys.stderr.write(f"[PathValidator] 白名单模式: {path_rules.get('whitelist_patterns', [])}\n")
            sys.stderr.write(f"[PathValidator] 白名单文件: {path_rules.get('whitelist', [])}\n")

        # 1. 检查黑名单（优先级最高）
        blacklist = path_rules.get('blacklist', [])
        if blacklist:
            if self._match_any_pattern(normalized_path, blacklist):
                return {
                    "allowed": False,
                    "reason": f"文件路径在黑名单中: {file_path}",
                    "suggestion": f"阶段 {stage_name} 禁止访问此文件"
                }

        blacklist_patterns = path_rules.get('blacklist_patterns', [])
        if blacklist_patterns:
            if self._match_any_glob_pattern(normalized_path, blacklist_patterns):
                return {
                    "allowed": False,
                    "reason": f"文件路径匹配黑名单模式: {file_path}",
                    "suggestion": f"阶段 {stage_name} 禁止访问此类型文件"
                }

        # 2. 检查白名单（如果定义了白名单，则必须匹配）
        whitelist = path_rules.get('whitelist', [])
        if whitelist:
            if not self._match_any_pattern(normalized_path, whitelist):
                return {
                    "allowed": False,
                    "reason": f"文件路径不在白名单中: {file_path}",
                    "suggestion": f"阶段 {stage_name} 只允许访问: {', '.join(whitelist[:3])}" + \
                                 ("..." if len(whitelist) > 3 else "")
                }

        whitelist_patterns = path_rules.get('whitelist_patterns', [])
        if whitelist_patterns:
            if not self._match_any_glob_pattern(normalized_path, whitelist_patterns):
                return {
                    "allowed": False,
                    "reason": f"文件路径不匹配白名单模式: {file_path}",
                    "suggestion": f"阶段 {stage_name} 只允许访问匹配以下模式的文件: {', '.join(whitelist_patterns[:2])}" + \
                                 ("..." if len(whitelist_patterns) > 2 else "")
                }

        # 3. 全部通过
        return {"allowed": True, "reason": "路径验证通过"}

    def _normalize_path(self, file_path: str) -> str:
        """
        规范化路径
        - 修复Windows中文路径编码问题
        - 转换为相对路径
        - 统一使用正斜杠
        - 去除开头的./
        """
        # ✅ 修复Windows中文路径编码问题
        import sys
        if sys.platform == 'win32':
            try:
                # 尝试检测并修复mojibake（文字化け）
                # 如果路径包含Latin-1范围外的字符但看起来像乱码，尝试重新解码
                if any(ord(c) > 127 for c in file_path):
                    # 尝试Latin-1 -> UTF-8转换
                    try:
                        fixed = file_path.encode('latin1').decode('utf-8')
                        file_path = fixed
                    except (UnicodeDecodeError, UnicodeEncodeError):
                        pass  # 转换失败，使用原始路径
            except Exception:
                pass  # 编码修复失败，继续使用原始路径

        # 转换为PurePath进行跨平台处理
        p = PurePath(file_path)

        # 如果是绝对路径，尝试转换为相对路径
        if p.is_absolute():
            try:
                cwd_path = PurePath(self.cwd)
                p = p.relative_to(cwd_path)
            except (ValueError, UnicodeDecodeError) as e:
                # ✅ 降级处理 - 尝试从项目根目录标志提取路径
                # 例如：D:\...\tests\behavior_packs\test.py -> behavior_packs/test.py
                path_str = str(p).replace('\\', '/')
                parts = path_str.split('/')

                # 查找项目根目录标志
                root_markers = ['behavior_packs', 'resource_packs', 'scripts', 'tests']
                for i, part in enumerate(parts):
                    if part in root_markers:
                        # 从标志开始重建相对路径
                        p = PurePath('/'.join(parts[i:]))
                        break
                # else: 找不到标志，保持原样（可能会匹配失败，但安全）

        # 转换为字符串，使用正斜杠
        normalized = str(p).replace('\\', '/')

        # 去除开头的./
        if normalized.startswith('./'):
            normalized = normalized[2:]

        return normalized

    def _match_any_pattern(self, file_path: str, patterns: List[str]) -> bool:
        """
        检查文件路径是否匹配任一精确模式

        Args:
            file_path: 规范化后的文件路径
            patterns: 精确匹配模式列表

        Returns:
            是否匹配任一模式
        """
        for pattern in patterns:
            # 规范化模式
            normalized_pattern = pattern.replace('\\', '/')
            if normalized_pattern.startswith('./'):
                normalized_pattern = normalized_pattern[2:]

            # 精确匹配或包含匹配
            if file_path == normalized_pattern or file_path.endswith('/' + normalized_pattern):
                return True

        return False

    def _match_any_glob_pattern(self, file_path: str, glob_patterns: List[str]) -> bool:
        """
        检查文件路径是否匹配任一通配符模式

        Args:
            file_path: 规范化后的文件路径
            glob_patterns: glob模式列表（如 "**/*.py", "docs/**/*.md"）

        Returns:
            是否匹配任一模式
        """
        from fnmatch import fnmatch

        for pattern in glob_patterns:
            # 规范化模式
            normalized_pattern = pattern.replace('\\', '/')

            # 使用fnmatch进行通配符匹配（支持*、?、**等）
            if self._glob_match(file_path, normalized_pattern):
                return True

        return False

    def _glob_match(self, file_path: str, pattern: str) -> bool:
        """
        执行glob模式匹配（支持**通配符）

        修复要点（解决glob模式匹配bug）：
        1. 使用re.escape()避免替换顺序问题
        2. 正确处理**（任意层级）和*（单层）的不同语义
        3. 转义正则特殊字符（., ?, [, ]等）

        Args:
            file_path: 文件路径（已规范化）
            pattern: glob模式（如 **/*.py, behavior_packs/**/*.py）

        Returns:
            bool: 是否匹配
        """
        import re

        # 处理**模式（匹配任意层级目录）
        if '**' in pattern:
            # Step 1: 转义所有正则特殊字符（保留*和?）
            regex_pattern = re.escape(pattern)

            # Step 2: 还原通配符（现在是转义后的形式 \*\* 和 \*）
            regex_pattern = regex_pattern.replace(r'\*\*', '.*')     # ** → 匹配任意层级
            regex_pattern = regex_pattern.replace(r'\*', '[^/]*')    # * → 匹配单层目录
            regex_pattern = regex_pattern.replace(r'\?', '.')        # ? → 匹配单字符

            # Step 3: 添加锚点
            regex_pattern = '^' + regex_pattern + '$'

            return bool(re.match(regex_pattern, file_path))
        else:
            # 普通通配符使用fnmatch
            from fnmatch import fnmatch
            return fnmatch(file_path, pattern)

    def is_code_file(self, file_path: str) -> bool:
        """判断是否为代码文件"""
        code_extensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h']
        return any(file_path.endswith(ext) for ext in code_extensions)

    def is_doc_file(self, file_path: str) -> bool:
        """判断是否为文档文件"""
        doc_extensions = ['.md', '.txt', '.rst', '.doc', '.docx']
        return any(file_path.endswith(ext) for ext in doc_extensions)

    def is_metadata_file(self, file_path: str) -> bool:
        """判断是否为元数据文件"""
        metadata_files = [
            '.task-meta.json',
            'workflow-state.json',
            '.task-active.json',
            '.cleanup-subagent.lock',
            '.conversation.jsonl'
        ]
        normalized = self._normalize_path(file_path)
        return any(normalized.endswith(meta_file) for meta_file in metadata_files)
