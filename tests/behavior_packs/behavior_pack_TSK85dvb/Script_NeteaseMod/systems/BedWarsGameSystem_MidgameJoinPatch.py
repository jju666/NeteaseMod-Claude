# -*- coding: utf-8 -*-
"""
BedWarsGameSystem中途加入功能补丁

此文件包含需要添加到BedWarsGameSystem.py的方法
请将以下方法添加到BedWarsGameSystem类中notify_show_join_button方法之后
"""

def notify_viewer_join(self, player_id):
    """
    通知BedWarsGameSystem有观战者加入

    由RoomManagementSystem.StageRunningState调用,当玩家中途加入作为观战者时

    功能:
    1. 记录观战者ID
    2. 同步游戏状态给观战者(床状态、队伍状态、计分板等)
    3. 检查是否允许中途参战,显示"参战"按钮

    Args:
        player_id (str): 观战者玩家ID
    """
    self.LogInfo("[notify_viewer_join] 观战者加入: {}".format(player_id))

    try:
        # 1. 同步游戏状态给观战者
        self._sync_game_state_to_viewer(player_id)

        # 2. 检查是否应该显示中途参战按钮
        if self.should_show_join_button(player_id):
            self.notify_show_join_button(player_id)
            self.LogInfo("观战者 {} 可以中途参战,已显示按钮".format(player_id))
        else:
            self.LogInfo("观战者 {} 不满足中途参战条件".format(player_id))

    except Exception as e:
        self.LogError("处理观战者加入失败: {}".format(str(e)))
        import traceback
        traceback.print_exc()

def notify_player_leave(self, player_id):
    """
    通知BedWarsGameSystem玩家离开游戏

    由RoomManagementSystem.StageRunningState调用,当玩家在游戏中离开时

    功能:
    1. 检查玩家是否在游戏中(有队伍)
    2. 如果在游戏中,触发玩家死亡/淘汰逻辑
    3. 清理玩家数据

    Args:
        player_id (str): 离开的玩家ID
    """
    self.LogInfo("[notify_player_leave] 玩家离开: {}".format(player_id))

    try:
        # 检查玩家是否在某个队伍中
        if self.team_module:
            team_id = self.team_module.get_player_team(player_id)
            if team_id:
                self.LogInfo("游戏参与玩家 {} 离开,触发淘汰逻辑".format(player_id))

                # 如果玩家还在游戏中(不在淘汰列表),触发淘汰
                # 修复: is_player_eliminated方法不存在,应检查eliminated_players列表
                if player_id not in self.eliminated_players:
                    # 检查床状态,判定是否直接淘汰
                    if team_id in self.destroyed_beds:
                        # 床已破坏,直接淘汰
                        self._eliminate_player(player_id)
                    else:
                        # 床存在,标记为离线淘汰(不复活)
                        self._eliminate_player(player_id)

                # 从队伍中移除
                self.team_module.remove_player_from_team(player_id, team_id)

                # 检查是否应该触发游戏结束
                self._check_game_end_condition()
            else:
                self.LogInfo("观战者 {} 离开".format(player_id))

    except Exception as e:
        self.LogError("处理玩家离开失败: {}".format(str(e)))
        import traceback
        traceback.print_exc()

def _sync_game_state_to_viewer(self, player_id):
    """
    同步游戏状态给观战者

    同步内容:
    1. 队伍床状态(哪些队伍的床已被破坏)
    2. 当前游戏阶段信息
    3. 计分板信息

    Args:
        player_id (str): 观战者玩家ID
    """
    try:
        # 1. 同步床状态
        self._sync_bed_status_to_viewer(player_id)

        # 2. 同步计分板
        if self.scoreboard:
            self.scoreboard.show_scoreboard_to_player(player_id)

        # 3. 同步游戏阶段信息 (如果BedWarsRunningState有相关信息)
        if self.root_state and self.root_state.current_sub_state:
            current_state = self.root_state.current_sub_state
            if hasattr(current_state, 'sync_stage_info_to_viewer'):
                current_state.sync_stage_info_to_viewer(player_id)

        self.LogInfo("游戏状态已同步给观战者: {}".format(player_id))

    except Exception as e:
        self.LogError("同步游戏状态失败: {}".format(str(e)))

def _sync_bed_status_to_viewer(self, player_id):
    """
    同步床状态给观战者

    向客户端发送所有已被破坏的床的信息

    Args:
        player_id (str): 观战者玩家ID
    """
    try:
        # 构造床状态数据
        bed_status = {
            'destroyed_beds': list(self.destroyed_beds)
        }

        # 发送到客户端
        self.NotifyToClient(player_id, 'SyncBedStatus', bed_status)

        self.LogInfo("床状态已同步给观战者 {}: 已破坏 {}".format(
            player_id, len(self.destroyed_beds)
        ))

    except Exception as e:
        self.LogError("同步床状态失败: {}".format(str(e)))
