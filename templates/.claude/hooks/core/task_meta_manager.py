"""
Task Meta Manager - 任务元数据管理器 (v2.0 架构重构)

核心变更:
- task-meta.json: 唯一数据源（存储完整任务状态）
- 删除 workflow-state.json 及其所有逻辑
- 增强文件锁机制（避免并发冲突）
- 实现重试逻辑（最多3次，延迟100ms）
- 保持原子写入（临时文件+重命名）

v2.0 架构原则:
1. 每个任务的 task-meta.json 是其唯一数据源
2. 所有运行时状态直接存储在 task-meta.json 中
3. 简化恢复逻辑（无需兼容旧格式）
4. 提升数据一致性（单一真相源）
"""

import os
import sys
import json
import time
import shutil
from datetime import datetime
from typing import Optional, Dict, Callable

# 跨平台文件锁支持
try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False
    # 🔥 v25.0修复：禁用警告输出，避免干扰 Hook 的 JSON 输出
    # 在 Windows 上，stderr 可能混入 stdout，导致 Claude Code 无法解析 JSON
    # sys.stderr.write("[TaskMetaManager] 警告: 未安装 portalocker，文件锁功能降级\n")
    pass  # 静默运行


class TaskMetaManager:
    """任务元数据管理器 - v3.0 Final 语义化架构"""

    # 配置常量
    MAX_RETRIES = 3
    RETRY_DELAY = 0.1  # 100ms
    ARCHITECTURE_VERSION = "v3.0 Final"

    def __init__(self, cwd: Optional[str] = None):
        """
        初始化任务元数据管理器

        Args:
            cwd: 工作目录路径（默认为当前目录）
        """
        self.cwd = cwd or os.getcwd()
        self.tasks_dir = os.path.join(self.cwd, 'tasks')
        self.active_flag_path = os.path.join(self.cwd, '.claude', '.task-active.json')

    # ============== 核心API ==============

    def load_task_meta(self, task_id: str) -> Optional[Dict]:
        """
        加载任务元数据（带重试机制）

        Args:
            task_id: 任务ID

        Returns:
            任务元数据字典，如果不存在则返回None
        """
        meta_path = self._get_meta_path(task_id)

        for attempt in range(self.MAX_RETRIES):
            try:
                task_meta = self._load_json_with_lock(meta_path)
                if task_meta:
                    return task_meta
                return None
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    sys.stderr.write(f"[TaskMetaManager] 加载失败(尝试{attempt+1}/{self.MAX_RETRIES}): {e}, 重试中...\n")
                    time.sleep(self.RETRY_DELAY)
                else:
                    sys.stderr.write(f"[TaskMetaManager] 加载失败(已达最大重试次数): {e}\n")
                    return None

        return None

    def save_task_meta(self, task_id: str, task_meta: Dict) -> bool:
        """
        保存任务元数据（带重试和原子写入）

        Args:
            task_id: 任务ID
            task_meta: 任务元数据字典

        Returns:
            是否保存成功
        """
        meta_path = self._get_meta_path(task_id)

        # 更新元数据
        task_meta['updated_at'] = datetime.now().isoformat()
        task_meta['architecture_version'] = self.ARCHITECTURE_VERSION

        for attempt in range(self.MAX_RETRIES):
            try:
                self._save_json_with_lock(meta_path, task_meta)
                return True
            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    sys.stderr.write(f"[TaskMetaManager] 保存失败(尝试{attempt+1}/{self.MAX_RETRIES}): {e}, 重试中...\n")
                    time.sleep(self.RETRY_DELAY)
                else:
                    sys.stderr.write(f"[TaskMetaManager] 保存失败(已达最大重试次数): {e}\n")
                    return False

        return False

    def atomic_update(self, task_id: str, update_func: Callable[[Dict], Dict]) -> Optional[Dict]:
        """
        原子更新任务元数据（读取-修改-保存）

        v3.2修复（正确的portalocker API使用）:
        - 使用lockfile保护整个读-改-写过程
        - 使用LOCK_NB非阻塞模式 + 手动重试（portalocker.lock不支持timeout参数）
        - 增加重试次数到10次
        - 指数退避（50ms → 100ms → 200ms → ...）

        Args:
            task_id: 任务ID
            update_func: 更新函数，接收当前task_meta，返回更新后的task_meta

        Returns:
            更新后的task_meta，如果失败则返回None
        """
        meta_path = self._get_meta_path(task_id)
        lock_path = meta_path + '.lock'

        max_retries = 10
        base_delay = 0.05  # 50ms

        for attempt in range(max_retries):
            lock_file = None
            try:
                # 🔒 获取全局锁（非阻塞模式 + 手动重试）
                lock_file = open(lock_path, 'w')
                if HAS_PORTALOCKER:
                    # ✅ 正确的API：使用LOCK_NB非阻塞模式，无timeout参数
                    # 如果锁被占用，会立即抛出LockException
                    portalocker.lock(lock_file, portalocker.LOCK_EX | portalocker.LOCK_NB)

                # 1. 读取（持有锁）
                task_meta = self.load_task_meta(task_id)
                if not task_meta:
                    sys.stderr.write(f"[TaskMetaManager] 原子更新失败: 任务元数据不存在 ({task_id})\n")
                    return None

                # 2. 修改（持有锁）
                updated_meta = update_func(task_meta)

                # 3. 写入（持有锁）
                if self.save_task_meta(task_id, updated_meta):
                    return updated_meta
                else:
                    raise Exception("保存失败")

            except Exception as e:
                # 计算指数退避延迟
                delay = min(base_delay * (2 ** attempt), 2.0)  # 最大2秒

                # 判断是否是锁冲突错误（portalocker.LockException）
                is_lock_conflict = (HAS_PORTALOCKER and
                                    hasattr(portalocker, 'exceptions') and
                                    isinstance(e, portalocker.exceptions.LockException))

                if is_lock_conflict:
                    # 锁被占用，等待后重试
                    if attempt < max_retries - 1:
                        sys.stderr.write(f"[TaskMetaManager] 🔒 锁冲突(尝试{attempt+1}/{max_retries}), 等待{delay*1000:.0f}ms后重试\n")
                        time.sleep(delay)
                        continue
                    else:
                        sys.stderr.write(f"[TaskMetaManager] 🔒 锁冲突超时(已达最大重试次数{max_retries})\n")
                        return None
                else:
                    # 其他错误
                    if attempt < max_retries - 1:
                        sys.stderr.write(f"[TaskMetaManager] 原子更新失败(尝试{attempt+1}/{max_retries}): {e}, 等待{delay*1000:.0f}ms后重试\n")
                        time.sleep(delay)
                        continue
                    else:
                        sys.stderr.write(f"[TaskMetaManager] 原子更新失败(已达最大重试次数): {e}\n")
                        return None

            finally:
                # 释放锁并清理lockfile
                if lock_file:
                    try:
                        if HAS_PORTALOCKER:
                            portalocker.unlock(lock_file)
                        lock_file.close()
                        # 清理lockfile
                        if os.path.exists(lock_path):
                            os.remove(lock_path)
                    except Exception as cleanup_err:
                        # 清理失败不影响主流程
                        sys.stderr.write(f"[TaskMetaManager] lockfile清理失败: {cleanup_err}\n")

        return None

    # ============== 活跃任务管理 ==============

    def get_active_task_id(self) -> Optional[str]:
        """
        获取当前活跃任务ID（v3.0兼容方法，已弃用）

        注意: v3.1推荐使用 get_active_task_by_session()

        Returns:
            活跃任务ID，如果没有活跃任务则返回None
        """
        if not os.path.exists(self.active_flag_path):
            return None

        active_data = self._load_json(self.active_flag_path)
        if not active_data:
            return None

        return active_data.get('task_id')

    # ============== v3.1: 会话绑定管理 ==============

    def get_active_task_by_session(self, session_id: str) -> Optional[Dict]:
        """
        根据session_id获取绑定的任务（v3.1核心方法）

        Args:
            session_id: 会话ID（从Hook输入获取）

        Returns:
            {
                "task_id": "任务-1116-161424-修复xxx",
                "task_dir": "tasks/...",
                "current_step": "implementation",
                "bound_at": "2025-11-16T10:00:00",
                "session_history": ["session_abc123"]
            }
            如果无绑定则返回None
        """
        if not os.path.exists(self.active_flag_path):
            return None

        active_data = self._load_json(self.active_flag_path)
        if not active_data:
            return None

        # 检查是否是v3.1格式（有active_tasks字段）
        if 'active_tasks' not in active_data:
            # 旧格式（v3.0），降级处理：返回全局任务
            sys.stderr.write("[TaskMetaManager] 检测到旧格式.task-active.json，建议升级到v3.1\n")
            task_id = active_data.get('task_id')
            if task_id:
                return {
                    "task_id": task_id,
                    "task_dir": active_data.get('task_dir', self.get_task_dir(task_id)),
                    "current_step": active_data.get('current_step', 'implementation'),
                    "bound_at": active_data.get('updated_at', datetime.now().isoformat()),
                    "session_history": []
                }
            return None

        # v3.1新格式：查找session_id的绑定
        active_tasks = active_data.get('active_tasks', {})

        # 直接查找session_id
        if session_id in active_tasks:
            return active_tasks[session_id]

        # 检查是否在session_history中（支持压缩后恢复）
        for sid, binding in active_tasks.items():
            if session_id in binding.get('session_history', []):
                # 找到了，更新绑定到新session_id
                sys.stderr.write(f"[TaskMetaManager] 检测到会话继承链，自动绑定到新session: {session_id}\n")
                self.add_session_to_history(sid, session_id)
                return binding

        return None

    def bind_task_to_session(self, task_id: str, session_id: str) -> bool:
        """
        绑定任务到会话（v3.1核心方法）

        Args:
            task_id: 任务ID
            session_id: 会话ID

        Returns:
            是否绑定成功

        行为:
        - 如果session_id已有绑定，覆盖旧绑定
        - 更新 .task-active.json
        - 初始化session_history为[session_id]
        """
        # 加载当前绑定
        active_data = self._load_json(self.active_flag_path) or {}

        # 检查并升级到v3.1格式
        if 'active_tasks' not in active_data:
            # 旧格式，升级为v3.1
            sys.stderr.write("[TaskMetaManager] 自动升级.task-active.json到v3.1格式\n")
            active_data = {
                "version": "v3.1",
                "active_tasks": {}
            }

        # 获取任务元数据
        task_meta = self.load_task_meta(task_id)
        if not task_meta:
            sys.stderr.write(f"[TaskMetaManager] 绑定失败: 任务元数据不存在 ({task_id})\n")
            return False

        # 创建绑定信息
        binding = {
            "task_id": task_id,
            "task_dir": self.get_task_dir(task_id),
            "current_step": task_meta.get('current_step', 'planning'),
            "bound_at": datetime.now().isoformat(),
            "session_history": [session_id]
        }

        # 如果session_id已有绑定，检查是否需要切换任务
        if session_id in active_data['active_tasks']:
            old_task_id = active_data['active_tasks'][session_id]['task_id']
            if old_task_id != task_id:
                sys.stderr.write(f"[TaskMetaManager] 会话 {session_id[:8]}... 从任务 {old_task_id[:20]}... 切换到 {task_id[:20]}...\n")

        # 更新绑定
        active_data['active_tasks'][session_id] = binding

        # 保存
        try:
            self._save_json(self.active_flag_path, active_data)
            sys.stderr.write(f"[TaskMetaManager] ✅ 任务已绑定到会话 {session_id[:8]}... → {task_id[:30]}...\n")
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 绑定失败: {e}\n")
            return False

    def unbind_task_from_session(self, session_id: str) -> bool:
        """
        解除会话绑定（用于 /mc cancel）

        Args:
            session_id: 会话ID

        Returns:
            是否解除成功

        行为:
        - 从 .task-active.json 中删除session_id对应的条目
        - 如果是最后一个绑定，保留文件但清空active_tasks
        """
        if not os.path.exists(self.active_flag_path):
            return True  # 文件不存在，视为已解除

        active_data = self._load_json(self.active_flag_path)
        if not active_data or 'active_tasks' not in active_data:
            return True

        # 删除session_id对应的绑定
        if session_id in active_data['active_tasks']:
            task_id = active_data['active_tasks'][session_id]['task_id']
            del active_data['active_tasks'][session_id]
            sys.stderr.write(f"[TaskMetaManager] ✅ 已解除会话 {session_id[:8]}... 的任务绑定 ({task_id[:30]}...)\n")
        else:
            sys.stderr.write(f"[TaskMetaManager] 会话 {session_id[:8]}... 没有绑定任务\n")

        # 保存
        try:
            self._save_json(self.active_flag_path, active_data)
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 解除绑定失败: {e}\n")
            return False

    def add_session_to_history(self, old_session_id: str, new_session_id: str) -> bool:
        """
        添加新session到继承链（用于压缩后恢复）

        Args:
            old_session_id: 当前会话ID（压缩前）
            new_session_id: 新会话ID（压缩后）

        Returns:
            是否添加成功

        行为:
        - 读取old_session_id的绑定信息
        - 将new_session_id添加到session_history
        - 创建new_session_id的绑定（复制task_id和current_step）
        - 删除old_session_id的绑定（节省空间）
        """
        if not os.path.exists(self.active_flag_path):
            return False

        active_data = self._load_json(self.active_flag_path)
        if not active_data or 'active_tasks' not in active_data:
            return False

        # 查找旧session的绑定
        if old_session_id not in active_data['active_tasks']:
            sys.stderr.write(f"[TaskMetaManager] 会话继承失败: 旧会话 {old_session_id[:8]}... 不存在\n")
            return False

        old_binding = active_data['active_tasks'][old_session_id]

        # 创建新session的绑定（复制task_id和current_step）
        new_binding = {
            "task_id": old_binding['task_id'],
            "task_dir": old_binding['task_dir'],
            "current_step": old_binding['current_step'],
            "bound_at": datetime.now().isoformat(),
            "session_history": old_binding.get('session_history', []) + [new_session_id]
        }

        # 添加新绑定
        active_data['active_tasks'][new_session_id] = new_binding

        # 删除旧绑定（可选，节省空间）
        del active_data['active_tasks'][old_session_id]

        # 保存
        try:
            self._save_json(self.active_flag_path, active_data)
            sys.stderr.write(f"[TaskMetaManager] ✅ 会话继承成功: {old_session_id[:8]}... → {new_session_id[:8]}...\n")
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 会话继承失败: {e}\n")
            return False

    def fuzzy_match_task_by_timestamp(self, timestamp: str) -> Optional[str]:
        """
        根据时间戳模糊匹配任务ID（v3.1新增）

        Args:
            timestamp: 时间戳字符串（如 "161424" 或 "1116-161424"）

        Returns:
            匹配的任务ID，如果无匹配或多个匹配则返回最近修改的

        逻辑:
        1. 扫描 tasks/ 目录
        2. 查找所有包含timestamp的任务目录
        3. 如果唯一匹配 → 返回task_id
        4. 如果多个匹配 → 返回最近修改的task_id
        5. 如果无匹配 → 返回None
        """
        if not os.path.exists(self.tasks_dir):
            return None

        # 扫描所有任务目录
        matching_tasks = []
        try:
            for task_dir_name in os.listdir(self.tasks_dir):
                task_path = os.path.join(self.tasks_dir, task_dir_name)

                # 检查是否是目录且包含时间戳
                if os.path.isdir(task_path) and timestamp in task_dir_name:
                    # 验证.task-meta.json存在
                    meta_path = os.path.join(task_path, '.task-meta.json')
                    if os.path.exists(meta_path):
                        mtime = os.path.getmtime(task_path)
                        matching_tasks.append((task_dir_name, mtime))

        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 时间戳模糊匹配失败: {e}\n")
            return None

        if len(matching_tasks) == 0:
            return None
        elif len(matching_tasks) == 1:
            sys.stderr.write(f"[TaskMetaManager] ✅ 时间戳 '{timestamp}' 唯一匹配: {matching_tasks[0][0][:40]}...\n")
            return matching_tasks[0][0]
        else:
            # 多个匹配，返回最近修改的
            matching_tasks.sort(key=lambda x: x[1], reverse=True)
            selected = matching_tasks[0][0]
            sys.stderr.write(f"[TaskMetaManager] ⚠️ 时间戳 '{timestamp}' 匹配到{len(matching_tasks)}个任务，选择最近修改的: {selected[:40]}...\n")
            return selected

    def list_all_active_sessions(self) -> list:
        """
        列出所有活跃会话及其绑定任务（v3.1新增）

        Returns:
            [
                {
                    "session_id": "abc123",
                    "task_id": "任务-1116-161424-修复xxx",
                    "current_step": "implementation"
                },
                ...
            ]
        """
        if not os.path.exists(self.active_flag_path):
            return []

        active_data = self._load_json(self.active_flag_path)
        if not active_data:
            return []

        # 检查格式
        if 'active_tasks' not in active_data:
            # 旧格式，返回单个任务
            task_id = active_data.get('task_id')
            if task_id:
                return [{
                    "session_id": "legacy",
                    "task_id": task_id,
                    "current_step": active_data.get('current_step', 'unknown')
                }]
            return []

        # v3.1格式
        result = []
        for session_id, binding in active_data.get('active_tasks', {}).items():
            result.append({
                "session_id": session_id,
                "task_id": binding.get('task_id'),
                "current_step": binding.get('current_step')
            })

        return result

    def set_active_task(self, task_id: str, current_step: Optional[str] = None) -> bool:
        """
        设置活跃任务

        Args:
            task_id: 任务ID
            current_step: 当前步骤（可选）

        Returns:
            是否设置成功
        """
        active_data = {
            'task_id': task_id,
            'task_dir': os.path.join(self.tasks_dir, task_id),
            'current_step': current_step,
            'updated_at': datetime.now().isoformat()
        }

        try:
            self._save_json(self.active_flag_path, active_data)
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 设置活跃任务失败: {e}\n")
            return False

    def clear_active_task(self) -> bool:
        """
        清除活跃任务标记

        Returns:
            是否清除成功
        """
        try:
            if os.path.exists(self.active_flag_path):
                os.remove(self.active_flag_path)
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 清除活跃任务失败: {e}\n")
            return False

    # ============== 任务目录管理 ==============

    def get_task_dir(self, task_id: str) -> str:
        """获取任务目录路径"""
        return os.path.join(self.tasks_dir, task_id)

    def create_task_directory(self, task_id: str) -> bool:
        """
        创建任务目录

        Args:
            task_id: 任务ID

        Returns:
            是否创建成功
        """
        task_dir = self.get_task_dir(task_id)
        try:
            os.makedirs(task_dir, exist_ok=True)
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 创建任务目录失败: {e}\n")
            return False

    # ============== 子代理锁管理 ==============

    def check_subagent_lock(self, task_id: str) -> bool:
        """
        检查收尾子代理锁文件是否存在

        Args:
            task_id: 任务ID

        Returns:
            True表示在子代理上下文中
        """
        task_dir = self.get_task_dir(task_id)
        lock_file = os.path.join(task_dir, '.cleanup-subagent.lock')
        return os.path.exists(lock_file)

    def create_subagent_lock(self, task_id: str) -> bool:
        """
        创建收尾子代理锁文件

        Args:
            task_id: 任务ID

        Returns:
            是否创建成功
        """
        task_dir = self.get_task_dir(task_id)
        lock_file = os.path.join(task_dir, '.cleanup-subagent.lock')

        try:
            with open(lock_file, 'w', encoding='utf-8') as f:
                f.write(f"locked_at: {datetime.now().isoformat()}\n")
                f.write(f"pid: {os.getpid()}\n")
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 创建子代理锁失败: {e}\n")
            return False

    def remove_subagent_lock(self, task_id: str) -> bool:
        """
        删除收尾子代理锁文件

        Args:
            task_id: 任务ID

        Returns:
            是否删除成功
        """
        task_dir = self.get_task_dir(task_id)
        lock_file = os.path.join(task_dir, '.cleanup-subagent.lock')

        try:
            if os.path.exists(lock_file):
                os.remove(lock_file)
            return True
        except Exception as e:
            sys.stderr.write(f"[TaskMetaManager] 删除子代理锁失败: {e}\n")
            return False

    # ============== 私有方法 ==============

    def _get_meta_path(self, task_id: str) -> str:
        """获取task-meta.json路径"""
        return os.path.join(self.tasks_dir, task_id, '.task-meta.json')

    def _load_json(self, file_path: str) -> Optional[Dict]:
        """加载JSON文件（无锁）"""
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            sys.stderr.write(f"[TaskMetaManager] 加载失败 {file_path}: {e}\n")
            return None

    def _load_json_with_lock(self, file_path: str) -> Optional[Dict]:
        """加载JSON文件（带文件锁）"""
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 尝试加锁（共享锁，允许多个读取者）
                if HAS_PORTALOCKER:
                    portalocker.lock(f, portalocker.LOCK_SH)

                data = json.load(f)

                if HAS_PORTALOCKER:
                    portalocker.unlock(f)

                return data
        except (json.JSONDecodeError, IOError) as e:
            sys.stderr.write(f"[TaskMetaManager] 加载失败 {file_path}: {e}\n")
            return None

    def _save_json(self, file_path: str, data: Dict):
        """保存JSON文件（原子写入，无锁）"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 原子写入：先写临时文件，再重命名
            temp_path = file_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

            # Windows下需要先删除目标文件
            if os.path.exists(file_path):
                os.remove(file_path)

            os.rename(temp_path, file_path)

        except (IOError, OSError) as e:
            sys.stderr.write(f"[TaskMetaManager] 保存失败 {file_path}: {e}\n")
            # 清理临时文件
            temp_path = file_path + '.tmp'
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise

    def _save_json_with_lock(self, file_path: str, data: Dict):
        """
        保存JSON文件（原子写入 + 文件锁）

        v3.1增强（Windows兼容性修复）:
        - 使用shutil.move代替os.rename（更可靠）
        - 改进错误处理（捕获PermissionError）
        - 添加详细错误日志
        """
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # 原子写入：先写临时文件，再重命名
            temp_path = file_path + '.tmp'

            # 使用独占锁写入临时文件
            with open(temp_path, 'w', encoding='utf-8') as f:
                if HAS_PORTALOCKER:
                    portalocker.lock(f, portalocker.LOCK_EX)

                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())

                if HAS_PORTALOCKER:
                    portalocker.unlock(f)

            # ✅ Windows兼容性改进：使用shutil.move代替os.remove + os.rename
            # shutil.move会自动处理跨平台差异
            if os.path.exists(file_path):
                # Windows下先尝试删除（如果被锁定会失败）
                try:
                    os.remove(file_path)
                except PermissionError as pe:
                    # 文件被锁定，记录详细错误
                    sys.stderr.write(f"[TaskMetaManager] ⚠️ 文件被锁定，无法删除: {file_path}\n")
                    sys.stderr.write(f"  错误详情: {pe}\n")
                    raise

            # 使用shutil.move（更可靠，跨平台兼容性更好）
            shutil.move(temp_path, file_path)

        except (IOError, OSError, PermissionError) as e:
            sys.stderr.write(f"[TaskMetaManager] 保存失败 {file_path}: {type(e).__name__}: {e}\n")

            # 清理临时文件
            temp_path = file_path + '.tmp'
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as cleanup_err:
                    sys.stderr.write(f"[TaskMetaManager] 临时文件清理失败: {cleanup_err}\n")
            raise
