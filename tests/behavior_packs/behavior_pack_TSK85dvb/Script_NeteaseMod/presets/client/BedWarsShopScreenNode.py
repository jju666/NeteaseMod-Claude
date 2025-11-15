# -*- coding: utf-8 -*-
import json

import mod.client.extraClientApi as clientApi

ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()
ScreenNode = clientApi.GetScreenNodeCls()

comp_item = clientApi.GetEngineCompFactory().CreateItem(clientApi.GetLevelId())
comp_game = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())

PATH_MAIN = "variables_button_mappings_and_controls/safezone_screen_matrix/inner_matrix/safezone_screen_panel/root_screen_panel"
PATH_SCROLL_MAIN = PATH_MAIN + "/content/scroll_main"
PATH_PANEL_DETAIL_SCROLL = PATH_MAIN + "/content/panel_detail/scroll_detail"
NAME_LAYOUT_GRID_BLOCK = "layout_grid_block"
NAME_LAYOUT_GRID_GRID = "layout_grid_grid"

MINI_MODE_SCREEN_WIDTH = 400
PC_WINDOW_MOD_WIDTH = 600


class BedWarsShopScreenNode(ScreenNode):
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.preset_client = None  # 关联的客户端预设对象
        self.ui_data = param
        self.tooltip = ""
        self.current_tab = 0
        self.current_detail_tab = None  # type: int | None
        # print(json.dumps(self.ui_data, indent=4, ensure_ascii=False))
        self.scheduled_grid_block_width_refresh = False
        self.scheduled_grid_grid_width_refresh = False
        comp_game.AddTimer(0, self.init_grid_entry_width)

    # comp_game.AddTimer(0.1, self.init_grid_entry_width)

    def init_grid_entry_width(self):
        self.refresh_grid_grid_width()
        self.refresh_grid_block_width()

    def Create(self):
        """
		@description UI创建成功时调用
		"""
        comp = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
        comp.SetEnableGaussianBlur(True)
        comp.SetGaussianBlurRadius(1)
        # 创建背景到最外层，并会自动播放渐变动画
        control = self.GetBaseUIControl("variables_button_mappings_and_controls")
        self.CreateChildControl("bedwars_shop.bg", "bg", control)
        if self.ui_data['categories'][0]['ui']['layout'] == "DETAIL":
            self.current_detail_tab = 0
        else:
            self.current_detail_tab = None

    def Destroy(self):
        """
		@description UI销毁时调用
		"""
        comp = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
        comp.SetEnableGaussianBlur(False)
        # 通过代码让背景渐变消失
        bg = self.GetBaseUIControl("variables_button_mappings_and_controls/bg")
        if bg is not None:
            bg.RemoveAnimation("alpha")
            bg.SetAnimation("alpha", "bedwars_shop", "anim_bg_alpha_out", True)

    def OnActive(self):
        """
		@description UI重新回到栈顶时调用
		"""

    def OnDeactive(self):
        """
		@description 栈顶UI有其他UI入栈时调用
		"""
        pass

    def Update(self):
        updated = False
        if self.scheduled_grid_block_width_refresh:
            self.refresh_grid_block_width()
            updated = True
            self.scheduled_grid_block_width_refresh = False
        if self.scheduled_grid_grid_width_refresh:
            self.refresh_grid_grid_width()
            updated = True
            self.scheduled_grid_grid_width_refresh = False
        if updated:
            print("BedWarsShopScreenNode UpdateScreen")
            comp = clientApi.GetEngineCompFactory().CreateGame(clientApi.GetLevelId())
            comp.AddTimer(0.1, lambda: self.UpdateScreen())

    def get_autolayout_count_block_main(self):
        width = self.GetBaseUIControl(PATH_SCROLL_MAIN).GetSize()[0]
        return max(1, int(float(width) / 200))

    def get_autolayout_count_block_detail(self):
        width = self.GetBaseUIControl(PATH_PANEL_DETAIL_SCROLL).GetSize()[0]
        return max(1, int(float(width) / 200))

    def get_autolayout_count_grid(self):
        width = self.GetBaseUIControl(PATH_SCROLL_MAIN).GetSize()[0]
        return max(1, int(float(width) / 64))

    def refresh_grid_block_width(self):
        self.refresh_grid_block_width_main()
        self.refresh_grid_block_width_detail()

    def refresh_grid_block_width_main(self):
        scroll = self.GetBaseUIControl(PATH_SCROLL_MAIN)
        if scroll is None:
            print("scroll is None")
            return
        if scroll.GetVisible() is False:
            return
        scroll_content = scroll.asScrollView().GetScrollViewContentControl()
        layout_grid = scroll_content.GetChildByName(NAME_LAYOUT_GRID_BLOCK)
        if layout_grid is None:
            print("layout_grid is None")
            return
        row_count = self.get_autolayout_count_block_main()
        children = self.GetChildrenName(layout_grid.GetPath())
        for child_name in children:
            child = layout_grid.GetChildByName(child_name)
            child.SetFullSize("x", {
                "followType": "parent",
                "relativeValue": float(float(1) / row_count) - 0.0001,
            })

    def refresh_grid_block_width_detail(self):
        scroll = self.GetBaseUIControl(PATH_PANEL_DETAIL_SCROLL)
        if scroll is None:
            print("scroll is None")
            return
        if scroll.GetVisible() is False:
            return
        scroll_content = scroll.asScrollView().GetScrollViewContentControl()
        layout_grid = scroll_content.GetChildByName(NAME_LAYOUT_GRID_BLOCK)
        if layout_grid is None:
            print("layout_grid is None")
            return
        row_count = self.get_autolayout_count_block_detail()
        children = self.GetChildrenName(layout_grid.GetPath())
        for child_name in children:
            child = layout_grid.GetChildByName(child_name)
            child.SetFullSize("x", {
                "followType": "parent",
                "relativeValue": float(float(1) / row_count) - 0.0001,
            })

    def refresh_grid_grid_width(self):
        scroll = self.GetBaseUIControl(PATH_SCROLL_MAIN)
        if scroll is None:
            print("scroll is None")
            return
        scroll_content = scroll.asScrollView().GetScrollViewContentControl()
        layout_grid = scroll_content.GetChildByName(NAME_LAYOUT_GRID_GRID)
        if layout_grid is None:
            print("layout_grid is None")
            return
        row_count = self.get_autolayout_count_grid()
        children = self.GetChildrenName(layout_grid.GetPath())
        for child_name in children:
            child = layout_grid.GetChildByName(child_name)
            child.SetFullSize("x", {
                "followType": "parent",
                "relativeValue": float(float(1) / row_count) - 0.0001,
            })

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_click_close(self, args):
        """
		玩家点击关闭按钮
		:param args:
		:return:
		"""
        clientApi.PopScreen()

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_exit(self, args):
        """
		玩家点击返回（esc/e）
		:return:
		"""
        clientApi.PopScreen()

    def show_tooltip(self, content):
        control_main = self.GetBaseUIControl(PATH_MAIN)
        control_tooltip = control_main.GetChildByName("tooltip")
        if control_tooltip is not None:
            self.RemoveChildControl(control_tooltip)
        self.tooltip = content
        self.CreateChildControl("bedwars_shop.tooltip", "tooltip", control_main)

    @ViewBinder.binding(ViewBinder.BF_BindString, "#pn_title_right.text")
    def on_refresh_title(self):
        return self.ui_data['currencies']

    @ViewBinder.binding(ViewBinder.BF_BindString, "#tooltip.text")
    def on_refresh_tooltip(self):
        return self.tooltip

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#title_name.default")
    def on_refresh_title_name_default(self):
        return self.ui_data['type'] == 'default'

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#title_name.upgrade")
    def on_refresh_title_name_upgrade(self):
        return self.ui_data['type'] == 'upgrade'

    # region TAB

    @ViewBinder.binding(ViewBinder.BF_BindInt, "#pn_tabs.item_count")
    def on_tab_grid_resize(self):
        return len(self.ui_data['categories'])

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "shop_tabs", "#label_name.text")
    def on_refresh_item_label(self, index):
        return self.ui_data['categories'][index]['name']

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "shop_tabs", "#texture")
    def on_refresh_item_icon(self, index):
        texture = self.ui_data['categories'][index]['ui']['categoryTexture']
        return texture

    @ViewBinder.binding(ViewBinder.BF_ToggleChanged, "#tab_toggle")
    def on_toggle_changed(self, args):
        index = args['index']
        if index >= len(self.ui_data['categories']):
            index = 0
        self.current_tab = index
        if self.ui_data['categories'][index]['ui']['layout'] == "DETAIL":
            self.current_detail_tab = 0
        else:
            self.current_detail_tab = None
        self.scheduled_grid_block_width_refresh = True
        self.scheduled_grid_grid_width_refresh = True

    # endregion

    # region CONTENT

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#bedwars_shop.detail_mode")
    def on_refresh_detail_mode(self):
        return self.ui_data['categories'][self.current_tab]['ui']['layout'] == "DETAIL"

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#bedwars_shop.not_detail_mode")
    def on_refresh_not_detail_mode(self):
        return self.ui_data['categories'][self.current_tab]['ui']['layout'] != "DETAIL"

    @ViewBinder.binding(ViewBinder.BF_BindString, "#main_layout.title")
    def on_refresh_shop_title(self):
        return self.ui_data['categories'][self.current_tab]['name']

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#layout_grid_grid.visible")
    def on_refresh_grid_visible(self):
        return self.ui_data['categories'][self.current_tab]['ui']['layout'] == "GRID"

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#layout_grid_block.visible")
    def on_refresh_block_visible(self):
        return (self.ui_data['categories'][self.current_tab]['ui']['layout'] == "BLOCK" or
                self.ui_data['categories'][self.current_tab]['ui']['layout'] == "DETAIL")

    # block

    @ViewBinder.binding(ViewBinder.BF_BindString, "#layout_grid_block.update")
    def on_refresh_grid_block_update(self):
        return
        self.scheduled_grid_block_width_refresh = True

    @ViewBinder.binding(ViewBinder.BF_BindInt, "#layout_grid.grid_item_count")
    def on_refresh_grid_item_count(self):
        return len(self.ui_data['categories'][self.current_tab]['goods'])

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_block", "#grid_entry.title")
    def on_refresh_layout_grid_block_title(self, index):
        return self.ui_data['categories'][self.current_tab]['goods'][index]['name']

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_block", "#grid_entry.intro")
    def on_refresh_layout_grid_block_intro(self, index):
        return self.ui_data['categories'][self.current_tab]['goods'][index]['intro']

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_block", "#grid_entry.price")
    def on_refresh_layout_grid_block_price(self, index):
        return self.ui_data['categories'][self.current_tab]['goods'][index]['price']

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_block", "#grid_entry.disable.msg")
    def on_refresh_layout_grid_block_disable(self, index):
        msg = self.ui_data['categories'][self.current_tab]['goods'][index]['cannot_buy_msg']
        if msg is None:
            return ""
        return " §c" + msg

    @ViewBinder.binding_collection(ViewBinder.BF_BindBool, "layout_grid_block", "#grid_entry.locked")
    def on_refresh_layout_grid_block_locked(self, index):
        good = self.ui_data['categories'][self.current_tab]['goods'][index]
        return good['cannot_buy_msg'] is not None

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_block", "#grid_entry.count")
    def on_refresh_layout_grid_block_count(self, index):
        count = self.ui_data['categories'][self.current_tab]['goods'][index]['show_item_dict']['count']
        if count is None or count <= 1:
            return ""
        return str(count)

    @ViewBinder.binding_collection(ViewBinder.BF_BindInt, "layout_grid_block", "#grid_entry.item")
    def on_refresh_layout_grid_block_item(self, index):
        item_dict = self.ui_data['categories'][self.current_tab]['goods'][index]['show_item_dict']
        identifier = item_dict['newItemName'] if 'newItemName' in item_dict else item_dict['itemName']
        aux_value = item_dict['newAuxValue'] if 'newAuxValue' in item_dict else (
            item_dict['auxValue'] if 'auxValue' in item_dict else 0)
        enchantment = len(item_dict['enchantData']) > 0 if 'enchantData' in item_dict else False
        info = comp_item.GetItemBasicInfo(identifier, aux_value, enchantment)
        if info:
            return info['id_aux']
        else:
            print("[ERROR] [BedWarsShopScreenNode] on_refresh_layout_grid_block_item: not found item info of {}:{}".format(identifier, aux_value))
            return 0

    @ViewBinder.binding_collection(ViewBinder.BF_BindFloat, "layout_grid_block", "#grid_entry.item_alpha")
    def on_refresh_layout_grid_block_item_alpha(self, index):
        return 1.0 if self.ui_data['categories'][self.current_tab]['goods'][index]['cannot_buy_msg'] is None else 0.8

    @ViewBinder.binding_collection(ViewBinder.BF_BindBool, "layout_grid_block", "#grid_entry.toggle_border")
    def on_refresh_layout_grid_block_toggle_border(self, index):
        good = self.ui_data['categories'][self.current_tab]['goods'][index]
        return self.ui_data['categories'][self.current_tab]['ui'][
            'layout'] == "DETAIL" and self.current_detail_tab == index

    # grid

    @ViewBinder.binding(ViewBinder.BF_BindString, "#layout_grid_grid.update")
    def on_refresh_grid_grid_update(self):
        return
        self.scheduled_grid_grid_width_refresh = True

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_grid", "#grid_entry.price")
    def on_refresh_layout_grid_grid_price(self, index):
        return self.ui_data['categories'][self.current_tab]['goods'][index]['price']

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_grid", "#grid_entry.disable.msg")
    def on_refresh_layout_grid_grid_disable(self, index):
        msg = self.ui_data['categories'][self.current_tab]['goods'][index]['cannot_buy_msg']
        if msg is None:
            return ""
        return " §c" + msg

    @ViewBinder.binding_collection(ViewBinder.BF_BindBool, "layout_grid_grid", "#grid_entry.locked")
    def on_refresh_layout_grid_grid_locked(self, index):
        return self.ui_data['categories'][self.current_tab]['goods'][index]['cannot_buy_msg'] is not None

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "layout_grid_grid", "#grid_entry.count")
    def on_refresh_layout_grid_grid_count(self, index):
        count = self.ui_data['categories'][self.current_tab]['goods'][index]['show_item_dict']['count']
        if count is None or count <= 1:
            return ""
        return str(count)

    @ViewBinder.binding_collection(ViewBinder.BF_BindInt, "layout_grid_grid", "#grid_entry.item")
    def on_refresh_layout_grid_grid_item(self, index):
        item_dict = self.ui_data['categories'][self.current_tab]['goods'][index]['show_item_dict']
        identifier = item_dict['newItemName'] if 'newItemName' in item_dict else item_dict['itemName']
        aux_value = item_dict['newAuxValue'] if 'newAuxValue' in item_dict else (
            item_dict['auxValue'] if 'auxValue' in item_dict else 0)
        enchantment = len(item_dict['enchantData']) > 0 if 'enchantData' in item_dict else False
        return comp_item.GetItemBasicInfo(identifier, aux_value, enchantment)['id_aux']

    @ViewBinder.binding_collection(ViewBinder.BF_BindFloat, "layout_grid_grid", "#grid_entry.item_alpha")
    def on_refresh_layout_grid_grid_item_alpha(self, index):
        return 1.0 if self.ui_data['categories'][self.current_tab]['goods'][index]['cannot_buy_msg'] is None else 0.8

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_click_button(self, args):
        """
		玩家点击功能按钮
		:param args:
		:return:
		"""
        if '#collection_index' not in args:
            print("[ERROR] [BedWarsShopScreenNode] on_click_button: '#collection_index' not in args")
            return
        goods_index = args['#collection_index']
        goods = self.ui_data['categories'][self.current_tab]['goods'][goods_index]
        goods_key = goods['key']
        info = {
            "player_id": clientApi.GetLocalPlayerId(),
            "category_index": self.current_tab,
            "goods_index": goods_index,
            "goods_key": goods_key
        }
        if self.ui_data['categories'][self.current_tab]['ui']['layout'] == "DETAIL":
            if goods_index != self.current_detail_tab:
                # 切换详情页tab
                self.current_detail_tab = goods_index
                self.UpdateScreen()
            else:
                # 尝试购买
                self._notify_to_server("BedWarsShopTryBuy", info)
        else:
            self._notify_to_server("BedWarsShopTryBuy", info)

    # endregion

    # region DETAIL
    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_click_detail_button(self, args):
        if self.ui_data['categories'][self.current_tab]['ui']['layout'] == "DETAIL":
            info = {
                "player_id": clientApi.GetLocalPlayerId(),
                "category_index": self.current_tab,
                "goods_index": self.current_detail_tab,
                "goods_key": self.ui_data['categories'][self.current_tab]['goods'][self.current_detail_tab]['key']
            }
            self._notify_to_server("BedWarsShopTryBuy", info)

    @ViewBinder.binding(ViewBinder.BF_BindString, "#pn_detail.title")
    def on_refresh_detail_title(self):
        if self.current_detail_tab is None and self.ui_data['categories'][self.current_tab]['ui']['layout'] != "DETAIL":
            return ""
        return self.ui_data['categories'][self.current_tab]['goods'][self.current_detail_tab]['name']

    @ViewBinder.binding(ViewBinder.BF_BindString, "#pn_detail.intro")
    def on_refresh_detail_intro(self):
        if self.current_detail_tab is None and self.ui_data['categories'][self.current_tab]['ui']['layout'] != "DETAIL":
            return ""
        return self.ui_data['categories'][self.current_tab]['goods'][self.current_detail_tab]['detail_intros']

    @ViewBinder.binding(ViewBinder.BF_BindInt, "#pn_detail.item")
    def on_refresh_detail_item(self):
        if self.current_detail_tab is None and self.ui_data['categories'][self.current_tab]['ui']['layout'] != "DETAIL":
            return 0
        item_dict = self.ui_data['categories'][self.current_tab]['goods'][self.current_detail_tab]['show_item_dict']
        identifier = item_dict['newItemName'] if 'newItemName' in item_dict else item_dict['itemName']
        aux_value = item_dict['newAuxValue'] if 'newAuxValue' in item_dict else (
            item_dict['auxValue'] if 'auxValue' in item_dict else 0)
        enchantment = len(item_dict['enchantData']) > 0 if 'enchantData' in item_dict else False
        info = comp_item.GetItemBasicInfo(identifier, aux_value, enchantment)
        if info:
            return info['id_aux']
        else:
            print("[ERROR] [BedWarsShopScreenNode] on_refresh_detail_item: not found item info of {}:{}".format(identifier, aux_value))
            return 0

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#pn_detail.can_buy")
    def on_refresh_detail_can_buy(self):
        if self.current_detail_tab is None and self.ui_data['categories'][self.current_tab]['ui']['layout'] != "DETAIL":
            return False
        return self.ui_data['categories'][self.current_tab]['goods'][self.current_detail_tab]['cannot_buy_msg'] is None

    @ViewBinder.binding(ViewBinder.BF_BindBool, "#pn_detail.cannot_buy")
    def on_refresh_detail_cannot_buy(self):
        if self.current_detail_tab is None and self.ui_data['categories'][self.current_tab]['ui']['layout'] != "DETAIL":
            return False
        return self.ui_data['categories'][self.current_tab]['goods'][self.current_detail_tab][
            'cannot_buy_msg'] is not None

    # endregion

    def _notify_to_server(self, event_name, event_data):
        """
        发送事件到服务端

        使用ECPreset的客户端到服务端事件通知机制
        """
        try:
            from ECPresetClientScripts import get_client_mgr

            preset_mgr = get_client_mgr("bedwars_room")
            if preset_mgr and self.preset_client:
                # 通过预设实例发送事件到服务端
                instance_id = self.preset_client.get_instance_id()
                preset_instance = preset_mgr.get_preset(instance_id)
                if preset_instance:
                    preset_instance.publish_event(event_name, event_data)
                    print("[INFO] [BedWarsShopScreenNode] 发送事件到服务端: {} -> {}".format(event_name, event_data))
                else:
                    print("[ERROR] [BedWarsShopScreenNode] 未找到预设实例: {}".format(instance_id))
            else:
                print("[ERROR] [BedWarsShopScreenNode] ECPreset管理器或预设客户端对象未初始化")
        except Exception as e:
            print("[ERROR] [BedWarsShopScreenNode] 发送事件到服务端失败: {}".format(e))
            import traceback
            traceback.print_exc()
