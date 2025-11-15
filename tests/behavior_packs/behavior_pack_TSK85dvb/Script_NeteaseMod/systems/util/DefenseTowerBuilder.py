# -*- coding: utf-8 -*-
"""
DefenseTowerBuilder - 防御塔构建器

功能:
- 异步构建防御塔结构(7x7x8)
- 支持结构旋转(0/90/180/270度)
- 定时器逐步放置方块(动画效果)
- 方块放置验证(只在空气处放置)

原文件: Parts/PropDefenseTower/DefenseTowerBuilder.py
重构为: systems/util/DefenseTowerBuilder.py

参考文档: D:\EcWork\NetEaseMapECBedWars备份\docs\PropDefenseTower.md
"""

from __future__ import print_function
import mod.server.extraServerApi as serverApi


# ========== 防御塔结构定义 ==========

# 防御塔三维结构 (7x7x8)
# 0 = 空气, 1 = 羊毛, 2 = 梯子
STRUCTURE = [
    # 第0层 (地面层) - 中空框架
    [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 2, 1, 0],  # 2 = 梯子
        [0, 1, 0, 0, 0, 1, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0]
    ],
    # 第1层 - 相同结构
    [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 2, 1, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0]
    ],
    # 第2层 - 相同结构
    [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 2, 1, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0]
    ],
    # 第3层 - 相同结构
    [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 2, 1, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0]
    ],
    # 第4层 - 相同结构
    [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 2, 1, 0],
        [0, 1, 0, 0, 0, 1, 0],
        [0, 0, 1, 1, 1, 0, 0],
        [0, 0, 0, 0, 0, 0, 0]
    ],
    # 第5层 (平台层) - 实心平台
    [
        [0, 1, 0, 1, 0, 1, 0],
        [1, 1, 1, 1, 1, 1, 1],
        [0, 1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 2, 1, 1],
        [0, 1, 1, 1, 1, 1, 0],
        [1, 1, 1, 1, 1, 1, 1],
        [0, 1, 0, 1, 0, 1, 0]
    ],
    # 第6层 (围栏层) - 中空围栏
    [
        [0, 1, 1, 1, 1, 1, 0],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [0, 1, 1, 1, 1, 1, 0]
    ],
    # 第7层 (顶层装饰) - 稀疏装饰
    [
        [0, 1, 0, 1, 0, 1, 0],
        [1, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 1],
        [0, 0, 0, 0, 0, 0, 0],
        [1, 0, 0, 0, 0, 0, 1],
        [0, 1, 0, 1, 0, 1, 0]
    ],
]


# ========== 辅助函数 ==========

def rotate_structure(structure, degrees):
    """
    旋转三维结构(在x-z平面上旋转)

    Args:
        structure: 三维列表 [y][x][z]
        degrees: 旋转角度(0/90/180/270)

    Returns:
        旋转后的三维列表
    """
    if degrees not in [0, 90, 180, 270, 360]:
        print("[WARNING] [DefenseTowerBuilder] 无效的旋转角度: {}".format(degrees))
        return structure

    # 每次旋转90度
    for _ in range(degrees // 90):
        new_structure = []
        for layer in structure:
            # 转置矩阵并反转行(实现顺时针90度旋转)
            new_layer = [list(row) for row in zip(*layer)][::-1]
            new_structure.append(new_layer)
        structure = new_structure

    return structure


def get_structure_size(structure):
    """
    获取结构尺寸

    Args:
        structure: 三维列表 [y][x][z]

    Returns:
        tuple: (width, height, length) = (x, y, z)
    """
    if not structure or not structure[0] or not structure[0][0]:
        return (0, 0, 0)
    return (len(structure[0]), len(structure), len(structure[0][0]))


# ========== 防御塔构建器 ==========

class DefenseTowerBuilder(object):
    """
    防御塔构建器

    使用异步定时器逐步放置方块,实现动画效果
    """

    def __init__(self, system, dimension, position, rotation, block_palette, game_system):
        """
        初始化构建器

        Args:
            system: PropsManagementSystem实例
            dimension (int): 维度ID
            position (tuple): 基础位置 (x, y, z)
            rotation (int): 旋转角度 (0/90/180/270)
            block_palette (dict): 方块ID到方块配置的映射 {1: {...}, 2: {...}}
            game_system: BedWarsGameSystem实例
        """
        self.system = system
        self.dimension = dimension
        self.position = position
        self.rotation = rotation % 360
        self.block_palette = block_palette
        self.game_system = game_system

        # 旋转结构
        self.structure = rotate_structure(STRUCTURE, self.rotation)
        self.structure_size = get_structure_size(self.structure)

        # 当前构建进度 [x, y, z]
        self.current = [0, 0, 0]

        # 组件缓存
        self.comp_block_info = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())

        # 启动定时器 (每0.05秒触发一次)
        self.timer_id = self.system.AddRepeatedTimer(0.05, self._on_update)

        print("[INFO] [DefenseTowerBuilder] 构建器创建: pos={} rotation={} size={}".format(
            position, rotation, self.structure_size
        ))

    def _on_update(self):
        """定时器回调 - 每次放置4个方块"""
        for _ in range(4):  # 每次放置4个方块
            if not self._place_next_block():
                # 构建完成,取消定时器
                self.system.CancelTimer(self.timer_id)
                print("[INFO] [DefenseTowerBuilder] 防御塔构建完成: pos={}".format(self.position))
                return

    def _place_next_block(self):
        """
        放置下一个方块

        Returns:
            bool: 是否还有方块需要放置
        """
        # 获取当前位置的方块类型
        block_type = self.structure[self.current[1]][self.current[0]][self.current[2]]

        # 跳过空气方块
        while block_type == 0:
            if not self._next_pos():
                return False  # 所有方块已遍历
            block_type = self.structure[self.current[1]][self.current[0]][self.current[2]]

        # 计算世界坐标(结构中心对齐到基础位置)
        world_pos = (
            self.position[0] + (self.current[0] - int(self.structure_size[0] / 2)),
            self.position[1] + self.current[1] + 1,  # +1 在目标方块上方
            self.position[2] + (self.current[2] - int(self.structure_size[2] / 2))
        )

        # 检查目标位置是否为空气
        old_block = self.comp_block_info.GetBlockNew(world_pos, self.dimension)
        if old_block and old_block.get('name') == 'minecraft:air':
            # 获取方块配置
            block_config = self.block_palette.get(block_type, {'name': 'minecraft:dirt', 'aux': 0})

            # 放置方块
            self._place_block(world_pos, block_config)

        # 移动到下一个位置
        return self._next_pos()

    def _place_block(self, pos, block_config):
        """
        放置方块

        Args:
            pos (tuple): 世界坐标 (x, y, z)
            block_config (dict): 方块配置 {'name': str, 'aux': int}
        """
        try:
            # 放置方块
            self.comp_block_info.SetBlockNew(
                pos,
                block_config,
                0,  # oldBlockHandling
                self.dimension,
                False  # 不触发方块更新
            )

            # 记录方块到placed_blocks(用于TNT爆炸判定)
            placed_blocks = getattr(self.game_system, 'placed_blocks', None)
            if placed_blocks is not None:
                placed_blocks.add(pos)

            # 播放放置音效
            comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
            comp_game.PlaySound("random.pop", pos, 1.0, 1.0, self.dimension)

        except Exception as e:
            print("[ERROR] [DefenseTowerBuilder] 放置方块失败: pos={} error={}".format(pos, str(e)))

    def _next_pos(self):
        """
        移动到下一个位置(按 x -> z -> y 顺序遍历)

        Returns:
            bool: 是否还有位置
        """
        self.current[0] += 1
        if self.current[0] >= self.structure_size[0]:
            self.current[0] = 0
            self.current[2] += 1
            if self.current[2] >= self.structure_size[2]:
                self.current[2] = 0
                self.current[1] += 1
                if self.current[1] >= self.structure_size[1]:
                    return False  # 所有方块已放置
        return True
