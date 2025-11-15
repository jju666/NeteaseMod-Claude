# -*- coding: utf-8 -*-
"""
EntityPresetServerBase - 实体预设基类

提供通用的异步创建实体功能，避免在未加载区块中创建实体失败
"""

from ECPresetServerScripts import PresetDefinitionServer
import mod.server.extraServerApi as serverApi
from Script_NeteaseMod.modConfig import MOD_NAME, SERVER_SYSTEMS

# 提取 BedWarsGameSystem 系统名称
BEDWARS_GAME_SYSTEM = SERVER_SYSTEMS[0][0]  # "BedWarsGameSystem"


class EntityPresetServerBase(PresetDefinitionServer):
    """
    实体预设基类

    提供通用的异步创建实体功能：
    1. 先异步加载实体位置所在区块
    2. 区块加载完成后再创建实体
    3. 避免在未加载区块中创建实体失败的问题
    """

    def __init__(self):
        super(EntityPresetServerBase, self).__init__()

    def create_entity_async(self, entity_identifier, pos, rotation, dimension_id, callback, is_npc=False, is_global=False, chunk_radius=1):
        """
        异步创建实体 - 先加载区块，再创建实体

        Args:
            entity_identifier: str 实体标识符
            pos: list/tuple 位置 [x, y, z]
            rotation: dict 旋转 {"pitch": 0, "yaw": 0, "roll": 0}
            dimension_id: int 维度ID
            callback: function 创建完成回调函数 callback(entity_id)
            is_npc: bool 是否为NPC (默认False)
            is_global: bool 是否为全局实体 (默认False)
            chunk_radius: int 区块加载半径 (默认1，即加载周围1个区块)

        Returns:
            bool 是否成功启动异步加载
        """
        print("[INFO] [EntityPresetBase] 准备异步创建实体: identifier={}, pos={}, dimension={}".format(
            entity_identifier, pos, dimension_id
        ))

        try:
            # 计算区块加载范围
            pos_min = (int(pos[0]) - chunk_radius * 16, int(pos[1]) - chunk_radius * 16, int(pos[2]) - chunk_radius * 16)
            pos_max = (int(pos[0]) + chunk_radius * 16, int(pos[1]) + chunk_radius * 16, int(pos[2]) + chunk_radius * 16)

            print("[INFO] [EntityPresetBase] 异步加载区块: pos_min={}, pos_max={}".format(pos_min, pos_max))

            # 准备回调函数，区块加载完成后创建实体
            def on_chunk_loaded(result):
                print("[INFO] [EntityPresetBase] 区块加载完成: result={}".format(result))

                if result.get('code') != 1:
                    print("[ERROR] [EntityPresetBase] 区块加载失败: result={}".format(result))
                    if callback:
                        callback(None)
                    return

                # 创建实体
                entity_id = self._create_entity_internal(
                    entity_identifier, pos, rotation, dimension_id, is_npc, is_global
                )

                # 调用回调函数
                if callback:
                    callback(entity_id)

            # 异步加载区块
            comp = serverApi.GetEngineCompFactory().CreateChunkSource(serverApi.GetLevelId())
            success = comp.DoTaskOnChunkAsync(dimension_id, pos_min, pos_max, on_chunk_loaded)

            if not success:
                print("[ERROR] [EntityPresetBase] 异步加载区块失败")
                return False

            return True

        except Exception as e:
            print("[ERROR] [EntityPresetBase] 异步加载区块异常: {}".format(e))
            import traceback
            traceback.print_exc()
            return False

    def _create_entity_internal(self, entity_identifier, pos, rotation, dimension_id, is_npc, is_global):
        """
        内部方法 - 创建实体

        Args:
            entity_identifier: str 实体标识符
            pos: list/tuple 位置 [x, y, z]
            rotation: dict 旋转 {"pitch": 0, "yaw": 0, "roll": 0}
            dimension_id: int 维度ID
            is_npc: bool 是否为NPC
            is_global: bool 是否为全局实体

        Returns:
            str|None 实体ID，失败返回None
        """
        try:
            # 准备旋转参数 (pitch, yaw)
            pitch = rotation.get("pitch", 0) if isinstance(rotation, dict) else 0
            yaw = rotation.get("yaw", 0) if isinstance(rotation, dict) else 0
            rot = (pitch, yaw)

            # 使用 modConfig 常量获取 BedWarsGameSystem
            system = serverApi.GetSystem(MOD_NAME, BEDWARS_GAME_SYSTEM)
            entity_id = system.CreateEngineEntityByTypeStr(
                entity_identifier,  # engineTypeStr
                tuple(pos),         # pos
                rot,                # rot (pitch, yaw)
                dimension_id,       # dimensionId
                is_npc,             # isNpc
                is_global           # isGlobal
            )

            if entity_id:
                print("[INFO] [EntityPresetBase] 实体创建成功: entity_id={}".format(entity_id))
            else:
                print("[ERROR] [EntityPresetBase] 实体创建失败: CreateEngineEntityByTypeStr返回None")

            return entity_id

        except Exception as e:
            print("[ERROR] [EntityPresetBase] 创建实体异常: {}".format(e))
            import traceback
            traceback.print_exc()
            return None

    def destroy_entity(self, entity_id):
        """
        销毁实体

        Args:
            entity_id: str 实体ID

        Returns:
            bool 是否成功
        """
        if not entity_id:
            return False

        try:
            # 使用 modConfig 常量获取 BedWarsGameSystem
            system = serverApi.GetSystem(MOD_NAME, BEDWARS_GAME_SYSTEM)
            system.DestroyEntity(entity_id)
            print("[INFO] [EntityPresetBase] 实体已销毁: entity_id={}".format(entity_id))
            return True

        except Exception as e:
            print("[ERROR] [EntityPresetBase] 销毁实体异常: {}".format(e))
            import traceback
            traceback.print_exc()
            return False