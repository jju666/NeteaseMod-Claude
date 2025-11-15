# -*- coding: utf-8 -*-
"""
BedWarsStateDragon - 末影龙事件动作状态

功能:
- 生成末影龙
- 广播事件消息
- 触发特殊效果

原文件: Parts/ECBedWars/state/sub/BedWarsStateDragon.py
重构为: systems/bedwars_states/phase_states/BedWarsStateDragon.py
"""

from Script_NeteaseMod.systems.state.GamingState import GamingState


class BedWarsStateDragon(GamingState):
    """
    末影龙事件动作状态

    配置格式:
    {
        "type": "DRAGON",
        "message": "{bold}{light-purple}末影龙出没"
    }
    """

    def __init__(self, parent, config):
        """
        初始化末影龙事件状态

        Args:
            parent: 父状态
            config (dict): 配置
        """
        GamingState.__init__(self, parent)
        self.with_enter(self.on_enter)
        self.message = config.get('message', u'{bold}{light-purple}末影龙出没')

    def on_enter(self):
        """
        进入状态时触发末影龙事件

        功能:
        1. 广播末影龙出没消息
        2. 播放Title通知
        3. 播放音效
        4. TODO: 生成末影龙实体(未来实现)
        """
        system = self.get_system()
        system.LogInfo("[BedWarsStateDragon] 进入")

        try:
            # 1. 广播Title通知
            self._broadcast_dragon_announcement()

            # 2. 播放音效
            self._trigger_dragon_effects()

            # TODO: 生成末影龙
            # 需要实现末影龙生成逻辑
            # 1. 在地图中心生成末影龙
            # 2. 末影龙AI行为
            # 3. 末影龙死亡奖励
            system.LogInfo("末影龙事件触发(生成逻辑待实现)")

        except Exception as e:
            system.LogError("BedWarsStateDragon 触发失败: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())

    def _broadcast_dragon_announcement(self):
        """
        广播末影龙出没公告

        通知形式:
        1. Title通知: 大标题显示末影龙警告
        2. 聊天栏消息: 文字提示
        """
        system = self.get_system()

        # 1. 广播Title通知
        try:
            title = u"§5§l末影龙出没！"
            subtitle = u"§7击杀末影龙可获得丰厚奖励"

            # 使用GamingStateSystem的broadcast_title方法
            system.broadcast_title(title, subtitle, fadein=10, duration=60, fadeout=10)

            system.LogInfo(u"[BedWarsStateDragon] 已发送Title通知")
        except Exception as e:
            system.LogError(u"[BedWarsStateDragon] 广播Title失败: {}".format(str(e)))

        # 2. 广播聊天栏消息
        try:
            # 使用配置中的消息,如果没有则使用默认消息
            if self.message:
                # 格式化消息(支持颜色代码)
                formatted_message = self.message
                # 简单的颜色代码替换
                formatted_message = formatted_message.replace('{bold}', u'§l')
                formatted_message = formatted_message.replace('{light-purple}', u'§d')
                formatted_message = formatted_message.replace('{purple}', u'§5')
                formatted_message = formatted_message.replace('{aqua}', u'§b')
                formatted_message = formatted_message.replace('{red}', u'§c')
                formatted_message = formatted_message.replace('{yellow}', u'§e')
                formatted_message = formatted_message.replace('{green}', u'§a')
                formatted_message = formatted_message.replace('{gray}', u'§7')
                formatted_message = formatted_message.replace('{white}', u'§f')

                message = formatted_message
            else:
                message = u"§5§l末影龙 §7即将苏醒！"

            # 使用GamingStateSystem的broadcast_message方法
            system.broadcast_message(message, u'\xa75')

            system.LogInfo(u"[BedWarsStateDragon] 已发送聊天栏消息")
        except Exception as e:
            system.LogError(u"[BedWarsStateDragon] 广播聊天栏消息失败: {}".format(str(e)))

    def _trigger_dragon_effects(self):
        """
        触发末影龙特效

        特效:
        1. 播放末影龙吼叫音效
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
                    # 播放末影龙吼叫音效
                    sfx_comp.PlaySfx("mob.enderdragon.growl", player_id, 1.0, 0.8)
                except Exception as e:
                    system.LogError(u"[BedWarsStateDragon] 为玩家 {} 播放音效失败: {}".format(
                        player_id, str(e)
                    ))

            system.LogInfo(u"[BedWarsStateDragon] 已播放末影龙音效")
        except Exception as e:
            system.LogError(u"[BedWarsStateDragon] 播放音效失败: {}".format(str(e)))

    def get_system(self):
        """
        获取BedWarsGameSystem实例

        Returns:
            BedWarsGameSystem: 系统实例
        """
        return self.parent.parent.get_system()
