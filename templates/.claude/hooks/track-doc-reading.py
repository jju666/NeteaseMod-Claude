#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Track Document Reading Hook - 追踪文档阅读进度
触发时机: Read工具调用后（PostToolUse事件）
职责: 统计.md文件阅读数量，自动标记步骤2完成
"""

import os
import sys
import json
from datetime import datetime
import io

# 修复Windows GBK编码问题：强制使用UTF-8输出
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 导入通知模块
try:
    from vscode_notify import notify_info, notify_warning
except ImportError:
    def notify_info(msg, detail=""): pass
    def notify_warning(msg, detail=""): pass

def main():
    """主函数：追踪文档阅读"""
    try:
        # 1. 读取Hook输入（stdin传入的JSON）
        hook_input = json.load(sys.stdin)

        tool_name = hook_input.get('toolName', '')
        tool_params = hook_input.get('parameters', {})
        project_path = hook_input.get('cwd', os.getcwd())

        # 2. 只追踪Read工具
        if tool_name != 'Read':
            sys.exit(0)

        # 3. 获取读取的文件路径
        file_path = tool_params.get('file_path', '')
        if not file_path:
            sys.exit(0)

        # 4. 只追踪.md文件
        if not file_path.endswith('.md'):
            sys.exit(0)

        # 5. 排除不应计入的文档（如README、索引等）
        excluded_patterns = [
            'README.md',
            '索引.md',
            '项目状态.md',
            '文档待补充清单.md',
            'CHANGELOG.md'
        ]
        if any(pattern in file_path for pattern in excluded_patterns):
            sys.exit(0)

        # 6. 读取工作流状态
        state_file = os.path.join(project_path, '.claude', 'workflow-state.json')
        if not os.path.exists(state_file):
            # 状态文件不存在，可能不是/mc任务，不追踪
            sys.exit(0)

        with open(state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        # 7. 更新docs_read列表（去重）
        docs_read = state.get('docs_read', [])
        if file_path not in docs_read:
            docs_read.append(file_path)
            state['docs_read'] = docs_read

        # 8. 更新文档计数
        doc_count = len(docs_read)
        state['steps_completed']['step2_doc_count'] = doc_count

        # 9. 如果文档数≥3，自动标记步骤2完成
        if doc_count >= 3:
            if not state['steps_completed']['step2_doc_reading']:
                state['steps_completed']['step2_doc_reading'] = True
                state['current_step'] = 3

                # 📢 通知：步骤2完成，进入步骤3
                try:
                    notify_info(
                        u"步骤2完成：查阅文档",
                        u"已阅读{}个文档 → 进入步骤3".format(doc_count)
                    )
                except:
                    pass

                # 输出步骤2完成提示
                completion_message = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 步骤2完成：已阅读{doc_count}个文档
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**已读取的文档**:
{chr(10).join([f"  {i+1}. {doc}" for i, doc in enumerate(docs_read)])}

**🎉 步骤2要求达成**:
- ✅ 已Read ≥3个markdown文档
- ✅ 现在可以进入步骤3探索代码

**下一步（步骤3 - 执行与收尾）**:
1. 探索相关代码（现在可以Read Python文件）
2. 设计修复方案
3. 执行修改（添加注释）
4. 验证修复

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                print(completion_message)

        # 10. 更新时间戳
        state['last_updated'] = datetime.now().isoformat()

        # 11. 保存状态文件
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        # 12. 允许工具继续执行
        sys.exit(0)

    except Exception as e:
        # 异常情况下允许继续
        print(f"⚠️ Hook执行异常: {str(e)}", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
