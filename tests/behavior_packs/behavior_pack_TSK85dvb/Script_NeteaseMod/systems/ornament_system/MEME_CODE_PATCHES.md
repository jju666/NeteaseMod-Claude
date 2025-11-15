# 墓碑装饰系统 - 代码补丁

本文档包含需要应用到现有代码的具体补丁。

---

## 补丁 1: OrnamentSystem.py - 添加墓碑系统属性

**文件:** `Script_NeteaseMod/systems/ornament_system/OrnamentSystem.py`

**位置:** `__init__` 方法，第 42 行附近

**查找代码:**
```python
        self.bed_destroy_effect_manager = None  # 床破坏特效管理器
        self.shop_npc_skin_manager = None  # 商店NPC皮肤管理器
        self.ornament_config = {}  # 装扮配置
```

**替换为:**
```python
        self.bed_destroy_effect_manager = None  # 床破坏特效管理器
        self.shop_npc_skin_manager = None  # 商店NPC皮肤管理器
        self.meme_ornament_system = None  # 墓碑装饰管理器
        self.ornament_config = {}  # 装扮配置
```

---

## 补丁 2: OrnamentSystem.py - 初始化墓碑系统

**文件:** `Script_NeteaseMod/systems/ornament_system/OrnamentSystem.py`

**位置:** `initialize()` 方法，第 84 行附近

**查找代码:**
```python
            # 初始化商店NPC皮肤管理器
            from ornament.ShopNPCSkinManager import ShopNPCSkinManager
            self.shop_npc_skin_manager = ShopNPCSkinManager(self)
            self.shop_npc_skin_manager.initialize()

            # 加载装扮配置
            self._load_ornament_config()
```

**替换为:**
```python
            # 初始化商店NPC皮肤管理器
            from ornament.ShopNPCSkinManager import ShopNPCSkinManager
            self.shop_npc_skin_manager = ShopNPCSkinManager(self)
            self.shop_npc_skin_manager.initialize()

            # 初始化墓碑装饰管理器
            from meme.MemeOrnamentSystem import MemeOrnamentSystem
            self.meme_ornament_system = MemeOrnamentSystem(self)
            self.meme_ornament_system.initialize()

            # 加载装扮配置
            self._load_ornament_config()
```

---

## 补丁 3: OrnamentSystem.py - 清理墓碑系统

**文件:** `Script_NeteaseMod/systems/ornament_system/OrnamentSystem.py`

**位置:** `cleanup()` 方法，第 118 行附近

**查找代码:**
```python
            if self.shop_npc_skin_manager:
                self.shop_npc_skin_manager.cleanup()

            self.player_ornaments = {}
```

**替换为:**
```python
            if self.shop_npc_skin_manager:
                self.shop_npc_skin_manager.cleanup()

            if self.meme_ornament_system:
                self.meme_ornament_system.cleanup()

            self.player_ornaments = {}
```

---

## 补丁 4: OrnamentSystem.py - 更新墓碑系统

**文件:** `Script_NeteaseMod/systems/ornament_system/OrnamentSystem.py`

**位置:** `update()` 方法，第 486 行附近

**查找代码:**
```python
    def update(self):
        """
        更新饰品系统 - 需要在游戏主循环中调用
        主要用于更新特效定时器
        """
        if self.victory_dance_manager:
            self.victory_dance_manager.update()

        # 床破坏特效管理器使用同一个定时器,不需要单独update
```

**替换为:**
```python
    def update(self):
        """
        更新饰品系统 - 需要在游戏主循环中调用
        主要用于更新特效定时器
        """
        if self.victory_dance_manager:
            self.victory_dance_manager.update()

        # 更新墓碑系统定时器
        if self.meme_ornament_system:
            self.meme_ornament_system.update()

        # 床破坏特效管理器使用同一个定时器,不需要单独update
```

---

## 补丁 5: OrnamentSystem.py - 添加墓碑生成接口

**文件:** `Script_NeteaseMod/systems/ornament_system/OrnamentSystem.py`

**位置:** 文件末尾 (第 549 行后)

**添加以下代码:**
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

## 补丁 6: BedWarsGameSystem.py - 生成墓碑

**文件:** `Script_NeteaseMod/systems/BedWarsGameSystem.py`

**位置:** `on_player_die()` 方法，第 442 行附近

**查找代码:**
```python
        # 播放击杀音效
        if attacker_id and self.ornament_system:
            # 获取玩家死亡位置
            comp = self.comp_factory.CreatePos(player_id)
            death_pos = comp.GetPos()
            self.ornament_system.play_kill_sound(attacker_id, player_id, death_pos)

        # 获取玩家队伍
        team_id = self.team_module.get_player_team(player_id) if self.team_module else None
```

**替换为:**
```python
        # 播放击杀音效
        if attacker_id and self.ornament_system:
            # 获取玩家死亡位置
            comp = self.comp_factory.CreatePos(player_id)
            death_pos = comp.GetPos()
            self.ornament_system.play_kill_sound(attacker_id, player_id, death_pos)

            # 生成墓碑装饰
            comp_dim = self.comp_factory.CreateDimension(player_id)
            dimension = comp_dim.GetPlayerDimensionId()
            if death_pos and dimension is not None:
                self.ornament_system.spawn_death_meme(player_id, death_pos, dimension)

        # 获取玩家队伍
        team_id = self.team_module.get_player_team(player_id) if self.team_module else None
```

---

## 应用补丁的步骤

### 方式 1: 手动应用

1. 打开对应的文件
2. 找到"查找代码"中的内容
3. 用"替换为"的内容替换
4. 保存文件

### 方式 2: 使用代码编辑器

在支持搜索替换的编辑器 (如 VSCode) 中:

1. 打开对应文件
2. 使用 Ctrl+F 搜索"查找代码"
3. 确认位置正确
4. 手动修改为"替换为"的内容

---

## 验证补丁是否应用成功

应用所有补丁后，运行以下检查:

### 1. 语法检查

```bash
python -m py_compile Script_NeteaseMod/systems/ornament_system/OrnamentSystem.py
python -m py_compile Script_NeteaseMod/systems/BedWarsGameSystem.py
python -m py_compile Script_NeteaseMod/systems/ornament_system/meme/MemeOrnamentSystem.py
```

如果没有输出，说明语法正确。

### 2. 检查导入

在 Python 环境中测试导入:

```python
# 测试配置文件是否存在
import os
config_path = r"D:\EcWork\NetEaseMapECBedWars\behavior_packs\behavior_pack_TSK85dvb\Script_NeteaseMod\config\ornaments\meme.json"
print("配置文件存在:", os.path.exists(config_path))

# 测试 JSON 格式
import json
with open(config_path, 'r') as f:
    data = json.load(f)
    print("墓碑数量:", len(data['meme_ornaments']))
```

预期输出:
```
配置文件存在: True
墓碑数量: 8
```

### 3. 日志检查

启动游戏服务器后，查看日志应包含:

```
[INFO] [OrnamentSystem] 初始化完成
[INFO] [MemeOrnamentSystem] 初始化完成
[INFO] [MemeOrnamentSystem] 尝试加载配置: ...
[INFO] [MemeOrnamentSystem] 成功加载 8 个墓碑配置
[INFO] [MemeOrnamentSystem] 系统初始化成功，已加载 8 个墓碑
[INFO] [OrnamentSystem] 系统初始化成功
```

---

## 回滚补丁

如果需要回滚，使用版本控制系统 (Git):

```bash
# 查看修改
git diff

# 撤销修改
git checkout -- Script_NeteaseMod/systems/ornament_system/OrnamentSystem.py
git checkout -- Script_NeteaseMod/systems/BedWarsGameSystem.py
```

或者手动还原为原始代码 (删除添加的行)。

---

**补丁版本:** 1.0.0
**创建日期:** 2025-11-02
**兼容版本:** Python 2.7
