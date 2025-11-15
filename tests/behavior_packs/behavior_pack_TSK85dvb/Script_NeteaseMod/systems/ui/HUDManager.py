# -*- coding: utf-8 -*-
"""
HUDManager - HUD管理器

功能:
- 管理HUD界面组件
- 消息堆叠显示
- 计分板显示
- 队伍状态显示

原文件: Parts/ECHUD/ECHUDScreenNode.py
重构为: systems/ui/HUDManager.py
"""

from __future__ import print_function
import mod.client.extraClientApi as clientApi


class HUDManager(object):
    """HUD管理器"""

    def __init__(self, hud_system):
        """
        初始化HUD管理器

        Args:
            hud_system: HUDSystem实例
        """
        self.hud_system = hud_system

        # UI组件
        self.screen_node = None  # ECHUDScreenNode实例
        self.is_visible = False

        # 队伍状态数据
        self.team_data = {}  # {team_id: {'player_count': int, 'bed_alive': bool}}

        # 游戏阶段数据
        self.current_phase = None
        self.phase_description = ""

    def initialize(self):
        """初始化HUD"""
        try:
            # 重要: 必须使用clientApi.CreateUI()创建ScreenNode
            # 不能直接实例化，否则UI不会正确渲染
            # UI已在modMain.py中通过RegisterUI注册
            self.screen_node = clientApi.CreateUI("ecbedwars", "ECHUDScreenNode", {})

            if not self.screen_node:
                print("[ERROR] [HUDManager] CreateUI返回None，ScreenNode创建失败")
                return

            self.is_visible = True
            print("[INFO] [HUDManager] ScreenNode创建成功")

        except Exception as e:
            print("[ERROR] [HUDManager] 初始化失败: {}".format(str(e)))
            import traceback
            print(traceback.format_exc())

    def cleanup(self):
        """清理HUD"""
        try:
            if self.screen_node:
                # 使用clientApi.DestroyUI()销毁ScreenNode
                # 这会自动调用ScreenNode的OnDestroy方法
                clientApi.DestroyUI("ecbedwars", "ECHUDScreenNode")
                self.screen_node = None

            self.is_visible = False
            print("[INFO] [HUDManager] 清理完成")

        except Exception as e:
            print("[ERROR] [HUDManager] 清理失败: {}".format(str(e)))

    def update(self):
        """每帧更新"""
        if not self.is_visible or not self.screen_node:
            return

        # 当前实现：HUD数据通过事件更新，不需要额外的定时更新逻辑

    # ========== 堆叠消息控制 ==========

    def handle_top_message(self, action, data):
        """
        处理顶部消息控制事件

        Args:
            action (str): 操作类型
            data (dict): 控制数据
        """
        if not self.screen_node:
            return

        # 直接传递给StackMsgController
        self.screen_node.stack_msg_top.handle_control(data)

    def handle_bottom_message(self, action, data):
        """
        处理底部消息控制事件

        Args:
            action (str): 操作类型
            data (dict): 控制数据
        """
        if not self.screen_node:
            return

        # 直接传递给StackMsgController
        self.screen_node.stack_msg_bottom.handle_control(data)

    # ========== 计分板控制 ==========

    def handle_scoreboard(self, action, data):
        """
        处理计分板控制事件

        Args:
            action (str): 操作类型
            data (dict): 控制数据
        """
        if not self.screen_node:
            return

        # 直接传递给ScoreboardController
        self.screen_node.scoreboard.handle_control(data)

    # ========== 队伍状态 ==========

    def update_team_info(self, team_id, player_count, bed_alive):
        """
        更新队伍信息

        Args:
            team_id (str): 队伍ID
            player_count (int): 存活人数
            bed_alive (bool): 床是否存活
        """
        self.team_data[team_id] = {
            'player_count': player_count,
            'bed_alive': bed_alive
        }
        print("[INFO] [HUDManager] 更新队伍 {} count={} bed={}".format(
            team_id, player_count, bed_alive
        ))

    def update_team_bed_status(self, team_id, destroyed):
        """
        更新队伍床状态

        Args:
            team_id (str): 队伍ID
            destroyed (bool): 是否被破坏
        """
        if team_id in self.team_data:
            self.team_data[team_id]['bed_alive'] = not destroyed
        else:
            self.team_data[team_id] = {
                'player_count': 0,
                'bed_alive': not destroyed
            }

    # ========== 游戏阶段 ==========

    def update_game_phase(self, phase, description):
        """
        更新游戏阶段

        Args:
            phase (str): 阶段名称
            description (str): 阶段描述
        """
        self.current_phase = phase
        self.phase_description = description
        print("[INFO] [HUDManager] 更新游戏阶段 phase={} desc={}".format(phase, description))

    # ========== 显示控制 ==========

    def show(self):
        """显示HUD"""
        self.is_visible = True
        # ScreenNode的显示由UI框架自动管理

    def hide(self):
        """隐藏HUD"""
        self.is_visible = False
        # ScreenNode的隐藏由UI框架自动管理