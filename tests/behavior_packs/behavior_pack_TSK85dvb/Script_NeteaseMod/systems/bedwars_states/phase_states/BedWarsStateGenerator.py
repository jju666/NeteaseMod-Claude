# -*- coding: utf-8 -*-
"""
BedWarsStateGenerator - 产矿机升级动作状态

功能:
- 升级指定资源类型的产矿机到指定等级
- 支持按队伍筛选或全局升级(team="NONE")
- 支持同时升级多种资源类型

原文件: Parts/ECBedWars/state/sub/BedWarsStateGenerator.py
重构为: systems/bedwars_states/phase_states/BedWarsStateGenerator.py
"""

from Script_NeteaseMod.systems.state.GamingState import GamingState


class BedWarsStateGenerator(GamingState):
    """
    产矿机升级动作状态

    配置格式:
    {
        "type": "GENERATOR",
        "resource_type": "DIAMOND",  # 或 ["DIAMOND", "EMERALD"]
        "team": "NONE",  # 或 "RED" 或 ["RED", "BLUE"]
        "level": 2
    }
    """

    def __init__(self, parent, config):
        """
        初始化产矿机升级状态

        Args:
            parent: 父状态
            config (dict): 升级配置
        """
        GamingState.__init__(self, parent)
        self.with_enter(self.on_enter)

        # 解析资源类型列表
        self.resource_types = []
        resource_type_config = config.get('resource_type') or config.get('resourceType')
        if isinstance(resource_type_config, list):
            self.resource_types = [rt.lower() for rt in resource_type_config]
        else:
            self.resource_types.append(resource_type_config.lower())

        # 解析队伍列表
        self.teams = []
        team_config = config.get('team', 'NONE')
        if isinstance(team_config, list):
            self.teams = team_config
        else:
            self.teams.append(team_config)

        # 升级目标等级
        self.level = config['level']

    def on_enter(self):
        """进入状态时执行升级"""
        system = self.get_system()
        system.LogInfo(u"[BedWarsStateGenerator] 进入，资源类型: {}, 等级: {}, 队伍: {}".format(
            self.resource_types, self.level, self.teams
        ))

        upgraded_count = 0
        matching_generators = []  # 记录匹配的产矿机信息（用于日志）

        try:
            # ===== [P0-5 FIX] 修复预设查找方式 =====
            from ECPresetServerScripts import get_server_mgr
            preset_manager = get_server_mgr("bedwars_room")

            if not preset_manager:
                system.LogError("[BedWarsStateGenerator] 无法获取PresetManager")
                return

            # 正确的API: get_all_presets() 返回 dict {preset_id: PresetInstance}
            all_presets = preset_manager.get_all_presets()

            # 第一步：遍历找出所有匹配的产矿机（仅用于统计和日志）
            for preset_id, preset_instance in all_presets.items():
                # 检查是否是生成器预设
                if preset_instance.preset_type != "bedwars:generator":
                    continue

                # 获取生成器配置
                gen_resource_type = preset_instance.get_config('resource_type_id', '').upper()
                gen_team = preset_instance.get_config('team', 'NONE')

                # 转换资源类型为大写进行比较
                resource_types_upper = [rt.upper() for rt in self.resource_types]
                teams_upper = [t.upper() for t in self.teams]

                # 检查资源类型和队伍是否匹配
                if gen_resource_type in resource_types_upper and gen_team in teams_upper:
                    old_level = preset_instance.get_data('level', 1)
                    preset_pos = preset_instance.get_config('pos', 'Unknown')

                    matching_generators.append({
                        'resource_type': gen_resource_type,
                        'team': gen_team,
                        'old_level': old_level,
                        'position': preset_pos
                    })
                    upgraded_count += 1

            # 第二步：广播升级事件（只广播一次，让产矿机自己判断是否响应）
            # ===== [CRITICAL FIX] 使用broadcast_preset_event而非遍历发布 =====
            # 通过GamingStateSystem的broadcast_preset_event方法广播到所有预设
            # EventBus会自动分发给所有订阅"GeneratorLevelUp"的预设
            # 每个产矿机的_on_level_up回调会自己判断是否应该升级（基于资源类型和队伍）
            try:
                # 构造事件数据：包含所有要升级的资源类型和队伍
                event_data = {
                    'resource_types': [rt.upper() for rt in self.resource_types],
                    'teams': [t.upper() for t in self.teams],
                    'new_level': self.level
                }

                # 只广播一次事件
                system.broadcast_preset_event('GeneratorLevelUp', event_data)

                # 输出匹配的产矿机日志
                for gen_info in matching_generators:
                    system.LogInfo(u"[BedWarsStateGenerator] 升级产矿机: 位置={}, 资源={}, 队伍={}, 等级 {} -> {}".format(
                        gen_info['position'],
                        gen_info['resource_type'],
                        gen_info['team'],
                        gen_info['old_level'],
                        self.level
                    ))

            except Exception as e:
                system.LogError(u"[BedWarsStateGenerator] 广播升级事件失败: {}".format(str(e)))

        except Exception as e:
            system.LogError(u"[BedWarsStateGenerator] 升级产矿机异常: {}".format(str(e)))
            import traceback
            system.LogError(traceback.format_exc())

        system.LogInfo(u"[BedWarsStateGenerator] 完成，共升级了 {} 个产矿机".format(upgraded_count))

        # ===== [P1-4 FIX] 添加全局公告 =====
        if upgraded_count > 0:
            self._broadcast_upgrade_announcement()

    def _broadcast_upgrade_announcement(self):
        """
        广播升级公告

        通知形式:
        1. Title通知: 大标题显示升级信息
        2. 聊天栏消息: 文字提示
        3. HUD堆叠消息: 持续显示倒计时(已在HUD定时更新中实现)
        """
        system = self.get_system()

        # 资源名称映射
        resource_name_map = {
            'DIAMOND': u'钻石',
            'EMERALD': u'绿宝石',
            'IRON': u'铁',
            'GOLD': u'金'
        }

        # 资源颜色映射 (使用§颜色代码)
        resource_color_map = {
            'DIAMOND': u'\xa7b',    # 青色(钻石) - §b
            'EMERALD': u'\xa7a',    # 绿色(绿宝石) - §a
            'IRON': u'\xa77',       # 灰色(铁) - §7
            'GOLD': u'\xa7e'        # 黄色(金) - §e
        }

        # 等级罗马数字映射
        level_roman_map = {
            1: u'I',
            2: u'II',
            3: u'III',
            4: u'IV'
        }

        # 获取资源名称和颜色
        resource_names = []
        resource_color = u'\xa7e'  # 默认黄色
        for rt in self.resource_types:
            rt_upper = rt.upper()
            resource_names.append(resource_name_map.get(rt_upper, rt))
            # 使用第一个资源的颜色
            if rt_upper in resource_color_map:
                resource_color = resource_color_map[rt_upper]

        resource_text = u'/'.join(resource_names)
        level_roman = level_roman_map.get(self.level, str(self.level))

        # 1. 广播Title通知
        try:
            title = u"{}§l{} 生成器升级".format(resource_color, resource_text)
            subtitle = u"§7已升级到 {}{}级".format(resource_color, level_roman)

            # 使用GamingStateSystem的broadcast_title方法
            system.broadcast_title(title, subtitle, fadein=10, duration=40, fadeout=10)

            system.LogInfo(u"[BedWarsStateGenerator] 已发送Title通知: {} -> {}级".format(
                resource_text, level_roman
            ))
        except Exception as e:
            system.LogError(u"[BedWarsStateGenerator] 广播Title失败: {}".format(str(e)))

        # 2. 广播聊天栏消息
        try:
            message = u"{}§l{} 生成器 §7已升级到 {}{}级".format(
                resource_color,
                resource_text,
                resource_color,
                level_roman
            )

            # 使用GamingStateSystem的broadcast_message方法
            system.broadcast_message(message, resource_color)

            system.LogInfo(u"[BedWarsStateGenerator] 已发送聊天栏消息")
        except Exception as e:
            system.LogError(u"[BedWarsStateGenerator] 广播聊天栏消息失败: {}".format(str(e)))

        # 注意: HUD倒计时显示已在BedWarsRunningState的on_tick_hud中实现
        # 不需要在这里额外添加

    def get_system(self):
        """
        获取BedWarsGameSystem实例

        Returns:
            BedWarsGameSystem: 系统实例
        """
        return self.parent.parent.get_system()
