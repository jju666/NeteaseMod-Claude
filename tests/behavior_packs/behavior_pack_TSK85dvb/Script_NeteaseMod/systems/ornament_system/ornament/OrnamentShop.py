# -*- coding: utf-8 -*-
"""
OrnamentShop - 装扮商店 (100%还原老项目UI)

功能:
- 装扮商店UI (完全还原老项目风格)
- 装扮预览
- 购买/装备逻辑

原文件: Parts/ECBedWarsOrnament/unlockupgrade/UnlockUpgradeUIHandler.py
重构为: systems/ornament_system/ornament/OrnamentShop.py

100%还原要点:
1. 标题: "解锁&升级中心" (不是"装扮商店")
2. 硬币显示: "我拥有 起床战争硬币: XXX"
3. 10个装扮分类按钮 (多行格式)
4. 三优先级排序: 已装备 > 已拥有 > 未解锁
5. 完整的状态机按钮逻辑
"""

import mod.server.extraServerApi as serverApi


class OrnamentShop(object):
    """
    装扮商店 (100%还原老项目UI)

    负责装扮的展示和购买
    """

    def __init__(self, ornament_system):
        """
        初始化装扮商店

        Args:
            ornament_system: OrnamentSystem实例
        """
        self.ornament_system = ornament_system
        self.game_system = ornament_system.game_system

        # 引用UnlockUpgradeManager
        self.unlock_upgrade_mgr = None

        # 当前查看状态 {player_id: {'type_id': str, 'prop_id': str}}
        self.player_viewing_state = {}

        print("[INFO] [OrnamentShop] 初始化完成")

    def initialize(self):
        """初始化装扮商店"""
        try:
            # 获取UnlockUpgradeManager引用
            self.unlock_upgrade_mgr = self.ornament_system.unlock_upgrade_manager
            if not self.unlock_upgrade_mgr:
                print("[ERROR] [OrnamentShop] UnlockUpgradeManager未找到")
                return

            print("[INFO] [OrnamentShop] 装扮商店初始化成功")
        except Exception as e:
            print("[ERROR] [OrnamentShop] 初始化失败: {}".format(str(e)))
            import traceback
            traceback.print_exc()

    def cleanup(self):
        """清理装扮商店"""
        try:
            self.player_viewing_state = {}
            print("[INFO] [OrnamentShop] 清理完成")
        except Exception as e:
            print("[ERROR] [OrnamentShop] 清理失败: {}".format(str(e)))

    # ========== 商店入口 ==========

    def open_shop(self, player_id):
        """
        打开装扮商店 (入口方法)

        Args:
            player_id (str): 玩家ID
        """
        self.show_shop_ui(player_id)

    # ========== UI方法 (100%还原老项目) ==========

    def show_shop_ui(self, player_id):
        """
        显示装扮商店主界面 (100%还原)

        Args:
            player_id (str): 玩家ID

        还原要点:
        - 标题: "解锁&升级中心"
        - 硬币显示: "我拥有 {yellow}起床战争硬币: {coin}"
        - 测试模式: "∞ (测试模式)"
        - 10个装扮类型按钮 (多行格式)
        - 按钮格式: "{类型名}{reset}{dark-gray}({已拥有}/{总数})\n{dark-gray}{类型介绍}"
        """
        try:
            # 1. 获取ServerForm构建器
            from Script_NeteaseMod.modConfig import MOD_NAME
            server_form_sys = serverApi.GetSystem(MOD_NAME, 'ServerFormServerSystem')
            if not server_form_sys:
                print("[ERROR] [OrnamentShop] ServerFormServerSystem未找到")
                return

            ServerForm = server_form_sys.getFormBuilder()

            # 2. 创建表单 (使用老项目标题)
            form = ServerForm(title=u'解锁&升级中心')

            # 3. 显示硬币 (支持测试模式)
            from Script_NeteaseMod.util.BetterSystemUtil import BetterSystemUtil

            coin = self._get_player_coin(player_id)
            test_mode = self._is_test_mode()

            if test_mode:
                label_text = BetterSystemUtil.format_text(
                    u'我拥有 {yellow}起床战争硬币: {green}∞ (测试模式)'
                )
            else:
                label_text = BetterSystemUtil.format_text(
                    u'我拥有 {yellow}起床战争硬币: {coin}',
                    coin=coin
                )
            form.label(label_text)

            # 4. 添加10个装扮类型按钮
            for type_data in self.unlock_upgrade_mgr.get_all_type_data():
                # 获取玩家在该类型下已拥有的数量
                have_count = self.unlock_upgrade_mgr.get_player_have_count(
                    player_id, type_data['type_id']
                )
                total_count = type_data['total_count']

                # 先格式化type_name和introduce中的颜色代码
                formatted_name = BetterSystemUtil.format_text(type_data['type_name'])
                formatted_intro = BetterSystemUtil.format_text(type_data['introduce'])

                # 按钮文本 (多行格式)
                button_text = BetterSystemUtil.format_text(
                    u"{name}{reset}{dark-gray}({have}/{total})\n{dark-gray}{intro}",
                    name=formatted_name,
                    have=have_count,
                    total=total_count,
                    intro=formatted_intro
                )
                form.button(button_text, type_data['type_id'])

            # 5. 发送表单并设置回调
            form.send(player_id, callback=self._cb_main)

            print("[INFO] [OrnamentShop] 向玩家 {} 显示主界面".format(player_id))

        except Exception as e:
            print("[ERROR] [OrnamentShop] 显示主界面失败: player={} error={}".format(
                player_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    def show_category_ui(self, player_id, type_id):
        """
        显示装扮分类界面 (100%还原)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID

        还原要点:
        - 标题使用类型名称 (含颜色代码)
        - 显示类型介绍
        - 添加"返回"按钮
        - **三优先级排序** (关键!):
          1. 已装备的装扮
          2. 已拥有但未装备的装扮
          3. 未解锁的装扮
        - 装扮按钮格式 (多行):
          "{已装备标记}{装扮名}{reset}{dark-gray} - {状态}\n{详细信息}"
        """
        try:
            # 1. 获取ServerForm系统
            from Script_NeteaseMod.modConfig import MOD_NAME
            from Script_NeteaseMod.util.BetterSystemUtil import BetterSystemUtil

            server_form_sys = serverApi.GetSystem(MOD_NAME, 'ServerFormServerSystem')
            ServerForm = server_form_sys.getFormBuilder()

            # 2. 获取类型配置
            type_data = self.unlock_upgrade_mgr.get_type_data(type_id)
            if not type_data:
                print("[ERROR] [OrnamentShop] 类型不存在: {}".format(type_id))
                self.show_shop_ui(player_id)
                return

            # 3. 创建表单 - 格式化类型名称
            formatted_type_name = BetterSystemUtil.format_text(type_data['type_name'])
            form = ServerForm(title=formatted_type_name)

            # 4. 添加类型介绍和返回按钮 - 格式化介绍
            formatted_intro = BetterSystemUtil.format_text(type_data['introduce'])
            form.label(formatted_intro)
            form.button(u"返回", "back")

            # 5. 获取所有装扮并分组 (三优先级)
            all_ornaments = type_data['ornaments']
            equipped = []  # 已装备
            owned = []     # 已拥有但未装备
            locked = []    # 未解锁

            for ornament in all_ornaments:
                player_entry = self.unlock_upgrade_mgr.get_player_entry(
                    player_id, type_id, ornament['prop_id']
                )

                if type_data['have_state'] and player_entry['equipped']:
                    equipped.append((ornament, player_entry))
                elif player_entry['level'] > 0:
                    owned.append((ornament, player_entry))
                else:
                    locked.append((ornament, player_entry))

            # 6. 按优先级添加按钮
            for group in [equipped, owned, locked]:
                for ornament, player_entry in group:
                    button_text = self._format_ornament_button(
                        ornament, player_entry, type_data, player_id
                    )
                    form.button(button_text, ornament['prop_id'])

            # 7. 发送表单 (使用默认参数避免lambda陷阱)
            def callback(args, tid=type_id):
                return self._cb_category(args, tid)

            form.send(player_id, callback=callback)

            # 记录查看状态
            self.player_viewing_state[player_id] = {'type_id': type_id}

            print("[INFO] [OrnamentShop] 向玩家 {} 显示分类界面: {}".format(player_id, type_id))

        except Exception as e:
            print("[ERROR] [OrnamentShop] 显示分类界面失败: player={} type={} error={}".format(
                player_id, type_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    def show_ornament_detail(self, player_id, type_id, prop_id):
        """
        显示装扮详情界面 (100%还原)

        Args:
            player_id (str): 玩家ID
            type_id (str): 类型ID
            prop_id (str): 装扮ID

        还原要点:
        - 标题使用装扮名称
        - 显示装扮介绍
        - 显示当前等级 ("未解锁"显示为红色)
        - **状态机按钮逻辑** (关键!):
          未解锁状态:
            - 非卖品 → 禁用按钮
            - 可购买 → "{bold}{dark-gray}立即解锁{reset}\n需花费 {price} 硬币"
            - 余额不足 → "{dark-gray}余额不足以解锁\n需花费 {price} 硬币"
          已拥有状态:
            - 支持装备且已装备 → 禁用按钮 "已装备"
            - 支持装备但未装备 → "{bold}{yellow}立即装备"
        """
        try:
            # 1. 获取ServerForm系统
            from Script_NeteaseMod.modConfig import MOD_NAME
            from Script_NeteaseMod.util.BetterSystemUtil import BetterSystemUtil

            server_form_sys = serverApi.GetSystem(MOD_NAME, 'ServerFormServerSystem')
            ServerForm = server_form_sys.getFormBuilder()

            # 2. 获取装扮数据
            ornament = self.unlock_upgrade_mgr.get_ornament(type_id, prop_id)
            if not ornament:
                print("[ERROR] [OrnamentShop] 装扮不存在: {} {}".format(type_id, prop_id))
                self.show_category_ui(player_id, type_id)
                return

            player_entry = self.unlock_upgrade_mgr.get_player_entry(player_id, type_id, prop_id)
            type_data = self.unlock_upgrade_mgr.get_type_data(type_id)

            # 3. 创建表单 - 格式化装扮名称
            formatted_ornament_name = BetterSystemUtil.format_text(ornament['name'])
            form = ServerForm(title=formatted_ornament_name)

            # 4. 添加介绍 - 格式化介绍文本
            formatted_ornament_intro = BetterSystemUtil.format_text(ornament['introduce'])
            form.label(formatted_ornament_intro)
            form.label(u"")  # 空行

            # 5. 添加等级信息
            if player_entry['level'] == 0:
                level_text = BetterSystemUtil.format_text(u"当前等级: {red}未解锁")
            else:
                level_text = BetterSystemUtil.format_text(
                    u"当前等级: {level}",
                    level=player_entry['level']
                )
            form.label(level_text)
            form.label(u"")  # 空行

            # 6. 添加操作按钮 (状态机逻辑)
            if player_entry['level'] == 0:  # 未解锁
                price = ornament.get('price', 0)
                coin = self._get_player_coin(player_id)
                test_mode = self._is_test_mode()

                if price < 0:
                    # 非卖品
                    form.button(BetterSystemUtil.format_text(u"{dark-gray}非卖品"), "self")
                elif test_mode or coin >= price:
                    # 可购买
                    button_text = BetterSystemUtil.format_text(
                        u"{bold}{dark-gray}立即解锁{reset}\n需花费 {price} 硬币",
                        price=price
                    )
                    form.button(button_text, "buy")
                else:
                    # 余额不足
                    button_text = BetterSystemUtil.format_text(
                        u"{dark-gray}余额不足以解锁\n需花费 {price} 硬币",
                        price=price
                    )
                    form.button(button_text, "self")
            else:  # 已拥有
                if type_data['have_state']:  # 支持装备
                    if player_entry['equipped']:
                        # 已装备
                        form.button(BetterSystemUtil.format_text(u"{dark-gray}已装备"), "self")
                    else:
                        # 未装备
                        form.button(
                            BetterSystemUtil.format_text(u"{bold}{yellow}立即装备"),
                            "set"
                        )
                # TODO: 支持升级逻辑 (多等级装扮)

            # 7. 添加返回按钮
            form.button(u"返回", "back")

            # 8. 发送表单 (使用默认参数避免lambda陷阱)
            def callback(args, tid=type_id, pid=prop_id):
                return self._cb_detail(args, tid, pid)

            form.send(player_id, callback=callback)

            # 记录查看状态
            self.player_viewing_state[player_id] = {
                'type_id': type_id,
                'prop_id': prop_id
            }

            print("[INFO] [OrnamentShop] 向玩家 {} 显示详情界面: {} {}".format(
                player_id, type_id, prop_id
            ))

        except Exception as e:
            print("[ERROR] [OrnamentShop] 显示详情界面失败: player={} type={} prop={} error={}".format(
                player_id, type_id, prop_id, str(e)
            ))
            import traceback
            traceback.print_exc()

    # ========== UI回调函数 ==========

    def _cb_main(self, args):
        """主界面回调"""
        player_id = args['playerId']
        click = args.get('click')

        if click is None or click == -1:
            return

        # click 是 type_id
        self.show_category_ui(player_id, click)

    def _cb_category(self, args, type_id):
        """分类界面回调"""
        player_id = args['playerId']
        click = args.get('click')

        if click == "back":
            self.show_shop_ui(player_id)
        elif click:
            # click 是 prop_id
            self.show_ornament_detail(player_id, type_id, click)

    def _cb_detail(self, args, type_id, prop_id):
        """详情界面回调"""
        player_id = args['playerId']
        click = args.get('click')

        if click == "back":
            self.show_category_ui(player_id, type_id)
        elif click == "self":
            # 刷新详情页 (无操作或禁用按钮)
            self.show_ornament_detail(player_id, type_id, prop_id)
        elif click == "buy":
            # 执行购买
            result = self.unlock_upgrade_mgr.buy_ornament(player_id, type_id, prop_id)
            self._show_purchase_result(player_id, result, type_id, prop_id)
        elif click == "set":
            # 执行装备
            success = self.unlock_upgrade_mgr.equip_ornament(player_id, type_id, prop_id)
            if success:
                print("[INFO] [OrnamentShop] 装备成功: player={} type={} prop={}".format(
                    player_id, type_id, prop_id
                ))
            # 刷新详情页显示最新状态
            self.show_ornament_detail(player_id, type_id, prop_id)

    # ========== 辅助方法 ==========

    def _format_ornament_button(self, ornament, player_entry, type_data, player_id):
        """
        格式化装扮按钮文本 (完全还原老项目格式)

        Args:
            ornament (dict): 装扮配置
            player_entry (dict): 玩家装扮数据
            type_data (dict): 类型配置
            player_id (str): 玩家ID

        Returns:
            unicode: 格式化后的按钮文本
        """
        from Script_NeteaseMod.util.BetterSystemUtil import BetterSystemUtil

        # 状态文本
        if player_entry['level'] > 0:
            status = BetterSystemUtil.format_text(u"{dark-green}已拥有")
        else:
            status = BetterSystemUtil.format_text(u"{dark-red}未解锁")

        # 详细信息
        if player_entry['level'] == 0:  # 未解锁
            price = ornament.get('price', 0)
            coin = self._get_player_coin(player_id)
            test_mode = self._is_test_mode()

            if price < 0:
                detail = BetterSystemUtil.format_text(u"{dark-gray}非卖品")
            elif test_mode or coin >= price:
                detail = BetterSystemUtil.format_text(
                    u"{dark-blue}可解锁: {price} 硬币",
                    price=price
                )
            else:
                detail = BetterSystemUtil.format_text(
                    u"{dark-gray}{price} 硬币",
                    price=price
                )
        else:  # 已拥有
            detail = BetterSystemUtil.format_text(u"{dark-gray}点击查看详情")

        # 组合按钮文本
        equipped_mark = u""
        if type_data['have_state'] and player_entry.get('equipped', False):
            equipped_mark = BetterSystemUtil.format_text(u"{bold}{yellow}[已装备] ")

        # 先格式化装扮名称中的颜色代码
        formatted_name = BetterSystemUtil.format_text(ornament['name'])

        button_text = BetterSystemUtil.format_text(
            u"{equipped}{reset}{name}{reset}{dark-gray} - {status}\n{detail}",
            equipped=equipped_mark,
            name=formatted_name,
            status=status,
            detail=detail
        )

        return button_text

    def _show_purchase_result(self, player_id, result, type_id, prop_id):
        """
        显示购买结果

        Args:
            player_id (str): 玩家ID
            result (dict): 购买结果 {'success': bool, 'message': str}
            type_id (str): 类型ID
            prop_id (str): 装扮ID
        """
        try:
            from Script_NeteaseMod.modConfig import MOD_NAME
            from Script_NeteaseMod.util.BetterSystemUtil import BetterSystemUtil

            server_form_sys = serverApi.GetSystem(MOD_NAME, 'ServerFormServerSystem')
            ServerForm = server_form_sys.getFormBuilder()

            form = ServerForm(title=u"购买结果")
            form.label(result['message'])
            form.button(BetterSystemUtil.format_text(u"{dark-gray}继续"))

            # 使用默认参数避免lambda陷阱
            def callback(args, tid=type_id, pid=prop_id):
                return self.show_ornament_detail(args['playerId'], tid, pid)

            form.send(player_id, callback=callback)

        except Exception as e:
            print("[ERROR] [OrnamentShop] 显示购买结果失败: {}".format(str(e)))
            # 即使失败也要刷新详情页
            self.show_ornament_detail(player_id, type_id, prop_id)

    def _get_player_coin(self, player_id):
        """
        获取玩家硬币数量

        Args:
            player_id (str): 玩家ID

        Returns:
            int: 硬币数量
        """
        try:
            room_system = getattr(self.game_system, 'room_system', None)
            if room_system:
                coin = room_system.get_player_data(player_id, "coin")
                return coin if isinstance(coin, (int, long)) else 0
            return 0
        except Exception as e:
            print("[ERROR] [OrnamentShop] 获取玩家硬币失败: {}".format(str(e)))
            return 0

    def _is_test_mode(self):
        """
        检查是否为测试模式

        Returns:
            bool: 是否为测试模式
        """
        try:
            room_system = getattr(self.game_system, 'room_system', None)
            if room_system:
                return getattr(room_system, 'ornament_shop_test_mode', False)
            return False
        except:
            return False

    # ========== 兼容旧接口 (保留现有功能) ==========

    def close_shop(self, player_id):
        """
        关闭装扮商店

        Args:
            player_id (str): 玩家ID
        """
        if player_id in self.player_viewing_state:
            del self.player_viewing_state[player_id]

        print("[INFO] [OrnamentShop] 玩家 {} 关闭商店".format(player_id))
