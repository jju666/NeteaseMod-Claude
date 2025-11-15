# -*- coding: utf-8 -*-
"""
IronGolemAISystem - 铁傀儡AI管理系统(服务端)

功能:
- 管理所有铁傀儡实体的AI行为
- 自动寻找并攻击敌对玩家
- 友军保护机制(免疫友军伤害)
- 队伍颜色名称显示
- 生命周期管理(维度检查/队伍消失销毁)

原文件: Parts/BedWarsIronGolem/BedWarsIronGolemPart.py
重构为: systems/IronGolemAISystem.py
"""

import mod.server.extraServerApi as serverApi
import time


def distance_squared(pos1, pos2):
    """计算两点间距离的平方"""
    return (pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2


class IronGolemAISystem(serverApi.GetServerSystemCls()):
    """
    铁傀儡AI管理系统(ServerSystem)

    核心职责:
    - 每秒扫描所有铁傀儡实体
    - 智能目标选择(攻击最近敌人)
    - 友军保护(免疫友军伤害)
    - 自动清理(维度/队伍消失)
    - 名称颜色管理
    """

    def __init__(self, namespace, systemName):
        """
        初始化铁傀儡AI系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        super(IronGolemAISystem, self).__init__(namespace, systemName)

        # 铁傀儡实体标识符
        self.golem_entity_type = 'ecbedwars:iron_golem'

        # 铁傀儡追踪记录 {entity_id: {'last_find_target': float, 'name_updated': bool}}
        self.golem_records = {}

        # 下次Tick时间
        self.next_tick = 0

        # 组件工厂
        self.comp_factory = serverApi.GetEngineCompFactory()

        print("[INFO] [IronGolemAISystem] 初始化完成")

        # ========== 重要：手动调用Create() ==========
        # 说明：网易引擎设计上只自动触发Destroy()，不自动触发Create()
        print("[IronGolemAISystem] 手动调用Create()完成系统初始化")
        self.Create()

    # ========== ServerSystem生命周期 ==========

    def Create(self):
        """系统创建时调用"""
        self.LogInfo("IronGolemAISystem.Create")

        # 注册伤害事件(友军保护)
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'DamageEvent',
            self,
            self._on_damage_event
        )

        # 注册实体移除事件(清理记录)
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'RemoveEntityServerEvent',
            self,
            self._on_entity_removed
        )

        # 注册实体生成事件(追踪新生成的铁傀儡)
        self.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'AddEntityServerEvent',
            self,
            self._on_entity_added
        )

        print("[INFO] [IronGolemAISystem] Create完成")

    def Destroy(self):
        """系统销毁时调用"""
        self.LogInfo("IronGolemAISystem.Destroy")
        self.golem_records.clear()
        print("[INFO] [IronGolemAISystem] Destroy完成")

    def Update(self):
        """系统每帧更新"""
        now = time.time()
        if now < self.next_tick:
            return

        self.next_tick = now + 1  # 每秒执行一次

        # 更新所有铁傀儡的AI
        self._update_all_golems()

    # ========== 铁傀儡AI更新 ==========

    def _update_all_golems(self):
        """更新所有铁傀儡的AI逻辑"""
        try:
            # 遍历已知的铁傀儡记录
            # 因为铁傀儡是通过道具生成的,我们在生成时就应该记录它们
            # 这样避免了遍历所有实体的性能问题
            for golem_entity_id in list(self.golem_records.keys()):
                # 检查实体是否还存在
                if not self._entity_exists(golem_entity_id):
                    # 实体已不存在,清理记录
                    del self.golem_records[golem_entity_id]
                    continue

                # 更新单个铁傀儡
                self._update_golem_ai(golem_entity_id)

        except Exception as e:
            self.LogError("更新铁傀儡AI失败: {}".format(str(e)))

    def _entity_exists(self, entity_id):
        """
        检查实体是否存在

        Args:
            entity_id (str): 实体ID

        Returns:
            bool: 实体是否存在
        """
        try:
            comp_type = self.comp_factory.CreateEngineType(entity_id)
            engine_type = comp_type.GetEngineTypeStr()
            return engine_type is not None and engine_type != ""
        except:
            return False

    def _is_iron_golem(self, entity_id):
        """
        检查实体是否是铁傀儡

        Args:
            entity_id (str): 实体ID

        Returns:
            bool: 是否是铁傀儡
        """
        try:
            comp_type = self.comp_factory.CreateEngineType(entity_id)
            engine_type = comp_type.GetEngineTypeStr()
            return engine_type == self.golem_entity_type
        except:
            return False

    def _update_golem_ai(self, golem_entity_id):
        """
        更新单个铁傀儡的AI

        Args:
            golem_entity_id (str): 铁傀儡实体ID
        """
        try:
            # 获取铁傀儡的队伍信息
            team = self._get_golem_team(golem_entity_id)
            if not team:
                return

            # 获取BedWarsGameSystem
            game_system = self._get_game_system()
            if not game_system:
                return

            # 初始化记录
            if golem_entity_id not in self.golem_records:
                self.golem_records[golem_entity_id] = {
                    'last_find_target': time.time(),
                    'name_updated': False
                }

            record = self.golem_records[golem_entity_id]

            # 更新名称颜色(只更新一次)
            if not record['name_updated']:
                self._update_golem_name(golem_entity_id, team)
                record['name_updated'] = True

            # 检查铁傀儡是否应该被销毁
            if self._should_destroy_golem(golem_entity_id, team, game_system):
                self._destroy_golem(golem_entity_id)
                return

            # 检查当前攻击目标
            current_target = self._get_attack_target(golem_entity_id)
            if current_target:
                # 如果目标是友军或观察者,重置目标
                if self._is_invalid_target(current_target, team, game_system):
                    self._reset_attack_target(golem_entity_id)
                    return

            # 寻找新目标
            new_target = self._find_nearest_enemy(golem_entity_id, team, game_system)
            if new_target:
                self._set_attack_target(golem_entity_id, new_target)
                record['last_find_target'] = time.time()
            elif time.time() - record['last_find_target'] > 10:
                # 超过10秒未找到目标,重置仇恨
                self._reset_attack_target(golem_entity_id)

        except Exception as e:
            self.LogError("更新铁傀儡AI失败 entity={}: {}".format(golem_entity_id, str(e)))

    # ========== 队伍信息获取 ==========

    def _get_golem_team(self, golem_entity_id):
        """
        获取铁傀儡的队伍

        Args:
            golem_entity_id (str): 铁傀儡实体ID

        Returns:
            str: 队伍ID,如果未找到返回None
        """
        try:
            comp_extra_data = self.comp_factory.CreateExtraData(golem_entity_id)
            team = comp_extra_data.GetExtraData("bedwars_team")
            return team
        except:
            return None

    # ========== 名称颜色管理 ==========

    def _update_golem_name(self, golem_entity_id, team):
        """
        更新铁傀儡的名称颜色

        Args:
            golem_entity_id (str): 铁傀儡实体ID
            team (str): 队伍ID
        """
        try:
            # [FIX 2025-11-04] 修复Python 2.7导入路径问题
            from Script_NeteaseMod.systems.team.TeamType import team_types

            # 获取队伍颜色
            if team in team_types:
                team_color = team_types[team].color
            else:
                team_color = u'\xa77'  # 灰色

            # 设置带颜色的名称
            colored_name = u"{}梦境守护者".format(team_color)

            comp_name = self.comp_factory.CreateName(golem_entity_id)
            comp_name.SetName(colored_name)
            comp_name.SetShowName(True)

            self.LogDebug("铁傀儡名称已更新: entity={} team={} name={}".format(
                golem_entity_id, team, colored_name))

        except Exception as e:
            self.LogError("更新铁傀儡名称失败: {}".format(str(e)))

    # ========== 生命周期检查 ==========

    def _should_destroy_golem(self, golem_entity_id, team, game_system):
        """
        检查铁傀儡是否应该被销毁

        Args:
            golem_entity_id (str): 铁傀儡实体ID
            team (str): 队伍ID
            game_system: BedWarsGameSystem实例

        Returns:
            bool: 是否应该销毁
        """
        try:
            # 检查维度
            comp_pos = self.comp_factory.CreatePos(golem_entity_id)
            golem_dimension = comp_pos.GetDimension()

            if golem_dimension != game_system.dimension:
                self.LogInfo("铁傀儡不在游戏维度,销毁 entity={} dim={}".format(
                    golem_entity_id, golem_dimension))
                return True

            # 检查队伍是否还存在
            if team and game_system.team_module:
                if team not in game_system.team_module.teams:
                    self.LogInfo("铁傀儡队伍已消失,销毁 entity={} team={}".format(
                        golem_entity_id, team))
                    return True

            return False

        except Exception as e:
            self.LogError("检查铁傀儡销毁条件失败: {}".format(str(e)))
            return False

    def _destroy_golem(self, golem_entity_id):
        """
        销毁铁傀儡

        Args:
            golem_entity_id (str): 铁傀儡实体ID
        """
        try:
            comp_game = self.comp_factory.CreateGame(serverApi.GetLevelId())
            comp_game.DestroyEntity(golem_entity_id)

            # 清理记录
            if golem_entity_id in self.golem_records:
                del self.golem_records[golem_entity_id]

            self.LogInfo("铁傀儡已销毁 entity={}".format(golem_entity_id))

        except Exception as e:
            self.LogError("销毁铁傀儡失败: {}".format(str(e)))

    # ========== 目标选择 ==========

    def _get_attack_target(self, golem_entity_id):
        """
        获取铁傀儡当前的攻击目标

        Args:
            golem_entity_id (str): 铁傀儡实体ID

        Returns:
            str: 目标实体ID,无目标返回None
        """
        try:
            comp_attr = self.comp_factory.CreateAttr(golem_entity_id)
            target_id = comp_attr.GetAttrValue(serverApi.GetMinecraftEnum().AttrType.ATTACK_TARGET)
            return target_id if target_id and target_id != -1 else None
        except:
            return None

    def _set_attack_target(self, golem_entity_id, target_id):
        """
        设置铁傀儡的攻击目标

        Args:
            golem_entity_id (str): 铁傀儡实体ID
            target_id (str): 目标实体ID
        """
        try:
            comp_attr = self.comp_factory.CreateAttr(golem_entity_id)
            comp_attr.SetAttrValue(
                serverApi.GetMinecraftEnum().AttrType.ATTACK_TARGET,
                target_id
            )
        except Exception as e:
            self.LogError("设置铁傀儡攻击目标失败: {}".format(str(e)))

    def _reset_attack_target(self, golem_entity_id):
        """
        重置铁傀儡的攻击目标

        Args:
            golem_entity_id (str): 铁傀儡实体ID
        """
        try:
            comp_attr = self.comp_factory.CreateAttr(golem_entity_id)
            comp_attr.SetAttrValue(
                serverApi.GetMinecraftEnum().AttrType.ATTACK_TARGET,
                -1
            )
        except Exception as e:
            self.LogError("重置铁傀儡攻击目标失败: {}".format(str(e)))

    def _is_invalid_target(self, target_id, golem_team, game_system):
        """
        检查目标是否无效(友军或观察者)

        Args:
            target_id (str): 目标实体ID
            golem_team (str): 铁傀儡队伍
            game_system: BedWarsGameSystem实例

        Returns:
            bool: 是否无效目标
        """
        try:
            # 检查是否是友军
            if game_system.team_module:
                target_team = game_system.team_module.get_player_team(target_id)
                if target_team and target_team == golem_team:
                    return True

            # 检查是否是观察者
            comp_game = self.comp_factory.CreateGame(serverApi.GetLevelId())
            game_type = comp_game.GetPlayerGameType(target_id)
            if game_type == serverApi.GetMinecraftEnum().GameType.SPECTATOR:
                return True

            return False

        except:
            return True

    def _find_nearest_enemy(self, golem_entity_id, golem_team, game_system):
        """
        寻找距离最近的敌对玩家

        Args:
            golem_entity_id (str): 铁傀儡实体ID
            golem_team (str): 铁傀儡队伍
            game_system: BedWarsGameSystem实例

        Returns:
            str: 最近敌人的实体ID,未找到返回None
        """
        try:
            if not game_system.team_module:
                return None

            # 获取铁傀儡位置
            comp_pos = self.comp_factory.CreatePos(golem_entity_id)
            golem_pos = comp_pos.GetPos()
            golem_dimension = comp_pos.GetDimension()

            # 获取所有敌对队伍的玩家
            enemy_players = game_system.team_module.get_team_players_except(golem_team)
            if not enemy_players:
                return None

            # 寻找最近的敌人
            nearest_enemy = None
            min_distance = float('inf')

            for player_obj in enemy_players:
                player_id = player_obj.GetPlayerId()

                # 排除不同维度的玩家
                if player_obj.GetDimensionId() != golem_dimension:
                    continue

                # 排除观察者
                comp_game = self.comp_factory.CreateGame(serverApi.GetLevelId())
                game_type = comp_game.GetPlayerGameType(player_id)
                if game_type == serverApi.GetMinecraftEnum().GameType.SPECTATOR:
                    continue

                # 计算距离
                player_pos = player_obj.GetFootPos()
                distance = distance_squared(golem_pos, player_pos)

                if distance < min_distance:
                    min_distance = distance
                    nearest_enemy = player_id

            return nearest_enemy

        except Exception as e:
            self.LogError("寻找最近敌人失败: {}".format(str(e)))
            return None

    # ========== 友军保护 ==========

    def _on_damage_event(self, args):
        """
        伤害事件处理 - 友军保护机制

        Args:
            args: {'entityId': str, 'srcId': str, 'damage': float, ...}
        """
        entity_id = args.get('entityId')
        src_id = args.get('srcId')

        if not entity_id or not src_id:
            return

        # 检查是否是铁傀儡受伤
        if not self._is_iron_golem(entity_id):
            return

        # 获取铁傀儡队伍
        golem_team = self._get_golem_team(entity_id)
        if not golem_team:
            return

        # 获取游戏系统
        game_system = self._get_game_system()
        if not game_system or not game_system.team_module:
            return

        # 获取攻击者队伍
        attacker_team = game_system.team_module.get_player_team(src_id)

        # 如果攻击者是友军,免疫伤害
        if attacker_team and attacker_team == golem_team:
            args['damage'] = 0
            args['knock'] = False
            args['ignite'] = False
            self.LogDebug("铁傀儡免疫友军伤害: golem={} attacker={}".format(
                entity_id, src_id))

    def _on_entity_removed(self, args):
        """
        实体移除事件 - 清理记录

        Args:
            args: {'entityId': str}
        """
        entity_id = args.get('entityId')
        if entity_id in self.golem_records:
            del self.golem_records[entity_id]

    def _on_entity_added(self, args):
        """
        实体生成事件 - 追踪新铁傀儡

        Args:
            args: {'entityId': str, 'engineTypeStr': str}
        """
        entity_id = args.get('entityId')
        engine_type = args.get('engineTypeStr')

        if engine_type == self.golem_entity_type:
            # 新铁傀儡生成,初始化记录
            self.golem_records[entity_id] = {
                'last_find_target': time.time(),
                'name_updated': False
            }
            self.LogInfo("检测到新铁傀儡生成: {}".format(entity_id))

    # ========== 辅助方法 ==========

    def _get_game_system(self):
        """
        获取BedWarsGameSystem实例

        Returns:
            BedWarsGameSystem: 游戏系统实例,未找到返回None
        """
        try:
            return serverApi.GetSystem("Script_NeteaseMod", "BedWarsGameSystem")
        except:
            return None

    def LogInfo(self, message):
        """输出Info日志"""
        print("[INFO] [IronGolemAISystem] {}".format(message))

    def LogDebug(self, message):
        """输出Debug日志"""
        # print("[DEBUG] [IronGolemAISystem] {}".format(message))
        pass

    def LogError(self, message):
        """输出Error日志"""
        print("[ERROR] [IronGolemAISystem] {}".format(message))
