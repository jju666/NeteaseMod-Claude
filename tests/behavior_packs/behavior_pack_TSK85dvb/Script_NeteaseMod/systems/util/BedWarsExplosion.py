# -*- coding: utf-8 -*-
"""
BedWarsExplosion - 起床战争爆炸系统

功能:
- 自定义爆炸逻辑
- 射线追踪计算影响范围
- 智能伤害(友军保护)
- 方块破坏(只破坏玩家放置的方块)
- 防爆机制(染色玻璃免疫)

参考老项目: Parts/ECBedWars/BedWarsExplosion.py
重构为: systems/util/BedWarsExplosion.py
"""

from __future__ import print_function
import math
import random
import mod.server.extraServerApi as serverApi


class Vector3(object):
    """三维向量类"""

    def __init__(self, x, y, z):
        self.x = x
        self.y = y
        self.z = z

    def set_components(self, x, y, z):
        """设置向量分量"""
        self.x = x
        self.y = y
        self.z = z

    def length(self):
        """计算向量长度"""
        return self.length_squared() ** 0.5

    def length_squared(self):
        """计算向量长度的平方"""
        return self.x ** 2 + self.y ** 2 + self.z ** 2

    def distance_squared(self, other):
        """计算到另一点的距离平方"""
        return (self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2

    def distance(self, other):
        """计算到另一点的距离"""
        return self.distance_squared(other) ** 0.5

    def subtract(self, other):
        """向量减法"""
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def add(self, other):
        """向量加法"""
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def multiply(self, scalar):
        """向量数乘"""
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def divide(self, scalar):
        """向量数除"""
        return Vector3(self.x / scalar, self.y / scalar, self.z / scalar)

    def normalize(self):
        """归一化向量"""
        length = self.length_squared()
        if length > 0:
            return self.divide(math.sqrt(length))
        return Vector3(0, 0, 0)

    def to_tuple(self):
        """转换为元组"""
        return (self.x, self.y, self.z)


def calculate_distance(pos1, pos2):
    """
    计算两点之间的距离

    Args:
        pos1 (tuple): 位置1 (x, y, z)
        pos2 (tuple): 位置2 (x, y, z)

    Returns:
        float: 两点之间的距离
    """
    return ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2) ** 0.5


def check_valid_pos(pos):
    """
    默认的位置检查函数(总是返回True)

    Args:
        pos (tuple): 方块位置

    Returns:
        bool: 是否有效
    """
    return True


def check_valid_hurt_target(entity_id):
    """
    默认的伤害目标检查函数(总是返回True)

    Args:
        entity_id (str): 实体ID

    Returns:
        bool: 是否可以造成伤害
    """
    return True


def check_tiny_hurt(entity_id):
    """
    默认的微量伤害检查函数(总是返回False)

    Args:
        entity_id (str): 实体ID

    Returns:
        bool: 是否只造成微量伤害
    """
    return False


class BedWarsExplosion(object):
    """
    起床战争爆炸系统

    使用射线追踪算法计算爆炸影响范围
    """

    def __init__(self, dimension, source_pos, size, entity_id, source_entity_id=None):
        """
        初始化爆炸

        Args:
            dimension (int): 维度ID
            source_pos (tuple): 爆炸中心位置 (x, y, z)
            size (float): 爆炸半径
            entity_id (str): 爆炸源实体ID
            source_entity_id (str): 爆炸发起者ID(可选)
        """
        assert source_pos is not None, "source_pos is None"

        self.dimension = dimension  # type: int
        self.source_pos = source_pos  # type: tuple
        self.size = size  # type: float
        self.entity_id = entity_id  # type: str
        self.source_entity_id = source_entity_id  # type: str
        self.affected_blocks = []  # type: list

        # 配置函数(可被外部覆盖)
        self.explosion_resistance_map = {}  # type: dict
        self.check_valid_pos = check_valid_pos  # type: callable
        self.check_valid_hurt_target = check_valid_hurt_target  # type: callable
        self.check_tiny_hurt = check_tiny_hurt  # type: callable

        # 组件缓存
        self._comp_block_info = None
        self._comp_game = None

    def _get_comp_block_info(self):
        """获取方块信息组件"""
        if self._comp_block_info is None:
            self._comp_block_info = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())
        return self._comp_block_info

    def _get_comp_game(self):
        """获取游戏组件"""
        if self._comp_game is None:
            self._comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
        return self._comp_game

    def explode(self):
        """
        执行爆炸

        分为两个阶段:
        1. explode_a(): 计算影响范围
        2. explode_b(): 执行破坏和伤害
        """
        if not self.explode_a():
            return
        self.explode_b()

    def explode_a(self):
        """
        爆炸阶段A: 使用射线追踪计算受影响的方块

        Returns:
            bool: 是否继续执行爆炸阶段B
        """
        if self.size < 0.1:
            return False

        comp_block_info = self._get_comp_block_info()

        # 射线数量(8x8x8立方体表面)
        rays = 8
        m_rays = rays - 1
        vector = Vector3(0, 0, 0)

        # 从爆炸中心向8x8x8立方体表面发射射线
        for i in range(rays):
            for j in range(rays):
                for k in range(rays):
                    # 只处理立方体表面的点
                    if i == 0 or i == m_rays or j == 0 or j == m_rays or k == 0 or k == m_rays:
                        # 计算射线方向向量
                        vector.set_components(
                            float(i) / float(m_rays) * 2 - 1,
                            float(j) / float(m_rays) * 2 - 1,
                            float(k) / float(m_rays) * 2 - 1
                        )

                        # 归一化并乘以步长
                        length = vector.length()
                        step_len = 0.3
                        vector.set_components(
                            (vector.x / length) * step_len,
                            (vector.y / length) * step_len,
                            (vector.z / length) * step_len
                        )

                        # 射线起点
                        pointer_x, pointer_y, pointer_z = self.source_pos

                        # 初始爆炸力(带随机性)
                        blast_force = self.size * (random.randint(700, 1301) / 1000.0)

                        # 沿射线推进
                        while blast_force > 0:
                            x, y, z = int(pointer_x), int(pointer_y), int(pointer_z)

                            # 获取当前位置的方块
                            block_dict = comp_block_info.GetBlockNew((x, y, z), self.dimension)

                            if 'name' in block_dict and block_dict['name'] != 'minecraft:air':
                                # 染色玻璃完全免疫爆炸
                                if 'stained_glass' in block_dict['name']:
                                    # 跳过,但不消耗爆炸力
                                    pass
                                else:
                                    # 获取方块爆炸抗性
                                    if block_dict['name'] in self.explosion_resistance_map:
                                        explosion_resistance = self.explosion_resistance_map[block_dict['name']]
                                    else:
                                        block_info = comp_block_info.GetBlockBasicInfo(block_dict['name'])
                                        explosion_resistance = block_info.get('explosionResistance', 0)

                                    # 消耗爆炸力
                                    blast_force -= (explosion_resistance / 5 + 0.3) * step_len

                                    # 如果爆炸力足够,标记此方块为受影响
                                    if blast_force > 0 and (x, y, z) not in self.affected_blocks:
                                        self.affected_blocks.append((x, y, z))

                            # 推进射线
                            pointer_x += vector.x
                            pointer_y += vector.y
                            pointer_z += vector.z

                            # 空气中也会消耗爆炸力
                            blast_force -= step_len * 0.75

        return True

    def explode_b(self):
        """
        爆炸阶段B: 破坏方块并造成伤害
        """
        comp_block_info = self._get_comp_block_info()
        comp_game = self._get_comp_game()

        # 掉落概率
        yield0 = (1.0 / self.size) * 100.0

        # 破坏受影响的方块
        for block_pos in self.affected_blocks:
            # 检查位置是否有效(只破坏玩家放置的方块)
            if not self.check_valid_pos(block_pos):
                continue

            # 再次检查是否为染色玻璃
            block_dict = comp_block_info.GetBlockNew(block_pos, self.dimension)
            if 'name' in block_dict and 'stained_glass' in block_dict['name']:
                continue

            # 是否掉落物品(基于概率)
            old_block_handling = 0
            if random.random() * 100 < yield0:
                old_block_handling = 1

            # 设置为空气
            comp_block_info.SetBlockNew(
                block_pos,
                {'name': 'minecraft:air', 'aux': 0},
                old_block_handling,
                self.dimension,
                False
            )

        # 对周围实体造成伤害
        entities = comp_game.GetEntitiesInSquareArea(
            None,
            (self.source_pos[0] - self.size, self.source_pos[1] - self.size, self.source_pos[2] - self.size),
            (self.source_pos[0] + self.size, self.source_pos[1] + self.size, self.source_pos[2] + self.size),
            self.dimension
        )

        explosion_size = self.size * 2

        for entity_id in entities:
            # 检查是否可以造成伤害
            if not self.check_valid_hurt_target(entity_id):
                continue

            # 获取实体位置
            comp_pos = serverApi.GetEngineCompFactory().CreatePos(entity_id)
            entity_pos = comp_pos.GetFootPos()

            # 计算距离
            distance = calculate_distance(self.source_pos, entity_pos) / explosion_size

            if distance <= 1:
                # 曝光度(简化为1)
                exposure = 1
                impact = (1 - distance) * exposure

                # 施加击退效果
                comp_motion = serverApi.GetEngineCompFactory().CreateActorMotion(entity_id)

                motion = Vector3(
                    entity_pos[0] - self.source_pos[0],
                    entity_pos[1] - self.source_pos[1],
                    entity_pos[2] - self.source_pos[2]
                ).normalize()

                comp_motion.SetPlayerMotion(motion.multiply(impact * 2.5).to_tuple())

                # 计算伤害
                if self.check_tiny_hurt(entity_id):
                    # 友军只造成2点伤害
                    damage = 2
                else:
                    # 敌军造成正常伤害
                    damage = int(((impact * impact + impact) / 2) * 2 * explosion_size + 1)

                # 造成伤害
                hurt_comp = serverApi.GetEngineCompFactory().CreateHurt(entity_id)
                hurt_comp.Hurt(
                    damage,
                    serverApi.GetMinecraftEnum().ActorDamageCause.EntityExplosion,
                    self.entity_id,
                    self.source_entity_id,
                    False
                )

        # 播放爆炸效果和音效
        self._play_explosion_effects()

    def _play_explosion_effects(self):
        """播放爆炸效果和音效"""
        try:
            # 获取BedWarsGameSystem
            from systems.BedWarsGameSystem import BedWarsGameSystem
            import mod.server.extraServerApi as serverApi

            game_system = serverApi.GetSystem("Script_NeteaseMod", "BedWarsGameSystem")  # type: BedWarsGameSystem

            if game_system:
                # 广播爆炸效果(客户端)
                game_system.NotifyToClient(
                    -1,  # 广播给所有玩家
                    "SpawnExplodeEffect",
                    {
                        "dimension": self.dimension,
                        "pos": self.source_pos,
                    }
                )

                # 播放爆炸音效
                game_system.SetCommand(
                    "playsound {} @a {} {} {} 1 1".format(
                        "random.explode",
                        self.source_pos[0],
                        self.source_pos[1],
                        self.source_pos[2]
                    )
                )

        except Exception as e:
            print("[ERROR] [BedWarsExplosion] 播放爆炸效果失败: {}".format(str(e)))
