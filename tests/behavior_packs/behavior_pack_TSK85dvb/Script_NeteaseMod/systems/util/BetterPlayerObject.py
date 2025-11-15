# -*- coding: utf-8 -*-
"""
BetterPlayerObject - 玩家对象封装类

功能:
- 封装常用的玩家API
- 提供便捷的消息发送方法
- 简化玩家操作接口

重构说明:
- 从原Parts/GamingState/util/BetterPlayerObject.py简化而来
- 移除对Preset系统PlayerObject的继承
- 直接使用ServerAPI操作玩家
"""

import math
import mod.server.extraServerApi as serverApi


class BetterPlayerObject(object):
    """玩家对象封装类"""

    def __init__(self, system, player_id):
        """
        初始化玩家对象

        Args:
            system: GamingStateSystem实例
            player_id (str): 玩家ID
        """
        self.system = system
        self.player_id = player_id
        self.comp_factory = serverApi.GetEngineCompFactory()
        self.level_id = serverApi.GetLevelId()

    def GetPlayerId(self):
        """
        获取玩家ID

        Returns:
            str: 玩家ID
        """
        return self.player_id

    def send_message(self, message, color=u'\xa7f'):
        """
        发送聊天消息

        Args:
            message (str): 消息内容
            color (str): 颜色代码
        """
        msg_comp = self.comp_factory.CreateMsg(self.player_id)
        msg_comp.NotifyOneMessage(self.player_id, message, color)

    def send_tip(self, tip):
        """
        发送Tip提示

        Args:
            tip (str): 提示内容
        """
        msg_comp = self.comp_factory.CreateMsg(self.player_id)
        msg_comp.SetOneTipMessage(self.player_id, tip)

    def send_popup(self, popup, sub=""):
        """
        发送Popup提示

        Args:
            popup (str): 主提示
            sub (str): 副提示
        """
        msg_comp = self.comp_factory.CreateMsg(self.player_id)
        msg_comp.SetPopupNotice(self.player_id, popup, sub)

    def send_title(self, title, sub_title=None, fadein=20, duration=20, fadeout=5):
        """
        发送Title

        Args:
            title (str): 标题内容
            sub_title (str): 副标题内容
            fadein (int): 淡入时间(ticks)
            duration (int): 保持时间(ticks)
            fadeout (int): 淡出时间(ticks)
        """
        command_comp = self.comp_factory.CreateCommand(self.level_id)

        # 设置显示时间
        command_comp.SetCommand(
            "title @s times {} {} {}".format(fadein, duration, fadeout),
            self.player_id
        )

        # 显示标题
        command_comp.SetCommand(
            "title @s title {}".format(title),
            self.player_id
        )

        # 显示副标题
        if sub_title:
            command_comp.SetCommand(
                "title @s subtitle {}".format(sub_title),
                self.player_id
            )

    def send_action_bar(self, action_bar):
        """
        发送ActionBar

        Args:
            action_bar (str): ActionBar内容
        """
        command_comp = self.comp_factory.CreateCommand(self.level_id)
        command_comp.SetCommand(
            "title @s actionbar {}".format(action_bar),
            self.player_id
        )

    def clear_title(self):
        """清除Title显示"""
        command_comp = self.comp_factory.CreateCommand(self.level_id)
        command_comp.SetCommand("title @s clear", self.player_id)

    def play_sound(self, sound, pos, volume=1, pitch=1):
        """
        通过服务端指令播放声音

        Args:
            sound (str): 声音ID (如 random.levelup, random.burp, note.pling)
            pos (tuple): 播放位置 (x, y, z)
            volume (float): 音量
            pitch (float): 音调

        Returns:
            bool: 是否成功
        """
        try:
            command_comp = self.comp_factory.CreateCommand(self.level_id)
            command_comp.SetCommand(
                "playsound {sound} @s {pos} {volume} {pitch}".format(
                    sound=sound,
                    pos="{} {} {}".format(pos[0], pos[1], pos[2]),
                    volume=volume,
                    pitch=pitch
                ),
                self.player_id
            )
            return True
        except Exception as e:
            print("[ERROR] [BetterPlayerObject] 播放音效失败: {}".format(e))
            return False

    @staticmethod
    def get_note_sound_pitch(key):
        """
        根据音符键值计算音高

        Args:
            key (int or list): 音符键值或键值列表

        Returns:
            float or list: 音高值或音高列表
        """
        if isinstance(key, list):
            return [math.pow(2, (float(k) - 12) / 12) for k in key]
        return math.pow(2, (float(key) - 12) / 12)

    def play_note_pling_sound(self, pos, key):
        """
        播放note.pling音效

        Args:
            pos (tuple): 播放位置 (x, y, z)
            key (int or list): 音符键值或键值列表

        Returns:
            bool: 是否成功
        """
        if isinstance(key, list):
            # 如果是列表，依次播放多个音符
            for k in key:
                pitch = self.get_note_sound_pitch(k)
                self.play_sound("note.pling", pos, 1, pitch)
            return True
        else:
            # 单个音符
            pitch = self.get_note_sound_pitch(key)
            return self.play_sound("note.pling", pos, 1, pitch)

    def teleport(self, pos, dim_id=None, rot=None):
        """
        传送玩家

        Args:
            pos (tuple): 目标位置 (x, y, z)
            dim_id (int): 维度ID
            rot (tuple): 朝向 (pitch, yaw)

        Returns:
            bool: 是否成功
        """
        try:
            if dim_id is not None:
                # 跨维度传送
                # ChangePlayerDimension 只接受2个参数: (dimensionId, pos)
                # 修复位置偏移：Y坐标增加2格
                adjusted_pos = (pos[0], pos[1] + 2, pos[2])
                dim_comp = self.comp_factory.CreateDimension(self.player_id)
                success = dim_comp.ChangePlayerDimension(dim_id, adjusted_pos)

                if success and rot:
                    # 如果需要设置朝向,在维度切换完成后通过事件回调设置
                    # 存储朝向信息到system,等待DimensionChangeFinishServerEvent触发
                    if self.system:
                        # 存储玩家ID和朝向信息
                        if not hasattr(self.system, '_pending_rotations'):
                            self.system._pending_rotations = {}
                        self.system._pending_rotations[self.player_id] = rot

                return success
            else:
                # 同维度传送
                pos_comp = self.comp_factory.CreatePos(self.player_id)
                if rot:
                    success1 = pos_comp.SetFootPos(self.player_id, pos)
                    # 修复：使用CreateRot组件设置朝向
                    rot_comp = self.comp_factory.CreateRot(self.player_id)
                    success2 = rot_comp.SetRot(rot)
                    return success1 and success2
                else:
                    return pos_comp.SetFootPos(self.player_id, pos)
        except Exception as e:
            print("[ERROR] [BetterPlayerObject] 传送玩家失败: {}".format(e))
            import traceback
            traceback.print_exc()
            return False

    def get_position(self):
        """
        获取玩家位置

        Returns:
            tuple: 位置 (x, y, z)
        """
        pos_comp = self.comp_factory.CreatePos(self.player_id)
        return pos_comp.GetFootPos()

    def get_dimension(self):
        """
        获取玩家所在维度

        Returns:
            int: 维度ID
        """
        dim_comp = self.comp_factory.CreateDimension(self.player_id)
        return dim_comp.GetPlayerDimensionId()

    def is_alive(self):
        """
        判断玩家是否存活

        Returns:
            bool: 是否存活
        """
        attr_comp = self.comp_factory.CreateAttr(self.player_id)
        # 修复: GetAttrValue只接受1个参数(属性类型)
        # CreateAttr已经绑定了player_id，不需要再次传递
        # 参考: SDK文档示例、老项目BetterPlayerObject.py:506-528
        health = attr_comp.GetAttrValue(
            serverApi.GetMinecraftEnum().AttrType.HEALTH
        )
        return health is not None and health > 0

    def get_health(self):
        """
        获取玩家生命值

        Returns:
            float: 生命值
        """
        attr_comp = self.comp_factory.CreateAttr(self.player_id)
        # 修复: GetAttrValue只接受1个参数(属性类型)
        # CreateAttr已经绑定了player_id，不需要再次传递
        # 参考: SDK文档示例、老项目BetterPlayerObject.py:506-528
        return attr_comp.GetAttrValue(
            serverApi.GetMinecraftEnum().AttrType.HEALTH
        )

    def set_health(self, health):
        """
        设置玩家生命值

        Args:
            health (float): 生命值

        Returns:
            bool: 是否成功
        """
        attr_comp = self.comp_factory.CreateAttr(self.player_id)
        return attr_comp.SetAttrValue(
            serverApi.GetMinecraftEnum().AttrType.HEALTH,
            self.player_id,
            health
        )

    def clear_inventory(self):
        """
        清空玩家背包

        Returns:
            bool: 是否成功
        """
        try:
            item_comp = self.comp_factory.CreateItem(self.player_id)
            # 清空所有槽位
            for slot in range(36):  # 0-35为背包槽位
                item_comp.SetInvItemNum(slot, 0)
            return True
        except Exception as e:
            print("[ERROR] [BetterPlayerObject] 清空背包失败: {}".format(e))
            return False

    def set_gamemode(self, gamemode):
        """
        设置玩家游戏模式

        Args:
            gamemode (int): 游戏模式 (0=生存, 1=创造, 2=冒险, 3=观察者)

        Returns:
            bool: 是否成功
        """
        try:
            game_comp = self.comp_factory.CreateGame(self.level_id)
            return game_comp.SetPlayerGameType(self.player_id, gamemode)
        except:
            return False

    def GetFootPos(self):
        """
        获取玩家脚部位置(兼容老API)

        Returns:
            tuple: 位置 (x, y, z)
        """
        return self.get_position()

    def GetDimensionId(self):
        """
        获取玩家维度ID(兼容老API)

        Returns:
            int: 维度ID
        """
        return self.get_dimension()

    def SendMessage(self, message, color=u'\xa7f'):
        """发送消息(兼容老API)"""
        return self.send_message(message, color)

    def SendTip(self, tip):
        """发送提示(兼容老API)"""
        return self.send_tip(tip)

    def SendTitle(self, title, sub_title=None):
        """发送标题(兼容老API)"""
        return self.send_title(title, sub_title)

    # ========== 观战模式相关方法 ==========

    def set_game_type(self, game_type):
        """
        设置玩家游戏模式(兼容老API)

        Args:
            game_type (int): 游戏模式
                0 = Survival (生存)
                1 = Creative (创造)
                2 = Adventure (冒险)
                3 = Spectator (观察者/旁观)

        Returns:
            bool: 是否成功
        """
        try:
            # 使用CreatePlayer组件而非CreateGameMode
            # 参考: SDK文档 - 接口/玩家/游戏模式.md SetPlayerGameType
            player_comp = self.comp_factory.CreatePlayer(self.player_id)
            player_comp.SetPlayerGameType(game_type)
            return True
        except Exception as e:
            print("[ERROR] [BetterPlayerObject] 设置游戏模式失败: {}".format(e))
            return False

    def SetImmuneDamage(self, immune):
        """
        设置伤害免疫

        Args:
            immune (bool): True=免疫伤害, False=取消免疫

        Returns:
            bool: 是否成功
        """
        try:
            # 使用CreateHurt组件的ImmuneDamage方法
            # 参考: SDK文档 - 接口/实体/行为.md ImmuneDamage
            hurt_comp = self.comp_factory.CreateHurt(self.player_id)
            hurt_comp.ImmuneDamage(immune)
            return True
        except Exception as e:
            print("[ERROR] [BetterPlayerObject] 设置伤害免疫失败: {}".format(e))
            return False

    def ChangeFlyState(self, can_fly):
        """
        设置飞行状态

        Args:
            can_fly (bool): True=允许飞行, False=禁止飞行

        Returns:
            bool: 是否成功
        """
        try:
            fly_comp = self.comp_factory.CreateFly(self.player_id)
            fly_comp.ChangePlayerFlyState(can_fly)
            return True
        except Exception as e:
            print("[ERROR] [BetterPlayerObject] 设置飞行状态失败: {}".format(e))
            return False

    def GetHealth(self):
        """获取玩家生命值(兼容老API)"""
        return self.get_health()

    def GetPos(self):
        """获取玩家位置(兼容老API)"""
        return self.get_position()
