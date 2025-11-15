# -*- coding: utf-8 -*-
"""
BedWarsEndingState - 起床战争结束状态

功能:
- 游戏结束阶段
- 显示胜利信息
- 切换玩家为旁观模式
- 清理游戏数据
- 通知房间系统

原文件: Parts/ECBedWars/state/BedWarsEndingState.py
"""

from ..state.GamingState import GamingState
import mod.server.extraServerApi as serverApi


class BedWarsEndingState(GamingState):
    """起床战争结束状态"""

    def __init__(self, parent):
        """
        初始化结束状态

        Args:
            parent: 父状态
        """
        GamingState.__init__(self, parent)

        # 注册生命周期回调
        self.with_enter(self._on_enter)
        self.with_exit(self._on_exit)

        # 结束展示时间
        self.display_duration = 10  # 10秒展示时间
        self.end_timer_id = None

    def _on_enter(self):
        """进入结束状态"""
        system = self.get_system()
        system.LogInfo("BedWarsEndingState entered")

        # 禁用标点系统（如果存在）
        if hasattr(system, 'waypoint_manager') and system.waypoint_manager:
            system.waypoint_manager.disable_waypoint()
            system.LogInfo("标点系统已禁用")

        # 获取获胜队伍
        winning_team = getattr(system, '_winning_team', None)

        # 显示胜利信息
        self._display_victory(winning_team)

        # 播放胜利之舞
        self._play_victory_dance(winning_team)

        # 收集排名数据并广播（供StageBroadcastScoreState使用）
        self._collect_and_broadcast_score_data(winning_team)

        # 切换所有玩家为旁观模式
        self._switch_all_to_spectator()

        # 启动结束定时器
        self._start_end_timer()

    def _on_exit(self):
        """退出结束状态"""
        system = self.get_system()
        system.LogInfo("BedWarsEndingState exited")

        # 清理定时器
        if self.end_timer_id:
            try:
                comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
                comp.CancelTimer(self.end_timer_id)
                self.end_timer_id = None
            except:
                pass

        # 清理玩家数据记录，防止下一局数据污染
        self._cleanup_player_records()

    def _cleanup_player_records(self):
        """
        清理玩家数据记录，防止下一局数据污染

        参考: 老项目 BedWarsEndingState.on_exit() line 155-165
        """
        system = self.get_system()

        try:
            # 清空护具记录
            if hasattr(system, 'player_armor_record'):
                count = len(system.player_armor_record)
                system.player_armor_record.clear()
                system.LogInfo("清空护具记录，记录数量: {}".format(count))

            # 清空剑类记录
            if hasattr(system, 'player_sword_record'):
                count = len(system.player_sword_record)
                system.player_sword_record.clear()
                system.LogInfo("清空剑类记录，记录数量: {}".format(count))

            # 清空复活物品记录
            if hasattr(system, 'respawn_contents'):
                count = len(system.respawn_contents)
                system.respawn_contents.clear()
                system.LogInfo("清空复活物品记录，记录数量: {}".format(count))

            # 清空BedWarsGameSystem的游戏数据
            if hasattr(system, 'bedwars_game_system') and system.bedwars_game_system:
                game_system = system.bedwars_game_system
                if hasattr(game_system, 'clear_game_data'):
                    game_system.clear_game_data()
                    system.LogInfo("BedWarsGameSystem游戏数据已清理")

        except Exception as e:
            system.LogError("清理玩家数据失败: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())

    def _display_victory(self, winning_team):
        """
        显示胜利信息

        参考: 老项目 BedWarsEndingState.on_enter() line 27-43
              必须与老项目保持100%一致的title显示效果

        Args:
            winning_team (str): 获胜队伍ID
        """
        system = self.get_system()

        # [FIX] 使用与老项目一致的title格式
        # 老项目第30-33行:
        #   主标题: "§f§l» §e游戏结束§f «"
        #   副标题: "§c红队 §6获得了胜利" (带颜色的队伍名称)

        # 获取所有玩家
        player_ids = serverApi.GetPlayerList()

        if winning_team:
            # 有获胜队伍
            if hasattr(system, 'team_module') and system.team_module:
                team_name = system.team_module.get_colored_team_name(winning_team)
            else:
                team_name = winning_team

            # 主标题: "» 游戏结束 «" (粗体白色、黄色、白色)
            main_title = u"§f§l» §e游戏结束§f «"
            # 副标题: "XXX队 获得了胜利" (队伍颜色 + 金色文字)
            sub_title = u"{} §6获得了胜利".format(team_name)

            # 广播聊天消息
            chat_message = u"{} §6获得了胜利".format(team_name)
            system.broadcast_message(chat_message, u'\xa7e')  # \xa7e = YELLOW

        else:
            # 平局
            # 主标题: "» 游戏结束 «"
            main_title = u"§f§l» §e游戏结束§f «"
            # 副标题: "平局"
            sub_title = u"平局"

            # 广播聊天消息
            system.broadcast_message(u"§e游戏结束 - 平局", u'\xa7e')  # \xa7e = YELLOW

        # 向所有玩家发送Title和播放音效
        for player_id in player_ids:
            try:
                player_obj = system.get_better_player_obj(player_id)

                # [FIX] 参考老项目第30行: 先重置之前的title
                comp = serverApi.GetEngineCompFactory().CreateCommand(serverApi.GetLevelId())
                comp.SetCommand("title @s reset", player_id)

                # 使用与老项目一致的淡入淡出时间(默认值)
                player_obj.send_title(main_title, sub_title, fadein=10, duration=70, fadeout=20)

                # [FIX] 参考老项目第44-45行: 播放胜利音效
                try:
                    player_pos = player_obj.GetPos()
                    if player_pos:
                        player_obj.play_sound("sound.ec.win", player_pos, 1.0, 1.0)
                except Exception as sound_err:
                    system.LogWarn("播放胜利音效失败 player_id={}: {}".format(player_id, str(sound_err)))

            except Exception as e:
                system.LogError("发送Title失败 player_id={}: {}".format(player_id, str(e)))
                import traceback
                system.LogError(traceback.format_exc())

        system.LogInfo("胜利信息已显示 winning_team={} player_count={}".format(
            winning_team, len(player_ids)
        ))

    def _play_victory_dance(self, winning_team):
        """
        播放胜利之舞

        Args:
            winning_team (str): 获胜队伍ID
        """
        system = self.get_system()

        # 检查饰品系统是否初始化（使用hasattr安全检查）
        if not hasattr(system, 'ornament_system') or not system.ornament_system:
            system.LogWarn("饰品系统未初始化,跳过胜利之舞")
            return

        # 获取玩家积分列表并排序
        player_scores = self._get_player_scores(winning_team)

        if player_scores and len(player_scores) > 0:
            # 播放胜利之舞
            system.ornament_system.start_victory_dance(player_scores)
            system.LogInfo("已启动胜利之舞 玩家数={}".format(len(player_scores)))

    def _get_player_scores(self, winning_team):
        """
        获取玩家积分列表

        Args:
            winning_team (str): 获胜队伍ID

        Returns:
            list: 玩家积分列表,按排名排序
                格式: [{'player_id': str, 'score': int, 'pos': (x, y, z)}, ...]
        """
        system = self.get_system()
        player_scores = []

        # 获取获胜队伍的玩家
        if winning_team and hasattr(system, 'team_module') and system.team_module:
            team_players = system.team_module.get_team_players(winning_team)
        else:
            # 如果没有获胜队伍,获取所有玩家
            # 使用serverApi.GetPlayerList()获取所有玩家ID
            team_players = serverApi.GetPlayerList()

        # 构建玩家积分列表
        comp_factory = serverApi.GetEngineCompFactory()
        for player_id in team_players:
            try:
                # 获取玩家位置
                pos_comp = comp_factory.CreatePos(player_id)
                pos = pos_comp.GetPos()

                # 获取玩家积分(TODO: 实际积分从记分板或其他地方获取)
                score = 0

                player_scores.append({
                    'player_id': player_id,
                    'score': score,
                    'pos': pos
                })
            except Exception as e:
                system.LogError("获取玩家{}信息失败: {}".format(player_id, str(e)))

        # 按积分排序(降序)
        player_scores.sort(key=lambda x: x['score'], reverse=True)

        return player_scores

    def _switch_all_to_spectator(self):
        """
        切换所有玩家为旁观模式

        修复说明：
        [FIX 2025-11-07] 修正API调用: CreateGameMode -> CreatePlayer
        参考：BedWarsGameSystem.py:669-672 正确API为CreatePlayer + SetPlayerGameType
        """
        system = self.get_system()

        # 使用serverApi.GetPlayerList()获取所有玩家ID
        player_ids = serverApi.GetPlayerList()

        comp = serverApi.GetEngineCompFactory()
        for player_id in player_ids:
            try:
                # 使用CreatePlayer而非CreateGameMode
                # 注意：网易MODSDK的GameType枚举使用首字母大写的Spectator，不是全大写的SPECTATOR
                player_comp = comp.CreatePlayer(player_id)
                player_comp.SetPlayerGameType(serverApi.GetMinecraftEnum().GameType.Spectator)
            except Exception as e:
                system.LogError("切换玩家{}为旁观模式失败: {}".format(player_id, str(e)))

        system.LogInfo("所有玩家已切换为旁观模式")

    def _start_end_timer(self):
        """启动结束定时器"""
        system = self.get_system()

        def on_end_timer():
            # 定时器结束,触发状态机完成
            if self.end_timer_id:
                self.end_timer_id = None
            # 进入下一个状态(会触发状态机结束)
            self.parent.next_sub_state()

        # 创建一次性定时器
        comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
        self.end_timer_id = comp.AddTimer(self.display_duration, on_end_timer)

        system.LogInfo("结束定时器已启动({}秒)".format(self.display_duration))

    def _collect_and_broadcast_score_data(self, winning_team):
        """
        收集排名数据并存储到system.tmp_broadcast_score_data
        供StageBroadcastScoreState使用

        参考: 老项目 BedWarsEndingState.on_enter() line 46
              part.BroadcastPresetSystemEvent("StageBroadcastScoreData",
                  part.scoreboard.collect_all_scoreboard_data())

        Args:
            winning_team (str): 获胜队伍ID
        """
        system = self.get_system()

        try:
            # 1. BedWarsEndingState的父系统就是BedWarsGameSystem
            # [FIX 2025-11-07 #5] system就是BedWarsGameSystem,不需要通过bedwars_game_system获取
            game_system = system

            # [FIX 2025-11-07 #6] 检查room_system是否存在
            if not hasattr(game_system, 'room_system') or not game_system.room_system:
                system.LogError("room_system未找到,无法收集排名数据")
                return

            room_system = game_system.room_system

            # [FIX 2025-11-07 #9] 使用scoreboard收集数据
            # 参考: 老项目BedWarsEndingState.py:46
            # part.BroadcastPresetSystemEvent("StageBroadcastScoreData", part.scoreboard.collect_all_scoreboard_data())
            if not hasattr(game_system, 'scoreboard') or not game_system.scoreboard:
                system.LogError("scoreboard未找到,无法收集排名数据")
                return

            # 2. 从scoreboard收集所有玩家的统计数据
            scoreboard_data = game_system.scoreboard.collect_all_scoreboard_data()

            if not scoreboard_data or 'scores' not in scoreboard_data:
                system.LogWarn("scoreboard数据为空")
                player_scores = []
            else:
                # scoreboard已经包含排序后的数据
                # BedWarsPlayerScore.to_dict()已经包含所有字段:
                # player_id, player_name, team, kills, deaths, final_kills, destroys, win_team, score, coin
                player_scores = scoreboard_data['scores']
                system.LogInfo("开始收集排名数据，玩家数量={}".format(len(player_scores)))

                # 添加排名字段
                for i, score_entry in enumerate(player_scores):
                    score_entry['rank'] = i + 1
                    system.LogInfo("收集玩家数据 player={} rank={} score={}".format(
                        score_entry.get('player_name', ''),
                        i + 1,
                        score_entry.get('score', 0)
                    ))

            # 5. 存储到room_system以供StageBroadcastScoreState使用
            # [FIX 2025-11-07] BUG修复: system是BedWarsGameSystem,需要存储到room_system
            # StageBroadcastScoreState从room_system(RoomManagementSystem)获取数据
            if hasattr(game_system, 'room_system') and game_system.room_system:
                game_system.room_system.tmp_broadcast_score_data = {
                    'scores': player_scores,
                    'winning_team': winning_team
                }
                system.LogInfo("排名数据已存储到room_system，玩家数量={}".format(len(player_scores)))
            else:
                system.LogError("room_system未找到,无法存储结算数据")
                # 作为备份,也存储到当前system
                system.tmp_broadcast_score_data = {
                    'scores': player_scores,
                    'winning_team': winning_team
                }

            # 6. 发放奖励
            self._award_players(player_scores)

        except Exception as e:
            system.LogError("收集排名数据失败: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())
            # 确保即使失败也有空数据结构
            system.tmp_broadcast_score_data = {'scores': []}

    def _calculate_coin_reward(self, stats, winning_team, player_id):
        """
        计算玩家奖励硬币

        参考: 老项目 score.calculate_coin()

        Args:
            stats (dict): 玩家统计数据
            winning_team (str): 获胜队伍
            player_id (str): 玩家ID

        Returns:
            int: 奖励硬币数量
        """
        system = self.get_system()

        # 基础奖励
        base_coin = 10

        # 获胜奖励
        if hasattr(system, 'team_module') and system.team_module:
            player_team = system.team_module.get_player_team(player_id)
            if player_team == winning_team:
                base_coin += 20  # 获胜队伍额外奖励

        # 击杀奖励
        base_coin += stats.get('kills', 0) * 2
        base_coin += stats.get('final_kills', 0) * 5

        # 破坏床奖励
        base_coin += stats.get('destroys', 0) * 10

        return base_coin

    def _award_players(self, player_scores):
        """
        发放玩家奖励

        参考: 老项目 BedWarsEndingState.players_award()

        Args:
            player_scores (list): 玩家分数列表
        """
        system = self.get_system()

        for score in player_scores:
            try:
                player_id = score['player_id']
                coin = score['coin']

                # 添加到玩家数据（持久化存储）
                if hasattr(system, 'add_player_data'):
                    system.add_player_data(player_id, "coin", coin)
                    system.LogInfo("玩家 {} 获得硬币: {}".format(player_id, coin))
                else:
                    system.LogWarn("add_player_data方法不存在，无法发放奖励")

            except Exception as e:
                system.LogError("发放奖励失败 player_id={}: {}".format(player_id, str(e)))
