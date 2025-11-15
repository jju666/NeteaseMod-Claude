# -*- coding: utf-8 -*-
"""
ServerForm 客户端系统

功能:
- 监听UI初始化完成事件并注册UI
- 接收服务端发送的表单数据并显示UI

迁移说明:
从老项目 ServerFormScript/ServerFormClientSystem.py 迁移
保持原有功能不变，调整为符合新项目规范
"""

from __future__ import print_function
import mod.client.extraClientApi as clientApi

# 从modConfig导入MOD_NAME
from Script_NeteaseMod.modConfig import MOD_NAME

ClientSystem = clientApi.GetClientSystemCls()


class ServerFormClientSystem(ClientSystem):
    """
    ServerForm 客户端系统

    功能:
    - 注册ServerForm UI
    - 接收服务端表单数据并显示
    """

    def __init__(self, namespace, systemName):
        super(ServerFormClientSystem, self).__init__(namespace, systemName)

        # 初始化成员变量
        self.mPlayerId = clientApi.GetLocalPlayerId()
        self.mLevelId = clientApi.GetLevelId()

        # ⚠️ 重要: 手动调用Create()完成系统初始化
        print("[ServerFormClientSystem] 手动调用Create()完成系统初始化")
        self.Create()

    def Create(self):
        """系统创建时的初始化逻辑"""
        print("[ServerFormClientSystem] Create() 被调用")

        # 监听UI初始化完成事件
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            'UiInitFinished',
            self,
            self.UiInitFinished
        )
        print("[ServerFormClientSystem] 已注册 UiInitFinished 事件监听")

        # 监听服务端发送表单事件
        self.ListenForEvent(
            MOD_NAME,
            'ServerFormServerSystem',
            'sendForm',
            self,
            self.getFormFromServer
        )
        print("[ServerFormClientSystem] 已注册 sendForm 事件监听")

    def UiInitFinished(self, args):
        # type: (dict) -> None
        """
        界面加载完成后注册ui

        Args:
            args (dict): 事件参数
        """
        print("[ServerFormClientSystem] UI初始化完成，注册ServerForm UI")
        clientApi.RegisterUI(
            MOD_NAME,
            'zmqy_server_form',
            "Script_NeteaseMod.systems.ui.ServerFormUi.ServerFormScreen",
            "zmqy_server_form.main"
        )
        print("[ServerFormClientSystem] ServerForm UI已注册")

    def getFormFromServer(self, args):
        # type: (dict) -> None
        """
        从服务端获取表单信息，将界面入栈弹出，并将信息传递给screen类

        Args:
            args (dict): 服务端发送的表单数据
        """
        print("[ServerFormClientSystem] 收到服务端表单数据，显示表单UI")

        topScreen = clientApi.GetTopScreen()
        if topScreen:
            if topScreen.GetScreenName() == 'zmqy_server_form.main':
                print("[ServerFormClientSystem] 关闭已存在的表单UI")
                topScreen.CloseButtonClick({})  # 模拟关闭按钮按下
            clientApi.PushScreen(MOD_NAME, 'zmqy_server_form', {'data': args, 'client': self})
        else:
            clientApi.PushScreen(MOD_NAME, 'zmqy_server_form', {'data': args, 'client': self})

        print("[ServerFormClientSystem] 表单UI已显示")

    def Destroy(self):
        """系统销毁时清理资源"""
        print("[ServerFormClientSystem] Destroy() 被调用")
