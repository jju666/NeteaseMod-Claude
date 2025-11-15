# -*- coding: utf-8 -*-
"""
BedWarsSubState - 起床战争游戏阶段子状态

功能:
- 继承TimedGamingState,每个游戏阶段是一个定时状态
- 根据配置动态创建阶段动作子状态(GENERATOR/DESTROY/DRAGON)
- 阶段结束后自动切换到下一阶段

原文件: Parts/ECBedWars/state/BedWarsSubState.py
重构为: systems/bedwars_states/phase_states/BedWarsSubState.py
"""

from Script_NeteaseMod.systems.state.TimedGamingState import TimedGamingState
from Script_NeteaseMod.systems.bedwars_states.phase_states.BedWarsStateGenerator import BedWarsStateGenerator
from Script_NeteaseMod.systems.bedwars_states.phase_states.BedWarsStateDestroy import BedWarsStateDestroy
from Script_NeteaseMod.systems.bedwars_states.phase_states.BedWarsStateDragon import BedWarsStateDragon


class BedWarsSubState(TimedGamingState):
    """
    游戏阶段子状态

    每个阶段包含:
    - duration: 阶段持续时间
    - name: 阶段名称
    - starting_do: 阶段开始时执行的动作(可选,支持列表)
    """

    def __init__(self, parent, config, next_state_name):
        """
        初始化游戏阶段子状态

        Args:
            parent: 父状态
            config (dict): 阶段配置
                {
                    "duration": 180000,  # 毫秒
                    "name": "钻石点II级",
                    "starting_do": {
                        "type": "GENERATOR",
                        "resource_type": "DIAMOND",
                        "team": "NONE",
                        "level": 2
                    }
                }
            next_state_name (str): 下一个阶段的状态名称
        """
        system = parent.get_system()
        system.LogDebug("BedWarsSubState.__init__: {}".format(str(config)))

        # 初始化定时状态 (duration从毫秒转换为秒)
        duration_seconds = config['duration'] / 1000.0
        TimedGamingState.__init__(self, parent, duration_seconds)

        self.state_name = config['name']
        self.next_state_name = next_state_name

        # 解析阶段动作配置
        if 'starting_do' not in config:
            starting_do = []
        elif isinstance(config['starting_do'], list):
            starting_do = config['starting_do']
        else:
            starting_do = [config['starting_do']]

        # 为每个动作创建子状态
        index = 0
        for action_config in starting_do:
            action_type = action_config['type']

            if action_type == 'GENERATOR':
                # 产矿机升级动作
                self.add_sub_state(
                    "bw_do_{}".format(index),
                    BedWarsStateGenerator,
                    config=action_config
                )
            elif action_type == 'DESTROY':
                # 床自毁动作
                self.add_sub_state(
                    "bw_do_{}".format(index),
                    BedWarsStateDestroy,
                    config=action_config
                )
            elif action_type == 'DRAGON':
                # 末影龙事件动作
                self.add_sub_state(
                    "bw_do_{}".format(index),
                    BedWarsStateDragon,
                    config=action_config
                )

            index += 1

        # ===== [CRITICAL FIX] 注册进入回调，启动子状态 =====
        # 老项目逻辑：如果阶段有starting_do配置，进入时立即启动第一个动作子状态
        # 如果没有starting_do（如"游戏开始"阶段），则不启动子状态，直接等待定时器超时
        self.with_enter(self._on_sub_state_enter)

        # ===== [CRITICAL FIX] 注册子状态完成回调，阻止父状态切换 =====
        # 老项目逻辑：子状态（starting_do动作）执行完后，不应该触发父状态切换
        # 而是继续等待BedWarsSubState自己的定时器超时
        # 只有定时器超时时(TimedGamingState._time_out)，才会切换到下一个阶段
        self.with_no_such_next_sub_state(self._on_sub_state_completed)

    def _on_sub_state_enter(self):
        """
        阶段进入时的回调

        功能:
        - 如果有子状态(starting_do动作)，则启动第一个子状态
        - 如果没有子状态，则只是等待定时器超时

        参考: 老项目 BedWarsSubState.py (在__init__中通过add_sub_state创建后自动进入)
        """
        system = self.get_system()

        # 检查是否有子状态需要启动
        if len(self.sub_states) > 0:
            system.LogInfo(u"[BedWarsSubState] 阶段'{}'进入，启动{}个动作子状态".format(
                self.state_name, len(self.sub_states)
            ))
            # 启动第一个子状态
            self.next_sub_state()
        else:
            system.LogInfo(u"[BedWarsSubState] 阶段'{}'进入，无动作，等待定时器({:.1f}秒)".format(
                self.state_name, self.duration
            ))

    def _on_sub_state_completed(self):
        """
        子状态全部执行完毕的回调

        功能:
        - 子状态（starting_do动作）执行完后被调用
        - 阻止GamingState.next_sub_state()中默认的parent.next_sub_state()调用
        - 继续等待当前阶段的定时器超时

        参考: 老项目行为
        - starting_do动作执行完后，不切换父状态
        - 继续等待duration时间
        - 只有TimedGamingState超时时才切换到下一阶段

        实现原理:
        - GamingState.next_sub_state()在执行callbacks_no_such_next_sub_state后
        - 会检查: if self.is_state_running() and self.current_sub_state_name == keys[-1]
        - 如果当前子状态仍然是最后一个，就会调用parent.next_sub_state()
        - 因此，我们需要清除current_sub_state，让状态机认为"状态已改变"
        """
        system = self.get_system()
        system.LogInfo(u"[BedWarsSubState] 阶段'{}'的动作已完成，等待定时器({:.1f}秒)".format(
            self.state_name, self.get_seconds_left()
        ))

        # ===== [CRITICAL FIX] 清除子状态，阻止parent.next_sub_state()调用 =====
        # 通过将current_sub_state_name设为None，使GamingState.next_sub_state()中的条件判断失败
        # if self.is_state_running() and self.current_sub_state_name == keys[-1]:
        # 这样就不会调用parent.next_sub_state()，继续等待定时器
        if self.current_sub_state is not None:
            # 注意：不调用exit()，因为子状态已经在之前的流程中exit了
            self.current_sub_state = None
            self.current_sub_state_name = None
            system.LogDebug(u"[BedWarsSubState] 已清除子状态引用，阻止父状态切换")

    def get_system(self):
        """
        获取BedWarsGameSystem实例

        Returns:
            BedWarsGameSystem: 系统实例
        """
        return self.parent.get_system()
