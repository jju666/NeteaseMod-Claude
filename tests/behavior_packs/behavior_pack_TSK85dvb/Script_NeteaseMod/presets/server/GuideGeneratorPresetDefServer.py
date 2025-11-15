# -*- coding: utf-8 -*-
"""
GuideGeneratorPresetDefServer - 资源生成器演示预设 (服务端)

功能:
- 在固定位置定时生成铁锭或金锭（每1秒，50%概率）
- 物品队列管理（最多5个，FIFO先进先出）
- 阻止玩家拾取生成的物品
- 播放粒子效果和音效

原预设: BedWarsGuideGeneratorPart
注意: 此预设不创建guide实体，仅在位置上生成物品
"""

from ECPresetServerScripts import PresetDefinitionServer
import mod.server.extraServerApi as serverApi
import random


class GuideGeneratorPresetDefServer(PresetDefinitionServer):
    """
    资源生成器演示预设 - 服务端

    核心功能:
    1. 定时器每1秒在固定位置生成物品（铁锭或金锭）
    2. 物品队列管理（最多5个，超出删除最早的）
    3. 阻止玩家拾取（ServerPlayerTryTouchEvent）
    4. 粒子效果和音效播放
    """

    def __init__(self):
        super(GuideGeneratorPresetDefServer, self).__init__()

        self.instance = None                     # PresetInstance引用
        self.pos = None                          # 生成器位置
        self.dimension_id = 0                    # 维度ID

        self.generated_items = []                # 已生成物品列表（FIFO队列）
        self.max_items = 5                       # 最多同时存在5个物品
        self.spawn_timer = None                  # 生成定时器

        self.is_listening_pickup = False         # 是否已注册拾取事件监听

    def on_init(self, instance):
        """
        预设初始化

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_generator] 预设初始化: {}".format(instance.instance_id))

        self.instance = instance
        self.pos = instance.get_config("pos", [0, 64, 0])
        self.dimension_id = instance.get_config("dimension_id", 0)

        print("  - pos: {}".format(self.pos))
        print("  - dimension_id: {}".format(self.dimension_id))

    def on_start(self, instance):
        """
        预设启动 - 启动定时器和事件监听

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_generator] 预设启动: {}".format(instance.instance_id))

        self.instance = instance

        # 启动资源生成定时器（每1秒生成一次）
        self._start_spawn_timer()

        # 注册拾取事件监听，阻止玩家拾取
        self._register_pickup_listener()

    def _start_spawn_timer(self):
        """
        启动资源生成定时器 - 每1秒触发一次
        """
        try:
            game_comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())

            # 创建重复定时器，每1秒生成一次物品
            self.spawn_timer = game_comp.AddRepeatedTimer(1.0, self._spawn_resource_item)

            print("[INFO] [bedwars:guide_generator] 资源生成定时器已启动（每1秒）")
        except Exception as e:
            print("[ERROR] [bedwars:guide_generator] 启动定时器失败: {}".format(e))

    def _spawn_resource_item(self):
        """
        生成资源物品 - 定时器回调

        逻辑:
        1. 检查物品数量是否达到上限（5个）
        2. 如果达到上限，删除最早的物品（FIFO）
        3. 随机选择资源类型（铁锭或金锭，50%概率）
        4. 创建物品实体
        5. 播放音效和粒子效果
        """
        # 检查是否达到最大数量限制
        if len(self.generated_items) >= self.max_items:
            # 删除最早的物品（FIFO队列）
            oldest_item = self.generated_items.pop(0)
            try:
                # 使用游戏系统API删除实体
                server_system = self.instance.manager.server_api
                if server_system:
                    server_system.DestroyEntity(oldest_item)
                # print("[DEBUG] [bedwars:guide_generator] 已删除旧物品: {}".format(oldest_item))
            except Exception as e:
                print("[DEBUG] [bedwars:guide_generator] 清理旧物品异常: {}".format(e))

        # 随机选择资源类型（50%概率）
        if random.random() < 0.5:
            item_name = "minecraft:iron_ingot"
        else:
            item_name = "minecraft:gold_ingot"

        # 创建物品实体
        try:
            # 构造物品字典
            item_dict = {
                'itemName': item_name,
                'count': 1,
                'enchantData': [],
                'auxValue': 0
            }

            # 确保位置是元组格式 (x, y, z)
            spawn_pos = tuple(self.pos) if isinstance(self.pos, list) else self.pos

            # 使用CreateEngineItemEntity生成物品（参考老项目BedWarsGuideGeneratorPart）
            # 这个API会返回正确的entity_id，而不是True/False
            server_system = self.instance.manager.server_api
            if not server_system:
                print("[WARN] [bedwars:guide_generator] server_api未初始化，跳过生成")
                return

            entity_id = server_system.CreateEngineItemEntity(item_dict, self.dimension_id, spawn_pos)

            # entity_id可能是None(失败)或实体ID字符串(成功)
            if entity_id:
                # 记录生成的物品ID
                self.generated_items.append(entity_id)

                # 播放音效（random.pop2，音量0.5，随机音调1.1-1.5）
                self._play_spawn_sound()

                # 广播粒子效果事件到所有客户端
                self._broadcast_particle_effect(item_name)

                # print("[DEBUG] [bedwars:guide_generator] 生成物品成功: {} at {}".format(item_name, spawn_pos))
            else:
                # 返回None表示失败，可能是区块未加载，静默忽略即可
                pass
        except Exception as e:
            print("[ERROR] [bedwars:guide_generator] 生成物品异常: {}".format(e))
            import traceback
            traceback.print_exc()

    def _play_spawn_sound(self):
        """
        播放资源生成音效（参考老项目BedWarsGuideGeneratorPart.spawn_entity_item）
        """
        try:
            # 随机音调（1.1 ~ 1.5）
            pitch = random.uniform(1.1, 1.5)

            # 执行命令播放音效（参考老项目格式）
            command = "playsound {sound} @a {pos} {volume} {pitch}".format(
                sound="random.pop2",
                pos="{} {} {}".format(self.pos[0], self.pos[1], self.pos[2]),
                volume=0.5,
                pitch=pitch
            )

            # 使用ServerSystem执行命令
            server_system = self.instance.manager.server_api
            if server_system:
                comp_command = serverApi.GetEngineCompFactory().CreateCommand(serverApi.GetLevelId())
                comp_command.SetCommand(command)
            else:
                print("[WARN] [bedwars:guide_generator] server_api未初始化，无法播放音效")
        except Exception as e:
            print("[ERROR] [bedwars:guide_generator] 播放音效失败: {}".format(e))

    def _broadcast_particle_effect(self, item_name):
        """
        广播粒子效果事件到所有客户端（参考老项目BedWarsGuideGeneratorPart.spawn_entity_item）

        Args:
            item_name: str 物品名称（用于确定粒子颜色）
        """
        try:
            # 使用instance.send_to_client广播到客户端
            # 注意：老项目使用BroadcastToAllClient("BedWarsGuideGeneratorEffect", {"color_id": item_name})
            # 这里通过ECPreset框架的send_to_client实现相同效果
            # 必须包含pos数据，因为客户端需要知道在哪里播放粒子
            self.instance.send_to_client(
                "guide_generator_effect",
                {
                    "pos": self.pos,  # 传递位置信息
                    "color_id": item_name
                }
            )
        except Exception as e:
            print("[ERROR] [bedwars:guide_generator] 广播粒子效果失败: {}".format(e))

    def _register_pickup_listener(self):
        """
        注册拾取事件监听 - 阻止玩家拾取生成的物品
        """
        if not self.is_listening_pickup and self.instance:
            try:
                server_system = self.instance.manager.server_api
                if server_system:
                    server_system.ListenForEvent(
                        serverApi.GetEngineNamespace(),
                        serverApi.GetEngineSystemName(),
                        "ServerPlayerTryTouchEvent",
                        self,
                        self._on_player_try_pickup
                    )
                    self.is_listening_pickup = True
                    print("[INFO] [bedwars:guide_generator] 已注册拾取事件监听，物品不可拾取")
                else:
                    print("[WARN] [bedwars:guide_generator] server_api未初始化，跳过拾取事件监听")
            except Exception as e:
                print("[ERROR] [bedwars:guide_generator] 注册拾取事件监听失败: {}".format(e))

    def _on_player_try_pickup(self, args):
        """
        玩家尝试拾取物品事件处理 - 阻止拾取生成的物品

        Args:
            args: dict 事件参数
                - playerId: str 玩家ID
                - entityId: str 物品实体ID
                - cancel: bool 是否取消拾取
                - pickupDelay: int 拾取延迟（tick）
        """
        entity_id = args.get('entityId')

        # 检查是否是本生成器生成的物品
        if entity_id in self.generated_items:
            args['cancel'] = True         # 取消拾取
            args['pickupDelay'] = 97814   # 设置超长拾取延迟（约81分钟）

    def on_stop(self, instance):
        """
        预设停止 - 取消事件监听和定时器

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_generator] 预设停止: {}".format(instance.instance_id))

        # 取消定时器
        self._cancel_spawn_timer()

        # 取消事件监听
        self._unlisten_pickup_event()

        # 清理生成的物品
        self._cleanup_generated_items()

    def on_destroy(self, instance):
        """
        预设销毁 - 取消事件监听、清理物品

        Args:
            instance: PresetInstance对象
        """
        print("[INFO] [bedwars:guide_generator] 预设销毁: {}".format(instance.instance_id))

        # 取消定时器
        self._cancel_spawn_timer()

        # 取消事件监听
        self._unlisten_pickup_event()

        # 清理生成的物品
        self._cleanup_generated_items()

    def _cancel_spawn_timer(self):
        """
        取消资源生成定时器
        """
        if self.spawn_timer:
            try:
                game_comp = serverApi.GetEngineCompFactory().CreateGame(serverApi.GetLevelId())
                game_comp.CancelTimer(self.spawn_timer)
                self.spawn_timer = None
                print("[INFO] [bedwars:guide_generator] 已取消资源生成定时器")
            except Exception as e:
                print("[ERROR] [bedwars:guide_generator] 取消定时器失败: {}".format(e))

    def _cleanup_generated_items(self):
        """
        清理所有生成的物品实体
        """
        for entity_id in self.generated_items:
            try:
                # 使用游戏系统API删除实体
                server_system = self.instance.manager.server_api
                if server_system:
                    server_system.DestroyEntity(entity_id)
            except Exception as e:
                print("[DEBUG] [bedwars:guide_generator] 清理物品异常: {}".format(e))

        self.generated_items = []
        print("[INFO] [bedwars:guide_generator] 已清理所有生成的物品")

    def _unlisten_pickup_event(self):
        """
        取消拾取事件监听 - 资源清理
        """
        if self.is_listening_pickup and self.instance:
            try:
                server_system = self.instance.manager.server_api
                if server_system:
                    server_system.UnListenForEvent(
                        serverApi.GetEngineNamespace(),
                        serverApi.GetEngineSystemName(),
                        "ServerPlayerTryTouchEvent",
                        self,
                        self._on_player_try_pickup
                    )
                    self.is_listening_pickup = False
                    print("[INFO] [bedwars:guide_generator] 已取消拾取事件监听")
            except Exception as e:
                print("[ERROR] [bedwars:guide_generator] 取消拾取事件监听失败: {}".format(e))