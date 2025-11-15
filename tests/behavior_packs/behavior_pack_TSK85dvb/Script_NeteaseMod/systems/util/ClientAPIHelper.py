# -*- coding: utf-8 -*-
"""
客户端API封装辅助类

提供常用客户端API的便捷封装，包括：
- 浮动文字（TextBoard）
- 浮空物品（ItemEntity）
- 粒子特效（ParticleSystem）

API调研完成时间：2025-01-30
MODSDK文档位置：D:\EcWork\netease-modsdk-wiki
"""

from __future__ import print_function
import mod.client.extraClientApi as clientApi
import traceback


class ClientAPIHelper(object):
    """客户端API封装辅助类"""

    # ========== 浮动文字（TextBoard）相关 ==========

    @staticmethod
    def create_floating_text(text, pos, text_color=(1.0, 1.0, 1.0, 1.0),
                            board_color=(0.0, 0.0, 0.0, 0.3), scale=(1.0, 1.0),
                            face_camera=True, depth_test=False):
        # type: (str, tuple, tuple, tuple, tuple, bool, bool) -> int or None
        """
        创建浮动文字

        Args:
            text (str): 文字内容（支持§格式化代码）
            pos (tuple): 位置 (x, y, z)
            text_color (tuple): 文字颜色 RGBA (r, g, b, a)，范围0-1，默认白色
            board_color (tuple): 背景颜色 RGBA (r, g, b, a)，范围0-1，默认半透明黑色
            scale (tuple): 缩放 (x, y)，默认(1.0, 1.0)
            face_camera (bool): 是否始终朝向相机，默认True
            depth_test (bool): 是否开启深度测试（被方块遮挡），默认False

        Returns:
            int or None: 文字面板ID（用于后续操作和销毁），失败返回None

        API文档位置：
            D:\EcWork\netease-modsdk-wiki\docs\mcdocs\1-ModAPI\接口\特效\文字面板.md
        """
        try:
            # 获取TextBoardComponent
            comp = clientApi.GetEngineCompFactory().CreateTextBoard(clientApi.GetLevelId())

            # 创建文字面板
            board_id = comp.CreateTextBoardInWorld(
                text=text,
                textColor=text_color,
                boardColor=board_color,
                faceCamera=face_camera
            )

            if board_id:
                # 设置位置
                comp.SetBoardPos(board_id, pos)

                # 设置缩放
                comp.SetBoardScale(board_id, scale)

                # 设置深度测试
                comp.SetBoardDepthTest(board_id, depth_test)

                print("[ClientAPIHelper] 创建浮动文字成功: board_id={}, pos={}".format(board_id, pos))
                return board_id
            else:
                print("[ERROR] [ClientAPIHelper] 创建浮动文字失败")
                return None

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 创建浮动文字异常: {}".format(str(e)))
            traceback.print_exc()
            return None

    @staticmethod
    def update_floating_text(board_id, text=None, text_color=None):
        # type: (int, str, tuple) -> bool
        """
        更新浮动文字内容和颜色

        Args:
            board_id (int): 文字面板ID
            text (str): 新文字内容（None表示不更新）
            text_color (tuple): 新文字颜色 RGBA (r, g, b, a)（None表示不更新）

        Returns:
            bool: 是否更新成功
        """
        try:
            comp = clientApi.GetEngineCompFactory().CreateTextBoard(clientApi.GetLevelId())

            success = True

            # 更新文字内容
            if text is not None:
                success = success and comp.SetText(board_id, text)

            # 更新文字颜色
            if text_color is not None:
                success = success and comp.SetBoardTextColor(board_id, text_color)

            return success

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 更新浮动文字异常: {}".format(str(e)))
            traceback.print_exc()
            return False

    @staticmethod
    def destroy_floating_text(board_id):
        # type: (int) -> bool
        """
        销毁浮动文字

        Args:
            board_id (int): 文字面板ID

        Returns:
            bool: 是否销毁成功
        """
        try:
            comp = clientApi.GetEngineCompFactory().CreateTextBoard(clientApi.GetLevelId())
            success = comp.RemoveTextBoard(board_id)

            if success:
                print("[ClientAPIHelper] 销毁浮动文字成功: board_id={}".format(board_id))
            else:
                print("[WARN] [ClientAPIHelper] 销毁浮动文字失败: board_id={}".format(board_id))

            return success

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 销毁浮动文字异常: {}".format(str(e)))
            traceback.print_exc()
            return False

    @staticmethod
    def bind_floating_text_to_entity(board_id, entity_id, offset=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0)):
        # type: (int, str, tuple, tuple) -> bool
        """
        将浮动文字绑定到实体

        Args:
            board_id (int): 文字面板ID
            entity_id (str): 实体ID（None表示取消绑定）
            offset (tuple): 相对于实体的偏移量 (x, y, z)
            rot (tuple): 相对于实体的偏移角度 (pitch, yaw, roll)

        Returns:
            bool: 是否绑定成功
        """
        try:
            comp = clientApi.GetEngineCompFactory().CreateTextBoard(clientApi.GetLevelId())
            success = comp.SetBoardBindEntity(board_id, entity_id, offset, rot)
            return success

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 绑定浮动文字到实体异常: {}".format(str(e)))
            traceback.print_exc()
            return False

    # ========== 粒子特效（ParticleSystem）相关 ==========

    @staticmethod
    def play_particle_circle(pos, color, radius=1.0, particle_name="minecraft:villager_happy", duration=-1):
        # type: (tuple, tuple, float, str, int) -> int or None
        """
        播放圆圈粒子特效

        Args:
            pos (tuple): 中心位置 (x, y, z)
            color (tuple): RGB颜色 (r, g, b)，范围0-1
            radius (float): 半径
            particle_name (str): 粒子名称（默认使用开心村民粒子）
            duration (int): 持续时间秒数（-1表示永久）

        Returns:
            int or None: 粒子ID，失败返回None

        注意：
            - 这是简化版本，使用单个粒子实现
            - 完整的圆圈效果需要自定义粒子JSON文件
            - 参考文档：D:\EcWork\netease-modsdk-wiki\docs\mcdocs\1-ModAPI\接口\特效\微软粒子.md
        """
        try:
            # 获取ParticleSystem组件
            comp = clientApi.GetEngineCompFactory().CreateParticleSystem(None)

            # 创建粒子
            par_id = comp.Create(particle_name, pos, (0, 0, 0))

            if par_id and par_id != 0:
                print("[ClientAPIHelper] 创建粒子特效成功: par_id={}, pos={}".format(par_id, pos))
                return par_id
            else:
                print("[ERROR] [ClientAPIHelper] 创建粒子特效失败")
                return None

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 创建粒子特效异常: {}".format(str(e)))
            traceback.print_exc()
            return None

    @staticmethod
    def play_particle(particle_name, pos, rot=(0, 0, 0)):
        # type: (str, tuple, tuple) -> int or None
        """
        播放粒子特效

        Args:
            particle_name (str): 粒子名称（identifier格式，如 "minecraft:water_evaporation_manual"）
            pos (tuple): 位置 (x, y, z)
            rot (tuple): 旋转角度 (pitch, yaw, roll)

        Returns:
            int or None: 粒子ID，失败返回None

        常用粒子名称：
            - "minecraft:villager_happy" - 开心粒子（绿色爱心）
            - "minecraft:villager_angry" - 愤怒粒子（黑色烟雾）
            - "minecraft:water_evaporation_manual" - 水蒸气
            - "minecraft:critical_hit_emitter" - 暴击粒子
        """
        try:
            comp = clientApi.GetEngineCompFactory().CreateParticleSystem(None)
            par_id = comp.Create(particle_name, pos, rot)

            if par_id and par_id != 0:
                return par_id
            else:
                return None

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 播放粒子异常: {}".format(str(e)))
            traceback.print_exc()
            return None

    @staticmethod
    def stop_particle(par_id):
        # type: (int) -> bool
        """
        停止粒子特效

        Args:
            par_id (int): 粒子ID

        Returns:
            bool: 是否停止成功
        """
        try:
            comp = clientApi.GetEngineCompFactory().CreateParticleSystem(None)
            success = comp.Stop(par_id)
            return success

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 停止粒子异常: {}".format(str(e)))
            traceback.print_exc()
            return False

    @staticmethod
    def remove_particle(par_id):
        # type: (int) -> bool
        """
        移除粒子特效

        Args:
            par_id (int): 粒子ID

        Returns:
            bool: 是否移除成功
        """
        try:
            comp = clientApi.GetEngineCompFactory().CreateParticleSystem(None)
            success = comp.Remove(par_id)
            return success

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 移除粒子异常: {}".format(str(e)))
            traceback.print_exc()
            return False

    @staticmethod
    def set_particle_variable(par_id, var_name, value):
        # type: (int, str, float) -> bool
        """
        设置粒子Molang变量（用于控制粒子颜色、大小等）

        Args:
            par_id (int): 粒子ID
            var_name (str): 变量名（如 "variable.color_r"）
            value (float): 变量值

        Returns:
            bool: 是否设置成功

        常用变量：
            - "variable.color_r" - 红色通道 (0-1)
            - "variable.color_g" - 绿色通道 (0-1)
            - "variable.color_b" - 蓝色通道 (0-1)
        """
        try:
            comp = clientApi.GetEngineCompFactory().CreateParticleSystem(None)
            success = comp.SetVariable(par_id, var_name, value)
            return success

        except Exception as e:
            print("[ERROR] [ClientAPIHelper] 设置粒子变量异常: {}".format(str(e)))
            traceback.print_exc()
            return False


# ========== 使用示例（用于参考） ==========

"""
# 示例1：创建浮动文字
board_id = ClientAPIHelper.create_floating_text(
    text="§e欢迎来到起床战争！",
    pos=(0, 5, 0),
    text_color=(1.0, 1.0, 0.0, 1.0),  # 黄色
    scale=(1.5, 1.5)
)

# 60秒后销毁
self.AddTimer(60.0, lambda: ClientAPIHelper.destroy_floating_text(board_id))

# 示例2：播放粒子特效
par_id = ClientAPIHelper.play_particle(
    "minecraft:villager_happy",
    pos=(0, 5, 0)
)

# 示例3：创建圆圈粒子（简化版）
par_id = ClientAPIHelper.play_particle_circle(
    pos=(0, 5, 0),
    color=(1.0, 0.0, 0.0),  # 红色
    radius=1.0
)
"""
