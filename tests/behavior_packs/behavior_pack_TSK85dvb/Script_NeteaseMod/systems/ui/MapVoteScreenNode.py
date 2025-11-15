# -*- coding: utf-8 -*-
"""
MapVoteScreenNode - 地图投票UI屏幕节点

功能:
- 显示地图投票界面
- 处理玩家投票操作
- 实时显示投票统计

原文件: Parts/ECStage/MapVoteScreenNode.py
重构为: systems/ui/MapVoteScreenNode.py
"""

import mod.client.extraClientApi as clientApi

ViewBinder = clientApi.GetViewBinderCls()
ScreenNode = clientApi.GetScreenNodeCls()

PATH_MAIN = "variables_button_mappings_and_controls/safezone_screen_matrix/inner_matrix/safezone_screen_panel/root_screen_panel"
PATH_SCROLL_MAIN = PATH_MAIN + "/content/scroll_main"
NAME_LAYOUT_GRID = "map_grid"


class MapVoteScreenNode(ScreenNode):
    """地图投票屏幕节点类"""

    def __init__(self, namespace, name, param):
        """
        初始化屏幕节点

        Args:
            namespace: UI命名空间
            name: UI名称
            param: UI数据参数
        """
        ScreenNode.__init__(self, namespace, name, param)
        self.system = None  # type: RoomManagementClientSystem | None
        self.ui_data = param
        self.current_tab = 0
        self.scheduled_width_refresh = False

    def Create(self):
        """UI创建成功时调用"""
        # 创建背景到最外层，并会自动播放渐变动画
        control = self.GetBaseUIControl("variables_button_mappings_and_controls")
        self.CreateChildControl("map_vote.bg", "bg", control)

        # 启用高斯模糊背景效果
        comp = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
        comp.SetEnableGaussianBlur(True)
        comp.SetGaussianBlurRadius(1)

    def Destroy(self):
        """UI销毁时调用"""
        # 禁用高斯模糊
        comp = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
        comp.SetEnableGaussianBlur(False)

        # 通过代码让背景渐变消失
        bg = self.GetBaseUIControl("variables_button_mappings_and_controls/bg")
        if bg is not None:
            bg.RemoveAnimation("alpha")
            bg.SetAnimation("alpha", "map_vote", "anim_bg_alpha_out", True)

    def OnActive(self):
        """UI重新回到栈顶时调用"""
        pass

    def OnDeactive(self):
        """栈顶UI有其他UI入栈时调用"""
        pass

    def on_tick(self):
        """每Tick调用"""
        if self.scheduled_width_refresh:
            self.refresh_item_width()
            self.scheduled_width_refresh = False

    def get_autolayout_count_block_main(self):
        """计算每行显示的地图数量"""
        width = self.GetBaseUIControl(PATH_SCROLL_MAIN).GetSize()[0]
        return max(1, int(float(width) / 168))

    def refresh_item_width(self):
        """刷新地图项的宽度"""
        scroll = self.GetBaseUIControl(PATH_SCROLL_MAIN)
        if scroll is None:
            print("scroll is None")
            return
        if scroll.GetVisible() is False:
            return
        scroll_content = scroll.asScrollView().GetScrollViewContentControl()
        layout_grid = scroll_content.GetChildByName(NAME_LAYOUT_GRID)
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
        self.UpdateScreen()

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_click_close(self, args):
        """玩家点击关闭按钮"""
        clientApi.PopScreen()

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_exit(self, args):
        """玩家点击返回（esc/e）"""
        clientApi.PopScreen()

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_click_button(self, args):
        """
        玩家点击地图按钮进行投票

        Args:
            args: 包含'#collection_index'的参数
        """
        if '#collection_index' not in args:
            print("[ERROR] [MapVoteScreenNode] on_click_button: '#collection_index' not in args")
            return

        # 安全检查：确保地图列表存在且不为空
        try:
            if ('categories' not in self.ui_data or
                not isinstance(self.ui_data['categories'], list) or
                self.current_tab >= len(self.ui_data['categories']) or
                'maps' not in self.ui_data['categories'][self.current_tab] or
                len(self.ui_data['categories'][self.current_tab]['maps']) == 0):
                print("[ERROR] [MapVoteScreenNode] on_click_button: 没有可用的地图或地图数据无效")
                return

            index = args['#collection_index']
            if index >= len(self.ui_data['categories'][self.current_tab]['maps']):
                index = 0

            # 发送投票请求到服务端
            if self.system:
                self.system.NotifyToServer("C2STryVoteMap", {
                    "player_id": clientApi.GetLocalPlayerId(),
                    "map_id": self.ui_data['categories'][self.current_tab]['maps'][index]['id']
                })
            else:
                print("[ERROR] [MapVoteScreenNode] system is None")
        except (IndexError, KeyError, TypeError) as e:
            print("[ERROR] [MapVoteScreenNode] on_click_button: 地图数据访问错误: {}".format(str(e)))

    # region TAB

    @ViewBinder.binding(ViewBinder.BF_BindInt, "#pn_tabs.item_count")
    def on_tab_grid_resize(self):
        """返回TAB数量"""
        try:
            if 'categories' in self.ui_data and isinstance(self.ui_data['categories'], list):
                return len(self.ui_data['categories'])
            return 0
        except (KeyError, TypeError):
            return 0

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "shop_tabs", "#label_name.text")
    def on_refresh_item_label(self, index):
        """刷新TAB标签文本"""
        try:
            if ('categories' in self.ui_data and isinstance(self.ui_data['categories'], list) and
                index < len(self.ui_data['categories']) and 'name' in self.ui_data['categories'][index]):
                return self.ui_data['categories'][index]['name']
            return u"未知分类"
        except (KeyError, IndexError, TypeError):
            return u"未知分类"

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "shop_tabs", "#texture")
    def on_refresh_item_icon(self, index):
        """刷新TAB图标"""
        try:
            if ('categories' in self.ui_data and isinstance(self.ui_data['categories'], list) and
                index < len(self.ui_data['categories']) and 'icon' in self.ui_data['categories'][index]):
                return self.ui_data['categories'][index]['icon']
            return "textures/ui/bw/bw_category_fast"  # 默认图标
        except (KeyError, IndexError, TypeError):
            return "textures/ui/bw/bw_category_fast"

    @ViewBinder.binding(ViewBinder.BF_ToggleChanged, "#tab_toggle")
    def on_toggle_changed(self, args):
        """TAB切换时调用"""
        try:
            index = args['index']
            if ('categories' in self.ui_data and isinstance(self.ui_data['categories'], list) and
                index >= len(self.ui_data['categories'])):
                index = 0
            self.current_tab = index
            # 滚动区回到顶部
            scroll = self.GetBaseUIControl(PATH_SCROLL_MAIN)
            if scroll is not None:
                scroll.asScrollView().SetScrollViewPos(0)
        except (KeyError, IndexError, TypeError):
            self.current_tab = 0

    # endregion

    # region 地图项绑定

    @ViewBinder.binding(ViewBinder.BF_BindString, "#map_vote.update")
    def on_refresh_update(self):
        """触发宽度刷新"""
        self.scheduled_width_refresh = True

    @ViewBinder.binding(ViewBinder.BF_BindInt, "#map_vote.grid_item_count")
    def on_refresh_item_count(self):
        """返回当前TAB的地图数量"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab]):
                return len(self.ui_data['categories'][self.current_tab]['maps'])
            return 0
        except (IndexError, KeyError):
            return 0

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "map_vote", "#map_vote.title")
    def on_refresh_item_title(self, index):
        """刷新地图标题"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab] and
                index < len(self.ui_data['categories'][self.current_tab]['maps'])):
                return self.ui_data['categories'][self.current_tab]['maps'][index]['name']
            return u"未知地图"
        except (IndexError, KeyError):
            return u"未知地图"

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "map_vote", "#map_vote.intro")
    def on_refresh_item_intro(self, index):
        """刷新地图介绍（模式名称）"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab] and
                index < len(self.ui_data['categories'][self.current_tab]['maps'])):
                return self.ui_data['categories'][self.current_tab]['maps'][index]['mode_name']
            return u"未知模式"
        except (IndexError, KeyError):
            return u"未知模式"

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "map_vote", "#map_vote.image")
    def on_refresh_item_image(self, index):
        """刷新地图图片"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab] and
                index < len(self.ui_data['categories'][self.current_tab]['maps'])):
                return self.ui_data['categories'][self.current_tab]['maps'][index]['image']
            return ""
        except (IndexError, KeyError):
            return ""

    @ViewBinder.binding_collection(ViewBinder.BF_BindString, "map_vote", "#map_vote.state")
    def on_refresh_item_state(self, index):
        """刷新地图投票状态文本"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab] and
                index < len(self.ui_data['categories'][self.current_tab]['maps'])):
                voters_count = len(self.ui_data['categories'][self.current_tab]['maps'][index]['voters'])
                if voters_count > 0:
                    return u"{} {}票".format(u"\uE180", voters_count)
                else:
                    return u"无人投票"
            return u"无人投票"
        except (IndexError, KeyError):
            return u"无人投票"

    @ViewBinder.binding_collection(ViewBinder.BF_BindFloat, "map_vote", "#map_vote.state_alpha")
    def on_refresh_item_state_alpha(self, index):
        """刷新地图投票状态透明度"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab] and
                index < len(self.ui_data['categories'][self.current_tab]['maps'])):
                voters_count = len(self.ui_data['categories'][self.current_tab]['maps'][index]['voters'])
                if voters_count > 0:
                    return 1.0
                else:
                    return 0.3
            return 0.3
        except (IndexError, KeyError):
            return 0.3

    @ViewBinder.binding_collection(ViewBinder.BF_BindFloat, "map_vote", "#map_vote.frame_alpha")
    def on_refresh_item_frame_alpha(self, index):
        """刷新地图边框透明度（表示是否已投票）"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab] and
                index < len(self.ui_data['categories'][self.current_tab]['maps'])):
                if clientApi.GetLocalPlayerId() in self.ui_data['categories'][self.current_tab]['maps'][index]['voters']:
                    return 1.0
                return 0.1
            return 0.1
        except (IndexError, KeyError):
            return 0.1

    @ViewBinder.binding_collection(ViewBinder.BF_BindBool, "map_vote", "#map_vote.tag_visible")
    def on_refresh_item_tag_visible(self, index):
        """刷新已投票标签可见性"""
        try:
            if (self.current_tab < len(self.ui_data['categories']) and
                'maps' in self.ui_data['categories'][self.current_tab] and
                index < len(self.ui_data['categories'][self.current_tab]['maps'])):
                return clientApi.GetLocalPlayerId() in self.ui_data['categories'][self.current_tab]['maps'][index]['voters']
            return False
        except (IndexError, KeyError):
            return False

    # endregion
