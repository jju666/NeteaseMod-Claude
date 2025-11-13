#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Hook 修复脚本 v20.2.6
修复测试会话中发现的 3 个关键问题：
1. 任务目录创建失败未被检测
2. Hook 误报中文编码问题
3. 通知系统未生效

使用方法:
python scripts/fix-hooks-v20.2.6.py <target_project_path>
"""

import sys
import os
import re
import shutil
from datetime import datetime

def backup_file(file_path):
    """备份文件"""
    backup_path = file_path + f".backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(file_path, backup_path)
    print(f"[BACKUP] {file_path} -> {backup_path}")
    return backup_path

def fix_user_prompt_submit_hook(hook_path):
    """修复 user-prompt-submit-hook.py - 增强目录创建验证"""
    print(f"\n[FIX 1] 修复 {hook_path}")

    if not os.path.exists(hook_path):
        print(f"[SKIP] 文件不存在: {hook_path}")
        return False

    # 备份
    backup_file(hook_path)

    with open(hook_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 修复 1.1: 增强 ensure_dir() 函数
    old_ensure_dir = r'''def ensure_dir\(path\):
    """确保目录存在.*?"""
    try:
        if not os\.path\.exists\(path\):
            os\.makedirs\(path\)
    except Exception as e:
        sys\.stderr\.write\(.*?\)'''

    new_ensure_dir = '''def ensure_dir(path):
    """确保目录存在 - 增强验证版 (v20.2.6)

    返回:
        bool: 成功返回True, 失败返回False
    """
    try:
        if not os.path.exists(path):
            os.makedirs(path)
            # 验证目录确实被创建
            if not os.path.exists(path):
                sys.stderr.write(u"[CRITICAL] 目录创建失败但未抛出异常: {}\\n".format(path))
                return False
        return True
    except Exception as e:
        sys.stderr.write(u"[CRITICAL] 创建目录失败: {}\\n错误: {}\\n".format(path, e))
        return False'''

    content_fixed = re.sub(old_ensure_dir, new_ensure_dir, content, flags=re.DOTALL)

    # 修复 1.2: 增加 ensure_dir 调用后的验证
    old_call = r'ensure_dir\(task_dir\)\s*\n\s*#'
    new_call = '''if not ensure_dir(task_dir):
            # 目录创建失败，阻塞流程
            sys.stderr.write(u"[CRITICAL] 任务初始化失败：无法创建任务目录\\n")
            sys.stderr.write(u"  任务ID: {}\\n".format(task_id))
            sys.stderr.write(u"  目标路径: {}\\n".format(task_dir))

            output = {
                "continue": False,
                "stopReason": "task_init_failed",
                "injectedContext": u"❌ 任务初始化失败：无法创建任务目录 {}".format(task_dir)
            }
            print(json.dumps(output, ensure_ascii=False))
            sys.exit(2)  # exit 2 = 阻塞错误

        #'''

    content_fixed = re.sub(old_call, new_call, content_fixed)

    # 写回文件
    with open(hook_path, 'w', encoding='utf-8') as f:
        f.write(content_fixed)

    print(f"[OK] 已修复 ensure_dir() 函数和调用")
    return True

def fix_check_critical_rules(hook_path):
    """修复 check-critical-rules.py - 改进 Edit 工具编码检测"""
    print(f"\n[FIX 2] 修复 {hook_path}")

    if not os.path.exists(hook_path):
        print(f"[SKIP] 文件不存在: {hook_path}")
        return False

    # 备份
    backup_file(hook_path)

    with open(hook_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已有 v20.2 的 skip_encoding_check 逻辑
    if 'skip_encoding_check' not in content:
        print(f"[WARN] 文件缺少 v20.2 编码检查跳过逻辑，需要完整更新")
        print(f"[INFO] 建议从模板复制: templates/.claude/hooks/check-critical-rules.py")
        return False

    # 修复编码检测逻辑 - 使用正则而非简单字符串匹配
    old_check = r"if 'coding' in file_content or 'utf-8' in file_content or 'utf8' in file_content:"
    new_check = "if re.search(r'#.*?coding[:=]\\s*utf-?8', file_content, re.IGNORECASE):"

    if old_check in content:
        content_fixed = content.replace(old_check, new_check)

        with open(hook_path, 'w', encoding='utf-8') as f:
            f.write(content_fixed)

        print(f"[OK] 已修复编码检测逻辑（使用正则匹配）")
        return True
    else:
        print(f"[SKIP] 未找到旧的编码检测代码，可能已修复")
        return True

def fix_settings_json(settings_path):
    """修复 settings.json - 移除错误的 Notification hook 配置"""
    print(f"\n[FIX 3] 修复 {settings_path}")

    if not os.path.exists(settings_path):
        print(f"[SKIP] 文件不存在: {settings_path}")
        return False

    # 备份
    backup_file(settings_path)

    with open(settings_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移除错误的 Notification hook 配置
    if '"Notification"' in content:
        # 使用正则删除整个 Notification 配置块
        pattern = r',?\s*"Notification":\s*\[\s*\{[^}]*"hooks":\s*\[[^\]]*vscode_notify\.py[^\]]*\][^\}]*\}\s*\]'
        content_fixed = re.sub(pattern, '', content)

        with open(settings_path, 'w', encoding='utf-8') as f:
            f.write(content_fixed)

        print(f"[OK] 已移除错误的 Notification hook 配置")
        return True
    else:
        print(f"[SKIP] 未找到错误的 Notification 配置")
        return True

def enhance_notify_fallback(hook_files):
    """增强通知降级输出"""
    print(f"\n[FIX 4] 增强通知降级输出")

    fixed_count = 0
    for hook_file in hook_files:
        if not os.path.exists(hook_file):
            continue

        with open(hook_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 查找静默吞噬通知错误的代码
        old_pattern = r'except:\s*pass\s*#\s*通知失败不影响主流程'
        new_code = '''except Exception as e:
            sys.stderr.write(u"[WARNING] 通知发送失败: {}\\n".format(e))'''

        if re.search(old_pattern, content):
            backup_file(hook_file)
            content_fixed = re.sub(old_pattern, new_code, content)

            with open(hook_file, 'w', encoding='utf-8') as f:
                f.write(content_fixed)

            print(f"[OK] 已增强 {os.path.basename(hook_file)} 的通知错误日志")
            fixed_count += 1

    print(f"[INFO] 共修复 {fixed_count} 个文件的通知错误处理")
    return fixed_count > 0

def main():
    if len(sys.argv) < 2:
        print("使用方法: python scripts/fix-hooks-v20.2.6.py <target_project_path>")
        print("示例: python scripts/fix-hooks-v20.2.6.py D:/EcWork/NetEaseMapECBedWars")
        sys.exit(1)

    target_project = sys.argv[1]

    if not os.path.exists(target_project):
        print(f"[ERROR] 目标项目不存在: {target_project}")
        sys.exit(1)

    hooks_dir = os.path.join(target_project, '.claude', 'hooks')
    if not os.path.exists(hooks_dir):
        print(f"[ERROR] Hooks 目录不存在: {hooks_dir}")
        sys.exit(1)

    print("=" * 60)
    print("Hook 修复脚本 v20.2.6")
    print("=" * 60)
    print(f"目标项目: {target_project}")
    print(f"Hooks 目录: {hooks_dir}")
    print("")

    # 修复 1: user-prompt-submit-hook.py
    user_prompt_hook = os.path.join(hooks_dir, 'user-prompt-submit-hook.py')
    fix_user_prompt_submit_hook(user_prompt_hook)

    # 修复 2: check-critical-rules.py
    check_rules_hook = os.path.join(hooks_dir, 'check-critical-rules.py')
    fix_check_critical_rules(check_rules_hook)

    # 修复 3: settings.json
    settings_file = os.path.join(target_project, '.claude', 'settings.json')
    fix_settings_json(settings_file)

    # 修复 4: 增强通知降级输出
    all_hooks = [
        os.path.join(hooks_dir, f) for f in os.listdir(hooks_dir)
        if f.endswith('.py') and 'hook' in f
    ]
    enhance_notify_fallback(all_hooks)

    print("\n" + "=" * 60)
    print("✅ 修复完成！")
    print("=" * 60)
    print("\n建议操作:")
    print("1. 查看备份文件（*.backup-*）确认修改正确")
    print("2. 重新运行测试会话验证修复效果")
    print("3. 如果有问题，可以从备份文件恢复")
    print("")

if __name__ == '__main__':
    main()
