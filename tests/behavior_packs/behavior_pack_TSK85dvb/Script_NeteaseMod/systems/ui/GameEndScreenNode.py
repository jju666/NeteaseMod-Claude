# -*- coding: utf-8 -*-
"""
GameEndScreenNode - 游戏结算UI屏幕节点

功能:
- 显示玩家排名
- 显示游戏统计数据(击杀/终结/破坏水晶)
- 显示获得的奖励列表
- 显示任务进度
- 提供"继续"按钮返回大厅

UI定义文件: resource_packs/resource_pack_l2YkhWt2/ui/game_end.json
"""

from __future__ import print_function
import mod.client.extraClientApi as clientApi

# 获取基础类
ViewBinder = clientApi.GetViewBinderCls()
ScreenNode = clientApi.GetScreenNodeCls()


class GameEndScreenNode(ScreenNode):
    """游戏结算UI节点"""

    def __init__(self, namespace, name, param):
        """
        初始化ScreenNode

        Args:
            namespace (str): 命名空间
            name (str): 节点名称
            param (dict): 初始化参数
                - rank (int): 玩家排名
                - score (str): 统计文本
                - stack_left_text (str): 左侧文本(奖励名称)
                - stack_left_delta (str): 左侧变化值(奖励数量)
                - stack_right_text (str): 右侧文本(任务名称)
                - stack_right_delta (str): 右侧变化值(任务进度)
        """
        super(GameEndScreenNode, self).__init__(namespace, name, param)

        # 保存初始数据
        self.ui_data = param

        print("[INFO] [GameEndScreenNode] 初始化完成 data={}".format(param))

    def Create(self):
        """UI创建成功时调用"""
        print("[INFO] [GameEndScreenNode] Create 开始设置UI数据")

        # 使用ViewBinder装饰器模式，数据会自动绑定到JsonUI
        # 不需要手动调用SetRepeatedData等API

        print("[INFO] [GameEndScreenNode] UI数据已设置完成")

    def OnDestroy(self):
        """UI销毁时调用"""
        print("[INFO] [GameEndScreenNode] OnDestroy")

    @ViewBinder.binding(ViewBinder.BF_ButtonClickUp)
    def on_click_button(self, args):
        """
        点击"继续"按钮回调

        [修复 2025-11-12] 添加@ViewBinder.binding装饰器
        问题: 缺少装饰器导致按钮点击无法触发回调
        参考: 老项目GameEndScreenNode.py:66使用ViewBinder.BF_ButtonClickUp

        Args:
            args: 按钮事件参数
        """
        print("[INFO] [GameEndScreenNode] 点击继续按钮")

        # 关闭UI (使用clientApi.PopScreen而不是DestroyUI)
        # 原因: 老项目使用PopScreen，这是标准的UI关闭方式
        try:
            import mod.client.extraClientApi as clientApi
            clientApi.PopScreen()
            print("[INFO] [GameEndScreenNode] UI已关闭(PopScreen)")
        except Exception as e:
            print("[ERROR] [GameEndScreenNode] 关闭UI失败: {}".format(str(e)))

    # ==================== ViewBinder数据绑定 ====================
    # 使用装饰器模式提供数据，对应game_end.json中的binding_name

    @ViewBinder.binding(ViewBinder.BF_BindString, "#game_end.rank")
    def get_rank_text(self):
        """绑定排名文本"""
        rank = self.ui_data.get('rank', 0)
        return self._format_rank_text(rank)

    @ViewBinder.binding(ViewBinder.BF_BindString, "#game_end.score")
    def get_score_text(self):
        """绑定统计文本"""
        return self.ui_data.get('score', '')

    @ViewBinder.binding(ViewBinder.BF_BindString, "#game_end.stack_left_text")
    def get_left_text(self):
        """绑定左侧文本(奖励名称)"""
        return self.ui_data.get('stack_left_text', '')

    @ViewBinder.binding(ViewBinder.BF_BindString, "#game_end.stack_left_delta")
    def get_left_delta(self):
        """绑定左侧变化值(奖励数量)"""
        return self.ui_data.get('stack_left_delta', '')

    @ViewBinder.binding(ViewBinder.BF_BindString, "#game_end.stack_right_text")
    def get_right_text(self):
        """绑定右侧文本(任务名称)"""
        return self.ui_data.get('stack_right_text', '')

    @ViewBinder.binding(ViewBinder.BF_BindString, "#game_end.stack_right_delta")
    def get_right_delta(self):
        """绑定右侧变化值(任务进度)"""
        return self.ui_data.get('stack_right_delta', '')

    def _format_rank_text(self, rank):
        """
        格式化排名文本

        Args:
            rank (int): 排名（1=第1名）

        Returns:
            str: 格式化的排名文本
        """
        if rank == 1:
            return u"\xa76\xa7lNo.\xa7f\xa7l1"  # 金色加粗
        elif rank == 2:
            return u"\xa77\xa7lNo.\xa7f\xa7l2"  # 灰色加粗
        elif rank == 3:
            return u"\xa7e\xa7lNo.\xa7f\xa7l3"  # 黄色加粗
        else:
            return u"\xa77No.\xa7f{}".format(rank)  # 灰色
