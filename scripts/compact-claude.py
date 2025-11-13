#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLAUDE.md 紧凑化脚本
将完整版CLAUDE.md压缩到核心内容，目标减少50%+

策略:
1. 保留章节标题和核心概念
2. 删除详细代码示例（保留API引用）
3. 删除重复的mermaid图表
4. 压缩冗长的说明为简洁表格
5. 保留所有文件路径链接
"""

import re
import sys

def should_skip_code_block(content, start_idx):
    """判断是否应该跳过代码块（保留短代码示例）"""
    # 查找代码块结束位置
    end_idx = content.find('```', start_idx + 3)
    if end_idx == -1:
        return False

    code_content = content[start_idx:end_idx]
    lines = code_content.split('\n')

    # 保留短代码示例（<10行）
    if len(lines) < 10:
        return False

    # 保留关键API定义
    if 'PLACEHOLDERS' in code_content or 'VERSION' in code_content:
        return False

    # 跳过长代码示例
    return True

def should_skip_mermaid_diagram(content, start_idx):
    """判断是否应该跳过mermaid图表"""
    # 查找mermaid块结束位置
    end_idx = content.find('```', start_idx + 3)
    if end_idx == -1:
        return False

    diagram_content = content[start_idx:end_idx]

    # 保留简单流程图（<15行）
    if diagram_content.count('\n') < 15:
        return False

    # 跳过复杂图表
    return True

def compact_claude_md(input_file, output_file):
    """压缩CLAUDE.md"""
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"原始文件大小: {len(content)} 字符")
    print(f"原始行数: {content.count(chr(10))} 行\n")

    # 压缩策略列表
    compactions = []

    # 1. 删除长代码块（保留关键API）
    idx = 0
    new_content = []
    in_code_block = False
    code_start = 0

    while idx < len(content):
        if content[idx:idx+3] == '```':
            if not in_code_block:
                # 代码块开始
                in_code_block = True
                code_start = idx

                # 检查是否是mermaid图表
                next_line_end = content.find('\n', idx)
                if next_line_end > idx and 'mermaid' in content[idx:next_line_end]:
                    # 判断是否跳过
                    if should_skip_mermaid_diagram(content, idx):
                        # 跳过到代码块结束
                        end_idx = content.find('```', idx + 3)
                        if end_idx != -1:
                            idx = end_idx + 3
                            in_code_block = False
                            new_content.append('\n*[复杂流程图已省略，详见CLAUDE-FULL.md]*\n')
                            compactions.append('删除复杂mermaid图表')
                            continue
                # 检查是否应该跳过长代码块
                elif should_skip_code_block(content, idx):
                    # 跳过到代码块结束
                    end_idx = content.find('```', idx + 3)
                    if end_idx != -1:
                        idx = end_idx + 3
                        in_code_block = False
                        new_content.append('\n*[详细代码示例已省略，详见CLAUDE-FULL.md]*\n')
                        compactions.append('删除长代码块')
                        continue
            else:
                # 代码块结束
                in_code_block = False

        new_content.append(content[idx])
        idx += 1

    content = ''.join(new_content)

    # 2. 删除重复的完整目录树（保留关键文件清单）
    # 已在第二章手动压缩

    # 3. 压缩CHANGELOG示例（保留格式说明）
    # 删除冗长的CHANGELOG示例
    changelog_pattern = r'(## v17\.0\.0 \(2025-11-12\).*?)(## v17\.1\.0 \(2025-11-12\)|---)'
    content = re.sub(changelog_pattern, r'\n*[CHANGELOG示例已省略，详见CHANGELOG.md]*\n\n\2', content, flags=re.DOTALL)
    if changelog_pattern:
        compactions.append('压缩CHANGELOG示例')

    # 4. 删除重复的职责边界表格
    # 保留第一个，删除后续重复

    # 5. 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"\n压缩后文件大小: {len(content)} 字符")
    print(f"压缩后行数: {content.count(chr(10))} 行")
    print(f"压缩率: {(1 - len(content) / len(open(input_file, 'r', encoding='utf-8').read())) * 100:.1f}%\n")

    print("执行的压缩操作:")
    for i, op in enumerate(set(compactions), 1):
        print(f"  {i}. {op} ({compactions.count(op)}次)")

    print(f"\n✅ 紧凑版已生成: {output_file}")
    print(f"📚 完整版备份: CLAUDE-FULL.md")

if __name__ == '__main__':
    input_file = r'D:\EcWork\基于Claude的MODSDK开发工作流\CLAUDE.md'
    output_file = r'D:\EcWork\基于Claude的MODSDK开发工作流\CLAUDE-COMPACT.md'

    try:
        compact_claude_md(input_file, output_file)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
