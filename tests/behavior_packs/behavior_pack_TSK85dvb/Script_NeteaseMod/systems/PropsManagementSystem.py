# -*- coding: utf-8 -*-
"""
PropsManagementSystem - 道具管理系统(服务端)

功能:
- 管理所有游戏道具的行为逻辑
- 插件化道具架构
- 统一道具触发和生命周期管理
- 支持6种道具(火球、防御塔、铁傀儡、蠹虫、搭路蛋、TNT)

原文件: Parts/Prop*/Prop*Part.py (6个道具Part)
重构为: systems/PropsManagementSystem.py + props/*Handler.py
"""

import mod.server.extraServerApi as serverApi


class PropsManagementSystem(serverApi.GetServerSystemCls()):
    """
    道具管理系统

    核心职责:
    - 注册所有道具处理器
    - 提供统一的道具触发接口
    - 管理道具生命周期(Create/Destroy/Update)
    - 协调道具与游戏系统的交互

    重构说明:
    - 原实现使用6个独立的Part
    - 现使用统一的System + Handler模式
    - Handler实现IPropHandler接口
    """

    def __init__(self, namespace, systemName):
        """
        初始化道具管理系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        super(PropsManagementSystem, self).__init__(namespace, systemName)

        # 道具处理器字典 {prop_type: IPropHandler}
        self.prop_handlers = {}

        # 跨系统引用
        self.bedwars_game_system = None  # BedWarsGameSystem实例引用

        print("[INFO] [PropsManagementSystem] 初始化完成")

        # ========== 重要：手动调用Create() ==========
        # 说明：网易引擎设计上只自动触发Destroy()，不自动触发Create()
        print("[PropsManagementSystem] 手动调用Create()完成系统初始化")
        self.Create()

    # ========== ServerSystem生命周期 ==========

    def Create(self):
        """系统创建时调用"""
        self.LogInfo("PropsManagementSystem.Create")

        # 注册所有道具处理器
        self._register_all_props()

        # 初始化所有道具处理器
        for prop_type, handler in self.prop_handlers.items():
            try:
                handler.on_create(self)
                self.LogInfo("道具处理器已初始化: {}".format(prop_type))
            except Exception as e:
                self.LogError("初始化道具处理器{}失败: {}".format(prop_type, str(e)))

        # 获取BedWarsGameSystem引用
        self._initialize_game_system_reference()

        print("[INFO] [PropsManagementSystem] Create完成")

    def Destroy(self):
        """系统销毁时调用"""
        self.LogInfo("PropsManagementSystem.Destroy")

        # 清理所有道具处理器
        for prop_type, handler in self.prop_handlers.items():
            try:
                handler.on_destroy()
                self.LogInfo("道具处理器已清理: {}".format(prop_type))
            except Exception as e:
                self.LogError("清理道具处理器{}失败: {}".format(prop_type, str(e)))

        self.prop_handlers = {}

        print("[INFO] [PropsManagementSystem] Destroy完成")

    def Update(self):
        """系统每帧更新"""
        # 更新所有需要Tick的道具
        for handler in self.prop_handlers.values():
            if getattr(handler, 'enable_tick', False):
                try:
                    handler.on_update()
                except Exception as e:
                    self.LogError("道具处理器更新失败: {}".format(str(e)))

    # ========== 日志方法 ==========

    def LogInfo(self, message):
        """输出Info日志"""
        print("[INFO] [PropsManagementSystem] {}".format(message))

    def LogDebug(self, message):
        """输出Debug日志"""
        # print("[DEBUG] [PropsManagementSystem] {}".format(message))
        pass

    def LogError(self, message):
        """输出Error日志"""
        print("[ERROR] [PropsManagementSystem] {}".format(message))

    def LogWarn(self, message):
        """输出Warn日志"""
        print("[WARN] [PropsManagementSystem] {}".format(message))

    # ========== 道具注册 ==========

    def _register_all_props(self):
        """注册所有道具处理器"""
        # 火球
        try:
            from Script_NeteaseMod.systems.props.PropFireballHandler import PropFireballHandler
            self.prop_handlers["fireball"] = PropFireballHandler()
        except Exception as e:
            self.LogWarn("火球处理器注册失败: {}".format(str(e)))

        # 防御塔
        try:
            from Script_NeteaseMod.systems.props.PropDefenseTowerHandler import PropDefenseTowerHandler
            self.prop_handlers["defense_tower"] = PropDefenseTowerHandler()
        except Exception as e:
            self.LogWarn("防御塔处理器注册失败: {}".format(str(e)))

        # 铁傀儡
        try:
            from Script_NeteaseMod.systems.props.PropIronGolemHandler import PropIronGolemHandler
            self.prop_handlers["iron_golem"] = PropIronGolemHandler()
        except Exception as e:
            self.LogWarn("铁傀儡处理器注册失败: {}".format(str(e)))

        # 蠹虫
        try:
            from Script_NeteaseMod.systems.props.PropBedbugHandler import PropBedbugHandler
            self.prop_handlers["bedbug"] = PropBedbugHandler()
        except Exception as e:
            self.LogWarn("蠹虫处理器注册失败: {}".format(str(e)))

        # 搭路蛋
        try:
            from Script_NeteaseMod.systems.props.PropBridgeEggHandler import PropBridgeEggHandler
            self.prop_handlers["bridge_egg"] = PropBridgeEggHandler()
        except Exception as e:
            self.LogWarn("搭路蛋处理器注册失败: {}".format(str(e)))

        # TNT
        try:
            from Script_NeteaseMod.systems.props.PropTNTHandler import PropTNTHandler
            self.prop_handlers["tnt"] = PropTNTHandler()
        except Exception as e:
            self.LogWarn("TNT处理器注册失败: {}".format(str(e)))

        self.LogInfo("已注册{}个道具处理器".format(len(self.prop_handlers)))

    # ========== 道具触发接口 ==========

    def trigger_prop(self, prop_type, player_id, **kwargs):
        """
        触发道具使用

        Args:
            prop_type (str): 道具类型
            player_id (str): 玩家ID
            **kwargs: 道具参数
        """
        handler = self.prop_handlers.get(prop_type)
        if not handler:
            self.LogError("trigger_prop: 未知道具类型 {}".format(prop_type))
            return False

        try:
            handler.on_trigger(player_id, **kwargs)
            self.LogDebug("道具触发成功: {} by {}".format(prop_type, player_id))
            return True
        except Exception as e:
            self.LogError("道具触发失败: {} - {}".format(prop_type, str(e)))
            return False

    # ========== 辅助接口 ==========

    def get_bedwars_game_system(self):
        """
        获取BedWarsGameSystem引用

        Returns:
            BedWarsGameSystem: 游戏系统实例
        """
        return self.bedwars_game_system

    def _initialize_game_system_reference(self):
        """初始化BedWarsGameSystem引用"""
        try:
            self.bedwars_game_system = serverApi.GetSystem(self.namespace, "BedWarsGameSystem")
            if self.bedwars_game_system:
                self.LogInfo("BedWarsGameSystem引用获取成功")
            else:
                self.LogWarn("BedWarsGameSystem未找到")
        except Exception as e:
            self.LogError("获取BedWarsGameSystem引用失败: {}".format(str(e)))
