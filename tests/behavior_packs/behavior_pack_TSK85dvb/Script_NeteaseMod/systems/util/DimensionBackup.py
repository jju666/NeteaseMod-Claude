# -*- coding: utf-8 -*-
"""
DimensionBackup - 地图备份还原系统

功能:
- 动态记录方块变更
- 通过SetBlock还原方块为空气
- 支持协程分批还原
- 循环定时器处理未加载区块

新方案说明:
- 只记录方块变更,不备份调色板
- 还原时将变更的方块设置为空气(minecraft:air)
- 存储开销小,性能优秀

原文件: Parts/ECStage/DimensionBackup.py
重构为: systems/util/DimensionBackup.py
"""

import time
import mod.server.extraServerApi as serverApi


class DimensionBackup(object):
    """
    地图备份还原类

    核心数据结构:
    - block_changes: dict[tuple, dict] - 记录方块变更
      格式: {(x,y,z): {"old": 初始方块信息, "new": 最新方块信息}}
    """

    def __init__(self, dimension):
        """
        初始化地图备份实例

        Args:
            dimension (int): 维度ID
        """
        self.dimension = dimension
        self.block_changes = {}  # 方块变更记录
        self.load_range = ()  # 备份范围
        self.store_block_dict = {}  # 待还原的方块(还原失败的)
        self.restoration_timer_id = None  # 循环还原定时器ID
        self.restoration_callback = None  # 还原完成回调

    def backup_initial_state(self, load_range, callback=None):
        """
        备份初始地图状态(新方案:只设置范围,不进行调色板备份)

        Args:
            load_range (tuple): 备份范围 ((min_x, min_y, min_z), (max_x, max_y, max_z))
            callback (function): 完成回调函数
        """
        # 设置备份范围,用于方块放置区域限制
        self.load_range = (tuple(load_range[0]), tuple(load_range[1]))
        print("[INFO] [DimensionBackup] 设置地图范围 dimension={} range={}".format(
            self.dimension, load_range
        ))

        # 新方案:不需要预先备份,直接完成初始化
        if callback:
            callback()

    def reset(self):
        """重置备份数据(保留变更记录)"""
        self.restoration_callback = None

    def record(self, pos):
        """
        记录方块变更

        Args:
            pos (tuple): 方块位置 (x, y, z)
        """
        comp_block = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())

        # 获取当前方块状态
        current_block = comp_block.GetBlockNew(pos, self.dimension)
        if not current_block:
            return

        current_block_info = {
            'name': current_block['name'],
            'aux': current_block.get('aux', 0)
        }

        # 如果该位置还没有记录,说明是第一次变更,记录初始状态
        if pos not in self.block_changes:
            self.block_changes[pos] = {
                'old': dict(current_block_info),  # 保存初始状态
                'new': dict(current_block_info)   # 当前状态
            }
        else:
            # 如果已经有记录,只更新new状态,保持old不变
            self.block_changes[pos]['new'] = dict(current_block_info)

    def get_change_count(self):
        """
        获取变更的方块数量

        Returns:
            int: 变更的方块数量
        """
        return len(self.block_changes)

    def restore_map_by_set_block(self, callback=None):
        """
        通过协程 + SetBlock的方式还原地图

        Args:
            callback (function): 还原完成回调函数
        """
        level_id = serverApi.GetLevelId()
        chunk_comp = serverApi.GetEngineCompFactory().CreateChunkSource(level_id)

        # 1. 注册常加载区域(扩大100格范围)
        print("[INFO] [DimensionBackup] 地图还原任务启动,注册常加载区域")
        res = chunk_comp.SetAddArea(
            'restore_area_{}'.format(self.dimension),
            self.dimension,
            (self.load_range[0][0] - 100, self.load_range[0][1], self.load_range[0][2] - 100),
            (self.load_range[1][0] + 100, self.load_range[1][1], self.load_range[1][2] + 100)
        )

        def _start_restore():
            """协程:批量还原方块"""
            print("[INFO] [DimensionBackup] 还原程序启动,待还原方块数: {}".format(
                len(self.block_changes)
        ))
            over_pos_list = []

            for pos in self.block_changes:
                # 尝试立即还原方块
                restore_res = self.set_block(pos)
                if not restore_res and pos not in self.store_block_dict:
                    # 还原失败的方块加入队列中等待定时器恢复
                    self.store_block_dict[pos] = self.block_changes[pos]['old']
                    continue

                if restore_res:
                    over_pos_list.append(pos)

            # 清理已还原的方块
            for pos in over_pos_list:
                if 'new' in self.block_changes[pos]:
                    del self.block_changes[pos]['new']

            yield

        def on_restore_end():
            """还原结束回调"""
            if not self.store_block_dict:
                # 全部还原完成
                self.reset()
                print("[INFO] [DimensionBackup] 地图还原程序结束,全部方块已还原")
                chunk_comp.DeleteArea('restore_area_{}'.format(self.dimension))
                if callback:
                    callback()
            else:
                # 存在未还原的方块,启动循环定时器
                block_count = len(self.store_block_dict)
                print("[WARN] [DimensionBackup] 存在未还原的方块,启动循环定时器,待还原数量: {}".format(
                    block_count
        ))
                self.set_loop_restore_timer(callback)

        def _on_timer_end():
            """定时器回调:启动协程"""
            print("[INFO] [DimensionBackup] 协程启动")
            serverApi.StartCoroutine(_start_restore, lambda: on_restore_end())

        if res:
            # 2. 定时器延迟1秒执行协程
            print("[INFO] [DimensionBackup] 常加载区域注册成功")
            comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            comp.AddTimer(1.0, _on_timer_end)
        else:
            print("[ERROR] [DimensionBackup] 常加载区域注册失败")
            if callback:
                callback()

    def set_block(self, pos):
        """
        还原单个方块(设置为空气)

        Args:
            pos (tuple): 方块位置 (x, y, z)

        Returns:
            bool: 是否还原成功
        """
        level_id = serverApi.GetLevelId()

        # 1. 检测区块是否已加载
        chunk_comp = serverApi.GetEngineCompFactory().CreateChunkSource(level_id)
        is_chunk_loaded = chunk_comp.CheckChunkState(self.dimension, pos)
        if not is_chunk_loaded:
            return False

        # 2. 获取该位置方块
        block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(level_id)
        block_data = block_comp.GetBlockNew(pos, self.dimension)

        # 获取不到,直接返回失败
        if not block_data:
            return False

        # 已经是空气,不需要还原
        if block_data['name'] == "minecraft:air":
            return True

        # 3. 尝试还原(设置为空气)
        res = block_comp.SetBlockNew(
            pos,
            {"name": "minecraft:air", "aux": 0},
            1,
            self.dimension,
            True,
            False
        )
        return res

    def set_loop_restore_timer(self, callback):
        """
        启动循环还原定时器

        Args:
            callback (function): 还原完成回调函数
        """
        level_id = serverApi.GetLevelId()
        timer_comp = serverApi.GetEngineCompFactory().CreateGame(level_id)

        # 1. 终止旧定时器
        if self.restoration_timer_id:
            timer_comp.CancelTimer(self.restoration_timer_id)

        # 2. 启动新定时器(每5秒执行一次)
        print("[INFO] [DimensionBackup] 循环还原定时器启动")
        self.restoration_timer_id = timer_comp.AddRepeatedTimer(
            5.0,
            self.start_loop_restore,
            callback
        )

    def start_loop_restore(self, callback):
        """
        循环还原方块(处理未加载区块)

        Args:
            callback (function): 还原完成回调函数
        """
        level_id = serverApi.GetLevelId()
        timer_comp = serverApi.GetEngineCompFactory().CreateGame(level_id)

        # 尝试还原失败队列中的方块
        over_pos_list = []
        for pos in list(self.store_block_dict.keys()):
            restore_res = self.set_block(pos)
            if restore_res:
                over_pos_list.append(pos)

        # 清理已还原的方块
        for pos in over_pos_list:
            del self.store_block_dict[pos]

        # 检查是否全部还原完成
        if not self.store_block_dict:
            print("[INFO] [DimensionBackup] 循环还原完成,取消定时器")
            if self.restoration_timer_id:
                timer_comp.CancelTimer(self.restoration_timer_id)
                self.restoration_timer_id = None

            # 清理常加载区域
            chunk_comp = serverApi.GetEngineCompFactory().CreateChunkSource(level_id)
            chunk_comp.DeleteArea('restore_area_{}'.format(self.dimension))

            # 调用回调
            if callback:
                callback()
        else:
            print("[INFO] [DimensionBackup] 循环还原中,剩余方块数: {}".format(
                len(self.store_block_dict)
        ))

    def clear_all(self):
        """清除所有备份数据"""
        self.block_changes = {}
        self.store_block_dict = {}
        self.restoration_callback = None

        # 取消定时器
        if self.restoration_timer_id:
            level_id = serverApi.GetLevelId()
            timer_comp = serverApi.GetEngineCompFactory().CreateGame(level_id)
            timer_comp.CancelTimer(self.restoration_timer_id)
            self.restoration_timer_id = None
