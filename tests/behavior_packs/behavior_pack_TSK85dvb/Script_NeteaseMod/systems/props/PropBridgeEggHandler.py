# -*- coding: utf-8 -*-
"""
PropBridgeEggHandler - 搭桥蛋道具处理器

功能:
- 监控搭桥蛋投射物的飞行状态
- 实时检测投射物与投掷者的距离限制
- 在搭桥蛋落地位置自动生成队伍颜色的羊毛桥梁
- 与 BedWarsGameSystem 协同工作，实现队伍归属和方块放置

原文件: Parts/PropBridgeEgg/PropBridgeEggPart.py
重构为: systems/props/PropBridgeEggHandler.py
"""

from __future__ import print_function
import time
from .IPropHandler import IPropHandler
import mod.server.extraServerApi as serverApi


class PropBridgeEggHandler(IPropHandler):
    """
    搭桥蛋道具处理器

    核心功能:
    - 每0.05秒检测所有搭桥蛋投射物
    - 距离限制检测(默认70格)
    - 生成2×2羊毛桥梁(队伍颜色)
    - 自动清理记录防止内存泄漏
    """

    def __init__(self):
        super(PropBridgeEggHandler, self).__init__()
        # 禁用Tick更新，因为GetAllEntities()方法不存在
        # 需要实现: 监听实体创建事件维护搭桥蛋实体列表
        self.enable_tick = False

        # 配置参数
        self.max_distance = 70  # 最大距离限制(方块)
        self.distance_check_interval = 0.03  # 距离检查间隔(秒)
        self.tick_interval = 0.05  # Tick检查间隔(秒)

        # 运行时数据
        self.next_tick = 0  # 下次Tick执行时间
        self.last_distance_check = {}  # 记录每个实体的最后检查时间

        # 组件缓存
        self._comp_game = None

    def on_create(self, system):
        """
        道具处理器创建时调用

        Args:
            system: PropsManagementSystem实例
        """
        super(PropBridgeEggHandler, self).on_create(system)
        print("[INFO] [PropBridgeEggHandler] 创建完成")

    def on_destroy(self):
        """道具处理器销毁时调用"""
        # 清理所有记录
        self.last_distance_check = {}
        super(PropBridgeEggHandler, self).on_destroy()
        print("[INFO] [PropBridgeEggHandler] 销毁完成")

    def on_update(self):
        """
        每帧更新(由PropsManagementSystem.Update调用)

        检测所有搭桥蛋投射物:
        1. 距离限制检测
        2. 桥梁生成逻辑
        """
        now = time.time()

        # 频率控制: 每0.05秒执行一次
        if self.next_tick > now:
            return
        self.next_tick = now + self.tick_interval

        # 获取游戏系统
        game_system = self.get_game_system()
        if not game_system:
            return

        # 获取所有实体
        comp_game = self._get_comp_game()
        all_entities = comp_game.GetAllEntities()

        # 定期清理已销毁实体的记录(每10秒清理一次)
        if int(now) % 10 == 0:
            self._cleanup_entity_records(all_entities)

        # 检测所有搭桥蛋投射物
        for entity_id in all_entities:
            self._process_bridge_egg_entity(entity_id, now, game_system)

    def on_trigger(self, player_id, **kwargs):
        """
        道具触发(搭桥蛋不使用此接口,使用投射物机制)

        Args:
            player_id (str): 玩家ID
            **kwargs: 道具参数
        """
        # 搭桥蛋通过投掷物品自动触发,不需要主动调用
        pass

    # ========== 实体检测逻辑 ==========

    def _process_bridge_egg_entity(self, entity_id, now, game_system):
        """
        处理单个搭桥蛋实体

        Args:
            entity_id (str): 实体ID
            now (float): 当前时间戳
            game_system: BedWarsGameSystem实例
        """
        try:
            # 获取实体组件
            comp_entity_info = serverApi.GetEngineCompFactory().CreateEngineEntityInfo(entity_id)
            entity_type = comp_entity_info.GetEntityIdentifier()

            # 只处理搭桥蛋实体
            if entity_type != "ecbedwars:bridge_egg":
                return

            # 获取位置组件
            comp_pos = serverApi.GetEngineCompFactory().CreatePos(entity_id)
            if not comp_pos:
                return

            # 检查维度是否匹配
            dimension_id = comp_pos.GetDimensionId()
            game_dimension = getattr(game_system, 'dimension', None)
            if game_dimension is not None and dimension_id != game_dimension:
                return

            # 获取所有者(投掷者)
            comp_owner = serverApi.GetEngineCompFactory().CreateEntityOwner(entity_id)
            owner_id = comp_owner.GetEntityOwner() if comp_owner else None
            if not owner_id:
                return

            # 距离限制检测
            if not self._check_distance_limit(entity_id, owner_id, comp_pos, now):
                # 距离过远,实体已销毁
                return

            # 查询玩家队伍
            team_module = getattr(game_system, 'team_module', None)
            if not team_module:
                return

            team = team_module.get_player_team(owner_id)
            if not team:
                return

            # 获取队伍类型
            # [FIX 2025-11-04] 修复Python 2.7导入路径问题
            from Script_NeteaseMod.systems.team.TeamType import team_types
            team_type = team_types.get(team)
            if not team_type:
                return

            # 获取当前位置
            egg_pos = comp_pos.GetPos()

            # 延迟生成桥梁(0.25秒后)
            self._schedule_bridge_build(egg_pos, dimension_id, team_type, game_system)

        except Exception as e:
            print("[ERROR] [PropBridgeEggHandler] 处理搭桥蛋实体失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    def _check_distance_limit(self, entity_id, owner_id, comp_pos, now):
        """
        检查距离限制

        Args:
            entity_id (str): 实体ID
            owner_id (str): 所有者ID
            comp_pos: 位置组件
            now (float): 当前时间戳

        Returns:
            bool: True=距离正常, False=距离过远(已销毁实体)
        """
        # 控制距离检查频率
        if entity_id not in self.last_distance_check:
            self.last_distance_check[entity_id] = 0

        if now - self.last_distance_check[entity_id] < self.distance_check_interval:
            return True  # 跳过此次检查

        self.last_distance_check[entity_id] = now

        # 获取所有者位置
        comp_owner_pos = serverApi.GetEngineCompFactory().CreatePos(owner_id)
        if not comp_owner_pos:
            return True  # 无法获取所有者位置,不销毁

        owner_pos = comp_owner_pos.GetPos()
        egg_pos = comp_pos.GetPos()

        # 使用更高效的距离计算(避免开方运算)
        dx = owner_pos[0] - egg_pos[0]
        dy = owner_pos[1] - egg_pos[1]
        dz = owner_pos[2] - egg_pos[2]
        distance_squared = dx * dx + dy * dy + dz * dz
        max_distance_squared = self.max_distance * self.max_distance

        # 如果距离超过限制,立即清除搭桥蛋
        if distance_squared > max_distance_squared:
            distance = distance_squared ** 0.5  # 只在需要显示时计算实际距离
            print("[INFO] [PropBridgeEggHandler] 搭桥蛋距离投掷者过远({:.1f}方块),立即清除".format(distance))

            # 销毁实体
            comp_game = self._get_comp_game()
            comp_game.DestroyEntity(entity_id)

            # 清理记录
            if entity_id in self.last_distance_check:
                del self.last_distance_check[entity_id]

            return False

        return True

    # ========== 桥梁生成逻辑 ==========

    def _schedule_bridge_build(self, pos, dimension_id, team_type, game_system):
        """
        延迟生成桥梁

        Args:
            pos (tuple): 投射物位置 (x, y, z)
            dimension_id (int): 维度ID
            team_type: TeamType实例
            game_system: BedWarsGameSystem实例
        """
        # 定义桥梁生成回调
        def build_bridge(pos, team_type):
            self._build_bridge_blocks(pos, dimension_id, team_type, game_system)

        # 0.25秒后生成桥梁(避免即时碰撞)
        self.system.AddTimer(0.25, build_bridge, pos, team_type)

    def _build_bridge_blocks(self, pos, dimension_id, team_type, game_system):
        """
        生成2×2羊毛桥梁

        Args:
            pos (tuple): 投射物落点位置 (x, y, z)
            dimension_id (int): 维度ID
            team_type: TeamType实例
            game_system: BedWarsGameSystem实例
        """
        try:
            # 计算桥梁位置(落点下方2格)
            base_x = int(round(pos[0]))
            base_z = int(round(pos[2]))
            bridge_y = int(round(pos[1])) - 2

            # 获取方块信息组件
            comp_block_info = serverApi.GetEngineCompFactory().CreateBlockInfo(serverApi.GetLevelId())

            # 羊毛方块数据
            wool_block = {
                "name": "minecraft:wool",
                "aux": team_type.item_color
            }

            # 放置2×2羊毛桥梁
            positions = [
                (base_x, bridge_y, base_z),
                (base_x + 1, bridge_y, base_z),
                (base_x, bridge_y, base_z + 1),
                (base_x + 1, bridge_y, base_z + 1)
            ]

            for block_pos in positions:
                # 使用BedWarsGameSystem的方块放置接口(记录到placed_blocks)
                if hasattr(game_system, 'bedwars_place_block'):
                    game_system.bedwars_place_block({
                        "dimension": dimension_id,
                        "pos": block_pos,
                        "block": wool_block
                    })
                else:
                    # 回退方案: 直接放置方块
                    comp_block_info.SetBlockNew(block_pos, wool_block, 0, dimension_id)
                    # 记录到placed_blocks
                    placed_blocks = getattr(game_system, 'placed_blocks', None)
                    if placed_blocks is not None:
                        placed_blocks.add(block_pos)

            # 播放音效
            comp_command = serverApi.GetEngineCompFactory().CreateCommand(serverApi.GetLevelId())
            comp_command.SetCommand(
                "playsound random.pop @a {} {} {}".format(pos[0], pos[1], pos[2])
            )

            print("[INFO] [PropBridgeEggHandler] 桥梁已生成: pos=({}, {}, {})".format(
                base_x, bridge_y, base_z
            ))

        except Exception as e:
            print("[ERROR] [PropBridgeEggHandler] 生成桥梁失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    # ========== 清理逻辑 ==========

    def _cleanup_entity_records(self, all_entities):
        """
        清理已销毁实体的记录(防止内存泄漏)

        Args:
            all_entities (list): 当前所有实体ID列表
        """
        try:
            # 获取当前存活的搭桥蛋实体ID集合
            active_entity_ids = set()
            for entity_id in all_entities:
                try:
                    comp_entity_info = serverApi.GetEngineCompFactory().CreateEngineEntityInfo(entity_id)
                    entity_type = comp_entity_info.GetEntityIdentifier()
                    if entity_type == "ecbedwars:bridge_egg":
                        active_entity_ids.add(entity_id)
                except:
                    pass

            # 清理不存在的实体记录
            to_remove = []
            for entity_id in self.last_distance_check:
                if entity_id not in active_entity_ids:
                    to_remove.append(entity_id)

            for entity_id in to_remove:
                del self.last_distance_check[entity_id]

            if to_remove:
                print("[INFO] [PropBridgeEggHandler] 清理{}个无效实体记录".format(len(to_remove)))

        except Exception as e:
            print("[ERROR] [PropBridgeEggHandler] 清理实体记录失败: {}".format(str(e)))

    # ========== 辅助方法 ==========

    def _get_comp_game(self):
        """获取Game组件"""
        if self._comp_game is None:
            self._comp_game = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
        return self._comp_game
