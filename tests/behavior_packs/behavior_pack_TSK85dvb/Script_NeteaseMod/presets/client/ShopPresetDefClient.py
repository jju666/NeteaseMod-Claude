# -*- coding: utf-8 -*-
"""
商店预设 - 客户端

功能:
- 显示商店NPC特效
- 显示商店NPC名字(一直显示)
- 播放购买成功/失败音效
- 显示商店UI界面
- 显示商品预览特效
"""

from ECPresetServerScripts import PresetDefinitionClient


class ShopPresetDefClient(PresetDefinitionClient):
    """
    商店预设客户端实现

    核心功能:
    1. 商店NPC粒子特效 (浮动、旋转)
    2. 购买成功/失败音效
    3. 打开/关闭商店UI
    4. 商品预览显示
    """

    def __init__(self):
        super(ShopPresetDefClient, self).__init__()

        # 配置数据
        self.team = None  # type: str | None  # 队伍ID
        self.shop_type = None  # type: str | None  # 商店类型
        self._instance_id = None  # 预设实例ID

        # 特效ID列表
        self._effect_ids = []

        # NPC粒子效果ID
        self._npc_particle_id = None

        # UI状态
        self._ui_opened = False
        self._ui_registered = False  # UI是否已注册

    def on_init(self, instance):
        """
        预设初始化

        解析配置数据:
        - team: 队伍ID
        - shop_type: 商店类型

        Args:
            instance: PresetInstanceClient对象
        """
        self.team = instance.data.get("team", "NONE")
        self.shop_type = instance.data.get("shop_type", "items")
        self._instance_id = instance.instance_id  # 保存实例ID

        print("[INFO] [商店-客户端] 初始化: team={}, type={}".format(
            self.team, self.shop_type
        ))

    def get_instance_id(self):
        """获取预设实例ID"""
        return self._instance_id

    def on_start(self, instance):
        """
        预设启动

        执行步骤:
        1. 创建商店NPC粒子特效
        2. 注册事件监听

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [商店-客户端] 启动: team={}".format(self.team))

        # 1. 创建商店NPC粒子特效
        self._create_npc_particles(instance)

        # 注意: 事件通过on_server_message接收,不需要手动注册

    def on_tick(self, instance):
        """
        每Tick更新

        更新NPC粒子效果 (如果需要)

        Args:
            instance: PresetInstanceClient对象
        """
        # 商店客户端通常使用循环粒子,不需要Tick更新
        pass

    def on_stop(self, instance):
        """
        预设停止

        清理工作:
        1. 移除NPC粒子特效
        2. 关闭商店UI
        3. 取消事件监听

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [商店-客户端] 停止: team={}".format(self.team))

        # 移除NPC粒子特效
        if self._npc_particle_id:
            self._stop_particle(self._npc_particle_id)
            self._npc_particle_id = None

        # 关闭商店UI
        if self._ui_opened:
            self._close_shop_ui()

        # 停止所有特效
        self._stop_all_effects()

    def on_destroy(self, instance):
        """
        预设销毁

        最终清理工作

        Args:
            instance: PresetInstanceClient对象
        """
        print("[INFO] [商店-客户端] 销毁: team={}".format(self.team))

        # 清理数据
        self._effect_ids = []
        self._npc_particle_id = None
        self._ui_opened = False

    # ========== 接收服务端消息 ==========

    def on_server_message(self, instance, message_type, data):
        """
        接收服务端消息回调 - ECPreset框架标准接口

        Args:
            instance: PresetInstanceClient对象
            message_type: str 消息类型
            data: dict 消息数据
        """
        if message_type == "BedWarsShopTryOpen":
            self._on_shop_open(data)
        elif message_type == "BedWarsShopBuyResult":
            self._on_buy_result(data)
        elif message_type == "ShopNpcShowName":
            self._on_show_npc_name(data)

    # ========== 事件处理方法 ==========

    def _on_show_npc_name(self, event_data):
        """
        设置NPC名字一直显示

        当服务端设置完NPC名字后，调用此方法让客户端名字永久显示

        Args:
            event_data: 事件数据
                - entity_id: NPC实体ID
        """
        entity_id = event_data.get('entity_id')
        if not entity_id:
            print("[ERROR] [商店-客户端] ShopNpcShowName消息缺少entity_id")
            return

        try:
            import mod.client.extraClientApi as clientApi

            # 获取NameComponent（客户端）
            name_comp = clientApi.GetEngineCompFactory().CreateName(entity_id)
            if not name_comp:
                print("[WARN] [商店-客户端] 无法创建NameComponent: entity_id={}".format(entity_id))
                return

            # 设置名字一直显示（不需要看向实体）
            success = name_comp.SetAlwaysShowName(True)

            if success:
                print("[INFO] [商店-客户端] NPC名字设置为一直显示: entity_id={}".format(entity_id))
            else:
                print("[WARN] [商店-客户端] SetAlwaysShowName返回False: entity_id={}".format(entity_id))

        except Exception as e:
            print("[ERROR] [商店-客户端] 设置名字显示异常: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def _on_shop_open(self, event_data):
        """
        处理商店UI打开事件

        显示商店界面

        Args:
            event_data: 事件数据
                - ui_dict: UI数据字典
                - player_id: 玩家ID
        """
        player_id = event_data.get('player_id')
        ui_dict = event_data.get('ui_dict')

        print("[INFO] [商店-客户端] 打开UI: player={}, type={}".format(
            player_id, self.shop_type
        ))

        # 显示商店UI
        self._open_shop_ui(ui_dict)

        # 播放打开音效
        self._play_shop_open_sound()

    def _on_buy_result(self, event_data):
        """
        处理购买结果事件

        显示购买成功/失败提示,播放音效

        Args:
            event_data: 事件数据
                - success: 是否成功
                - msg: 消息
        """
        success = event_data.get('success', False)
        msg = event_data.get('msg', '')

        print("[INFO] [商店-客户端] 购买结果: success={}, msg={}".format(success, msg))

        # 播放购买音效
        if success:
            self._play_buy_success_sound()
            self._play_buy_success_effect()
        else:
            self._play_buy_fail_sound()

        # 显示提示消息
        # TODO: 需要UI系统支持
        # self._show_tip_message(msg)

    # ========== 内部辅助方法 ==========

    def _create_npc_particles(self, instance):
        """
        创建商店NPC粒子特效

        在NPC周围显示循环粒子

        Args:
            instance: PresetInstanceClient对象
        """
        # [FIX 2025-11-04] 修复PresetInstanceClient没有get_position()方法的问题
        position = instance.get_config("position") or instance.get_config("pos")
        if not position:
            print("[ERROR] [商店-客户端] 无法获取position配置")
            return

        print("[INFO] [商店-客户端] 创建NPC粒子: type={}, pos={}".format(
            self.shop_type, position
        ))

        # TODO: 需要引擎API支持
        # 在NPC周围创建循环粒子效果
        # npc_pos = {
        #     'x': position['x'],
        #     'y': position['y'] + 1.5,  # NPC上方1.5格
        #     'z': position['z']
        # }
        #
        # # 根据商店类型选择粒子颜色
        # particle_type = self._get_shop_particle_type(self.shop_type)
        # self._npc_particle_id = self._create_looping_particle(particle_type, npc_pos)

    def _register_ui(self):
        """注册商店UI到引擎"""
        if self._ui_registered:
            return

        try:
            import mod.client.extraClientApi as clientApi

            clientApi.RegisterUI(
                'bedwars_shop',  # UI名称
                'bedwars_shop',  # UI命名空间
                "Script_NeteaseMod.presets.client.BedWarsShopScreenNode.BedWarsShopScreenNode",  # ScreenNode类路径
                "bedwars_shop.main"  # UI JSON配置路径
            )

            self._ui_registered = True
            print("[INFO] [商店-客户端] UI注册成功")

        except Exception as e:
            print("[ERROR] [商店-客户端] UI注册失败: {}".format(e))
            import traceback
            traceback.print_exc()

    def _open_shop_ui(self, ui_dict):
        """
        打开商店UI

        Args:
            ui_dict: UI数据字典
        """
        print("[INFO] [商店-客户端] 打开商店界面")

        try:
            import mod.client.extraClientApi as clientApi
            from Script_NeteaseMod.modConfig import MOD_NAME

            # 通过ShopClientSystem推送UI
            # ShopClientSystem已经注册了bedwars_shop_screen
            clientApi.PushScreen(
                MOD_NAME,
                "bedwars_shop_screen",
                {
                    'ui_dict': ui_dict
                }
            )

            self._ui_opened = True
            print("[INFO] [商店-客户端] 商店UI推送成功")

        except Exception as e:
            print("[ERROR] [商店-客户端] 打开商店UI失败: {}".format(e))
            import traceback
            traceback.print_exc()

    def _close_shop_ui(self):
        """关闭商店UI"""
        print("[INFO] [商店-客户端] 关闭商店界面")

        # TODO: 需要UI系统支持
        # 隐藏商店UI屏幕
        # self._hide_ui_screen("bedwars_shop_screen")

        self._ui_opened = False

    def _play_shop_open_sound(self):
        """播放商店打开音效"""
        print("[INFO] [商店-客户端] 播放打开音效")

        # TODO: 需要引擎API支持
        # 播放"咻"的音效
        # position = self.instance.get_position()
        # self._play_sound("mob.villager.yes", position, volume=0.8)

    def _play_buy_success_sound(self):
        """播放购买成功音效"""
        print("[INFO] [商店-客户端] 播放购买成功音效")

        # TODO: 需要引擎API支持
        # 播放成功音效
        # position = self.instance.get_position()
        # self._play_sound("random.orb", position, volume=1.0, pitch=1.5)

    def _play_buy_fail_sound(self):
        """播放购买失败音效"""
        print("[INFO] [商店-客户端] 播放购买失败音效")

        # TODO: 需要引擎API支持
        # 播放失败音效
        # position = self.instance.get_position()
        # self._play_sound("mob.villager.no", position, volume=0.8)

    def _play_buy_success_effect(self):
        """播放购买成功特效"""
        print("[INFO] [商店-客户端] 播放购买成功特效")

        # TODO: 需要引擎API支持
        # position = self.instance.get_position()
        #
        # # 播放绿色粒子
        # for i in range(10):
        #     particle_id = self._create_particle("minecraft:villager_happy", position)

    def _get_shop_particle_type(self, shop_type):
        """
        获取商店粒子类型

        Args:
            shop_type: 商店类型

        Returns:
            str: 粒子类型
        """
        # 根据商店类型返回不同颜色的粒子
        particle_map = {
            'items': 'minecraft:blue_glint',     # 物品商店 - 蓝色
            'upgrades': 'minecraft:purple_glint',# 升级商店 - 紫色
        }

        return particle_map.get(shop_type, 'minecraft:white_glint')

    # ========== 特效和音效工具方法 ==========

    def _play_effect(self, effect_path, position):
        """
        播放特效

        Args:
            effect_path: 特效文件路径
            position: 特效位置 (dict: {x, y, z})

        Returns:
            int: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放特效: {} at {}".format(effect_path, position))
        return 0  # 占位返回

    def _stop_effect(self, effect_id):
        """
        停止特效

        Args:
            effect_id: 特效ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 停止特效: {}".format(effect_id))

    def _stop_all_effects(self):
        """停止所有特效"""
        for effect_id in self._effect_ids:
            self._stop_effect(effect_id)
        self._effect_ids = []

    def _play_sound(self, sound_path, position, volume=1.0, pitch=1.0):
        """
        播放音效

        Args:
            sound_path: 音效文件路径
            position: 播放位置
            volume: 音量 (0.0-1.0)
            pitch: 音调 (0.5-2.0)
        """
        # TODO: 需要引擎API支持
        print("[INFO] 播放音效: {} at {} (volume={}, pitch={})".format(
            sound_path, position, volume, pitch
        ))

    def _create_particle(self, particle_type, position):
        """
        创建粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置

        Returns:
            int: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 创建粒子效果: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    def _create_looping_particle(self, particle_type, position):
        """
        创建循环粒子效果

        Args:
            particle_type: 粒子类型
            position: 粒子位置

        Returns:
            int: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 创建循环粒子: {} at {}".format(particle_type, position))
        return 0  # 占位返回

    def _stop_particle(self, particle_id):
        """
        停止粒子效果

        Args:
            particle_id: 粒子效果ID
        """
        # TODO: 需要引擎API支持
        print("[INFO] 停止粒子效果: {}".format(particle_id))