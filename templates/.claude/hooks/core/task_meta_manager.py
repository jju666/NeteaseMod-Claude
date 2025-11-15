"""
Task Meta Manager - 任务元数据管理器 (v21.0 架构重构)

核心变更:
- task-meta.json: 唯一数据源（存储完整任务状态）
- 删除 workflow-state.json 及其所有逻辑
- 增强文件锁机制（避免并发冲突）
- 实现重试逻辑（最多3次，延迟100ms）
- 保持原子写入（临时文件+重命名）

v21.0 架构原则:
1. 每个任务的 task-meta.json 是其唯一数据源
2. 所有运行时状态直接存储在 task-meta.json 中
3. 简化恢复逻辑（无需兼容旧格式）
4. 提升数据一致性（单一真相源）
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Optional, Dict, Callable

# 跨平台文件锁支持
try:
    import portalocker
    HAS_PORTALOCKER = True
except ImportError:
    HAS_PORTALOCKER = False
    sys.stderr.write("[TaskMetaManager] 警告: 未安装 portalocker，文件锁功能降级\n")


class TaskMetaManager:
    """任务元数据管理器 - v21.0 单一数据源架构"""

    # 配置常量
    MAX_RETRIES = 3
    RETRY_DELAY = 0.1  # 100ms
    ARCHITECTURE_VERSION = "v21.0"

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

        Args:
            task_id: 任务ID
            update_func: 更新函数，接收当前task_meta，返回更新后的task_meta

        Returns:
            更新后的task_meta，如果失败则返回None
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                # 1. 加载当前状态
                task_meta = self.load_task_meta(task_id)
                if not task_meta:
                    sys.stderr.write(f"[TaskMetaManager] 原子更新失败: 任务元数据不存在 ({task_id})\n")
                    return None

                # 2. 执行更新函数
                updated_meta = update_func(task_meta)

                # 3. 保存更新后的状态
                if self.save_task_meta(task_id, updated_meta):
                    return updated_meta
                else:
                    raise Exception("保存失败")

            except Exception as e:
                if attempt < self.MAX_RETRIES - 1:
                    sys.stderr.write(f"[TaskMetaManager] 原子更新失败(尝试{attempt+1}/{self.MAX_RETRIES}): {e}, 重试中...\n")
                    time.sleep(self.RETRY_DELAY)
                else:
                    sys.stderr.write(f"[TaskMetaManager] 原子更新失败(已达最大重试次数): {e}\n")
                    return None

        return None

    # ============== 活跃任务管理 ==============

    def get_active_task_id(self) -> Optional[str]:
        """
        获取当前活跃任务ID

        Returns:
            活跃任务ID，如果没有活跃任务则返回None
        """
        if not os.path.exists(self.active_flag_path):
            return None

        active_data = self._load_json(self.active_flag_path)
        if not active_data:
            return None

        return active_data.get('task_id')

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
        """保存JSON文件（原子写入 + 文件锁）"""
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


# ============== 兼容性API（可选） ==============

def migrate_from_v20(task_meta: Dict) -> Dict:
    """
    从 v20.x 格式迁移到 v21.0

    v20.3.2 → v21.0 迁移规则:
    1. 删除 workflow_state_ref（不再使用引用指针）
    2. 删除 archived_snapshot（不再需要快照）
    3. 保留所有运行时状态字段（current_step, steps, bug_fix_tracking等）

    Args:
        task_meta: v20.x 格式的元数据

    Returns:
        v21.0 格式的元数据
    """
    migrated = dict(task_meta)

    # 删除 v20.3.2 特有字段
    migrated.pop('workflow_state_ref', None)
    migrated.pop('archived_snapshot', None)
    migrated.pop('archived', None)
    migrated.pop('archived_at', None)

    # 更新版本号
    migrated['architecture_version'] = 'v21.0'
    migrated['migrated_at'] = datetime.now().isoformat()
    migrated['migrated_from'] = task_meta.get('architecture_version', 'unknown')

    return migrated
