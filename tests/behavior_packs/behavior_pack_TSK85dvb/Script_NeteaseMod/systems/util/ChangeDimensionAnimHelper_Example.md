# ChangeDimensionAnimHelper 使用示例

## 概述

ChangeDimensionAnimHelper 提供统一的维度切换动画触发接口，在玩家传送到不同维度时提供平滑的视觉过渡效果。

## 基本使用

### 1. 在System中初始化

```python
from systems.util import ChangeDimensionAnimHelper

class MyGameSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MyGameSystem, self).__init__(namespace, systemName)
        # 初始化维度切换动画工具
        self.change_dim_anim = ChangeDimensionAnimHelper(self)
```

### 2. 触发动画

#### 方式1：广播所有玩家

```python
# 触发动画
self.change_dim_anim.trigger_animation()

# 延迟0.8秒后执行维度切换
self.add_timer(0.8, lambda: self._switch_dimension(), False)
```

#### 方式2：指定玩家

```python
# 只针对特定玩家触发动画
player_ids = ['player1', 'player2', 'player3']
self.change_dim_anim.trigger_animation(players=player_ids)

# 延迟0.8秒后切换
self.add_timer(0.8, lambda: self._switch_players(player_ids), False)
```

### 3. 便捷方法（自动延迟切换）

```python
# 准备玩家位置映射
positions = {
    'player1': (100, 65, 100),
    'player2': (110, 65, 110),
    'player3': (120, 65, 120),
}

# 一行代码触发动画+自动切换
self.change_dim_anim.trigger_and_switch(
    dimension=10000,  # 目标维度ID
    positions_dict=positions,
    delay=0.8  # 延迟时间（秒）
)
```

## 实战示例

### 示例1：游戏开始 - 所有玩家进入地图

```python
class StageWaitingState(TimedGamingState):
    def on_countdown_end(self):
        """倒计时结束，传送玩家到游戏地图"""
        # 1. 触发维度切换动画（所有玩家）
        self.get_part().change_dim_anim.trigger_animation()

        # 2. 延迟0.8秒后执行维度切换
        def switch_to_game():
            game_dimension = 10000
            spawn_positions = self._get_team_spawn_positions()

            for player in self.get_all_players():
                player_id = player.GetPlayerId()
                pos = spawn_positions.get(player_id, (0, 100, 0))

                # 传送玩家
                comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
                comp_pos.SetFootPos(pos)

                comp_dim = serverApi.GetEngineCompFactory().CreateDimension(player_id)
                comp_dim.ChangePlayerDimension(game_dimension)

        self.add_timer(0.8, switch_to_game, False)
```

### 示例2：游戏结束 - 玩家返回大厅

```python
class BedWarsEndingState(GamingState):
    def teleport_players_to_lobby(self):
        """游戏结束，传送玩家返回大厅"""
        # 获取在线玩家
        online_players = self.get_part().better_util.get_better_players_list()
        player_ids = [p.GetPlayerId() for p in online_players]

        # 准备位置映射
        lobby_dimension = 20024
        lobby_spawn = (0, 150, 0)
        positions = {pid: lobby_spawn for pid in player_ids}

        # 触发动画并切换（便捷方法）
        self.get_part().change_dim_anim.trigger_and_switch(
            dimension=lobby_dimension,
            positions_dict=positions,
            players=player_ids,
            delay=0.8
        )
```

### 示例3：中途加入 - 单个玩家进入游戏

```python
class BedWarsGameSystem(ServerSystem):
    def on_player_midway_join(self, player_id):
        """玩家中途加入游戏"""
        # 1. 触发动画（仅该玩家）
        self.change_dim_anim.trigger_animation(players=[player_id])

        # 2. 延迟切换
        def teleport_player():
            team = self._find_least_populated_team()
            spawn_pos = team.get_spawn_position()
            game_dim = self.game_dimension

            comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
            comp_pos.SetFootPos(spawn_pos)

            comp_dim = serverApi.GetEngineCompFactory().CreateDimension(player_id)
            comp_dim.ChangePlayerDimension(game_dim)

        self.add_timer(0.8, teleport_player, False)
```

### 示例4：观战模式 - 玩家淘汰后观战

```python
class BedWarsGameSystem(ServerSystem):
    def _eliminate_player(self, player_id):
        """淘汰玩家，进入观战模式"""
        # 如果需要切换到观战维度
        if self.spectator_dimension != self.game_dimension:
            # 触发动画
            self.change_dim_anim.trigger_animation(players=[player_id])

            # 延迟切换到观战维度
            def switch_to_spectator():
                spectator_pos = (0, 100, 0)

                comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
                comp_pos.SetFootPos(spectator_pos)

                comp_dim = serverApi.GetEngineCompFactory().CreateDimension(player_id)
                comp_dim.ChangePlayerDimension(self.spectator_dimension)

                # 设置观战模式
                comp_game = serverApi.GetEngineCompFactory().CreateGame(player_id)
                comp_game.SetGameMode(3)  # 观战模式

            self.add_timer(0.8, switch_to_spectator, False)
        else:
            # 同维度，直接设置观战模式
            comp_game = serverApi.GetEngineCompFactory().CreateGame(player_id)
            comp_game.SetGameMode(3)
```

### 示例5：地图投票 - 切换到预览维度

```python
class MapVoteInstance(object):
    def preview_map(self, player_id, map_config):
        """预览地图（传送玩家到预览维度）"""
        # 触发动画
        helper = ChangeDimensionAnimHelper(self.system)
        helper.trigger_animation(players=[player_id])

        # 延迟切换到预览维度
        def switch_to_preview():
            preview_dim = map_config['preview_dimension']
            preview_pos = map_config['preview_spawn']

            comp_pos = serverApi.GetEngineCompFactory().CreatePos(player_id)
            comp_pos.SetFootPos(preview_pos)

            comp_dim = serverApi.GetEngineCompFactory().CreateDimension(player_id)
            comp_dim.ChangePlayerDimension(preview_dim)

        self.system.add_timer(0.8, switch_to_preview, False)
```

## 时序说明

### 动画流程

```
t=0.0s: 触发动画 (trigger_animation)
        ↓
t=0.0s: 客户端收到事件
        关闭非HUD界面
        开始淡入动画
        ↓
t=0.5s: 淡入动画完成
        启用Vignette遮罩
        屏幕完全遮挡
        ↓
t=0.6-0.8s: 服务端执行维度切换
        ↓
t=0.7-0.9s: 引擎切换维度
        加载新维度资源
        ↓
t=0.8-1.0s: 新维度加载完成
        开始淡出动画
        ↓
t=1.8-2.0s: 淡出动画完成
        禁用Vignette
        玩家看到新场景
```

### 推荐延迟时间

| 网络环境 | 推荐延迟 | 说明 |
|---------|---------|------|
| 本地测试 | 0.6秒 | 网络延迟可忽略 |
| 局域网 | 0.8秒 | 一般网络环境 |
| 公网服务器 | 1.0秒 | 高延迟环境，留缓冲 |

```python
# 本地测试
self.change_dim_anim.trigger_and_switch(dim, pos, delay=0.6)

# 局域网（推荐）
self.change_dim_anim.trigger_and_switch(dim, pos, delay=0.8)

# 公网服务器
self.change_dim_anim.trigger_and_switch(dim, pos, delay=1.0)
```

## 全局工具函数

如果不想创建Helper实例，可以使用全局工具函数：

```python
from systems.util.ChangeDimensionAnimHelper import trigger_dimension_animation

# 触发动画（所有玩家）
trigger_dimension_animation(self)

# 触发动画（指定玩家）
trigger_dimension_animation(self, players=['player1', 'player2'])
```

## 注意事项

### 1. 时序同步

**错误示例**：
```python
# ❌ 动画还没播放完就切换维度
self.change_dim_anim.trigger_animation()
self._switch_dimension()  # 立即切换，玩家会看到跳跃
```

**正确示例**：
```python
# ✅ 等待淡入动画完成
self.change_dim_anim.trigger_animation()
self.add_timer(0.8, lambda: self._switch_dimension(), False)
```

### 2. UI栈管理

系统会自动关闭非HUD界面，防止UI冲突。如果有特殊UI需要保留，需要手动处理。

### 3. 网络延迟

在高延迟环境下，建议增加延迟时间，确保所有客户端都完成动画：

```python
# 自适应延迟（根据玩家ping值）
max_ping = max([get_player_ping(p) for p in players])
delay = 0.6 + max_ping / 1000.0  # 基础0.6秒 + ping延迟
self.change_dim_anim.trigger_and_switch(dim, pos, delay=delay)
```

### 4. 频繁切换

短时间内多次切换维度可能导致动画混乱，建议添加冷却时间：

```python
class MySystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MySystem, self).__init__(namespace, systemName)
        self.last_switch_time = 0
        self.switch_cooldown = 2.0  # 冷却2秒

    def switch_dimension_with_cooldown(self):
        import time
        now = time.time()

        if now - self.last_switch_time < self.switch_cooldown:
            print("[WARN] 维度切换冷却中，跳过")
            return

        self.last_switch_time = now
        self.change_dim_anim.trigger_animation()
        # ...
```

## 故障排查

### 问题1：动画不播放

**可能原因**：
1. 客户端系统未正确注册
2. 事件监听未初始化

**解决方案**：
```python
# 检查modConfig.py中是否包含：
CLIENT_SYSTEMS = [
    # ...
    ("ChangeDimensionClientSystem", "Script_NeteaseMod.systems.ChangeDimensionClientSystem.ChangeDimensionClientSystem"),
]
```

### 问题2：屏幕闪烁

**可能原因**：
延迟时间太短，维度切换发生在动画播放前

**解决方案**：
```python
# 增加延迟时间
self.change_dim_anim.trigger_and_switch(dim, pos, delay=1.0)  # 从0.6改为1.0
```

### 问题3：遮罩不消失

**可能原因**：
Vignette效果未正确清理

**解决方案**：
```python
# 手动清理Vignette（客户端执行）
import mod.client.extraClientApi as clientApi
comp_post = clientApi.GetEngineCompFactory().CreatePostProcess(clientApi.GetLevelId())
comp_post.SetEnableVignette(False)
```

## 完整示例：房间系统集成

```python
class RoomManagementSystem(GamingStateSystem):
    def __init__(self, namespace, systemName):
        super(RoomManagementSystem, self).__init__(namespace, systemName)
        # 初始化维度切换动画工具
        self.change_dim_anim = ChangeDimensionAnimHelper(self)

    def start_game(self):
        """游戏开始，传送所有玩家到游戏地图"""
        # 获取所有玩家
        players = self.get_all_better_players()
        positions = {}

        # 分配出生点
        for player in players:
            player_id = player.GetPlayerId()
            team = self._get_player_team(player_id)
            spawn_pos = team.get_spawn_position()
            positions[player_id] = spawn_pos

        # 触发动画并切换
        self.change_dim_anim.trigger_and_switch(
            dimension=self.game_dimension,
            positions_dict=positions,
            delay=0.8
        )

        # 切换后的逻辑（定时器会自动执行）
        def on_switch_complete():
            # 初始化游戏逻辑
            self._init_game_logic()
            # 发放初始装备
            self._give_starter_kit()

        self.add_timer(2.0, on_switch_complete, False)  # 动画+切换总耗时约2秒
```

## 性能优化

### 批量切换

```python
# 分批次切换，避免同时切换大量玩家
def batch_switch_players(self, players, batch_size=5):
    """分批切换玩家"""
    for i in range(0, len(players), batch_size):
        batch = players[i:i+batch_size]
        player_ids = [p.GetPlayerId() for p in batch]

        # 触发动画
        self.change_dim_anim.trigger_animation(players=player_ids)

        # 延迟切换
        delay = 0.8 + i * 0.2  # 每批次间隔0.2秒
        # ...
```
