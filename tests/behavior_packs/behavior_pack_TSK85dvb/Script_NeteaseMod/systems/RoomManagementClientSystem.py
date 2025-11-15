# -*- coding: utf-8 -*-
"""
RoomManagementClientSystem - 房间管理客户端系统

功能:
- 监听客户端玩家加载完成事件
- 通知服务端进行玩家初始化
- 管理地图投票UI
"""

import mod.client.extraClientApi as clientApi
from Script_NeteaseMod.modConfig import MOD_NAME


class RoomManagementClientSystem(clientApi.GetClientSystemCls()):
    """
    房间管理客户端系统

    职责:
    - 监听OnLocalPlayerStopLoading事件
    - 向服务端发送玩家就绪通知
    - 注册和管理地图投票UI
    """

    def __init__(self, namespace, systemName):
        """
        初始化客户端系统

        Args:
            namespace: 命名空间
            systemName: 系统名称
        """
        super(RoomManagementClientSystem, self).__init__(namespace, systemName)
        print("[INFO] [RoomManagementClientSystem] __init__ 开始")

        # UI注册标志
        self.ui_registered = False

        # 手动调用Create()进行初始化（引擎不会主动调用）
        self.Create()

        print("[INFO] [RoomManagementClientSystem] 初始化完成")

    def Create(self):
        """客户端系统创建 - 注册所有事件监听"""
        print("[INFO] [RoomManagementClientSystem] Create 开始")

        # 监听引擎事件
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            'OnLocalPlayerStopLoading',
            self,
            self._on_local_player_stop_loading
        )
        print("[INFO] [RoomManagementClientSystem] OnLocalPlayerStopLoading 事件监听已注册")

        # 监听UI初始化完成事件（UI注册必须在此事件后）
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            'UiInitFinished',
            self,
            self._on_ui_init_finished
        )
        print("[INFO] [RoomManagementClientSystem] UiInitFinished 事件监听已注册")

        # 监听服务端RoomManagementSystem发送的事件
        # 服务端使用NotifyToClient发送，客户端需要监听服务端System
        self.ListenForEvent(
            MOD_NAME,
            'RoomManagementSystem',  # 监听服务端RoomManagementSystem
            'OpenMapVote',
            self,
            self._on_open_map_vote
        )
        print("[INFO] [RoomManagementClientSystem] OpenMapVote 事件监听已注册")

        self.ListenForEvent(
            MOD_NAME,
            'RoomManagementSystem',  # 监听服务端RoomManagementSystem
            'RefreshMapVote',
            self,
            self._on_refresh_map_vote
        )
        print("[INFO] [RoomManagementClientSystem] RefreshMapVote 事件监听已注册")

        # [新增 2025-11-08] 监听ScoreBoardNPCSkin事件
        # 参考: 老项目ECStagePart.py:91
        # 原因: 胜利结算阶段需要将NPC皮肤设置为对应玩家的皮肤
        # 服务端在StageBroadcastScoreState._spawn_score_npcs中发送此事件
        self.ListenForEvent(
            MOD_NAME,
            'RoomManagementSystem',  # 监听服务端RoomManagementSystem
            'ScoreBoardNPCSkin',
            self,
            self._on_score_board_npc_skin
        )
        print("[INFO] [RoomManagementClientSystem] ScoreBoardNPCSkin 事件监听已注册")

        # [新增 2025-11-12] 监听OpenGameEnd事件
        # 服务端在StageBroadcastScoreState._open_game_end_ui中发送此事件
        # 用于显示游戏结算UI
        self.ListenForEvent(
            MOD_NAME,
            'RoomManagementSystem',  # 监听服务端RoomManagementSystem
            'OpenGameEnd',
            self,
            self._on_open_game_end
        )
        print("[INFO] [RoomManagementClientSystem] OpenGameEnd 事件监听已注册")

        print("[INFO] [RoomManagementClientSystem] Create 完成")

    def Destroy(self):
        """客户端系统销毁"""
        print("[INFO] [RoomManagementClientSystem] Destroy")

    def _on_ui_init_finished(self, args):
        """
        UI初始化完成时重置注册标志

        Args:
            args: 事件参数

        说明：
        - [FIX 2025-11-07 #4] 参考老项目延迟注册模式
        - UI不在此时注册,而是在首次打开前延迟注册
        - 此事件仅用于重置注册标志,支持重新注册
        - 这样可以解决维度传送/状态重置后UI丢失的问题
        """
        print("[INFO] [RoomManagementClientSystem] UI初始化完成，重置注册标志")
        self.ui_registered = False

    def _register_ui(self):
        """注册地图投票UI"""
        try:
            print("[INFO] [RoomManagementClientSystem] 开始注册地图投票UI")
            clientApi.RegisterUI(
                'map_vote',  # UI命名空间（必须与JSON文件的namespace和PushScreen保持一致）
                'map_vote',  # UI资源名称
                "Script_NeteaseMod.systems.ui.MapVoteScreenNode.MapVoteScreenNode",  # ScreenNode类的完整路径
                "map_vote.main"  # UI JSON文件路径
            )
            self.ui_registered = True
            print("[INFO] [RoomManagementClientSystem] 地图投票UI注册成功")
        except Exception as e:
            print("[ERROR] [RoomManagementClientSystem] 注册UI失败: {}".format(e))
            import traceback
            traceback.print_exc()

    def _on_local_player_stop_loading(self, args):
        """
        本地玩家加载完成事件处理

        Args:
            args: 事件参数 {'playerId': player_id}
        """
        player_id = args.get('playerId')
        print("[INFO] [RoomManagementClientSystem] 玩家加载完成: {}".format(player_id))

        # 参考ServerFormUi.py的实现方式发送事件
        self.NotifyToServer('C2SOnLocalPlayerStopLoading', {'playerId': player_id})

    def _on_open_map_vote(self, args):
        """
        打开地图投票UI

        Args:
            args: UI数据参数

        说明:
        - [FIX 2025-11-07 #4] 参考老项目延迟注册模式
        - 打开UI前检查是否已注册,如果未注册则先注册
        - 这样可以解决维度传送/状态重置后UI丢失的问题
        """
        try:
            print("[INFO] [RoomManagementClientSystem] 收到OpenMapVote事件，UI数据: {}".format(
                "包含 {} 个分类".format(len(args.get('categories', []))) if 'categories' in args else "无数据"
            ))

            # [FIX 2025-11-07 #4] 延迟注册: 打开前检查并注册
            if not self.ui_registered:
                print("[INFO] [RoomManagementClientSystem] UI未注册，现在进行延迟注册")
                self._register_ui()

            # 导入MapVoteScreenNode（使用绝对导入路径）
            from Script_NeteaseMod.systems.ui.MapVoteScreenNode import MapVoteScreenNode

            # 打开UI（namespace必须与RegisterUI保持一致）
            node = clientApi.PushScreen('map_vote', 'map_vote', args)

            # 使用isinstance检查确保类型正确
            if isinstance(node, MapVoteScreenNode):
                node.system = self
                print("[INFO] [RoomManagementClientSystem] 地图投票UI已打开，ScreenNode已绑定system")
            else:
                print("[ERROR] [RoomManagementClientSystem] PushScreen返回的不是MapVoteScreenNode实例: {}".format(type(node)))

        except Exception as e:
            print("[ERROR] [RoomManagementClientSystem] 打开地图投票UI失败: {}".format(e))
            import traceback
            traceback.print_exc()

    def _on_refresh_map_vote(self, args):
        """
        刷新地图投票UI

        Args:
            args: 新的UI数据参数
        """
        try:
            from ui.MapVoteScreenNode import MapVoteScreenNode
            node = clientApi.GetTopUINode()
            if isinstance(node, MapVoteScreenNode):
                node.ui_data = args
                node.UpdateScreen()
                print("[INFO] [RoomManagementClientSystem] 地图投票UI已刷新")
        except Exception as e:
            print("[ERROR] [RoomManagementClientSystem] 刷新地图投票UI失败: {}".format(e))
            import traceback
            traceback.print_exc()

    def _on_vote_response(self, args):
        """
        处理投票响应（占位，实际投票由服务端处理）

        Args:
            args: 投票参数
        """
        pass

    def _on_score_board_npc_skin(self, args):
        """
        处理结算NPC皮肤渲染

        [新增 2025-11-08] 100%还原老项目NPC皮肤渲染实现
        参考: 老项目ECStagePart.py:152-163

        流程:
        1. 从事件参数获取entity_id, skin_player, texture_key
        2. 使用ActorRender组件复制玩家的几何体(Geometry)到NPC
        3. 复制玩家的材质(Material)到NPC
        4. 复制玩家的纹理(Texture)到NPC
        5. 重建NPC渲染以应用更改

        Args:
            args (dict): 事件参数
                - entity_id (str): NPC实体ID
                - skin_player (str): 要复制皮肤的玩家ID
                - texture_key (str): 纹理键名 (如: "rank1", "rank2", "rank3")
        """
        try:
            entity_id = args.get('entity_id')
            skin_player = args.get('skin_player')
            texture_key = args.get('texture_key')

            print("[INFO] [RoomManagementClientSystem] 收到ScoreBoardNPCSkin事件: entity_id={}, skin_player={}, texture_key={}".format(
                entity_id, skin_player, texture_key
            ))

            if not entity_id or not skin_player or not texture_key:
                print("[ERROR] [RoomManagementClientSystem] ScoreBoardNPCSkin参数不完整")
                return

            # 获取客户端引擎组件工厂
            comp_factory = clientApi.GetEngineCompFactory()

            # 获取ActorRender组件 (用于设置实体渲染)
            # 参考: 老项目ECStagePart.py:159
            level_id = clientApi.GetLevelId()
            comp_render = comp_factory.CreateActorRender(level_id)

            if not comp_render:
                print("[ERROR] [RoomManagementClientSystem] 创建ActorRender组件失败")
                return

            # [核心] 100%还原老项目的皮肤复制流程
            # 参考: 老项目ECStagePart.py:160-163

            # 1. 复制玩家的几何体(模型)到NPC
            # CopyActorGeometryFromPlayer(玩家ID, 实体类型, 源几何体名, 目标几何体名)
            comp_render.CopyActorGeometryFromPlayer(
                skin_player,  # 从哪个玩家复制
                "ecbedwars:broadcast_score_npc",  # NPC实体类型
                "default",  # 源几何体名
                "default"   # 目标几何体名
            )

            # 2. 复制玩家的渲染材质到NPC
            # CopyActorRenderMaterialFromPlayer(玩家ID, 实体类型, 源材质名, 目标材质名)
            comp_render.CopyActorRenderMaterialFromPlayer(
                skin_player,
                "ecbedwars:broadcast_score_npc",
                "default",
                "default"
            )

            # 3. 复制玩家的纹理(皮肤贴图)到NPC
            # CopyActorTextureFromPlayer(玩家ID, 实体类型, 源纹理名, 目标纹理键)
            comp_render.CopyActorTextureFromPlayer(
                skin_player,
                "ecbedwars:broadcast_score_npc",
                "default",
                texture_key  # 使用传入的texture_key作为目标纹理键
            )

            # 4. 重建NPC的渲染以应用上述更改
            # 参考: 老项目ECStagePart.py:163
            comp_render.RebuildActorRender("ecbedwars:broadcast_score_npc")

            print("[INFO] [RoomManagementClientSystem] NPC皮肤设置完成: entity_id={}".format(entity_id))

        except Exception as e:
            print("[ERROR] [RoomManagementClientSystem] 设置NPC皮肤失败: {}".format(e))
            import traceback
            traceback.print_exc()

    def _on_open_game_end(self, args):
        """
        处理游戏结算UI打开事件

        [新增 2025-11-12] 创建并显示结算UI
        参考: 老项目game_end.json定义的UI结构

        Args:
            args (dict): 事件参数
                - rank (int): 玩家排名
                - score (str): 统计文本(击杀/终结/破坏水晶)
                - left_text (str): 奖励类型文本
                - left_delta (str): 奖励变化值
        """
        try:
            print("[INFO] [RoomManagementClientSystem] 收到OpenGameEnd事件 rank={}".format(args.get('rank')))

            # 注册UI（如果还没注册）
            self._ensure_game_end_ui_registered()

            # 准备UI数据
            ui_data = {
                'rank': args.get('rank', 0),
                'score': args.get('score', ''),
                'stack_left_text': args.get('left_text', ''),
                'stack_left_delta': args.get('left_delta', ''),
                'stack_right_text': '',  # 右侧任务进度(暂时为空)
                'stack_right_delta': ''
            }

            # 创建UI
            # [修复 2025-11-12] 改用PushScreen而不是CreateUI
            # 原因: 老项目使用PushScreen，这样可以用PopScreen正确关闭
            # 参考: 老项目ECStagePart.py: clientApi.PushScreen('game_end', "game_end", args)
            result = clientApi.PushScreen(
                "game_end",  # namespace (与game_end.json的namespace字段一致)
                "game_end",  # UI唯一标识
                ui_data      # 传递给ScreenNode.__init__的参数
            )

            if result:
                print("[INFO] [RoomManagementClientSystem] 结算UI创建成功(PushScreen)")
            else:
                print("[ERROR] [RoomManagementClientSystem] 结算UI创建失败(PushScreen返回None)")

        except Exception as e:
            print("[ERROR] [RoomManagementClientSystem] 打开结算UI失败: {}".format(e))
            import traceback
            traceback.print_exc()

    def _ensure_game_end_ui_registered(self):
        """确保结算UI已注册"""
        try:
            # 注册UI（如果还没注册）
            # RegisterUI只需调用一次，重复调用会失败但不影响功能
            clientApi.RegisterUI(
                "game_end",  # namespace
                "game_end",  # UI唯一标识
                "Script_NeteaseMod.systems.ui.GameEndScreenNode.GameEndScreenNode",  # ScreenNode类路径
                "game_end.main"  # UI入口路径(对应game_end.json中的main节点)
            )
            print("[INFO] [RoomManagementClientSystem] GameEndScreenNode UI已注册")
        except Exception as e:
            # RegisterUI重复调用会抛出异常，但这是预期行为，可以忽略
            pass

