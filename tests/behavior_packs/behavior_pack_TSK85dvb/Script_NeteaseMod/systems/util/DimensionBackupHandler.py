# -*- coding: utf-8 -*-
"""
DimensionBackupHandler - 地图备份还原管理器

功能:
- 管理DimensionBackup实例
- 提供简化的备份/还原接口
- 跟踪备份状态

原文件: Parts/ECStage/DimensionBackupHandler.py
重构为: systems/util/DimensionBackupHandler.py
"""

from .DimensionBackup import DimensionBackup


class DimensionBackupHandler(object):
    """
    地图备份还原管理器

    封装DimensionBackup,提供简化接口
    """

    def __init__(self, room_system, dimension):
        """
        初始化备份管理器

        Args:
            room_system: RoomManagementSystem实例
            dimension (int): 维度ID
        """
        self.room_system = room_system
        self.dimension = dimension
        self.backup = DimensionBackup(dimension)
        self.backup_map_identifier = None  # 备份时的地图标识

    def restore_and_start_record(self, load_range, is_record=True):
        """
        还原地图并开始记录

        Args:
            load_range (tuple): 加载范围
            is_record (bool): 是否进行备份记录
        """
        if is_record:
            print("[INFO] [BackupHandler] 维度{}第一次调用,备份初始地图状态".format(
                self.dimension
        ))
            self.save_initial_state(load_range)
        else:
            print("[INFO] [BackupHandler] 维度{}只清理方块记录,不进行备份".format(
                self.dimension
        ))

        # 清理方块变更记录
        self.backup.reset()

    def save_initial_state(self, load_range, callback=None):
        """
        保存初始地图状态

        Args:
            load_range (tuple): 备份范围
            callback (function): 完成回调
        """
        # 使用维度ID作为地图标识
        self.backup_map_identifier = "dim_{}".format(self.dimension)

        # 备份初始地图状态
        self.backup.backup_initial_state(load_range, callback)

    def restore(self, callback):
        """
        还原地图

        Args:
            callback (function): 还原完成回调
        """
        self.backup.restore_map_by_set_block(callback)

    def has_backup(self):
        """
        检查是否已有备份

        Returns:
            bool: 是否已有备份
        """
        return self.backup_map_identifier is not None

    def get_backup_info(self):
        """
        获取备份信息

        Returns:
            dict: 备份信息字典
        """
        return {
            "dimension": self.dimension,
            "has_backup": self.has_backup(),
            "backup_identifier": self.backup_map_identifier,
            "change_count": self.backup.get_change_count()
        }

    def clear_backup(self):
        """清除备份数据"""
        try:
            self.backup_map_identifier = None
            self.backup.clear_all()
            print("[INFO] [BackupHandler] 维度{}备份数据已清除".format(self.dimension))
        except Exception as e:
            print("[ERROR] [BackupHandler] 维度{}清除备份失败: {}".format(
                self.dimension, str(e)
        ))
