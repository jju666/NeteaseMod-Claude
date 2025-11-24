#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Task Initializer - 任务初始化器 (v25.0)

负责任务创建和恢复的所有逻辑。

核心功能：
1. `/mc`命令解析
2. 任务ID生成（时间戳+描述）
3. 任务目录创建（带回滚机制）
4. 玩法包匹配（知识库查询）
5. task-meta.json初始化
6. 任务恢复检测与绑定
7. 初始文件创建（context.md, solution.md）

作者: NeteaseMod-Claude工作流系统
版本: v25.0
日期: 2025-11-20
"""

import sys
import os
import json
import re
from datetime import datetime


class TaskInitializer:
    """
    任务初始化器 (v25.0)

    负责所有任务创建和恢复逻辑，包括：
    - /mc命令处理
    - 任务ID生成
    - 任务目录创建
    - 玩法包匹配
    - task-meta.json初始化
    - 任务恢复
    """

    def __init__(self, cwd, session_id):
        """
        初始化任务初始化器

        Args:
            cwd: 工作目录
            session_id: 当前会话ID
        """
        self.cwd = cwd
        self.session_id = session_id
        self.meta_manager = self._get_task_meta_manager()
        self.knowledge_base = self._load_knowledge_base()

    def handle_mc_command(self, command_args):
        """
        处理/mc命令（主入口）

        Args:
            command_args: /mc命令参数（任务描述或任务ID）

        Returns:
            dict: 处理结果
                {
                    'continue': True/False,
                    'additionalContext': str  # 注入内容
                }
        """
        # 参数验证
        task_desc = command_args.strip().strip('"\'')
        if not task_desc:
            return {
                'continue': False,
                'additionalContext': self._generate_missing_desc_prompt()
            }

        # 1. 检测任务恢复
        resume_info = self._detect_resume(task_desc)
        if resume_info['is_resume']:
            return self.resume_existing_task(resume_info)

        # 2. 创建新任务
        return self.create_new_task(task_desc)

    # ==================== 新任务创建 ====================

    def create_new_task(self, task_desc):
        """
        创建新任务（完整流程）

        流程：
        1. 生成任务ID
        2. 创建任务目录
        3. 玩法包匹配
        4. 生成task-meta.json
        5. 保存元数据并绑定会话
        6. 创建初始文件
        7. 生成注入内容

        Args:
            task_desc: 任务描述

        Returns:
            dict: 创建结果
        """
        # 1. 生成任务ID
        task_id = self._generate_task_id(task_desc)
        sys.stderr.write(u"[INFO] 创建新任务: {}\n".format(task_id))

        # 2. 创建任务目录
        try:
            task_dir = self._create_task_directory(task_id)
        except Exception as e:
            sys.stderr.write(u"[ERROR] 任务目录创建失败: {}\n".format(e))
            return {
                'continue': False,
                'additionalContext': self._generate_dir_creation_error(task_id, str(e))
            }

        # 3. 玩法包匹配
        matched_pattern = self._match_gameplay_pack(task_desc)
        is_bugfix = self._is_bugfix_task(task_desc)

        # 4. 生成task-meta.json
        task_meta = self._build_task_meta(
            task_id, task_desc, matched_pattern, is_bugfix
        )

        # 5. 保存元数据并绑定会话
        if not self.meta_manager.save_task_meta(task_id, task_meta):
            sys.stderr.write(u"[ERROR] 保存task-meta.json失败\n")
            return {
                'continue': False,
                'additionalContext': u"❌ 任务元数据保存失败"
            }

        if not self.meta_manager.bind_task_to_session(task_id, self.session_id):
            sys.stderr.write(u"[WARN] 绑定任务到会话失败\n")

        # 6. 创建初始文件
        self._create_initial_files(task_dir, task_id, task_desc)

        # 7. 生成注入内容
        injection_content = self._generate_injection_content(
            task_id, task_desc, matched_pattern, is_bugfix
        )

        sys.stderr.write(u"[INFO] 任务创建成功: {}\n".format(task_id))

        # 8. 生成systemMessage（用户和Claude都可见，强制性更强）
        system_message_for_planning = u""
        if is_bugfix:
            system_message_for_planning = u"""
╭─── 📋 BUG修复工作流要求 ───────────────╮
│ **强制性步骤**：专家审查                  │
│                                         │
│ ⚠️ 在向用户展示方案之前，你**必须**：      │
│                                         │
│ 1. 使用Task工具启动专家审查子代理        │
│ 2. 等待审查结果返回                     │
│ 3. 根据审查意见调整方案（如需要）        │
│ 4. 然后才能向用户展示最终方案           │
│                                         │
│ ❌ 禁止跳过审查直接要求用户确认          │
╰─────────────────────────────────────────╯
"""

        return {
            'continue': True,
            'additionalContext': injection_content,
            'systemMessage': system_message_for_planning
        }

    def _generate_task_id(self, task_desc):
        """
        生成任务ID

        格式：任务-{MMDD-HHMMSS}-{描述}

        Args:
            task_desc: 任务描述

        Returns:
            str: 任务ID
        """
        timestamp = datetime.now().strftime('%m%d-%H%M%S')
        max_desc_length = self._get_max_task_desc_length()
        safe_desc = task_desc[:max_desc_length]

        # 移除Windows路径非法字符
        for char in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
            safe_desc = safe_desc.replace(char, '-')

        return u"任务-{}-{}".format(timestamp, safe_desc)

    def _create_task_directory(self, task_id):
        """
        创建任务目录

        Args:
            task_id: 任务ID

        Returns:
            str: 任务目录路径

        Raises:
            Exception: 目录创建失败
        """
        task_dir = os.path.join(self.cwd, 'tasks', task_id)

        try:
            if not os.path.exists(task_dir):
                os.makedirs(task_dir)
                sys.stderr.write(u"[INFO] 任务目录创建成功: {}\n".format(task_dir))
            return task_dir
        except Exception as e:
            sys.stderr.write(u"[ERROR] 创建任务目录失败: {}\n".format(e))
            raise

    def _match_gameplay_pack(self, task_desc):
        """
        玩法包匹配

        Args:
            task_desc: 任务描述

        Returns:
            Optional[dict]: 匹配的玩法包，无匹配返回None
        """
        if not self.knowledge_base or 'gameplay_patterns' not in self.knowledge_base:
            return None

        matched_patterns = []
        for pattern in self.knowledge_base['gameplay_patterns']:
            score = self._calculate_match_score(
                task_desc, pattern.get('keywords', [])
            )
            # v20.3: 降低阈值到10%，提高玩法包匹配召回率
            if score > 0.10:
                matched_patterns.append((pattern, score))

        # 排序并选择最佳匹配
        if matched_patterns:
            matched_patterns.sort(key=lambda x: x[1], reverse=True)
            best_match = matched_patterns[0][0]
            sys.stderr.write(u"[INFO] 玩法包匹配: {} (score: {:.2f})\n".format(
                best_match['name'], matched_patterns[0][1]
            ))
            return best_match

        return None

    def _build_task_meta(self, task_id, task_desc, gameplay_pack, is_bugfix):
        """
        构建task-meta.json结构

        Args:
            task_id: 任务ID
            task_desc: 任务描述
            gameplay_pack: 玩法包（可选）
            is_bugfix: 是否为BUG修复任务

        Returns:
            dict: task-meta.json完整结构
        """
        task_type = "bug_fix" if is_bugfix else "general"

        # v3.0 Final: 动态required_doc_count（根据task_type差异化设置）
        if task_type == "bug_fix":
            required_doc_count = 0  # BUG修复: 无强制文档要求，触发专家审查
        elif gameplay_pack:
            required_doc_count = 2  # 玩法包模式
        else:
            required_doc_count = 3  # 标准功能设计模式

        return {
            # 基础元数据
            "task_id": task_id,
            "task_description": task_desc,
            "task_type": task_type,
            "task_complexity": "standard",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "architecture_version": "v3.0 Final",

            # 运行时状态（v3.0 Final: 语义化4步状态机 - 从planning开始）
            "current_step": "planning",
            "last_injection_step": None,
            "steps": {
                # v3.0 Final: 语义化4步状态机
                "activation": {
                    "description": u"任务激活（自动）",
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "prompt": u"（v3.0 Final: 任务类型识别已自动完成）"
                },
                "planning": {
                    "description": u"方案制定阶段",
                    "status": "in_progress",
                    "started_at": datetime.now().isoformat(),
                    "required_doc_count": required_doc_count,

                    # v22.1新增：专家审查追踪（仅BUG修复任务）
                    "expert_review_required": (task_type == "bug_fix"),
                    "expert_review_completed": False,
                    "expert_review_count": 0,
                    "expert_review_result": None,

                    # v26.0新增：Planning迭代轮次追踪
                    "planning_round": 1,

                    "prompt": (
                        u"直接分析代码，制定修复方案，**启动专家审查子代理**，等待用户确认后进入implementation。"
                        if task_type == "bug_fix"
                        else u"查阅至少{}个相关文档，制定修复/实现方案，等待用户确认后进入implementation。".format(required_doc_count)
                    )
                },
                "implementation": {
                    "description": u"代码实施",
                    "status": "pending",
                    "user_confirmed": False,
                    "prompt": u"基于确认的方案，实施代码修改，测试验证，直到用户确认完成。"
                },
                "finalization": {
                    "description": u"收尾归档",
                    "status": "pending",
                    "prompt": u"清理DEBUG代码，更新文档，归档任务。"
                }
            },

            # 玩法包追踪
            "gameplay_pack_matched": gameplay_pack['id'] if gameplay_pack else None,
            "gameplay_pack_name": gameplay_pack['name'] if gameplay_pack else None,

            # v2.0: 性能指标
            "metrics": {
                "docs_read": [],
                "code_changes": [],
                "tools_used": [],
                "failure_count": 0,
                "expert_review_triggered": False
            },

            # 会话追踪
            "session_started_at": datetime.now().isoformat(),
            "session_ended_at": None,
        }

    def _create_initial_files(self, task_dir, task_id, task_desc):
        """
        创建初始文件

        创建：
        - context.md: 任务上下文
        - solution.md: 解决方案
        - .conversation.jsonl: 会话记录

        Args:
            task_dir: 任务目录
            task_id: 任务ID
            task_desc: 任务描述
        """
        # 创建 context.md
        context_file = os.path.join(task_dir, 'context.md')
        try:
            with open(context_file, 'w', encoding='utf-8') as f:
                f.write(u"# 任务上下文\n\n")
                f.write(u"**任务ID**: {}\n".format(task_id))
                f.write(u"**任务描述**: {}\n\n".format(task_desc))
                f.write(u"## 背景\n\n[待补充]\n\n")
                f.write(u"## 需求分析\n\n[待补充]\n\n")
        except Exception as e:
            sys.stderr.write(u"[WARN] 创建context.md失败: {}\n".format(e))

        # 创建 solution.md
        solution_file = os.path.join(task_dir, 'solution.md')
        try:
            with open(solution_file, 'w', encoding='utf-8') as f:
                f.write(u"# 解决方案\n\n")
                f.write(u"**任务ID**: {}\n".format(task_id))
                f.write(u"**任务描述**: {}\n\n".format(task_desc))
                f.write(u"## 设计方案\n\n[待补充]\n\n")
                f.write(u"## 实现步骤\n\n[待补充]\n\n")
        except Exception as e:
            sys.stderr.write(u"[WARN] 创建solution.md失败: {}\n".format(e))

        # 创建 .conversation.jsonl
        conversation_file = os.path.join(task_dir, '.conversation.jsonl')
        try:
            with open(conversation_file, 'w', encoding='utf-8') as f:
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "role": "system",
                    "content": u"任务创建: {}".format(task_desc),
                    "event_type": "task_created"
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            sys.stderr.write(u"[WARN] 创建.conversation.jsonl失败: {}\n".format(e))

    def _generate_injection_content(
        self, task_id, task_desc, gameplay_pack, is_bugfix
    ):
        """
        生成注入内容（玩法包或通用指南）

        Args:
            task_id: 任务ID
            task_desc: 任务描述
            gameplay_pack: 玩法包（可选）
            is_bugfix: 是否为BUG修复任务

        Returns:
            str: 注入内容（Markdown格式）
        """
        # 任务头部
        project_name = os.path.basename(self.cwd)
        task_type = "bug_fix" if is_bugfix else "general"
        header = self._generate_task_header(task_id, task_type, task_desc, project_name)

        # 玩法包内容或通用指南
        if gameplay_pack:
            content = self._format_gameplay_pack(gameplay_pack)
        elif is_bugfix:
            content = self._format_bugfix_guide(task_desc)
        else:
            content = self._format_fallback_guide()

        return header + content

    # ==================== 任务恢复 ====================

    def resume_existing_task(self, resume_info):
        """
        恢复已有任务

        Args:
            resume_info: 恢复信息字典
                {
                    'is_resume': True,
                    'task_id': str,
                    'task_dir': str,
                    'new_user_input': str
                }

        Returns:
            dict: 恢复结果
        """
        task_id = resume_info['task_id']
        task_dir = resume_info['task_dir']
        new_user_input = resume_info['new_user_input']

        sys.stderr.write(u"[INFO] 进入任务恢复模式: {}\n".format(task_id))

        # 1. 加载任务元数据
        task_meta = self.meta_manager.load_task_meta(task_id)
        if not task_meta:
            return {
                'continue': False,
                'additionalContext': u"❌ 加载任务元数据失败: .task-meta.json不存在或损坏"
            }

        # 2. 更新恢复信息
        task_meta['resumed_at'] = datetime.now().isoformat()
        task_meta['resume_reason'] = new_user_input

        # 保存更新后的元数据
        if not self.meta_manager.save_task_meta(task_id, task_meta):
            sys.stderr.write(u"[WARN] 保存任务元数据失败\n")

        # 3. 绑定任务到当前会话
        if not self.meta_manager.bind_task_to_session(task_id, self.session_id):
            sys.stderr.write(u"[WARN] 绑定任务到会话失败\n")

        sys.stderr.write(u"[INFO] 任务已绑定到会话 {}\n".format(self.session_id[:8] + "..."))

        # 4. 记录恢复事件到 .conversation.jsonl
        conversation_file = os.path.join(task_dir, '.conversation.jsonl')
        try:
            with open(conversation_file, 'a', encoding='utf-8') as f:
                entry = {
                    "timestamp": datetime.now().isoformat(),
                    "role": "system",
                    "content": u"任务恢复: {}".format(new_user_input),
                    "event_type": "task_resume",
                    "new_user_input": new_user_input
                }
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            sys.stderr.write(u"[WARN] 记录会话历史失败: {}\n".format(e))

        # 5. 生成智能恢复提示
        resume_prompt = self._generate_resume_prompt(task_id, task_meta, new_user_input)

        return {
            'continue': True,
            'additionalContext': resume_prompt
        }

    def _detect_resume(self, task_desc):
        """
        检测任务恢复

        Args:
            task_desc: 用户输入

        Returns:
            dict: 恢复信息
                {
                    'is_resume': True/False,
                    'task_id': str,
                    'task_dir': str,
                    'new_user_input': str
                }
        """
        tasks_base_dir = os.path.join(self.cwd, 'tasks')

        # 如果 tasks/ 目录不存在,直接返回
        if not os.path.exists(tasks_base_dir):
            return {"is_resume": False}

        # 获取所有已存在的任务目录名
        try:
            existing_tasks = [d for d in os.listdir(tasks_base_dir)
                             if os.path.isdir(os.path.join(tasks_base_dir, d))
                             and d.startswith(u'任务-')]
        except Exception as e:
            sys.stderr.write(u"[WARN] 读取tasks目录失败: {}\n".format(e))
            return {"is_resume": False}

        if not existing_tasks:
            return {"is_resume": False}

        # 检测用户输入中是否包含任何已存在的任务目录
        for task_id in existing_tasks:
            # 构造多种可能的匹配模式
            patterns = [
                re.escape(task_id),  # 精确匹配任务ID
                re.escape(os.path.join('tasks', task_id).replace('\\', '/')),
                re.escape(os.path.join('tasks', task_id)),
            ]

            # 尝试匹配
            for pattern in patterns:
                match = re.search(pattern, task_desc, re.IGNORECASE)
                if match:
                    task_dir = os.path.join(tasks_base_dir, task_id)

                    # 验证 .task-meta.json 存在
                    meta_path = os.path.join(task_dir, '.task-meta.json')
                    if not os.path.exists(meta_path):
                        sys.stderr.write(u"[WARN] 检测到任务目录但缺少.task-meta.json: {}\n".format(task_dir))
                        continue

                    # 提取新用户输入(去除路径部分)
                    new_user_input = task_desc

                    # 1. 移除 /mc 命令
                    new_user_input = new_user_input.replace('/mc', '').strip()

                    # 2. 移除匹配到的完整路径部分
                    matched_text = match.group(0)
                    new_user_input = new_user_input.replace(matched_text, '').strip()

                    # 3. 清理可能残留的路径前缀/后缀
                    new_user_input = re.sub(r'^[A-Z]:[\\\/].*?tasks[\\\/]', '', new_user_input, flags=re.IGNORECASE).strip()
                    new_user_input = re.sub(r'^\.?\/.*?tasks\/', '', new_user_input).strip()
                    new_user_input = re.sub(r'^tasks[\\\/]', '', new_user_input, flags=re.IGNORECASE).strip()
                    new_user_input = re.sub(r'^[\\\/]+', '', new_user_input).strip()

                    sys.stderr.write(u"[INFO] 检测到任务恢复意图\n")
                    sys.stderr.write(u"  任务ID: {}\n".format(task_id))
                    sys.stderr.write(u"  新用户输入: {}\n".format(new_user_input))

                    return {
                        "is_resume": True,
                        "task_dir": task_dir,
                        "task_id": task_id,
                        "new_user_input": new_user_input
                    }

        return {"is_resume": False}

    def _generate_resume_prompt(self, task_id, task_meta, new_input):
        """
        生成恢复提示

        Args:
            task_id: 任务ID
            task_meta: 任务元数据
            new_input: 新的用户输入

        Returns:
            str: 恢复提示（Markdown格式）
        """
        # 确定任务类型
        task_type = task_meta.get('task_type', 'unknown')
        bug_fix_tracking = task_meta.get('bug_fix_tracking', {})
        feature_tracking = task_meta.get('feature_tracking', {})

        if bug_fix_tracking.get('enabled'):
            task_type_display = u"🐛 BUG修复"
            iterations = bug_fix_tracking.get('iterations', [])
        elif feature_tracking.get('enabled'):
            task_type_display = u"✨ 功能实现"
            iterations = feature_tracking.get('iterations', [])
        else:
            task_type_display = u"📝 通用任务"
            iterations = []

        resume_prompt = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔄 **任务恢复模式已激活**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**任务ID**: {}
**任务类型**: {}
**原始需求**: {}
**当前步骤**: {}
**已完成迭代**: {}次

**新指令**: {}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
            task_id,
            task_type_display,
            task_meta.get('task_description', ''),
            task_meta.get('current_step', 'unknown'),
            len(iterations),
            new_input if new_input else "继续执行"
        )

        return resume_prompt

    # ==================== 辅助方法 ====================

    def _get_task_meta_manager(self):
        """获取TaskMetaManager实例"""
        try:
            from core.task_meta_manager import TaskMetaManager
            return TaskMetaManager(self.cwd)
        except ImportError:
            sys.stderr.write(u"[ERROR] TaskMetaManager不可用\n")
            return None

    def _load_knowledge_base(self):
        """加载玩法知识库"""
        kb_path = os.path.join(self.cwd, '.claude', 'knowledge-base.json')
        try:
            if not os.path.exists(kb_path):
                return None
            with open(kb_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            sys.stderr.write(u"[WARNING] 加载知识库失败: {}\n".format(e))
            return None

    def _calculate_match_score(self, task_desc, keywords):
        """计算关键词匹配分数"""
        task_lower = task_desc.lower()
        matches = 0
        for keyword in keywords:
            if keyword.lower() in task_lower:
                matches += 1

        if len(keywords) == 0:
            return 0.0

        return float(matches) / len(keywords)

    def _is_bugfix_task(self, task_desc):
        """BUG修复任务检测"""
        task_lower = task_desc.lower()

        bugfix_patterns = [
            r'(bug|错误|error|问题|异常|exception)',
            r'(修复|fix|解决|solve)',
            r'(不工作|失败|不生效|没有效果)',
            r'(返回none|返回null|attributeerror)',
        ]

        for pattern in bugfix_patterns:
            if re.search(pattern, task_lower):
                return True
        return False

    def _get_max_task_desc_length(self):
        """获取任务描述最大长度配置"""
        config_path = os.path.join(self.cwd, '.claude', 'task-naming-config.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('max_task_desc_length', 30)
        except Exception as e:
            sys.stderr.write(u"[WARN] 读取task-naming-config.json失败: {}\n".format(e))

        return 30  # 默认值

    def _format_api_info(self, api):
        """格式化API信息"""
        result = u"**{}** ({})\n".format(api['name'], api['type'])

        if 'trigger' in api:
            result += u"  - 触发时机: {}\n".format(api['trigger'])

        if 'purpose' in api:
            result += u"  - 功能: {}\n".format(api['purpose'])

        if 'fields' in api:
            result += u"  - 字段:\n"
            for field_name, field_desc in api['fields'].items():
                result += u"    - `{}`: {}\n".format(field_name, field_desc)

        if 'params' in api:
            result += u"  - 参数:\n"
            for param_name, param_info in api['params'].items():
                param_type = param_info.get('type', '未知')
                result += u"    - `{}` ({})\n".format(param_name, param_type)
                if 'required' in param_info:
                    result += u"      必需字段: {}\n".format(', '.join(param_info['required']))
                if 'example' in param_info:
                    result += u"      示例: `{}`\n".format(json.dumps(param_info['example'], ensure_ascii=False))

        if 'common_pitfall' in api:
            result += u"  - ⚠️ 常见陷阱: {}\n".format(api['common_pitfall'])

        return result

    def _format_gameplay_pack(self, pattern):
        """格式化玩法包为可读文本"""
        impl_guide = pattern.get('implementation_guide', {})

        # 1. 头部信息
        result = u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 玩法包已加载: {}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**分类**: {} | **难度**: {} | **预计时间**: {}

🎮 **实现原理**:
{}

""".format(
            pattern['name'],
            pattern.get('category', '未分类'),
            pattern.get('difficulty', '未知'),
            pattern.get('estimated_time', '未知'),
            impl_guide.get('principle', '待补充')
        )

        # 2. 完整代码
        code_info = impl_guide.get('complete_code', {})
        if code_info:
            result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 完整代码实现 (可直接使用或修改)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**文件路径**: {}

```python
{}
```

""".format(
                code_info.get('file', 'unknown.py'),
                code_info.get('content', '# 代码缺失')
            )

        # 3. 配置指南
        config_guide = impl_guide.get('config_guide', {})
        if config_guide:
            result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ 配置说明
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{}

**示例配置**:
```python
{}
```

**字段说明**:
""".format(
                config_guide.get('description', ''),
                json.dumps(config_guide.get('example', {}), indent=4, ensure_ascii=False)
            )

            for field_name, field_desc in config_guide.get('fields', {}).items():
                result += u"- `{}`: {}\n".format(field_name, field_desc)

            result += u"\n"

        # 4. MODSDK API 清单
        modsdk_apis = impl_guide.get('modsdk_apis', [])
        if modsdk_apis:
            result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 所需 MODSDK API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            for idx, api in enumerate(modsdk_apis, 1):
                result += u"{}. {}\n".format(idx, self._format_api_info(api))

        # 5. 常见问题
        common_issues = impl_guide.get('common_issues', [])
        if common_issues:
            result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐛 常见问题与解决方案
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            for idx, issue in enumerate(common_issues, 1):
                result += u"""**问题 {}**: {}
**原因**: {}
**解决**: {}

""".format(
                    idx,
                    issue.get('problem', '未知'),
                    issue.get('cause', '未知'),
                    issue.get('solution', '未知')
                )

        # 6. 相关玩法
        related = impl_guide.get('related_gameplay', [])
        if related:
            result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 相关玩法扩展
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            for r in related:
                result += u"- **{}**: {}\n".format(r['name'], r.get('similarity', ''))
                if 'extension' in r:
                    result += u"  扩展思路: {}\n".format(r['extension'])

            result += u"\n"

        # 7. 底部提示
        result += u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ AI 使用指南
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 上述代码可以直接使用或根据需求修改
2. Hook会自动检查CRITICAL规范,无需担心违规
3. 如遇到错误,Hook会自动推送精确的修复方案
4. 无需再查阅大量文档,专注于实现业务逻辑

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

        return result

    def _format_fallback_guide(self):
        """降级方案:未匹配到玩法包时的通用指南"""
        return u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️ 未匹配到玩法包
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

当前任务未匹配到预定义的玩法包。

**建议做法**:
1. 分析任务需求，确定需要使用的MODSDK API
2. 查阅项目中的类似实现代码
3. 编写代码时注意遵守CRITICAL规范
4. Hook会在违规时自动阻断并提供修复建议

**重要提醒**:
- 无需提前阅读大量规范文档
- Hook会在编码时进行实时检查
- 遇到错误时会自动推送解决方案

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _format_bugfix_guide(self, task_desc):
        """v22.1: BUG修复流程指引（强制专家审查）"""
        guidance = u"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        guidance += u"🐛 BUG修复工作流 v22.1（强制专家审查）\n"
        guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

        guidance += u"**当前阶段**: Planning（方案制定）\n"
        guidance += u"**核心策略**: 代码分析 → 方案制定 → **强制专家审查** → 用户确认 → Implementation\n\n"

        guidance += u"### 第1步：代码分析定位BUG\n\n"
        guidance += u"**推荐流程**:\n"
        guidance += u"1. 使用 Grep/Glob 定位相关代码文件\n"
        guidance += u"2. 使用 Read 阅读关键代码逻辑\n"
        guidance += u"3. 分析根本原因（而非表象）\n"
        guidance += u"4. 制定修复方案（明确要修改的文件和逻辑）\n\n"

        guidance += u"**可选**：如果代码逻辑不清楚，可以查阅项目文档理解设计意图\n\n"

        guidance += u"### 第2步：启动专家审查子代理（强制性要求）⚠️\n\n"
        guidance += u"**CRITICAL - 必须立即执行，不可跳过**:\n\n"
        guidance += u"BUG修复任务**必须**通过专家审查才能进入Implementation阶段。\n\n"
        guidance += u"❌ **绝对禁止**:\n"
        guidance += u"- 在启动Task工具之前向用户展示方案\n"
        guidance += u"- 在启动Task工具之前请求用户确认\n"
        guidance += u"- 跳过专家审查直接进入下一步\n\n"
        guidance += u"✅ **正确流程**:\n"
        guidance += u"1. 分析代码并制定修复方案\n"
        guidance += u"2. **立即启动Task工具**进行专家审查\n"
        guidance += u"3. 等待审查结果并根据建议调整方案\n"
        guidance += u"4. 然后才能向用户展示最终方案\n\n"
        guidance += u"**立即执行以下Task工具调用**（制定方案后的第一件事）：\n\n"
        guidance += u"```python\n"
        guidance += u"Task(\n"
        guidance += u"  subagent_type=\"general-purpose\",\n"
        guidance += u"  description=\"BUG修复方案专家审查\",\n"
        guidance += u"  prompt=\"\"\"\n"
        guidance += u"请审查以下BUG修复方案：\n\n"
        guidance += u"**BUG描述**: {}\n\n"
        guidance += u"**我的分析**:\n"
        guidance += u"[在这里粘贴你的根因分析]\n\n"
        guidance += u"**修复方案**:\n"
        guidance += u"[在这里粘贴你的修复方案]\n\n"
        guidance += u"**请审查以下CRITICAL要点**:\n"
        guidance += u"1. 根因分析是否准确（是否只解决表象而非根因）\n"
        guidance += u"2. 修复方案是否会引入新问题\n"
        guidance += u"3. 是否考虑了边界情况和异常处理\n"
        guidance += u"4. 是否有更优雅的解决方案\n\n"
        guidance += u"请在回复末尾输出审查结果标记：\n"
        guidance += u"<!-- SUBAGENT_RESULT {{\"approved\": true/false, \"issues\": [\"问题1\", \"问题2\"], \"suggestions\": [\"建议1\", \"建议2\"]}} -->\n"
        guidance += u"\"\"\"\n"
        guidance += u")\n"
        guidance += u"```\n\n".format(task_desc)
        guidance += u"**审查完成后**：\n"
        guidance += u"- 如果审查通过，向用户展示最终方案并等待确认\n"
        guidance += u"- 如果审查发现问题，根据建议调整方案后重新展示\n\n"

        guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        guidance += u"⚠️ 重要提醒\n"
        guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        guidance += u"1. **无需强制查阅文档**：required_doc_count=0\n"
        guidance += u"2. **禁止直接修改代码**：Planning阶段只能分析和制定方案\n"
        guidance += u"3. **强制专家审查**：未完成专家审查无法进入Implementation阶段\n\n"

        guidance += u"**立即开始**: 使用代码分析工具定位BUG根本原因\n"
        guidance += u"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"

        return guidance

    def _generate_task_header(self, task_id, task_type, task_desc, project_name):
        """生成任务头部信息"""
        task_type_map = {
            "bug_fix": u"🐛 BUG修复",
            "feature_implementation": u"✨ 功能实现",
            "general": u"📝 通用任务"
        }

        task_type_display = task_type_map.get(task_type, u"📝 通用任务")

        return u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 任务信息
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**项目**: {}
**任务ID**: {}
**任务类型**: {}
**任务描述**: {}
**创建时间**: {}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(
            project_name,
            task_id,
            task_type_display,
            task_desc,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )

    def _generate_missing_desc_prompt(self):
        """生成缺少任务描述的提示"""
        return u"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❌ 缺少任务描述
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**用法**: `/mc <任务描述>`

**示例**:
- `/mc 修复玩家死亡复活丢失装备的BUG`
- `/mc 实现金币系统`
- `/mc 任务-1116-201326 继续修改`（恢复已有任务）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

    def _generate_dir_creation_error(self, task_id, error_msg):
        """生成目录创建失败错误提示"""
        return u"""
❌ 任务初始化失败

**问题**: 无法创建任务目录

**任务ID**: {}
**错误**: {}

**可能原因**:
1. 路径包含无效字符（中文路径编码问题）
2. 磁盘权限不足
3. 磁盘空间不足
4. 父目录不存在

**建议**:
1. 检查 tasks/ 目录是否存在且可写
2. 检查磁盘空间
3. 如果是 Windows 系统，确认路径不包含特殊字符

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""".format(task_id, error_msg)


# ==================== 导出符号 ====================

__all__ = [
    'TaskInitializer'
]
