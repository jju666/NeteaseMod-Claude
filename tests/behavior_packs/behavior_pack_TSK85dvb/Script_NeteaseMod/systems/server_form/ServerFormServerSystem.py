# -*- coding: utf-8 -*-
"""
ServerForm 服务端系统

功能:
- 提供友好的表单构建API（ServerForm类）
- 处理表单回调事件
- 管理表单回调缓存

迁移说明:
从老项目 ServerFormScript/ServerFormServerSystem.py 迁移
保持原有功能不变，调整为符合新项目规范
"""

from __future__ import print_function
import uuid
import mod.server.extraServerApi as serverApi

# 从modConfig导入MOD_NAME
from Script_NeteaseMod.modConfig import MOD_NAME

ServerSystem = serverApi.GetServerSystemCls()


class ServerForm(object):
    """
    表单构建器，封装表单List

    使用示例:
        form = ServerForm(title="测试表单")
        form.label("欢迎！")
        form.button("确定", tag="confirm")
        form.send(player_id, callback=on_button_click)
    """

    def __init__(self, title='未命名表单'):
        # type: (str) -> None
        self.data = []  # 表单元数据
        self.title = title  # 表单的标题
        self.boardId = str(uuid.uuid4())  # 表单的唯一标识

    def label(self, text=''):
        # type: (str) -> ServerForm
        """纯文本"""
        self.data.append({'type': 'label', 'text': text})
        return self

    def image(self, path='textures/ui/rating_screen', size=(260, 64)):
        # type: (str, tuple) -> ServerForm
        """图片"""
        self.data.append({'type': 'image', 'path': path, 'size': size})
        return self

    def button(self, text='未命名按钮', tag='undefined'):
        # type: (str, str) -> ServerForm
        """按钮"""
        self.data.append({'type': 'button', 'text': text, 'tag': tag})
        return self

    def imgButton(self, text='未命名按钮', path='textures/ui/redX1', tag='undefined'):
        # type: (str, str, str) -> ServerForm
        """左侧带图片的按钮"""
        self.data.append({'type': 'button_img', 'text': text, 'path': path, 'tag': tag})
        return self

    def itemButton(self, text='未命名按钮', item_name='minecraft:unknown', item_aux=0, item_ench=False,
                   tag='undefined'):
        # type: (str, str, int, bool, str) -> ServerForm
        """左侧带物品渲染器的按钮"""
        self.data.append(
            {'type': 'button_item', 'text': text, 'item_name': item_name, 'item_aux': item_aux, 'item_ench': item_ench,
             'tag': tag})
        return self

    def inputBox(self, text='请输入文字:', holder='请输入内容', default='', tag='undefined'):
        # type: (str, str, str, str) -> ServerForm
        """输入框"""
        self.data.append({'type': 'input', 'text': text, 'default': default, 'holder': holder, 'tag': tag})
        return self

    def toggle(self, text='开/关', default=False, tag='undefined'):
        # type: (str, bool, str) -> ServerForm
        """开关"""
        self.data.append({'type': 'toggle', 'text': text, 'default': default, 'tag': tag})
        return self

    def slider(self, text='当前值: {value}%%', start=0, end=100, step=1, default=0, tag='undefined'):
        # type: (str, int, int, int, int, str) -> ServerForm
        """滑动栏"""
        if '{value}' not in text:
            text += '{value}'
        self.data.append(
            {'type': 'slider', 'text': text, 'start': start, 'end': end, 'step': step, 'default': default, 'tag': tag})
        return self

    def paperDoll(self, entityId='', scale=1):
        # type: (str, int) -> ServerForm
        """网易纸娃娃"""
        self.data.append({'type': 'doll', 'entityId': entityId, 'scale': scale})
        return self

    def progressBar(self, value=0.8, color=(0, 0.6, 1)):
        # type: (float, tuple) -> ServerForm
        """进度条"""
        self.data.append({'type': 'progress', 'value': value, 'color': color})
        return self

    def send(self, playerId, callback=None):
        # type: (str, callable) -> ServerForm
        """将本表单发送给该playerId的玩家客户端"""
        sys = serverApi.GetSystem(MOD_NAME, 'ServerFormServerSystem')
        args = {
            'form': self.data,  # 表单元数据
            'title': self.title,  # 表单的标题
            'boardId': self.boardId  # 表单的唯一标识
        }
        sys.NotifyToClient(playerId, 'sendForm', args)  # 与客户端通讯，将表单数据发送给客户端
        if callback:  # 如果配置回调函数了
            sys.callbackCache[self.boardId] = callback  # 将boardId - callback 映射关系存入缓存
        return self


class ServerFormServerSystem(ServerSystem):
    """
    ServerForm 服务端系统

    功能:
    - 提供表单构建器（getFormBuilder）
    - 处理客户端按钮点击事件
    - 管理表单回调函数缓存
    """

    def __init__(self, namespace, systemName):
        super(ServerFormServerSystem, self).__init__(namespace, systemName)

        # 初始化成员变量
        self.mlevelId = serverApi.GetLevelId()
        self.callbackCache = {}  # 回调缓存: {boardId: function}

        # ⚠️ 重要: 手动调用Create()完成系统初始化
        print("[ServerFormServerSystem] 手动调用Create()完成系统初始化")
        self.Create()

    def Create(self):
        """系统创建时的初始化逻辑"""
        print("[ServerFormServerSystem] Create() 被调用")

        # 注册事件监听
        self.ListenForEvent(
            MOD_NAME,
            'ServerFormClientSystem',
            'buttonClickEvent',
            self,
            self.buttonClickEvent
        )
        print("[ServerFormServerSystem] 已注册 buttonClickEvent 事件监听")

    def getFormBuilder(self):
        # type: () -> type
        """
        获取表单构建器类

        Returns:
            ServerForm: 表单构建器类
        """
        return ServerForm

    def buttonClickEvent(self, args):
        # type: (dict) -> None
        """
        客户端点击按钮后触发该事件

        Args:
            args (dict): 事件参数，包含 boardId, click, data 等
        """
        args['playerId'] = args['__id__']  # 获取客户端玩家Id
        board_id = args.get('boardId')

        if board_id in self.callbackCache:  # 如果配置回调函数了
            callback = self.callbackCache[board_id]
            print("[ServerFormServerSystem] 触发表单回调: boardId={}".format(board_id))
            callback(args)  # 从缓存中找到该boardId对应的回调函数，调用并传参
        else:
            print("[ServerFormServerSystem] 未找到表单回调: boardId={}".format(board_id))

    def Destroy(self):
        """系统销毁时清理资源"""
        print("[ServerFormServerSystem] Destroy() 被调用")
        self.callbackCache.clear()
