# -*- coding: utf-8 -*-
"""
ParticleClientSystem - 客户端粒子系统

功能说明：
    客户端粒子效果管理系统，监听服务端的粒子生成请求，在客户端创建粒子效果。

重构说明：
    老项目: PlayerClientParticlePart零件的客户端部分
    新项目: 独立的ClientSystem实现

核心职责：
    1. 监听服务端的粒子生成事件（ClientSpawnParticle）
    2. 在客户端创建并播放粒子效果
    3. 支持粒子绑定到实体
    4. 支持粒子变量参数配置
"""

import mod.client.extraClientApi as clientApi

ClientSystem = clientApi.GetClientSystemCls()


class ParticleClientSystem(ClientSystem):
    """客户端粒子系统"""

    def __init__(self, namespace, systemName):
        super(ParticleClientSystem, self).__init__(namespace, systemName)
        print("[INFO] [ParticleClientSystem] 粒子客户端系统初始化")

    def Create(self):
        """系统创建时调用"""
        # 注册事件监听
        self.ListenForEvent(
            clientApi.GetEngineNamespace(),
            clientApi.GetEngineSystemName(),
            "ClientSpawnParticle",
            self,
            self._on_client_spawn_particle
        )
        print("[INFO] [ParticleClientSystem] 事件监听注册完成")

    def Destroy(self):
        """系统销毁"""
        print("[INFO] [ParticleClientSystem] 粒子客户端系统销毁")
        super(ParticleClientSystem, self).Destroy()

    def OnDestroy(self):
        """系统销毁回调"""
        pass

    def Update(self):
        """系统Tick更新"""
        pass

    # ===== 事件处理 =====

    def _on_client_spawn_particle(self, args):
        """
        处理客户端粒子生成事件

        Args:
            args (dict): 粒子参数
                {
                    "pos": [x, y, z],          # 必需：粒子生成位置
                    "particle": "particle_id",  # 必需：粒子类型ID
                    "entity": entity_id,        # 可选：绑定到的实体ID
                    "variables": {              # 可选：粒子变量参数
                        "var_name": value
                    }
                }
        """
        # 1. 参数校验
        if 'pos' not in args:
            print("[ERROR] [ParticleClientSystem] ClientSpawnParticle: pos not in args")
            return
        if 'particle' not in args:
            print("[ERROR] [ParticleClientSystem] ClientSpawnParticle: particle not in args")
            return

        pos = args['pos']
        particle_id = args['particle']

        # 2. 创建粒子系统组件
        comp_factory = clientApi.GetEngineCompFactory()
        if 'entity' in args:
            # 绑定到实体（粒子跟随实体移动）
            comp_particle = comp_factory.CreateParticleSystem(args['entity'])
        else:
            # 独立粒子
            comp_particle = comp_factory.CreateParticleSystem(None)

        # 3. 创建粒子实例
        try:
            par_id = comp_particle.Create(
                particle_id,
                (float(pos[0]), float(pos[1]), float(pos[2]))
            )

            # 4. 设置粒子变量（可选）
            if 'variables' in args and par_id is not None:
                for var_name, var_value in args['variables'].items():
                    comp_particle.SetVariable(par_id, var_name, float(var_value))

            print("[INFO] [ParticleClientSystem] 粒子生成成功: {} at {}".format(particle_id, pos))

        except Exception as e:
            print("[ERROR] [ParticleClientSystem] 粒子生成失败: {}".format(e))
