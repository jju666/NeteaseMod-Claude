# -*- coding: utf-8 -*-
"""
FocusUI - 焦点UI

功能:
- 显示重要游戏事件提示
- 床被破坏提示
- 游戏阶段变化提示
- 队伍淘汰提示

原文件: Parts/ECFocusNode/ECFocusNodePart.py
"""

import mod.client.extraClientApi as clientApi


class FocusUI(object):
    """焦点UI管理器"""

    def __init__(self):
        """初始化焦点UI"""
        # UI组件
        self.screen_node = None
        self.is_visible = False

        # 当前显示的消息
        self.current_message = None
        self.message_end_time = 0

    def initialize(self):
        """初始化UI"""
        # ScreenNode由UI框架自动创建和管理
        print("[INFO] [FocusUI] 初始化完成")

    def cleanup(self):
        """清理UI"""
        # ScreenNode由UI框架自动销毁
        self.is_visible = False
        print("[INFO] [FocusUI] 清理完成")

    def update(self):
        """每帧更新"""
        if not self.is_visible:
            return

        # 检查消息是否过期
        import time
        if self.current_message and time.time() > self.message_end_time:
            self.hide()

    # ========== 显示焦点消息 ==========

    def show_bed_destroyed(self, team_id, destroyer_name):
        """
        显示床被破坏消息

        Args:
            team_id (str): 队伍ID
            destroyer_name (str): 破坏者名称
        """
        message = u"{}的床被{}破坏了!".format(team_id, destroyer_name)
        self.show_focus_message(message, duration=5.0, message_type='bed_destroyed')

        print("[INFO] [FocusUI] 显示床破坏消息 team={}".format(team_id))

    def show_team_eliminated(self, team_id):
        """
        显示队伍淘汰消息

        Args:
            team_id (str): 队伍ID
        """
        message = u"{}已被淘汰!".format(team_id)
        self.show_focus_message(message, duration=4.0, message_type='team_eliminated')

        print("[INFO] [FocusUI] 显示队伍淘汰消息 team={}".format(team_id))

    def show_phase_change(self, phase_name, description):
        """
        显示阶段变化消息

        Args:
            phase_name (str): 阶段名称
            description (str): 阶段描述
        """
        message = u"{}: {}".format(phase_name, description)
        self.show_focus_message(message, duration=6.0, message_type='phase_change')

        print("[INFO] [FocusUI] 显示阶段变化 phase={}".format(phase_name))

    def show_focus_message(self, message, duration=5.0, message_type='default'):
        """
        显示焦点消息

        Args:
            message (str): 消息内容
            duration (float): 显示时长(秒)
            message_type (str): 消息类型
        """
        import time
        self.current_message = {
            'message': message,
            'type': message_type
        }
        self.message_end_time = time.time() + duration

        self.show()

        # ScreenNode的显示更新由UI框架自动处理

        print("[INFO] [FocusUI] 焦点消息: {} type={}".format(message, message_type))

    # ========== 显示控制 ==========

    def show(self):
        """显示UI"""
        self.is_visible = True
        # ScreenNode的显示由UI框架自动管理

    def hide(self):
        """隐藏UI"""
        self.is_visible = False
        self.current_message = None
        # ScreenNode的隐藏由UI框架自动管理