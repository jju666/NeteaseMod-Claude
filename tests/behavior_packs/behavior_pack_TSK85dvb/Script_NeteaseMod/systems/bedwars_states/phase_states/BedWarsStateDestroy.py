# -*- coding: utf-8 -*-
"""
BedWarsStateDestroy - 床自毁动作状态

功能:
- 销毁所有未被摧毁的床
- 在特定阶段触发(通常是游戏后期)
- 强制所有玩家进入不可复活状态

原文件: Parts/ECBedWars/state/sub/BedWarsStateDestroy.py
重构为: systems/bedwars_states/phase_states/BedWarsStateDestroy.py
"""

from Script_NeteaseMod.systems.state.GamingState import GamingState


class BedWarsStateDestroy(GamingState):
    """
    床自毁动作状态

    配置格式:
    {
        "type": "DESTROY"
    }
    """

    def __init__(self, parent, config):
        """
        初始化床自毁状态

        Args:
            parent: 父状态
            config (dict): 配置(可为空)
        """
        GamingState.__init__(self, parent)
        self.with_enter(self.on_enter)

    def on_enter(self):
        """进入状态时执行床自毁"""
        system = self.get_system()
        system.LogInfo("[BedWarsStateDestroy] 进入")

        destroyed_count = 0

        try:
            # ===== [P0-6 FIX] 修复预设查找 =====
            from ECPresetServerScripts import get_server_mgr
            preset_manager = get_server_mgr("bedwars_room")

            if not preset_manager:
                system.LogError("[BedWarsStateDestroy] 无法获取PresetManager")
                return

            all_presets = preset_manager.get_all_presets()
            system.LogInfo(u"[BedWarsStateDestroy] 找到{}个预设实例".format(len(all_presets)))

            for preset_id, preset_instance in all_presets.items():
                # 检查是否是床预设
                if preset_instance.preset_type != "bedwars:bed":
                    continue

                team = preset_instance.get_config('team', 'UNKNOWN')

                # ===== [P0-6 FIX] 通过preset_def调用业务方法 =====
                preset_def = preset_instance.preset_def
                if not preset_def:
                    system.LogWarn(u"[BedWarsStateDestroy] 床预设{}没有preset_def".format(preset_id))
                    continue

                # 检查床是否已被销毁
                if hasattr(preset_def, 'is_destroyed'):
                    is_destroyed = preset_def.is_destroyed(preset_instance)
                else:
                    # 如果没有is_destroyed方法,检查data中的标志
                    is_destroyed = preset_instance.get_data('bed_destroyed', False)

                if not is_destroyed:
                    # 调用床的销毁方法(无攻击者)
                    if hasattr(preset_def, 'destroy_bed'):
                        try:
                            preset_def.destroy_bed(preset_instance, attacker_id=None)
                            destroyed_count += 1

                            preset_pos = preset_instance.get_config('pos', 'Unknown')
                            system.LogInfo(u"[BedWarsStateDestroy] 销毁床: 队伍={}, 位置={}".format(
                                team, preset_pos
                            ))
                        except Exception as e:
                            system.LogError(u"[BedWarsStateDestroy] 销毁床失败: {}".format(str(e)))
                    else:
                        system.LogWarn(u"[BedWarsStateDestroy] 床预设定义类没有destroy_bed方法")
                else:
                    preset_pos = preset_instance.get_config('pos', 'Unknown')
                    system.LogInfo(u"[BedWarsStateDestroy] 床已被销毁: 队伍={}, 位置={}".format(
                        team, preset_pos
                    ))

        except Exception as e:
            system.LogError(u"[BedWarsStateDestroy] 销毁床异常: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())

        system.LogInfo(u"[BedWarsStateDestroy] 完成，共销毁了 {} 个床".format(destroyed_count))

        # ===== [P1-6 FIX] 添加全局公告和特效 =====
        if destroyed_count > 0:
            self._broadcast_destroy_announcement()
            self._trigger_destroy_effects()

    def _broadcast_destroy_announcement(self):
        """
        广播床自毁公告

        通知形式:
        1. Title通知: 大标题显示床自毁警告
        2. 聊天栏消息: 文字提示
        3. 音效: 播放警告音效
        """
        system = self.get_system()

        # 1. 广播Title通知
        try:
            title = u"§c§l所有床已被摧毁！"
            subtitle = u"§7死亡后将无法重生"

            # 使用GamingStateSystem的broadcast_title方法
            system.broadcast_title(title, subtitle, fadein=10, duration=60, fadeout=10)

            system.LogInfo(u"[BedWarsStateDestroy] 已发送Title通知")
        except Exception as e:
            system.LogError(u"[BedWarsStateDestroy] 广播Title失败: {}".format(str(e)))

        # 2. 广播聊天栏消息
        try:
            message = u"§c§l所有床位 §7已被系统摧毁！死亡后将无法重生！"

            # 使用GamingStateSystem的broadcast_message方法
            system.broadcast_message(message, u'\xa7c')

            system.LogInfo(u"[BedWarsStateDestroy] 已发送聊天栏消息")
        except Exception as e:
            system.LogError(u"[BedWarsStateDestroy] 广播聊天栏消息失败: {}".format(str(e)))

    def _trigger_destroy_effects(self):
        """
        触发床破坏特效

        特效:
        1. 播放全局警告音效(凋零死亡音效)
        2. 可选: 粒子效果(如需要可添加)
        """
        system = self.get_system()

        # 播放全局音效
        try:
            import mod.server.extraServerApi as serverApi

            # 获取所有玩家
            all_players = []
            if system.team_module:
                all_players = system.team_module.get_all_players()

            # 为每个玩家播放音效
            comp_factory = serverApi.GetEngineCompFactory()
            for player_id in all_players:
                try:
                    sfx_comp = comp_factory.CreateSfx(player_id)
                    # 播放凋零死亡音效(恐怖的警告音效)
                    sfx_comp.PlaySfx("mob.wither.death", player_id, 1.0, 1.0)
                except Exception as e:
                    system.LogError(u"[BedWarsStateDestroy] 为玩家 {} 播放音效失败: {}".format(
                        player_id, str(e)
                    ))

            system.LogInfo(u"[BedWarsStateDestroy] 已播放床自毁音效")
        except Exception as e:
            system.LogError(u"[BedWarsStateDestroy] 播放音效失败: {}".format(str(e)))

    def get_system(self):
        """
        获取BedWarsGameSystem实例

        Returns:
            BedWarsGameSystem: 系统实例
        """
        return self.parent.parent.get_system()
