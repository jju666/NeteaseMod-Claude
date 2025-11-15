# -*- coding: utf-8 -*-
"""
GuideBedPresetDefServer - 床位保护演示预设 (服务端)

功能:
- 自动在指定位置放置床方块（两个方块：头和尾）
- 在床方块周围循环放置和清除8块白色羊毛，形成教学动画
- 阶段：放置（2.4秒）→ 保持（3秒）→ 清除 → 循环
- 羊毛中心位置是床方块本身（不是实体）

原预设: BedWarsGuideBedPart (BlockPreset)
重构说明: 老项目中这是一个BlockPreset绑定到minecraft:bed方块，新项目中通过代码主动放置床方块
"""

from Script_NeteaseMod.presets.server.BlockPresetServerBase import BlockPresetServerBase
import random


class GuideBedPresetDefServer(BlockPresetServerBase):
    """
    床位保护演示预设 - 服务端

    演示流程:
    0. 初始化：异步加载区块，然后自动放置床方块（头和尾两个方块，根据rotation.yaw确定朝向）
    1. 放置阶段：每0.3秒放置一块羊毛，共8块（2.4秒）
    2. 保持阶段：展示完整防御结构（3秒）
    3. 清除阶段：瞬间清除所有羊毛方块，播放粒子
    4. 循环重复

    重要：
    - 羊毛中心位置是床方块本身（配置中的pos）
    - 床方块会被自动放置和清除，无需手动在地图中放置
    - 床的朝向由配置中的rotation.yaw决定
    - 使用异步区块加载机制，确保床方块能正确放置
    """

    def __init__(self):
        super(GuideBedPresetDefServer, self).__init__()

        # 8个方块的相对位置（相对于配置中的pos，即羊毛演示的中心点）
        # 格式: (x_offset, y_offset, z_offset): is_placed
        #
        # 注意：配置中的pos是羊毛演示的中心点（床的正上方）
        # 床方块实际在pos的下方一格（Y-1），这样羊毛不会覆盖床
        self.block_pos_dict = {
            (0, 0, 0): False,      # 床位正上方前侧
            (0, 0, -1): False,     # 床位正上方后侧
            (-1, 0, -2): False,    # 床位后方延伸
            (-1, 0, 1): False,     # 床位前方延伸
            (-2, 0, 0): False,     # 床位左侧延伸
            (-2, 0, -1): False,    # 床位左后侧
            (-1, 1, 0): False,     # 床位上方一层前侧
            (-1, 1, -1): False     # 床位上方一层后侧
        }

        self.lock = False          # 锁定标志，True时停止放置
        self.place_timer = None    # 放置定时器ID
        self.instance = None       # PresetInstance引用
        self.dimension_id = 0      # 维度ID
        self.bed_pos = None        # 床方块位置（羊毛中心）

    def on_init(self, instance):
        """
        预设初始化 - 读取床方块位置

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_bed] 预设初始化: {}".format(instance.instance_id))

        # 保存instance引用
        self.instance = instance

        # 获取床方块位置（羊毛中心）
        self.bed_pos = self.get_block_position(instance)
        self.dimension_id = self.get_dimension_id(instance)

        print("  - bed_pos (羊毛中心): {}".format(self.bed_pos))
        print("  - dimension_id: {}".format(self.dimension_id))

    def on_start(self, instance):
        """
        预设启动 - 异步放置床方块，然后启动方块演示定时器

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_bed] 预设启动: {}".format(instance.instance_id))

        # 保存instance引用
        self.instance = instance

        # 异步放置床方块（确保区块已加载）
        self._place_bed_blocks_async()

    def _place_blocks_gradually(self):
        """
        定时器回调 - 逐个放置方块

        每次调用放置一个方块，直到8个方块全部放置完成
        """
        # 如果已锁定（展示阶段），直接返回
        if self.lock:
            return

        # 检查床方块位置是否有效
        if not self.bed_pos:
            print("[ERROR] [bedwars:guide_bed] 床方块位置无效")
            return

        # 遍历所有位置，找到第一个未放置的方块
        for block_offset in self.block_pos_dict:
            if not self.block_pos_dict[block_offset]:
                # 计算实际世界坐标（相对于床方块位置）
                object_pos = (
                    self.bed_pos[0] + block_offset[0],
                    self.bed_pos[1] + block_offset[1],
                    self.bed_pos[2] + block_offset[2]
                )

                # 放置白色羊毛方块（使用新版本方块ID）
                success = self.set_block(object_pos, 'minecraft:white_wool', 0, self.dimension_id)

                if success:
                    # 播放放置音效（随机音调）
                    pitch = random.uniform(1.1, 1.5)
                    self.play_sound('dig.cloth', object_pos, volume=0.5, pitch=pitch)

                    # 注意：放置时不发送粒子效果，只在清除时发送

                    # 标记该位置已放置
                    self.block_pos_dict[block_offset] = True

                    # print("[INFO] [bedwars:guide_bed] 放置方块: {}".format(object_pos))
                else:
                    print("[ERROR] [bedwars:guide_bed] 放置方块失败: {}".format(object_pos))

                return  # 本次只放置一个，等待下次定时器触发

        # 所有方块已放置完成，进入展示阶段
        self.lock = True  # 锁定，停止放置
        # print("[INFO] [bedwars:guide_bed] 所有方块放置完成，进入展示阶段（3秒）")

        # 3秒后清除所有方块
        self.add_timer(3.0, self._remove_all_blocks)

    def _place_bed_blocks_async(self):
        """
        异步放置床方块 - 先加载区块，再在配置位置的下方一格放置床

        重要：配置中的pos是羊毛演示的中心点（床的正上方）
        床方块实际放置在pos的Y-1位置，这样羊毛不会覆盖床

        床方块由两部分组成（头和尾），根据配置的朝向放置
        """
        if not self.bed_pos:
            print("[ERROR] [bedwars:guide_bed] 床方块位置无效")
            return

        # 获取床的朝向（yaw角度）
        rotation = self.instance.get_config("rotation", {"yaw": 180.0})
        yaw = rotation.get("yaw", 180.0)

        # 根据yaw角度确定床的朝向
        # yaw=0: 南(+Z), yaw=90: 西(-X), yaw=180: 北(-Z), yaw=270: 东(+X)
        # 床方块数据值：0=南, 1=西, 2=北, 3=东
        # 床方块需要两个方块：头(head)和脚(foot)

        # 计算床的实际位置（x-1, y保持不变, z-1）
        actual_bed_x = self.bed_pos[0] - 1
        actual_bed_y = self.bed_pos[1]
        actual_bed_z = self.bed_pos[2] - 1

        # 确定床的方向和两个方块的位置
        if -45 <= yaw < 45:  # 南(+Z)
            direction = 0
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x, actual_bed_y, actual_bed_z + 1)
        elif 45 <= yaw < 135:  # 西(-X)
            direction = 1
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x - 1, actual_bed_y, actual_bed_z)
        elif -135 <= yaw < -45 or 135 <= yaw <= 180 or -180 <= yaw < -135:  # 北(-Z)
            direction = 2
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x, actual_bed_y, actual_bed_z - 1)
        else:  # 东(+X)
            direction = 3
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x + 1, actual_bed_y, actual_bed_z)

        print("[INFO] [bedwars:guide_bed] 准备异步放置床方块: foot={}, head={}, direction={}".format(
            foot_pos, head_pos, direction))

        # 异步放置床的脚部
        # aux值：0-3表示方向，+8表示是头部
        def on_foot_placed(success_foot):
            if not success_foot:
                print("[WARN] [bedwars:guide_bed] 床脚部放置失败")
                # BUG修复：即使床放置失败，也要启动羊毛演示定时器（这是核心功能）
                self._start_wool_demo_timer()
                return

            # 床尾放置成功后，先验证床尾方块确实存在，再放置床头
            # 修复原因: Minecraft床头方块无法单独放置，必须在床尾存在后才能放置
            import mod.server.extraServerApi as serverApi
            levelId = serverApi.GetLevelId()
            block_comp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

            # 验证床尾方块是否存在
            foot_block = block_comp.GetBlockNew(foot_pos, self.dimension_id)
            if not foot_block or foot_block.get('name') != 'minecraft:bed':
                print("[WARN] [bedwars:guide_bed] 床尾方块验证失败，可能地图中已有床方块")
                self._start_wool_demo_timer()
                return

            print("[INFO] [bedwars:guide_bed] 床尾方块验证成功，准备放置床头")

            # 添加延迟，确保床尾方块在游戏世界中完全生效
            def delayed_place_head():
                def on_head_placed(success_head):
                    if success_head:
                        print("[INFO] [bedwars:guide_bed] 床方块放置成功: foot={}, head={}, direction={}".format(
                            foot_pos, head_pos, direction))
                    else:
                        print("[WARN] [bedwars:guide_bed] 床头部放置失败，但脚部已放置")

                    # BUG修复：无论床头是否放置成功，都要启动羊毛演示定时器（这是核心功能）
                    self._start_wool_demo_timer()

                # 异步放置头部
                self.set_block_async(head_pos, 'minecraft:bed', direction + 8, self.dimension_id, on_head_placed)

            # 延迟0.05秒（1 tick）后放置床头
            self.add_timer(0.05, delayed_place_head)

        # 异步放置脚部
        self.set_block_async(foot_pos, 'minecraft:bed', direction, self.dimension_id, on_foot_placed)

    def _start_wool_demo_timer(self):
        """
        启动羊毛演示定时器

        在床方块放置成功后调用
        """
        print("[INFO] [bedwars:guide_bed] 启动羊毛演示定时器")

        # 启动方块放置定时器（0.3秒间隔，循环）
        self.place_timer = self.add_timer(0.3, self._place_blocks_gradually, is_repeated=True)

        if self.place_timer:
            print("[INFO] [bedwars:guide_bed] 羊毛演示定时器已启动")
        else:
            print("[ERROR] [bedwars:guide_bed] 启动羊毛演示定时器失败")

    def _remove_bed_blocks(self):
        """
        移除床方块 - 清除床的头部和脚部两个方块

        重要：与放置逻辑保持一致，床方块在配置位置的Y-1处
        """
        if not self.bed_pos:
            print("[ERROR] [bedwars:guide_bed] 床方块位置无效")
            return

        # 获取床的朝向（yaw角度）
        rotation = self.instance.get_config("rotation", {"yaw": 180.0})
        yaw = rotation.get("yaw", 180.0)

        # 计算床的实际位置（x-1, y保持不变, z-1）
        actual_bed_x = self.bed_pos[0] - 1
        actual_bed_y = self.bed_pos[1]
        actual_bed_z = self.bed_pos[2] - 1

        # 根据yaw角度确定床的两个方块位置
        if -45 <= yaw < 45:  # 南(+Z)
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x, actual_bed_y, actual_bed_z + 1)
        elif 45 <= yaw < 135:  # 西(-X)
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x - 1, actual_bed_y, actual_bed_z)
        elif -135 <= yaw < -45 or 135 <= yaw <= 180 or -180 <= yaw < -135:  # 北(-Z)
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x, actual_bed_y, actual_bed_z - 1)
        else:  # 东(+X)
            foot_pos = (actual_bed_x, actual_bed_y, actual_bed_z)
            head_pos = (actual_bed_x + 1, actual_bed_y, actual_bed_z)

        # 清除床的脚部和头部
        self.set_block(foot_pos, 'minecraft:air', 0, self.dimension_id)
        self.set_block(head_pos, 'minecraft:air', 0, self.dimension_id)

        print("[INFO] [bedwars:guide_bed] 床方块已清除: foot={}, head={}".format(foot_pos, head_pos))

    def _remove_all_blocks(self):
        """
        清除所有方块 - 3秒后执行

        瞬间清除所有8个方块，播放音效和粒子效果
        """
        # 检查床方块位置是否有效
        if not self.bed_pos:
            print("[ERROR] [bedwars:guide_bed] 床方块位置无效")
            return

        pos_list = []

        # 遍历所有位置，清除方块
        for block_offset in self.block_pos_dict:
            object_pos = (
                self.bed_pos[0] + block_offset[0],
                self.bed_pos[1] + block_offset[1],
                self.bed_pos[2] + block_offset[2]
            )
            pos_list.append(object_pos)

            # 设置为空气方块（清除）
            self.set_block(object_pos, 'minecraft:air', 0, self.dimension_id)

            # 播放破坏音效（随机音调）
            pitch = random.uniform(1.1, 1.5)
            self.play_sound('dig.cloth', object_pos, volume=0.5, pitch=pitch)

            # 重置为未放置状态
            self.block_pos_dict[block_offset] = False

        # 解锁，允许下一轮放置
        self.lock = False

        # 广播所有位置的粒子效果
        if self.instance:
            self.instance.send_to_client("guide_bed_effect", {
                "pos_list": pos_list
            })

        # print("[INFO] [bedwars:guide_bed] 方块已清除，重新开始循环")

    def on_stop(self, instance):
        """
        预设停止 - 取消定时器并清除所有方块（包括床）

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_bed] 预设停止: {}".format(instance.instance_id))

        # 取消定时器（使用基类方法）
        if self.place_timer:
            self.cancel_timer(self.place_timer)
            self.place_timer = None
            print("[INFO] [bedwars:guide_bed] 已取消方块演示定时器")

        # 清除所有羊毛方块
        if self.bed_pos:
            for block_offset in self.block_pos_dict:
                if self.block_pos_dict[block_offset]:
                    object_pos = (
                        self.bed_pos[0] + block_offset[0],
                        self.bed_pos[1] + block_offset[1],
                        self.bed_pos[2] + block_offset[2]
                    )
                    self.set_block(object_pos, 'minecraft:air', 0, self.dimension_id)
                    self.block_pos_dict[block_offset] = False

            # 清除床方块（两个方块：头和尾）
            self._remove_bed_blocks()

    def on_destroy(self, instance):
        """
        预设销毁 - 取消定时器、清除所有方块（包括床）

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_bed] 预设销毁: {}".format(instance.instance_id))

        # 清除所有已放置的羊毛方块
        if self.bed_pos:
            for block_offset in self.block_pos_dict:
                if self.block_pos_dict[block_offset]:
                    object_pos = (
                        self.bed_pos[0] + block_offset[0],
                        self.bed_pos[1] + block_offset[1],
                        self.bed_pos[2] + block_offset[2]
                    )
                    self.set_block(object_pos, 'minecraft:air', 0, self.dimension_id)

            # 清除床方块（两个方块：头和尾）
            self._remove_bed_blocks()

        # 调用基类的on_destroy清理定时器
        super(GuideBedPresetDefServer, self).on_destroy(instance)