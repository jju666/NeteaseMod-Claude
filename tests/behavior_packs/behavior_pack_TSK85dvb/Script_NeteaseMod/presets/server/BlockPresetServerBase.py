# -*- coding: utf-8 -*-
"""
BlockPresetServerBase - 方块预设基类

提供方块预设的通用功能，支持定时器、方块操作等
"""

from ECPresetServerScripts import PresetDefinitionServer
import mod.server.extraServerApi as serverApi


class BlockPresetServerBase(PresetDefinitionServer):
    """
    方块预设基类

    用于绑定到方块上的预设（如床方块、告示牌等），不是实体预设
    提供通用的方块预设功能：
    1. 获取方块世界位置
    2. 定时器管理
    3. 方块操作辅助
    """

    def __init__(self):
        super(BlockPresetServerBase, self).__init__()
        self.timers = []  # 定时器列表，用于清理

    def get_block_position(self, instance):
        """
        获取方块的世界坐标

        Args:
            instance: PresetInstance对象

        Returns:
            tuple (x, y, z) 方块的世界坐标
        """
        pos = instance.get_config("pos", [0, 64, 0])
        return (int(pos[0]), int(pos[1]), int(pos[2]))

    def get_dimension_id(self, instance):
        """
        获取方块所在维度ID

        Args:
            instance: PresetInstance对象

        Returns:
            int 维度ID
        """
        return instance.get_config("dimension_id", 0)

    def set_block(self, pos, block_name, aux_value, dimension_id):
        """
        设置方块（同步方式，不保证区块已加载）

        警告：此方法不保证区块已加载，可能导致放置失败
        推荐使用 set_block_async() 方法

        Args:
            pos: tuple (x, y, z) 方块位置
            block_name: str 方块名称（如 'minecraft:wool'）
            aux_value: int 附加值（如羊毛颜色）
            dimension_id: int 维度ID

        Returns:
            bool 是否成功
        """
        try:
            comp_block_info = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())

            # 首先检查设置前后该位置方块是否相同：
            blockDict = comp_block_info.GetBlockNew(pos, dimension_id)
            if blockDict and blockDict['name'] == block_name and blockDict['aux'] == aux_value:
                # 全都一样不用放了
                return True

            result = comp_block_info.SetBlockNew(
                pos,
                {'name': block_name, 'aux': aux_value},
                0,
                dimension_id,
                True  # isLegacy=True: 使用传统aux,不随版本变化
            )

            if not result:
                # SetBlockNew返回False，可能是因为目标方块已经和要放置的方块一致
                # 再次检查方块是否一致，如果一致则视为放置成功
                blockDict_after = comp_block_info.GetBlockNew(pos, dimension_id)
                if blockDict_after and blockDict_after['name'] == block_name and blockDict_after['aux'] == aux_value:
                    # 方块一致，视为放置成功
                    return True
                else:
                    # 方块不一致，确实是放置失败
                    print("[WARN] [BlockPresetBase] SetBlockNew返回False且方块不一致: pos={}, 期望={}/aux={}, 实际={}/aux={}".format(
                        pos, block_name, aux_value,
                        blockDict_after['name'] if blockDict_after else 'None',
                        blockDict_after['aux'] if blockDict_after else 'None'
                    ))
                    return False

            return True
        except Exception as e:
            print("[ERROR] [BlockPresetBase] 设置方块失败: {}".format(e))
            import traceback
            traceback.print_exc()
            return False

    def set_block_async(self, pos, block_name, aux_value, dimension_id, callback=None, chunk_radius=5):
        """
        异步设置方块 - 先加载区块，再设置方块

        推荐使用此方法，确保区块已加载后再放置方块

        Args:
            pos: tuple (x, y, z) 方块位置
            block_name: str 方块名称（如 'minecraft:wool'）
            aux_value: int 附加值（如羊毛颜色）
            dimension_id: int 维度ID
            callback: function 完成回调函数 callback(success: bool)
            chunk_radius: int 区块加载半径（默认5）

        Returns:
            bool 是否成功启动异步加载
        """
        # 验证dimension_id参数
        if dimension_id is None:
            print("[ERROR] [BlockPresetBase] 维度ID为None，无法异步放置方块")
            if callback:
                callback(False)
            return False

        if not isinstance(dimension_id, int):
            print("[ERROR] [BlockPresetBase] 维度ID类型错误: type={}, value={}".format(
                type(dimension_id), dimension_id
            ))
            if callback:
                callback(False)
            return False

        print("[INFO] [BlockPresetBase] 准备异步放置方块: pos={}, block={}, aux={}, dimension={}".format(
            pos, block_name, aux_value, dimension_id
        ))

        try:
            # 计算区块加载范围
            pos_min = (int(pos[0]) - chunk_radius * 16, int(pos[1]) - chunk_radius * 16, int(pos[2]) - chunk_radius * 16)
            pos_max = (int(pos[0]) + chunk_radius * 16, int(pos[1]) + chunk_radius * 16, int(pos[2]) + chunk_radius * 16)

            print("[INFO] [BlockPresetBase] 异步加载区块: pos_min={}, pos_max={}".format(pos_min, pos_max))

            # 准备回调函数，区块加载完成后放置方块
            def on_chunk_loaded(result):
                print("[INFO] [BlockPresetBase] 区块加载完成: result={}".format(result))

                if result.get('code') != 1:
                    print("[ERROR] [BlockPresetBase] 区块加载失败: result={}".format(result))
                    if callback:
                        callback(False)
                    return

                # 放置方块
                success = self.set_block(pos, block_name, aux_value, dimension_id)

                # 调用回调函数
                if callback:
                    callback(success)

            # 异步加载区块
            comp = serverApi.GetEngineCompFactory().CreateChunkSource(serverApi.GetLevelId())
            success = comp.DoTaskOnChunkAsync(dimension_id, pos_min, pos_max, on_chunk_loaded)

            if not success:
                print("[ERROR] [BlockPresetBase] 异步加载区块失败")
                return False

            return True

        except Exception as e:
            print("[ERROR] [BlockPresetBase] 异步加载区块异常: {}".format(e))
            import traceback
            traceback.print_exc()
            return False

    def add_timer(self, delay, callback, is_repeated=False):
        """
        添加定时器

        Args:
            delay: float 延时（秒）
            callback: function 回调函数
            is_repeated: bool 是否重复（默认False）

        Returns:
            int|None 定时器ID，失败返回None
        """
        try:
            comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            if is_repeated:
                timer_id = comp.AddRepeatedTimer(delay, callback)
            else:
                timer_id = comp.AddTimer(delay, callback)

            if timer_id:
                self.timers.append(timer_id)
            return timer_id
        except Exception as e:
            print("[ERROR] [BlockPresetBase] 添加定时器失败: {}".format(e))
            return None

    def cancel_timer(self, timer_id):
        """
        取消定时器

        Args:
            timer_id: int 定时器ID

        Returns:
            bool 是否成功
        """
        try:
            comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            comp.CancelTimer(timer_id)
            if timer_id in self.timers:
                self.timers.remove(timer_id)
            return True
        except Exception as e:
            print("[ERROR] [BlockPresetBase] 取消定时器失败: {}".format(e))
            return False

    def cancel_all_timers(self):
        """
        取消所有定时器
        """
        comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
        for timer_id in self.timers[:]:  # 使用切片复制避免修改列表时的问题
            try:
                comp.CancelTimer(timer_id)
            except Exception as e:
                print("[WARN] [BlockPresetBase] 取消定时器失败: timer_id={}, error={}".format(timer_id, e))
        self.timers = []

    def play_sound(self, sound_name, pos, volume=1.0, pitch=1.0):
        """
        播放音效

        Args:
            sound_name: str 音效名称（如 'dig.cloth'）
            pos: tuple (x, y, z) 位置
            volume: float 音量（0.0-1.0）
            pitch: float 音调（0.5-2.0）
        """
        try:
            comp = serverApi.GetEngineCompFactory().CreateCommand(serverApi.GetLevelId())
            command = "playsound {sound} @a {x} {y} {z} {volume} {pitch}".format(
                sound=sound_name,
                x=pos[0],
                y=pos[1],
                z=pos[2],
                volume=volume,
                pitch=pitch
            )
            comp.SetCommand(command)
        except Exception as e:
            print("[ERROR] [BlockPresetBase] 播放音效失败: {}".format(e))

    def on_destroy(self, instance):
        """
        预设销毁时的清理逻辑

        子类如果重写此方法，必须调用 super().on_destroy(instance)

        Args:
            instance: PresetInstance对象
        """
        # 清理所有定时器
        self.cancel_all_timers()
        print("[INFO] [BlockPresetBase] 预设销毁，已清理 {} 个定时器".format(len(self.timers)))