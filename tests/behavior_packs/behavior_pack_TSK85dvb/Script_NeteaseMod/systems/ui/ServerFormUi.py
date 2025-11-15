# -*- coding: utf-8 -*-
import mod.client.extraClientApi as clientApi

ScreenNode = clientApi.GetScreenNodeCls()
ViewBinder = clientApi.GetViewBinderCls()
ViewRequest = clientApi.GetViewViewRequestCls()


class ServerFormScreen(ScreenNode):
    def __init__(self, namespace, name, param):
        ScreenNode.__init__(self, namespace, name, param)
        self.mPlayerId = clientApi.GetLocalPlayerId()
        self.mLevelId = clientApi.GetLevelId()
        self.data = param.get('data', {})
        self.client = param.get('client', None)  # 客户端System实例
        self.form = self.data['form']  # 表单List
        self.title = self.data['title']  # 表单标题
        self.boardId = self.data['boardId']  # 表单唯一Id
        self.titlePath = '/panel/bg/label'  # 标题路径
        self.scrollViewPath = 'panel/bg/scroll_view/'  # 滚动列表原路径
        self.stackPanelPath = '{}/stack_panel'  # 布局面板路径，因涉及滚动列表，需动态获取

    def Create(self):  # 当界面加载完成后
        self.stackPanelPath = self.stackPanelPath.format(
            self.GetBaseUIControl(
                self.scrollViewPath).asScrollView().GetScrollViewContentPath())  # 获取当前操作方式滚动列表下的路径, 并格式化给布局面板
        self.GetBaseUIControl(self.titlePath).asLabel().SetText(self.title)  # 设置表单标题
        for i, element in enumerate(self.form):  # 遍历表单中的每个组件元素
            self.addElement(element, i)  # 添加组件
        self.UpdateScreen()
        print('=====> ServerFormUI Created <=====')

    def addElement(self, element, index):  # 添加组件
        typ = element['type']  # 组件类型
        basePath = self.stackPanelPath + '/z_' + typ  # 组件路径
        newName = '__INDEX__' + str(index)  # Clone后的新名称
        path = self.stackPanelPath + '/' + newName + '/'  # Clone后的新组件路径
        self.Clone(basePath, self.stackPanelPath, newName, False)  # Clone操作
        self.GetBaseUIControl(path).SetVisible(True)  # 将新组件置为可见
        if typ == 'label':  # 纯文本
            self.GetBaseUIControl(path + 'label').asLabel().SetText(element['text'])
        elif typ == 'image':  # 图片
            self.GetBaseUIControl(path + 'image').asImage().SetSprite(element['path'])
            self.GetBaseUIControl(path + 'image').SetFullSize('x', {"absoluteValue": element['size'][0],
                                                                    "followType": "none", "relativeValue": 1})
            self.GetBaseUIControl(path + 'image').SetFullSize('y', {"absoluteValue": element['size'][1],
                                                                    "followType": "none", "relativeValue": 1})
        elif typ == 'button':  # 按钮
            self.GetBaseUIControl(path + 'button/button_label').asLabel().SetText(element['text'])
        elif typ == 'button_img':  # 左侧带图片的按钮
            self.GetBaseUIControl(path + 'button/button_label').asLabel().SetText(element['text'])
            self.GetBaseUIControl(path + 'image').asImage().SetSprite(element['path'])
        elif typ == 'button_item':  # 左侧带物品渲染器的按钮
            self.GetBaseUIControl(path + 'button/button_label').asLabel().SetText(element['text'])
            self.GetBaseUIControl(path + 'item_renderer').asItemRenderer().SetUiItem(element['item_name'],
                                                                                     element['item_aux'],
                                                                                     element['item_ench'])
        elif typ == 'input':  # 输入框
            self.GetBaseUIControl(path + 'label').asLabel().SetText(element['text'])
            self.GetBaseUIControl(
                path + 'edit_box/centering_panel/clipper_panel/visibility_panel/place_holder_control').asLabel().SetText(
                element['holder'])
            self.GetBaseUIControl(path + 'edit_box').asTextEditBox().SetEditText(element['default'])
        elif typ == 'toggle':  # 开关
            self.GetBaseUIControl(path + 'label').asLabel().SetText(element['text'])
            self.GetBaseUIControl(path + 'switch_toggle').asSwitchToggle().SetToggleState(element['default'])
        elif typ == 'slider':  # 滑动栏
            self.GetBaseUIControl(path + 'label').asLabel().SetText(element['text'])
            self.GetBaseUIControl(path + 'slider').asSlider().SetSliderValue(
                float(element['default'] - element['start']) / float(element['end'] - element['start']))
        elif typ == 'doll':  # 网易纸娃娃
            self.GetBaseUIControl(path + 'netease_paper_doll').asNeteasePaperDoll().RenderEntity(
                {'entity_id': element['entityId'], 'scale': element['scale']})
        elif typ == 'progress':  # 进度条
            self.GetBaseUIControl(path + 'progress_bar').asProgressBar().SetValue(element['value'])
            self.GetBaseUIControl(path + 'progress_bar/filled_progress_bar').asImage().SetSpriteColor(element['color'])
            self.GetBaseUIControl(path + 'progress_bar/label').asLabel().SetText(
                '{}%%'.format(str(int(round(element['value'] * 100))).zfill(2)))

    def getFormData(self):  # 从表单中读取数据
        data = {}
        for i, element in enumerate(self.form):  # 遍历表单中的每个组件元素
            typ = element['type']
            path = self.stackPanelPath + '/__INDEX__' + str(i) + '/'  # 拿到该组件的ui路径
            if typ == 'input':  # 找到需要读取元素：输入框
                value = self.GetBaseUIControl(path + 'edit_box').asTextEditBox().GetEditText()  # 读取数据
                data[i if element['tag'] == 'undefined' else element['tag']] = value  # 存入字典, 有tag则返回tag, 没有则返回index
            elif typ == 'toggle':  # 开关
                value = self.GetBaseUIControl(path + 'switch_toggle').asSwitchToggle().GetToggleState()
                data[i if element['tag'] == 'undefined' else element['tag']] = value
            elif typ == 'slider':  # 滑动条
                _value = self.GetBaseUIControl(path + 'slider').asSlider().GetSliderValue()
                value = element['start'] + int(round((element['end'] - element['start']) * _value))
                data[i if element['tag'] == 'undefined' else element['tag']] = value
        return data  # 返回表单中的数据字典: {tag/index : value}

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp, '#CloseButtonClick')  # 使用数据绑定，将关闭按钮弹起回调绑至本函数
    def CloseButtonClick(self, args):
        data = self.getFormData()  # 获取此时表单上的数据值
        self.client.NotifyToServer('buttonClickEvent', {  # 使用客户端System与服务端通讯，将数据传递给服务端
            'boardId': self.boardId,
            'click': -1,
            'data': data
        })
        clientApi.PopScreen()  # 界面出栈，关闭窗口

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp, '#ButtonClick')  # 使用数据绑定，将按钮弹起回调绑至本函数
    def ButtonClick(self, args):
        path = args['ButtonPath']  # 点击按钮的路径
        index = int(path.split('__INDEX__')[1].split('/')[0])  # 从路径字符串中提取该按钮的index
        data = self.getFormData()  # 获取此时表单上的数据值
        self.client.NotifyToServer('buttonClickEvent', {  # 使用客户端System与服务端通讯，将数据传递给服务端
            'boardId': self.boardId,
            'click': index if self.form[index]['tag'] == 'undefined' else self.form[index]['tag'],
            'data': data
        })
        clientApi.PopScreen()  # 界面出栈，关闭窗口

    def Update(self):  # 每秒被引擎调用30次，更新滑动条数值
        try:  # UI未加载完成可能会报错，这里直接忽略
            for i, element in enumerate(self.form):  # 遍历表单中的每个组件元素
                typ = element['type']
                if typ == 'slider':  # 找到slider
                    path = self.stackPanelPath + '/__INDEX__' + str(i) + '/'  # 拿到该组件的ui路径
                    _value = self.GetBaseUIControl(path + 'slider').asSlider().GetSliderValue()  # 原始slider的value [0, 1]
                    value = element['start'] + int(
                        round((element['end'] - element['start']) * _value))  # 计算真实数值 [start, end] ∈ Z
                    self.GetBaseUIControl(path + 'label').asLabel().SetText(
                        element['text'].format(value=value))  # 格式化并更新
        except:
            pass

    def Destroy(self):
        print('=====> ServerFormUI Destroyed <=====')
