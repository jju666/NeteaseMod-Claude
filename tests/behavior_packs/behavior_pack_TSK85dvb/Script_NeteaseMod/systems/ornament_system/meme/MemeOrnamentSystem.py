# -*- coding: utf-8 -*-
"""
MemeOrnamentSystem - 墓碑装饰系统

功能:
- 配置化加载墓碑装饰(meme)
- 玩家死亡时生成墓碑实体
- 资源收集时生成墓碑展示
- 定时销毁墓碑实体

原文件: Parts/ECBedWarsOrnament/ornament/BedWarsOrnamentMeme.py
重构为: systems/ornament_system/meme/MemeOrnamentSystem.py
"""

import mod.server.extraServerApi as serverApi
import json
import os


class MemeOrnamentSystem(object):
    """
    墓碑装饰系统

    管理玩家死亡/收集资源时的墓碑(meme)特效
    """

    def __init__(self, ornament_system):
        """
        初始化墓碑系统

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system  # BedWarsGameSystem
        self.comp_factory = serverApi.GetEngineCompFactory()

        # 墓碑配置数据 {meme_id: config_dict}
        self.meme_configs = {}

        # 已生成的墓碑实体 {entity_id: {'player_id': str, 'destroy_time': float}}
        self.spawned_memes = {}

        # 定时器系统(用于销毁墓碑)
        self.timers = []  # [(destroy_time, entity_id), ...]

        print("[INFO] [MemeOrnamentSystem] 初始化完成")

    def initialize(self):
        """初始化墓碑系统"""
        try:
            # 加载墓碑配置
            self._load_meme_config()

            print("[INFO] [MemeOrnamentSystem] 系统初始化成功，已加载 {} 个墓碑".format(
                len(self.meme_configs)
            ))
        except Exception as e:
            print("[ERROR] [MemeOrnamentSystem] 初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """清理墓碑系统"""
        try:
            # 销毁所有墓碑实体
            for entity_id in list(self.spawned_memes.keys()):
                self._destroy_meme_entity(entity_id)

            self.spawned_memes = {}
            self.timers = []

            print("[INFO] [MemeOrnamentSystem] 清理完成")
        except Exception as e:
            print("[ERROR] [MemeOrnamentSystem] 清理失败: {}".format(str(e)))

    def _load_meme_config(self):
        """加载墓碑配置文件"""
        try:
            # 获取配置文件路径
            # 假设脚本在 behavior_packs/behavior_pack_TSK85dvb/Script_NeteaseMod/
            script_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(script_dir, 'config', 'ornaments', 'meme.json')

            print("[INFO] [MemeOrnamentSystem] 尝试加载配置: {}".format(config_path))

            # 读取配置文件
            if not os.path.exists(config_path):
                print("[WARN] [MemeOrnamentSystem] 配置文件不存在: {}".format(config_path))
                self._load_default_config()
                return

            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # 解析墓碑配置
            meme_list = config_data.get('meme_ornaments', [])
            for meme_config in meme_list:
                meme_id = meme_config.get('id')
                if meme_id:
                    self.meme_configs[meme_id] = meme_config

            print("[INFO] [MemeOrnamentSystem] 成功加载 {} 个墓碑配置".format(
                len(self.meme_configs)
            ))

        except Exception as e:
            print("[ERROR] [MemeOrnamentSystem] 加载配置失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

            # 使用默认配置
            self._load_default_config()

    def _load_default_config(self):
        """加载默认墓碑配置"""
        print("[WARN] [MemeOrnamentSystem] 使用默认墓碑配置")

        # 默认配置(8个墓碑)
        default_memes = [
            {"id": "smile", "name": u"微笑", "variant": 1},
            {"id": "black", "name": u"黑脸", "variant": 2},
            {"id": "embrace", "name": u"尴尬", "variant": 3},
            {"id": "huaji", "name": u"滑稽", "variant": 4},
            {"id": "angry", "name": u"狂怒", "variant": 5},
            {"id": "qm", "name": u"问号", "variant": 6},
            {"id": "ec", "name": u"EC", "variant": 7},
            {"id": "anubis", "name": u"阿努比斯", "variant": 8},
        ]

        for meme in default_memes:
            meme_id = meme['id']
            self.meme_configs[meme_id] = {
                "id": meme_id,
                "name": meme['name'],
                "variant": meme['variant'],
                "entity_type": "ecbedwars:meme",
                "duration": 5.0,
                "display_on_death": True,
                "display_on_resource_collect": True
            }

    # ========== 墓碑生成 ==========

    def spawn_meme(self, player_id, pos, dimension):
        """
        生成墓碑实体

        Args:
            player_id (str): 玩家ID
            pos (tuple): 生成位置 (x, y, z)
            dimension (int): 维度ID

        Returns:
            str: 墓碑实体ID，失败返回None
        """
        try:
            # 获取玩家装备的墓碑配置
            meme_config = self.get_player_meme_config(player_id)
            if not meme_config:
                return None

            # 检查是否允许在死亡时显示
            if not meme_config.get('display_on_death', True):
                return None

            # 创建墓碑实体
            entity_type = meme_config.get('entity_type', 'ecbedwars:meme')
            entity_id = self.comp_factory.CreateEngineEntityByTypeStr(
                entity_type,
                pos,
                (0, 0),  # 旋转角度
                dimension,
                True  # 是否立即生成
            )

            if not entity_id:
                print("[ERROR] [MemeOrnamentSystem] 创建墓碑实体失败 pos={}".format(pos))
                return None

            # 设置墓碑variant(外观)
            variant = meme_config.get('variant', 1)
            comp_def = self.comp_factory.CreateEntityDefinitions(entity_id)
            if comp_def:
                comp_def.SetVariant(variant)

            # 记录墓碑实体
            duration = meme_config.get('duration', 5.0)
            import time
            destroy_time = time.time() + duration

            self.spawned_memes[entity_id] = {
                'player_id': player_id,
                'destroy_time': destroy_time,
                'pos': pos,
                'dimension': dimension
            }

            # 添加定时器(延迟销毁)
            self.timers.append((destroy_time, entity_id))

            print("[INFO] [MemeOrnamentSystem] 生成墓碑 player={} variant={} pos={} entity_id={}".format(
                player_id, variant, pos, entity_id
            ))

            return entity_id

        except Exception as e:
            print("[ERROR] [MemeOrnamentSystem] 生成墓碑失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()
            return None

    def spawn_meme_at_generator(self, player_id, generator_pos, dimension):
        """
        在生成器上方生成墓碑展示

        Args:
            player_id (str): 玩家ID
            generator_pos (tuple): 生成器位置 (x, y, z)
            dimension (int): 维度ID

        Returns:
            str: 墓碑实体ID，失败返回None
        """
        try:
            # 获取玩家装备的墓碑配置
            meme_config = self.get_player_meme_config(player_id)
            if not meme_config:
                return None

            # 检查是否允许在资源收集时显示
            if not meme_config.get('display_on_resource_collect', True):
                return None

            # 计算生成位置(生成器上方1-2格)
            spawn_pos = (
                generator_pos[0],
                generator_pos[1] + 2.0,
                generator_pos[2]
            )

            # 生成墓碑(复用spawn_meme逻辑)
            return self.spawn_meme(player_id, spawn_pos, dimension)

        except Exception as e:
            print("[ERROR] [MemeOrnamentSystem] 在生成器生成墓碑失败: {}".format(str(e)))
            return None

    # ========== 墓碑销毁 ==========

    def update(self):
        """
        更新墓碑系统(定时器检查)

        需要在游戏主循环中调用
        """
        import time
        current_time = time.time()

        # 检查定时器,销毁到期的墓碑
        timers_to_remove = []

        for destroy_time, entity_id in self.timers:
            if current_time >= destroy_time:
                # 销毁墓碑
                self._destroy_meme_entity(entity_id)
                timers_to_remove.append((destroy_time, entity_id))

        # 移除已处理的定时器
        for timer in timers_to_remove:
            if timer in self.timers:
                self.timers.remove(timer)

    def _destroy_meme_entity(self, entity_id):
        """
        销毁墓碑实体

        Args:
            entity_id (str): 墓碑实体ID
        """
        try:
            # 销毁实体
            comp_engine = self.comp_factory.CreateEngineType(entity_id)
            if comp_engine:
                self.game_system.DestroyEntity(entity_id)

            # 移除记录
            if entity_id in self.spawned_memes:
                del self.spawned_memes[entity_id]

        except Exception as e:
            print("[ERROR] [MemeOrnamentSystem] 销毁墓碑实体失败: {}".format(str(e)))

    # ========== 玩家数据接口 ==========

    def get_player_meme_config(self, player_id):
        """
        获取玩家装备的墓碑配置

        从OrnamentSystem的玩家数据缓存中读取墓碑ID，
        然后返回对应的配置

        Args:
            player_id (str): 玩家ID

        Returns:
            dict: 墓碑配置，未装备返回None
        """
        try:
            # 从OrnamentSystem获取玩家装备的墓碑ID
            meme_id = self.ornament_system.get_player_ornament(player_id, 'meme')

            if not meme_id:
                # 未装备墓碑
                return None

            # 返回墓碑配置
            meme_config = self.meme_configs.get(meme_id)

            if not meme_config:
                print("[WARN] [MemeOrnamentSystem] 找不到墓碑配置 meme_id={}".format(meme_id))
                return None

            return meme_config

        except Exception as e:
            print("[ERROR] [MemeOrnamentSystem] 获取玩家墓碑配置失败: {}".format(str(e)))
            return None

    def get_all_meme_configs(self):
        """
        获取所有墓碑配置

        Returns:
            dict: {meme_id: config_dict}
        """
        return self.meme_configs

    # ========== 工具方法 ==========

    def get_meme_config_by_id(self, meme_id):
        """
        根据墓碑ID获取配置

        Args:
            meme_id (str): 墓碑ID

        Returns:
            dict: 墓碑配置，未找到返回None
        """
        return self.meme_configs.get(meme_id)
