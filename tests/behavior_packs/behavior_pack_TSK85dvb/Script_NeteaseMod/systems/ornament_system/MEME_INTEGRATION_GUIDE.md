# 墓碑装饰系统集成指南

## 概述

本文档说明如何将 `MemeOrnamentSystem` (墓碑装饰系统) 集成到现有的起床战争系统中。

## 文件结构

```
Script_NeteaseMod/
├── config/
│   └── ornaments/
│       └── meme.json                    # 墓碑配置文件 (已创建)
├── systems/
│   ├── BedWarsGameSystem.py             # 游戏系统 (需要修改)
│   └── ornament_system/
│       ├── OrnamentSystem.py            # 装扮系统 (需要修改)
│       └── meme/
│           ├── __init__.py              # (已创建)
│           └── MemeOrnamentSystem.py    # 墓碑系统实现 (已创建)
```

## 集成步骤

### 步骤 1: 修改 OrnamentSystem.py

在 `D:\EcWork\NetEaseMapECBedWars\behavior_packs\behavior_pack_TSK85dvb\Script_NeteaseMod\systems\ornament_system\OrnamentSystem.py` 中:

#### 1.1 添加墓碑系统属性 (第 42 行附近)

```python
self.bed_destroy_effect_manager = None  # 床破坏特效管理器
self.shop_npc_skin_manager = None  # 商店NPC皮肤管理器
self.meme_ornament_system = None  # 墓碑装饰管理器  <-- 添加这行
self.ornament_config = {}  # 装扮配置
```

#### 1.2 在 initialize() 方法中初始化墓碑系统 (第 84 行后)

```python
# 初始化商店NPC皮肤管理器
from ornament.ShopNPCSkinManager import ShopNPCSkinManager
self.shop_npc_skin_manager = ShopNPCSkinManager(self)
self.shop_npc_skin_manager.initialize()

# 初始化墓碑装饰管理器  <-- 添加以下3行
from meme.MemeOrnamentSystem import MemeOrnamentSystem
self.meme_ornament_system = MemeOrnamentSystem(self)
self.meme_ornament_system.initialize()

# 加载装扮配置
self._load_ornament_config()
```

#### 1.3 在 cleanup() 方法中清理墓碑系统 (第 118 行后)

```python
if self.shop_npc_skin_manager:
    self.shop_npc_skin_manager.cleanup()

if self.meme_ornament_system:  <-- 添加以下2行
    self.meme_ornament_system.cleanup()

self.player_ornaments = {}
```

#### 1.4 在 update() 方法中更新墓碑系统 (第 489 行后)

```python
def update(self):
    """
    更新饰品系统 - 需要在游戏主循环中调用
    主要用于更新特效定时器
    """
    if self.victory_dance_manager:
        self.victory_dance_manager.update()

    # 更新墓碑系统定时器  <-- 添加以下2行
    if self.meme_ornament_system:
        self.meme_ornament_system.update()

    # 床破坏特效管理器使用同一个定时器,不需要单独update
```

#### 1.5 添加墓碑生成接口 (在文件末尾添加)

```python
# ========== 墓碑装饰 ==========

def spawn_death_meme(self, player_id, death_pos, dimension):
    """
    在玩家死亡位置生成墓碑

    Args:
        player_id (str): 玩家ID
        death_pos (tuple): 死亡位置 (x, y, z)
        dimension (int): 维度ID

    Returns:
        str: 墓碑实体ID，失败返回None
    """
    if not self.meme_ornament_system:
        print("[WARN] [OrnamentSystem] 墓碑系统未初始化")
        return None

    return self.meme_ornament_system.spawn_meme(player_id, death_pos, dimension)
```

---

### 步骤 2: 修改 BedWarsGameSystem.py

在 `D:\EcWork\NetEaseMapECBedWars\behavior_packs\behavior_pack_TSK85dvb\Script_NeteaseMod\systems\BedWarsGameSystem.py` 中:

#### 2.1 在 on_player_die() 方法中生成墓碑 (第 442 行后)

```python
def on_player_die(self, player_id, attacker_id=None, damage_cause=None):
    """
    玩家死亡处理

    Args:
        player_id (str): 玩家ID
        attacker_id (str): 攻击者ID(可选)
        damage_cause (str): 伤害原因(可选)
    """
    # ... 原有代码 ...

    # 播放击杀音效
    if attacker_id and self.ornament_system:
        # 获取玩家死亡位置
        comp = self.comp_factory.CreatePos(player_id)
        death_pos = comp.GetPos()
        self.ornament_system.play_kill_sound(attacker_id, player_id, death_pos)

        # 生成墓碑装饰 <-- 添加以下4行
        comp_dim = self.comp_factory.CreateDimension(player_id)
        dimension = comp_dim.GetPlayerDimensionId()
        if death_pos and dimension:
            self.ornament_system.spawn_death_meme(player_id, death_pos, dimension)

    # 获取玩家队伍
    team_id = self.team_module.get_player_team(player_id) if self.team_module else None
    # ... 后续代码 ...
```

---

### 步骤 3: (可选) 在资源生成器中集成墓碑展示

如果你已经实现了 `GeneratorPreset` 系统，可以在玩家拾取钻石/绿宝石时触发墓碑展示。

在生成器的 `on_item_pickup` 事件处理中:

```python
def on_item_pickup(self, player_id, item_name):
    """
    玩家拾取物品事件

    Args:
        player_id (str): 玩家ID
        item_name (str): 物品名称 (minecraft:diamond / minecraft:emerald)
    """
    # 检查是否为钻石或绿宝石
    if item_name in ['minecraft:diamond', 'minecraft:emerald']:
        # 获取生成器位置
        generator_pos = self.get_generator_position()
        dimension = self.dimension_id

        # 获取装扮系统
        ornament_system = self.game_system.ornament_system
        if ornament_system and ornament_system.meme_ornament_system:
            # 在生成器上方生成墓碑展示
            ornament_system.meme_ornament_system.spawn_meme_at_generator(
                player_id,
                generator_pos,
                dimension
            )
```

---

## RoomManagementSystem 中获取玩家装备的墓碑ID

在 `RoomManagementSystem` 中，如果需要获取玩家装备的墓碑ID:

```python
def get_player_equipped_meme(self, player_id):
    """
    获取玩家装备的墓碑ID

    Args:
        player_id (str): 玩家ID

    Returns:
        str: 墓碑ID，未装备返回None
    """
    # 通过BedWarsGameSystem获取OrnamentSystem
    if not self.bedwars_game_system:
        return None

    ornament_system = self.bedwars_game_system.ornament_system
    if not ornament_system:
        return None

    # 获取玩家装备的墓碑ID
    # 墓碑装扮类型为 'meme'
    meme_id = ornament_system.get_player_ornament(player_id, 'meme')

    return meme_id

def set_player_equipped_meme(self, player_id, meme_id):
    """
    设置玩家装备的墓碑

    Args:
        player_id (str): 玩家ID
        meme_id (str): 墓碑ID (smile/black/embrace/huaji/angry/qm/ec/anubis)
    """
    if not self.bedwars_game_system:
        return

    ornament_system = self.bedwars_game_system.ornament_system
    if not ornament_system:
        return

    # 设置玩家装备的墓碑
    ornament_system.set_player_ornament(player_id, 'meme', meme_id)
    print("[INFO] 玩家 {} 装备墓碑: {}".format(player_id, meme_id))
```

---

## 配置文件说明

墓碑配置文件位于: `Script_NeteaseMod/config/ornaments/meme.json`

### 配置项说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | 墓碑唯一标识符 |
| `name` | string | 墓碑显示名称 (中文) |
| `variant` | int | 实体variant值 (决定外观) |
| `entity_type` | string | 实体类型标识符 |
| `duration` | float | 墓碑存在时长(秒) |
| `display_on_death` | bool | 是否在死亡时显示 |
| `display_on_resource_collect` | bool | 是否在收集资源时显示 |
| `description` | string | 墓碑描述 |

### 可用墓碑列表

1. `smile` - 微笑 (variant: 1)
2. `black` - 黑脸 (variant: 2)
3. `embrace` - 尴尬 (variant: 3)
4. `huaji` - 滑稽 (variant: 4)
5. `angry` - 狂怒 (variant: 5)
6. `qm` - 问号 (variant: 6)
7. `ec` - EC (variant: 7)
8. `anubis` - 阿努比斯 (variant: 8)

---

## 测试验证

### 1. 测试死亡墓碑生成

```python
# 在游戏中让玩家死亡，观察是否生成墓碑实体
# 墓碑应在5秒后自动消失
```

### 2. 测试配置加载

```python
# 查看日志输出
[INFO] [MemeOrnamentSystem] 成功加载 8 个墓碑配置
```

### 3. 测试玩家装备墓碑

```python
# 设置玩家装备墓碑
room_system.set_player_equipped_meme(player_id, 'huaji')

# 获取玩家装备的墓碑
meme_id = room_system.get_player_equipped_meme(player_id)
print("玩家装备的墓碑: {}".format(meme_id))  # 输出: huaji
```

---

## 常见问题

### Q1: 墓碑不显示？

**检查项:**
1. 玩家是否装备了墓碑 (使用 `get_player_ornament(player_id, 'meme')` 检查)
2. 配置文件中 `display_on_death` 是否为 `true`
3. 实体类型 `ecbedwars:meme` 是否已在行为包中定义
4. 查看日志是否有错误信息

### Q2: 墓碑不会自动消失？

**检查项:**
1. `OrnamentSystem.update()` 是否在 `BedWarsGameSystem.Update()` 中被调用
2. `MemeOrnamentSystem.update()` 是否在 `OrnamentSystem.update()` 中被调用
3. 查看日志确认定时器是否正常运行

### Q3: 配置文件加载失败？

**检查项:**
1. 配置文件路径是否正确
2. JSON 格式是否正确 (使用 JSON 验证器检查)
3. 文件编码是否为 UTF-8

---

## 完成标志

集成完成后，你应该能够:

1. ✅ 配置文件成功加载，显示 8 个墓碑
2. ✅ 玩家死亡时在死亡位置生成墓碑实体
3. ✅ 墓碑实体在 5 秒后自动消失
4. ✅ 可以通过 API 获取/设置玩家装备的墓碑
5. ✅ 未装备墓碑的玩家死亡时不生成墓碑

---

**最后更新:** 2025-11-02
**版本:** 1.0.0
