# ParticleManager 使用示例

## 概述

ParticleManager 是客户端粒子管理工具，提供统一的粒子播放接口。

## 基本使用

### 1. 在System中初始化

```python
from systems.util import ParticleManager

class MyGameSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MyGameSystem, self).__init__(namespace, systemName)
        # 初始化粒子管理器
        self.particle_mgr = ParticleManager(self)
```

### 2. 播放粒子效果

#### 方式1：全局广播粒子

```python
# 向所有玩家广播粒子
self.particle_mgr.spawn_particle(
    "minecraft:critical_hit_emitter",  # 粒子ID
    [100, 65, 100]                     # 位置 [x, y, z]
)
```

#### 方式2：向特定玩家显示粒子

```python
# 只有指定玩家能看到
self.particle_mgr.spawn_particle(
    "minecraft:heart_particle",
    [100, 65, 100],
    players=['player1', 'player2'],    # 玩家ID列表
    variables={'scale': 2.0}            # 粒子变量（大小）
)
```

#### 方式3：向特定维度的玩家显示粒子

```python
# 只向特定维度的玩家显示
self.particle_mgr.spawn_particle(
    "minecraft:dragon_breath_fire",
    [0, 100, 0],
    dimension=10000                    # 维度ID
)
```

### 3. 便捷方法

#### 在玩家位置播放粒子

```python
# 在玩家头顶播放粒子
self.particle_mgr.spawn_particle_at_player(
    player_id,
    "minecraft:totem_particle",
    offset=(0, 2, 0)  # 向上偏移2格
)
```

#### 在实体位置播放粒子

```python
# 在实体位置播放粒子
self.particle_mgr.spawn_particle_at_entity(
    entity_id,
    "minecraft:flame",
    offset=(0, 1, 0)
)
```

## 常用粒子效果

使用 `ParticleEffects` 常量类：

```python
from systems.util import ParticleManager, ParticleEffects

# 击杀特效
self.particle_mgr.spawn_particle(
    ParticleEffects.CRITICAL_HIT,
    player_pos
)

# 爱心效果
self.particle_mgr.spawn_particle(
    ParticleEffects.HEART,
    player_pos,
    players=[player_id]
)

# 爆炸效果
self.particle_mgr.spawn_particle(
    ParticleEffects.HUGE_EXPLODE,
    bed_pos
)

# 图腾闪光效果
self.particle_mgr.spawn_particle(
    ParticleEffects.TOTEM,
    upgrade_pos
)
```

## 实战示例

### 示例1：击杀特效

```python
def on_player_killed(self, killer_id, victim_id):
    """玩家击杀时的粒子效果"""
    # 获取受害者位置
    comp_pos = self.comp_factory.CreatePos(victim_id)
    pos = comp_pos.GetFootPos()

    # 播放暴击粒子
    self.particle_mgr.spawn_particle(
        ParticleEffects.CRITICAL_HIT,
        [pos[0], pos[1] + 1, pos[2]],
        dimension=self.game_dimension
    )
```

### 示例2：床位破坏特效

```python
def on_bed_destroyed(self, bed_pos, team_color):
    """床位破坏时的粒子效果"""
    # 播放大爆炸粒子
    self.particle_mgr.spawn_particle(
        ParticleEffects.HUGE_EXPLODE,
        bed_pos,
        dimension=self.game_dimension,
        variables={'scale': 3.0}  # 放大3倍
    )
```

### 示例3：资源生成提示

```python
def on_generator_spawn_item(self, generator_pos, item_type):
    """资源生成器生成物品时的粒子"""
    # 根据物品类型选择粒子颜色
    particle_vars = {}
    if item_type == 'iron':
        particle_vars['color'] = 0xC0C0C0  # 银色
    elif item_type == 'gold':
        particle_vars['color'] = 0xFFD700  # 金色

    self.particle_mgr.spawn_particle(
        "minecraft:shulker_bullet",
        generator_pos,
        dimension=self.game_dimension,
        variables=particle_vars
    )
```

### 示例4：队伍升级特效

```python
def on_team_upgraded(self, team_players):
    """队伍升级时的粒子效果"""
    # 向队伍所有玩家播放图腾粒子
    for player_id in team_players:
        self.particle_mgr.spawn_particle_at_player(
            player_id,
            ParticleEffects.TOTEM,
            offset=(0, 1, 0)
        )
```

### 示例5：治疗池效果

```python
def on_player_in_healing_pool(self, player_id):
    """玩家在治疗池中的持续粒子效果"""
    # 每0.5秒播放一次治疗粒子
    self.particle_mgr.spawn_particle_at_player(
        player_id,
        ParticleEffects.HEART,
        offset=(0, 1.5, 0)
    )
```

## 粒子变量参数

支持的常用变量参数：

```python
variables = {
    'scale': 2.0,        # 粒子大小（缩放倍数）
    'color': 0xFF0000,   # 颜色（十六进制RGB）
    'lifetime': 5.0,     # 生命周期（秒）
}

self.particle_mgr.spawn_particle(
    particle_id,
    pos,
    variables=variables
)
```

## 性能优化建议

### 1. 控制粒子生成频率

```python
# 不推荐：频繁生成大量粒子
for i in range(100):
    self.particle_mgr.spawn_particle(particle_id, pos)

# 推荐：使用定时器控制频率
if current_time - last_spawn_time > 0.5:  # 每0.5秒一次
    self.particle_mgr.spawn_particle(particle_id, pos)
    last_spawn_time = current_time
```

### 2. 选择合适的发送模式

```python
# 个人效果：指定玩家
self.particle_mgr.spawn_particle(
    particle_id, pos,
    players=[player_id]  # 只发送给该玩家
)

# 游戏事件：指定维度
self.particle_mgr.spawn_particle(
    particle_id, pos,
    dimension=game_dim  # 只发送给该维度的玩家
)

# 全局事件：全局广播
self.particle_mgr.spawn_particle(
    particle_id, pos
    # 发送给所有玩家
)
```

### 3. 避免绑定到已移除的实体

```python
# 检查实体是否存在
comp_actor = self.comp_factory.CreateActorInfo(entity_id)
if comp_actor.GetState():  # 实体存在
    self.particle_mgr.spawn_particle_at_entity(
        entity_id,
        particle_id
    )
```

## 常见粒子效果ID

| 粒子ID | 效果 | 适用场景 |
|--------|------|----------|
| `minecraft:critical_hit_emitter` | 暴击粒子 | 击杀、攻击 |
| `minecraft:heart_particle` | 爱心粒子 | 治疗、buff |
| `minecraft:huge_explode_emitter` | 大爆炸 | 床位破坏、TNT |
| `minecraft:totem_particle` | 图腾闪光 | 升级、成就 |
| `minecraft:shulker_bullet` | 潜影贝轨迹 | 资源生成 |
| `minecraft:dragon_breath_fire` | 龙息火焰 | 特殊效果 |
| `minecraft:villager_angry` | 愤怒粒子 | 负面状态 |
| `minecraft:villager_happy` | 开心粒子 | 正面状态 |
| `minecraft:basic_flame_particle` | 火焰 | 燃烧效果 |
| `minecraft:basic_smoke_particle` | 烟雾 | 爆炸、燃烧 |

## 故障排查

### 粒子不显示

1. 检查粒子ID是否正确
2. 检查位置是否在加载范围内
3. 检查客户端系统是否正确注册（modConfig.py）
4. 查看客户端日志是否有错误信息

### 粒子位置错误

1. 确保位置参数格式正确：`[x, y, z]`
2. 检查坐标值是否合理
3. 使用 `float()` 转换确保数值类型正确
