# -*- coding: utf-8 -*-
"""
SprayManager - 喷漆管理器

功能:
- 处理玩家喷漆放置
- 管理喷漆实体
- 清理喷漆

原文件: Parts/ECBedWarsOrnament/Spray/SprayManager.py
重构为: systems/ornament_system/spray/SprayManager.py
"""

import mod.server.extraServerApi as serverApi


class SprayManager(object):
    """
    喷漆管理器

    负责喷漆的放置、管理和清理
    """

    def __init__(self, ornament_system):
        """
        初始化喷漆管理器

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        # 喷漆数据
        # key: (dimension, (x, y, z)), value: entity_id
        # 参考老项目: sprays = {(dimention, (x, y, z)): entity_id}
        self.spray_entities = {}  # 当前场景中的喷漆实体字典
        self.spray_config = {}  # 喷漆配置


        print("[INFO] [SprayManager] 初始化完成")

    def initialize(self):
        """初始化喷漆管理器"""
        try:
            # 加载喷漆配置
            self._load_spray_config()

            # 注册事件监听
            self._register_events()

            print("[INFO] [SprayManager] 喷漆管理器初始化成功")
        except Exception as e:
            print("[ERROR] [SprayManager] 初始化失败: {}".format(str(e)))

    def cleanup(self):
        """清理喷漆管理器"""
        try:
            # 清理所有喷漆实体
            self.clear_all_sprays()

            print("[INFO] [SprayManager] 清理完成")
        except Exception as e:
            print("[ERROR] [SprayManager] 清理失败: {}".format(str(e)))

    def _load_spray_config(self):
        """加载喷漆配置（从配置文件）"""
        try:
            from Script_NeteaseMod.config import ornament_config

            self.spray_config = ornament_config.SPRAY_CONFIG
            print("[INFO] [SprayManager] 从配置文件加载 {} 个喷漆".format(len(self.spray_config)))

        except Exception as e:
            print("[ERROR] [SprayManager] 加载配置失败: {}".format(str(e)))
            # 使用默认配置
            self.spray_config = {
                "default": {
                    "id": "default",
                    "name": u"默认喷漆",
                    "variant": 0,
                    "price": 0,
                    "unlocked_by_default": True
                }
            }
            print("[WARN] [SprayManager] 使用默认喷漆配置")

    def _register_events(self):
        """
        注册事件监听

        老项目使用BlockUseEventWhiteList监听物品框点击
        新架构使用ServerItemUseOnEvent事件
        """
        # 监听玩家右键方块事件(物品框点击)
        self.game_system.ListenForEvent(
            serverApi.GetEngineNamespace(),
            serverApi.GetEngineSystemName(),
            'ServerBlockUseEvent',
            self,
            self.on_player_use_block
        )

        print("[INFO] [SprayManager] 事件监听注册完成")

    # ========== 事件处理 ==========

    def on_player_use_block(self, args):
        """
        玩家右键方块事件

        参考老项目SprayManager.on_player_use_block()
        只响应物品框(frame/glow_frame)的点击

        Args:
            args: {
                'playerId': player_id,
                'blockName': block_name,
                'x': x, 'y': y, 'z': z,
                'dimensionId': dimension,
                'cancel': False
            }
        """
        block_name = args.get('blockName', '')

        # 只处理物品框
        if block_name != 'minecraft:frame' and block_name != 'minecraft:glow_frame':
            return

        # 取消默认行为(防止打开物品框界面)
        args['cancel'] = True

        player_id = args.get('playerId')
        dimension = args.get('dimensionId')
        pos = (args.get('x'), args.get('y'), args.get('z'))

        if not player_id or not pos or dimension is None:
            return

        # 如果位置已有喷漆,移除
        spray_key = (dimension, pos)
        if spray_key in self.spray_entities:
            entity_id = self.spray_entities[spray_key]
            self._remove_spray_entity(entity_id, spray_key)
            print("[INFO] [SprayManager] 移除位置 {} 的旧喷漆".format(pos))

        # 获取玩家装备的喷漆
        spray_id = self.ornament_system.get_player_ornament(player_id, 'spray')

        # 如果玩家未装备喷漆或装备的喷漆不在配置中,使用默认喷漆
        if not spray_id or spray_id not in self.spray_config:
            spray_id = 'spray.default'
            print("[INFO] [SprayManager] 玩家 {} 未装备喷漆,使用默认喷漆".format(player_id))

        # 获取喷漆配置(使用.get()避免KeyError)
        spray_data = self.spray_config.get(spray_id)
        if not spray_data:
            # 如果连spray.default都不存在,使用fallback配置
            print("[ERROR] [SprayManager] 喷漆配置 {} 不存在,使用fallback默认配置".format(spray_id))
            spray_data = {
                "id": "spray.default",
                "name": u"默认喷漆",
                "variant": 0
            }

        # 获取物品框朝向(facing_direction状态)
        comp = serverApi.GetEngineCompFactory()
        block_comp = comp.CreateBlockState(serverApi.GetLevelId())
        states = block_comp.GetBlockStates(pos, dimension)
        face = states.get('facing_direction', 2) if states else 2

        # 放置喷漆
        self.place_spray(player_id, pos, dimension, spray_data, face)

    # ========== 喷漆操作 ==========

    def place_spray(self, player_id, pos, dimension, spray_data, face):
        """
        放置喷漆

        参考老项目SprayManager中的实现

        Args:
            player_id (str): 玩家ID
            pos (tuple): 方块位置 (x, y, z)
            dimension (int): 维度ID
            spray_data (dict): 喷漆数据 {'id':..., 'variant':..., 'name':...}
            face (int): 物品框朝向(facing_direction: 2=north, 3=south, 4=west, 5=east)
        """
        try:
            variant = spray_data.get('variant', 0)
            spray_id = spray_data.get('id', 'default')
            spray_name = spray_data.get('name', u'默认')

            # 创建喷漆实体
            # 位置: 方块中心点 (x+0.5, y, z+0.5)
            spray_pos = (pos[0] + 0.5, pos[1], pos[2] + 0.5)
            entity_id = self._create_spray_entity(spray_pos, (0, 0), dimension, variant, face)

            if entity_id:
                # 记录到spray_entities字典 (key: (dimension, pos))
                spray_key = (dimension, pos)
                self.spray_entities[spray_key] = entity_id

                # 播放音效(蜘蛛声音)
                comp = serverApi.GetEngineCompFactory()
                game_comp = comp.CreateGame(serverApi.GetLevelId())
                game_comp.PlaySound(spray_pos, "mob.spider.say", 1.0, 1.0, False)

                # 播放粒子效果
                # 粒子位置在方块中心稍上方
                particle_pos = (pos[0] + 0.5, pos[1] + 0.5, pos[2] + 0.5)
                game_comp.PlayEffect("ecbedwars:spray", particle_pos, dimension, None)

                print("[INFO] [SprayManager] 玩家 {} 放置喷漆 '{}' entity={} at {}".format(
                    player_id, spray_name, entity_id, pos))
            else:
                print("[ERROR] [SprayManager] 创建喷漆实体失败")

        except Exception as e:
            print("[ERROR] [SprayManager] 放置喷漆失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def clear_dimension_sprays(self, dimension):
        """
        清理指定维度的所有喷漆

        参考老项目SprayManager.clear_dimension()

        Args:
            dimension (int): 维度ID
        """
        removed_count = 0
        for spray_key in list(self.spray_entities.keys()):
            if spray_key[0] == dimension:
                entity_id = self.spray_entities[spray_key]
                self._remove_spray_entity(entity_id, spray_key)
                removed_count += 1

        print("[INFO] [SprayManager] 清理维度 {} 的 {} 个喷漆".format(dimension, removed_count))

    def clear_all_sprays(self):
        """清理所有喷漆"""
        removed_count = len(self.spray_entities)
        for spray_key in list(self.spray_entities.keys()):
            entity_id = self.spray_entities[spray_key]
            self._remove_spray_entity(entity_id, spray_key)

        print("[INFO] [SprayManager] 已清理所有喷漆 (共{}个)".format(removed_count))

    # ========== 内部方法 ==========

    def _create_spray_entity(self, pos, rot, dimension, variant, face):
        """
        创建喷漆实体

        参考老项目:
        - 使用自定义实体 ecbedwars:spray
        - SetVariant(variant) 设置喷漆材质索引
        - SetMarkVariant(face-2) 设置朝向骨骼显示

        Args:
            pos (tuple): 位置 (x, y, z)
            rot (tuple): 旋转 (yaw, pitch)
            dimension (int): 维度ID
            variant (int): 喷漆变体索引(0-53)
            face (int): 物品框朝向(2=north, 3=south, 4=west, 5=east)

        Returns:
            str: 实体ID,失败返回None
        """
        try:
            comp = serverApi.GetEngineCompFactory()

            # 创建自定义喷漆实体
            entity_id = comp.CreateEngineEntity(serverApi.GetLevelId())\
                .CreateEngineTypeEntity("ecbedwars:spray", pos, (0, 0), dimension, True)

            if not entity_id:
                print("[ERROR] [SprayManager] CreateEngineTypeEntity失败")
                return None

            # 设置variant(选择喷漆材质)
            entity_def_comp = comp.CreateEntityDefinitions(entity_id)
            entity_def_comp.SetVariant(variant)

            # 设置mark_variant(控制朝向骨骼显示)
            # face: 2=north, 3=south, 4=west, 5=east
            # mark_variant: 0=n, 1=s, 2=w, 3=e
            mark_variant = face - 2
            entity_def_comp.SetMarkVariant(mark_variant)

            return entity_id

        except Exception as e:
            print("[ERROR] [SprayManager] 创建喷漆实体异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return None

    def _remove_spray_entity(self, entity_id, spray_key):
        """
        移除喷漆实体

        参考老项目使用DestroyEntity()而不是KillEntity()

        Args:
            entity_id (str): 实体ID
            spray_key (tuple): 喷漆键 (dimension, (x, y, z))
        """
        try:
            comp = serverApi.GetEngineCompFactory()
            entity_comp = comp.CreateEngineEntity(serverApi.GetLevelId())
            entity_comp.RemoveEntity(entity_id)

            # 从字典中移除
            if spray_key in self.spray_entities:
                del self.spray_entities[spray_key]

        except Exception as e:
            print("[ERROR] [SprayManager] 移除喷漆实体失败: {}".format(str(e)))

    def _send_message(self, player_id, message):
        """
        发送消息给玩家

        Args:
            player_id (str): 玩家ID
            message (str): 消息内容
        """
        comp = serverApi.GetEngineCompFactory()
        msg_comp = comp.CreateMsg(player_id)
        msg_comp.NotifyOneMessage(player_id, message, "§e")