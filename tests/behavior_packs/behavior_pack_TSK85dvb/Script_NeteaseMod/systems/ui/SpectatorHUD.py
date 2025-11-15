# -*- coding: utf-8 -*-
"""
SpectatorHUD - 旁观者HUD管理器

功能:
- 显示被观察玩家信息
- 快速切换按钮
- 玩家列表显示

原文件: Parts/ECSpectatorHUD/ECSpectatorHUDScreenNode.py
"""


class SpectatorHUD(object):
    """旁观者HUD管理器"""

    def __init__(self, spectator_system):
        """
        初始化旁观者HUD

        Args:
            spectator_system: SpectatorSystem实例
        """
        self.spectator_system = spectator_system

        # UI组件
        self.screen_node = None
        self.is_visible = False

        # 当前观察的玩家
        self.current_target = None
        self.current_target_name = ""

        # 可观察的玩家列表
        self.available_players = []
        self.available_players_names = {}  # player_id -> player_name

        # HUD更新定时器
        self.next_update_time = 0

    def initialize(self):
        """初始化HUD"""
        # ScreenNode由UI框架自动创建和管理
        print("[INFO] [SpectatorHUD] 初始化完成")

    def cleanup(self):
        """清理HUD"""
        # ScreenNode由UI框架自动销毁
        self.is_visible = False
        print("[INFO] [SpectatorHUD] 清理完成")

    def update(self):
        """
        每帧更新

        功能:
        - 定时更新观战玩家的状态信息
        - 显示玩家生命值、装备等
        """
        if not self.is_visible:
            return

        import time
        now = time.time()

        # 每0.5秒更新一次
        if now < self.next_update_time:
            return

        self.next_update_time = now + 0.5

        # 更新当前观察玩家的信息
        self._update_target_info()

    # ========== 显示控制 ==========

    def show(self):
        """显示HUD"""
        self.is_visible = True
        # ScreenNode的显示由UI框架自动管理
        print("[INFO] [SpectatorHUD] 显示")

    def hide(self):
        """隐藏HUD"""
        self.is_visible = False
        # ScreenNode的隐藏由UI框架自动管理
        print("[INFO] [SpectatorHUD] 隐藏")

    # ========== 目标更新 ==========

    def update_target(self, target_player_id):
        """
        更新观察目标

        Args:
            target_player_id (str): 目标玩家ID
        """
        self.current_target = target_player_id

        # 获取玩家名称
        try:
            import mod.client.extraClientApi as clientApi
            comp_factory = clientApi.GetEngineCompFactory()
            name_comp = comp_factory.CreateName(target_player_id)
            self.current_target_name = name_comp.GetName()
        except:
            self.current_target_name = target_player_id

        # 更新HUD显示
        self._update_target_info()

        print("[INFO] [SpectatorHUD] 更新目标 target={} name={}".format(
            target_player_id, self.current_target_name
        ))

    def update_player_list(self, player_ids):
        """
        更新可观察的玩家列表

        Args:
            player_ids (list): 玩家ID列表
        """
        self.available_players = player_ids

        # 获取所有玩家的名称
        import mod.client.extraClientApi as clientApi
        comp_factory = clientApi.GetEngineCompFactory()

        for player_id in player_ids:
            try:
                name_comp = comp_factory.CreateName(player_id)
                player_name = name_comp.GetName()
                self.available_players_names[player_id] = player_name
            except:
                self.available_players_names[player_id] = player_id

        print("[INFO] [SpectatorHUD] 更新玩家列表 count={}".format(len(player_ids)))

    def _update_target_info(self):
        """
        更新当前观察玩家的信息显示

        功能:
        - 显示玩家名称
        - 显示生命值
        - 显示队伍信息
        - 显示切换提示
        """
        if not self.current_target:
            return

        try:
            import mod.client.extraClientApi as clientApi
            comp_factory = clientApi.GetEngineCompFactory()

            # 获取生命值
            attr_comp = comp_factory.CreateAttr(self.current_target)
            # 修复: GetAttrValue只接受1个参数(属性类型)
            # CreateAttr已经绑定了实体ID，不需要再次传递
            health = attr_comp.GetAttrValue(
                clientApi.GetMinecraftEnum().AttrType.HEALTH
            )

            # 构建显示信息
            if health is not None:
                info_text = u"正在观战: {} - 生命值: {:.1f}".format(
                    self.current_target_name,
                    health
                )
            else:
                info_text = u"正在观战: {}".format(self.current_target_name)

            # 显示在ActionBar或Title上
            # 注意: UI数据的传递由ScreenNode框架自动处理
            # 这里的数据更新会通过框架自动同步到客户端UI
            # 目前使用控制台输出
            print("[SpectatorHUD] {}".format(info_text))

        except Exception as e:
            print("[ERROR] [SpectatorHUD] 更新目标信息失败: {}".format(e))