# 胜利之舞系统配置化实现文档

## 概述

本文档描述了胜利之舞系统从硬编码到配置驱动的重构实现。系统现在使用JSON配置文件驱动，支持5种不同的胜利舞蹈特效（不包括末影龙），每种特效都根据排名（1、2、3）进行差异化展示。

## 文件结构

```
Script_NeteaseMod/
├── config/
│   ├── ornament_config.py                    # 装饰配置加载器（已更新）
│   └── ornaments/
│       └── victory_dance.json                # 胜利舞蹈JSON配置文件（新建）
└── systems/
    ├── ornament_system/
    │   ├── OrnamentSystem.py                 # 装饰系统主类
    │   └── ornament/
    │       └── VictoryDanceManager.py        # 胜利之舞管理器（已重构）
    └── bedwars_states/
        └── BedWarsEndingState.py             # 游戏结束状态（集成点）
```

## 核心组件

### 1. 配置文件: `victory_dance.json`

**位置**: `D:\EcWork\NetEaseMapECBedWars\behavior_packs\behavior_pack_TSK85dvb\Script_NeteaseMod\config\ornaments\victory_dance.json`

**格式说明**:

```json
{
  "victory_dances": [
    {
      "id": "dance_id",                    // 舞蹈唯一标识符
      "name": "显示名称",                   // 在商店中显示的名称
      "effect_type": "effect_type",        // 特效类型，对应play_{effect_type}_dance方法
      "price": 800,                        // 购买价格
      "unlocked_by_default": false,        // 是否默认解锁
      "description": "描述",                // 特效描述
      "rank_configs": {                    // 不同排名的配置
        "1": { /* 第一名配置 */ },
        "2": { /* 第二名配置 */ },
        "3": { /* 第三名配置 */ }
      },
      "particles": [ /* 粒子配置 */ ],
      "sounds": [ /* 音效配置 */ ]
    }
  ]
}
```

**已实现的舞蹈**:

1. **default** - 默认庆祝
   - 简单的心形粒子垂直上升
   - 音效: `random.levelup`

2. **futou** - 斧头雨
   - 斧头从天而降，撞击地面产生火花
   - 音效: `item.axe.hit`
   - 粒子: `minecraft:iron_ingot_particle` (掉落), `minecraft:critical_hit_emitter` (撞击)

3. **lightning** - 闪电
   - 连续闪电波次，垂直闪电柱效果
   - 音效: `ambient.weather.thunder`
   - 粒子: `minecraft:end_rod` (偶数层), `minecraft:critical_hit_emitter` (奇数层)

4. **space** - 太空
   - 星星轨道环绕 + 中心传送门效果
   - 音效: `ambient.weather.thunder` (高音调)
   - 粒子: `minecraft:end_rod` (轨道), `minecraft:portal_particle` (中心)

5. **yanhua** - 烟花
   - 大型烟花秀，多批次阵列发射
   - 音效: `firework.blast`
   - 粒子: 多种变体（firework_emitter, critical_hit_emitter, end_rod, totem_particle）

### 2. 配置加载器: `ornament_config.py`

**关键函数**: `_load_victory_dance_config()`

```python
def _load_victory_dance_config():
    """从JSON文件加载胜利舞蹈配置"""
    # 读取victory_dance.json
    # 转换为字典格式
    # 保存完整配置到_full_config字段
```

**特点**:
- 自动加载JSON配置
- 错误降级到默认配置
- 保留完整配置供VictoryDanceManager使用
- 向后兼容旧配置格式

### 3. 胜利之舞管理器: `VictoryDanceManager.py`

**核心类**:

#### EffectTimer
定时器管理器，用于管理持续粒子效果

```python
class EffectTimer(object):
    def add_timer(self, timer_id, duration, callback)
    def update()  # 每帧调用，检查并执行到期回调
    def clear_timer(self, timer_id)
```

#### VictoryDanceManager
主管理器类

**主要方法**:

```python
# 初始化和配置
def __init__(self, ornament_system)
def initialize()
def _load_config()

# 播放控制
def play_victory_dance(self, player_scores)  # 入口方法
def _play_dance_effect(self, player_id, dance_id, pos, rank)

# 特效实现
def play_default_dance(self, config, pos, rank)
def play_futou_dance(self, config, pos, rank)
def play_lightning_dance(self, config, pos, rank)
def play_space_dance(self, config, pos, rank)
def play_yanhua_dance(self, config, pos, rank)
def play_dragon_dance(self, config, pos, rank)  # 保留以向后兼容

# 工具方法
def spawn_timed_particle(self, pos, particle_type, delay)
def _spawn_particle(self, pos, particle_type)
def _play_sound(self, pos, sound_name, volume, pitch)
```

## 集成点

### BedWarsEndingState.py

游戏结束时，通过以下流程触发胜利之舞：

```python
def _on_enter(self):
    # 1. 显示胜利信息
    self._display_victory(winning_team)

    # 2. 播放胜利之舞
    self._play_victory_dance(winning_team)

    # 3. 切换旁观模式
    self._switch_all_to_spectator()

def _play_victory_dance(self, winning_team):
    # 获取获胜队伍的玩家积分列表
    player_scores = self._get_player_scores(winning_team)

    # 调用装饰系统
    system.ornament_system.start_victory_dance(player_scores)

def _get_player_scores(self, winning_team):
    # 返回格式: [{'player_id': str, 'score': int, 'pos': (x, y, z)}, ...]
```

## 特效实现细节

### 1. Default Dance (默认庆祝)

**特点**:
- 心形粒子垂直序列生成
- 根据rank调整粒子数量和高度范围

**实现**:
```python
# Rank 1: 15个粒子，3.0高度范围，1.5音量
# Rank 2: 12个粒子，2.5高度范围，1.2音量
# Rank 3: 8个粒子，2.0高度范围，1.0音量
```

**粒子生成模式**: `vertical_sequence`
- 从玩家位置上方1格开始
- 每个粒子间隔0.15秒
- 垂直向上分布

### 2. Futou Dance (斧头雨)

**特点**:
- 斧头从天而降的雨状效果
- 撞击地面产生火花

**实现**:
```python
# Rank 1: 25个斧头，1.5半径，2.0高度范围
# Rank 2: 18个斧头，1.2半径，1.5高度范围
# Rank 3: 12个斧头，1.0半径，1.0高度范围
```

**粒子生成模式**:
- `rain`: 从高处随机散落
  - 基础高度: 3格
  - 随机x/z偏移: ±radius
  - 随机高度偏移: 0~height_range
- `ground_impact`: 撞击地面效果
  - 延迟0.5秒（粒子下落时间）

### 3. Lightning Dance (闪电)

**特点**:
- 连续闪电波次
- 垂直闪电柱，随机偏移模拟不规则性

**实现**:
```python
# Rank 1: 10波，每波4道闪电，音量2.5
# Rank 2: 7波，每波3道闪电，音量2.0
# Rank 3: 5波，每波2道闪电，音量1.5
```

**粒子生成模式**: `vertical_bolts`
- 每道闪电10个高度段
- 偶数层使用end_rod，奇数层使用critical_hit_emitter
- 每层随机偏移±0.3格模拟闪电曲折
- 波次间隔0.6秒，闪电间隔0.1秒

**关键参数**:
- `height_segments`: 闪电高度分段数
- `segment_interval`: 段间时间间隔
- `random_offset`: 随机偏移范围
- `layer_parity`: 层奇偶性过滤（even/odd/all）

### 4. Space Dance (太空)

**特点**:
- 星星轨道环绕
- 中心传送门效果

**实现**:
```python
# Rank 1: 4条轨道，每轨道20颗星，30个传送门粒子
# Rank 2: 3条轨道，每轨道16颗星，20个传送门粒子
# Rank 3: 2条轨道，每轨道12颗星，15个传送门粒子
```

**粒子生成模式**:
- `orbit`: 轨道环绕
  - 基础半径1.5，每轨道增加0.7
  - 基础高度1.0，每轨道增加0.4
  - 旋转偏移45度
  - 使用正弦函数产生高度波动
- `center_vertical`: 中心垂直柱
  - 从0.5高度到3.5高度
  - 均匀分布传送门粒子

**关键参数**:
- `base_radius`: 第一轨道半径
- `radius_increment`: 每轨道半径增量
- `rotation_offset`: 轨道间旋转偏移
- `height_range`: 中心柱高度范围

### 5. Yanhua Dance (烟花)

**特点**:
- 大型烟花秀
- 阵列发射，多批次
- 爆炸散射效果

**实现**:
```python
# Rank 1: 5批，17个点位，音量2.5
# Rank 2: 4批，13个点位，音量2.0
# Rank 3: 3批，9个点位，音量1.5
```

**粒子生成模式**:
- `array_burst`: 阵列爆发
  - 点位配置在firework_points中
  - 高度4-8格随机
  - 使用4种粒子变体循环
- `radial_sparks`: 径向火花
  - 8个方向均匀分布
  - 半径1.2格
  - 延迟0.1秒

**关键参数**:
- `batch_count`: 批次数量
- `firework_array_size`: 每批烟花数量
- `batch_interval`: 批次间隔
- `spark_count`: 每个烟花的火花数
- `particle_variants`: 粒子类型变体数组

## 粒子生成模式详解

### vertical_sequence (垂直序列)
用于: default
- 粒子沿垂直方向依次生成
- 时间间隔: particle_interval
- 高度分布: 均匀

### rain (雨状散落)
用于: futou
- 从高处随机位置生成
- X/Z随机偏移: ±radius
- 高度随机: base_height + 0~height_range

### ground_impact (地面撞击)
用于: futou
- 与rain配合使用
- 延迟: 0.5秒
- 位置: 地面高度

### vertical_bolts (垂直闪电柱)
用于: lightning
- 分段生成，模拟闪电
- 随机偏移模拟曲折
- 支持奇偶层过滤

### orbit (轨道环绕)
用于: space
- 圆形轨道，多层嵌套
- 使用三角函数计算位置
- 支持高度波动

### center_vertical (中心垂直)
用于: space
- 垂直柱状分布
- 均匀间隔

### array_burst (阵列爆发)
用于: yanhua
- 预定义点位阵列
- 批次发射
- 高度随机

### radial_sparks (径向火花)
用于: yanhua
- 径向均匀分布
- 与array_burst配合

## Rank差异化

所有特效都支持3个排名的差异化配置：

| Rank | 说明 | 特点 |
|------|------|------|
| 1 | 第一名 | 最大规模、最高音量、最多粒子 |
| 2 | 第二名 | 中等规模、中等音量、中等粒子 |
| 3 | 第三名 | 较小规模、较低音量、较少粒子 |

**配置参数示例** (futou):
```json
"rank_configs": {
  "1": {
    "axe_count": 25,      // 第一名: 25个斧头
    "radius": 1.5,
    "height_range": 2.0,
    "volume": 1.5
  },
  "2": {
    "axe_count": 18,      // 第二名: 18个斧头
    "radius": 1.2,
    "height_range": 1.5,
    "volume": 1.2
  },
  "3": {
    "axe_count": 12,      // 第三名: 12个斧头
    "radius": 1.0,
    "height_range": 1.0,
    "volume": 1.0
  }
}
```

## 定时器系统

**EffectTimer类**:
- 基于time.time()的简单定时器
- 支持延迟回调
- 每帧update时检查并执行到期回调

**使用示例**:
```python
# 添加延迟粒子
def spawn_callback(timer_id):
    self._spawn_particle(pos, particle_type)

timer_id = self.get_next_effect_id()
self.timer_manager.add_timer(timer_id, delay_seconds, spawn_callback)

# 在主循环中调用
def update(self):
    self.timer_manager.update()
```

## 音效重复播放

支持音效的延迟和重复播放（虽然当前JSON未配置）：

```json
"sounds": [
  {
    "name": "firework.blast",
    "delay": 0.0,
    "repeat_interval": 0.8,  // 每0.8秒重复
    "repeat_count": 5         // 重复5次
  }
]
```

## 验证和测试

### 语法验证
```bash
# Python语法检查
python -m py_compile ornament_config.py
python -m py_compile VictoryDanceManager.py

# JSON格式验证
python -m json.tool victory_dance.json
```

### 运行时验证
1. 配置加载日志
   ```
   [INFO] [ornament_config] 从JSON加载胜利舞蹈配置: 5 个
   [INFO] [VictoryDanceManager] 胜利之舞管理器初始化成功，已加载 5 种舞蹈
   ```

2. 游戏结束时
   ```
   [INFO] [VictoryDanceManager] 玩家 {player_id} 排名 1 播放胜利之舞: futou
   ```

### 集成测试
1. 启动游戏
2. 进入BedWars游戏
3. 完成游戏，触发结束状态
4. 观察胜利之舞是否正常播放
5. 验证不同排名的特效差异

## 扩展指南

### 添加新舞蹈

1. **在JSON中添加配置**:
```json
{
  "id": "new_dance",
  "name": "新舞蹈",
  "effect_type": "new_effect",
  "rank_configs": { /* ... */ },
  "particles": [ /* ... */ ],
  "sounds": [ /* ... */ ]
}
```

2. **在VictoryDanceManager中实现方法**:
```python
def play_new_effect_dance(self, config, pos, rank=1):
    """新舞蹈特效实现"""
    # 从config中读取rank_configs
    rank_config = config['rank_configs'][str(rank)]

    # 读取particles和sounds配置
    particles = config.get('particles', [])
    sounds = config.get('sounds', [])

    # 实现特效逻辑
    # ...
```

### 添加新粒子生成模式

在特效方法中实现新模式：
```python
spawn_pattern = particle_config.get('spawn_pattern', '')
if spawn_pattern == 'new_pattern':
    # 实现新模式逻辑
    pass
```

### 配置参数扩展

在JSON中添加自定义参数，在实现方法中读取：
```python
custom_param = rank_config.get('custom_param', default_value)
```

## 技术特点

1. **配置驱动**: 特效参数完全由JSON控制，无需修改代码
2. **模块化**: 每种特效独立实现，互不影响
3. **可扩展**: 支持添加新舞蹈和粒子模式
4. **向后兼容**: 保留dragon舞蹈，支持旧配置格式
5. **错误降级**: 配置加载失败时使用默认配置
6. **定时器系统**: 支持复杂的时序控制
7. **Rank差异化**: 根据排名自动调整特效强度

## 注意事项

1. **末影龙特效**: 已从JSON配置中移除，但代码中保留`play_dragon_dance`方法以向后兼容
2. **粒子限制**: 避免一次生成过多粒子，可能导致性能问题
3. **音效音量**: 注意音量参数，避免过大
4. **定时器清理**: 游戏结束时自动清理所有定时器
5. **位置参数**: 特效位置通常是玩家当前位置或NPC位置

## 性能优化建议

1. 控制粒子数量（通过rank_configs调整）
2. 使用适当的时间间隔（避免过密集）
3. 定时器到期后自动清理
4. 避免复杂的数学计算（如需要，使用查找表）

## 常见问题

### Q: 如何修改特效强度？
A: 编辑victory_dance.json中的rank_configs参数

### Q: 如何添加新音效？
A: 在sounds数组中添加新条目，指定name、delay、pitch等

### Q: 特效不播放怎么办？
A: 检查日志，确认配置加载成功，玩家是否装备了对应舞蹈

### Q: 如何调整特效持续时间？
A: 调整粒子数量和时间间隔参数

## 维护建议

1. 定期备份victory_dance.json
2. 新增特效时充分测试
3. 记录配置变更
4. 保持代码和配置的一致性
5. 监控性能影响

---

**文档版本**: 1.0
**创建日期**: 2025-11-02
**作者**: Claude (Anthropic)
**项目**: NetEaseMapECBedWars - 胜利之舞配置化重构
