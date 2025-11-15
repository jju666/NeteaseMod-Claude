# CameraPreviewHelper 使用示例

## 概述

CameraPreviewHelper 提供地图预览摄像机运镜功能，在游戏开始前为玩家呈现地图的螺旋环绕视角。

## 运动原理

### 螺旋轨迹

相机围绕地图中心点进行螺旋上升的圆周运动：

```
半径: r = 初始半径 + 增长率 * tick数
角度: θ = 角速度 * tick数
X坐标: x = center_x + r * cos(θ)
Z坐标: z = center_z + r * sin(θ)
Y坐标: y = center_y + 高度偏移
```

### 默认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 初始半径 | 10.0格 | 起始距离 |
| 角速度 | 0.005弧度/tick | 旋转速度 |
| 半径增长率 | 0.1格/tick | 每tick增加的半径 |
| 高度偏移 | 5.0格 | 相对中心点的高度 |

### 运动特性

- **完整旋转一圈**: 约63秒（角速度0.005）
- **10秒内半径扩展**: 从10格到30格
- **视角**: 始终朝向地图中心点

## 基本使用

### 1. 在System中初始化

```python
from systems.util import CameraPreviewHelper

class MyGameSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MyGameSystem, self).__init__(namespace, systemName)
        # 初始化地图预览工具
        self.camera_preview = CameraPreviewHelper(self)
```

### 2. 启动运镜

#### 基本用法

```python
# 启动运镜（所有玩家）
self.camera_preview.start_preview(center_pos=(0, 100, 0))
```

#### 指定玩家

```python
# 只针对特定玩家启动运镜
player_ids = ['player1', 'player2']
self.camera_preview.start_preview(
    center_pos=(0, 100, 0),
    players=player_ids
)
```

#### 自定义参数

```python
# 自定义运镜参数
self.camera_preview.start_preview(
    center_pos=(100, 65, 100),  # 地图中心点
    radius=15.0,                 # 更大的初始半径
    angular_velocity=0.01,       # 更快的旋转速度（完整旋转约31秒）
    height_offset=10.0           # 更高的视角
)
```

### 3. 停止运镜

```python
# 停止运镜（所有玩家）
self.camera_preview.stop_preview()

# 停止特定玩家的运镜
self.camera_preview.stop_preview(players=['player1', 'player2'])
```

## 实战示例

### 示例1：游戏开始倒计时运镜

```python
class BedWarsStartingState(TimedGamingState):
    def __init__(self, timeout_seconds):
        super(BedWarsStartingState, self).__init__(timeout_seconds)
        # 地图中心点（需要根据实际地图配置）
        self.map_centers = {
            10000: (0, 100, 0),
            10001: (100, 65, 100),
            10002: (50, 80, 50),
        }

    def on_enter(self):
        """进入倒计时状态"""
        super(BedWarsStartingState, self).on_enter()

        # 获取当前地图的中心点
        part = self.get_part()
        center_pos = self.map_centers.get(part.game_dimension)

        if center_pos:
            # 启动地图预览运镜
            part.camera_preview.start_preview(center_pos=center_pos)
            print("[INFO] 已启动地图预览运镜")
        else:
            print("[WARN] 未找到当前维度的地图中心点配置")

    def on_exit(self):
        """退出倒计时状态"""
        # 停止运镜
        part = self.get_part()
        part.camera_preview.stop_preview()
        print("[INFO] 已停止地图预览运镜")

        super(BedWarsStartingState, self).on_exit()
```

### 示例2：地图投票预览

```python
class MapVoteInstance(object):
    def preview_map(self, map_id):
        """预览特定地图"""
        map_config = self.get_map_config(map_id)

        # 获取所有投票玩家
        voters = self.get_voting_players()
        player_ids = [p.GetPlayerId() for p in voters]

        # 启动运镜（仅投票玩家）
        self.system.camera_preview.start_preview(
            center_pos=map_config['center_pos'],
            players=player_ids,
            radius=map_config.get('preview_radius', 10.0)
        )

    def end_preview(self):
        """结束地图预览"""
        voters = self.get_voting_players()
        player_ids = [p.GetPlayerId() for p in voters]

        self.system.camera_preview.stop_preview(players=player_ids)
```

### 示例3：不同地图的自适应参数

```python
class MapConfigLoader(object):
    """地图配置加载器"""

    # 地图预览配置
    MAP_PREVIEW_CONFIGS = {
        # 小型地图：更小的半径，更快的旋转
        'small_map_10000': {
            'center_pos': (0, 100, 0),
            'radius': 8.0,
            'angular_velocity': 0.008,  # 更快
            'height_offset': 3.0,        # 更低
        },
        # 中型地图：默认参数
        'medium_map_10001': {
            'center_pos': (100, 65, 100),
            'radius': 10.0,
            'angular_velocity': 0.005,
            'height_offset': 5.0,
        },
        # 大型地图：更大的半径，更慢的旋转
        'large_map_10002': {
            'center_pos': (200, 80, 200),
            'radius': 20.0,
            'angular_velocity': 0.003,  # 更慢
            'height_offset': 15.0,       # 更高
        },
    }

    def start_map_preview(self, system, map_key):
        """根据地图配置启动预览"""
        config = self.MAP_PREVIEW_CONFIGS.get(map_key)

        if config:
            system.camera_preview.start_preview(
                center_pos=config['center_pos'],
                radius=config['radius'],
                angular_velocity=config['angular_velocity'],
                height_offset=config['height_offset']
            )
        else:
            print("[WARN] 未找到地图 {} 的预览配置".format(map_key))
```

### 示例4：完整的游戏流程集成

```python
class RoomManagementSystem(GamingStateSystem):
    def __init__(self, namespace, systemName):
        super(RoomManagementSystem, self).__init__(namespace, systemName)
        # 初始化运镜工具
        self.camera_preview = CameraPreviewHelper(self)

        # 地图中心点配置
        self.map_centers = {}
        self._load_map_centers()

    def _load_map_centers(self):
        """从配置文件加载地图中心点"""
        # TODO: 从JSON配置文件加载
        self.map_centers = {
            10000: (0, 100, 0),
            10001: (100, 65, 100),
            # 更多地图...
        }

    def on_game_starting(self):
        """游戏开始倒计时"""
        # 获取当前游戏维度
        center_pos = self.map_centers.get(self.game_dimension)

        if center_pos:
            # 启动运镜
            self.camera_preview.start_preview(center_pos=center_pos)

            # 10秒后自动停止（倒计时结束）
            self.add_timer(10.0, lambda: self.camera_preview.stop_preview(), False)
        else:
            print("[WARN] 未找到维度 {} 的地图中心点".format(self.game_dimension))
```

## 全局工具函数

如果不想创建Helper实例，可以使用全局工具函数：

```python
from systems.util.CameraPreviewHelper import start_camera_preview, stop_camera_preview

# 启动运镜
start_camera_preview(self, (0, 100, 0))

# 自定义参数
start_camera_preview(
    self,
    center_pos=(0, 100, 0),
    radius=15.0,
    angular_velocity=0.01
)

# 停止运镜
stop_camera_preview(self)

# 停止特定玩家
stop_camera_preview(self, players=['player1'])
```

## 参数调优

### 角速度（angular_velocity）

影响旋转速度：

```python
# 很慢（完整旋转约126秒）
angular_velocity = 0.0025

# 默认（完整旋转约63秒）
angular_velocity = 0.005

# 快速（完整旋转约31秒）
angular_velocity = 0.01

# 很快（完整旋转约13秒）
angular_velocity = 0.025
```

### 初始半径（radius）

影响起始距离：

```python
# 小半径（近距离观察）
radius = 5.0

# 默认（适中距离）
radius = 10.0

# 大半径（远距离全景）
radius = 20.0
```

### 高度偏移（height_offset）

影响相机高度：

```python
# 低角度（接近地面）
height_offset = 2.0

# 默认（中等高度）
height_offset = 5.0

# 高角度（俯瞰视角）
height_offset = 15.0
```

### 半径增长率

客户端默认为0.1格/tick，不可配置（需修改客户端系统代码）：

```python
# 在CameraPreviewClientSystem中修改
self.radius_growth_rate = 0.2  # 更快扩展
self.radius_growth_rate = 0.05 # 更慢扩展
```

## 配置文件示例

建议创建地图配置文件存储中心点：

```json
// config/map_preview.json
{
    "map_centers": {
        "10000": {
            "center_pos": [0, 100, 0],
            "radius": 10.0,
            "angular_velocity": 0.005,
            "height_offset": 5.0
        },
        "10001": {
            "center_pos": [100, 65, 100],
            "radius": 15.0,
            "angular_velocity": 0.008,
            "height_offset": 10.0
        }
    }
}
```

加载配置：

```python
import json

def load_map_preview_config(self):
    """加载地图预览配置"""
    config_path = "config/map_preview.json"

    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            self.map_centers = data.get('map_centers', {})
            print("[INFO] 已加载地图预览配置")
    except Exception as e:
        print("[ERROR] 加载地图预览配置失败: {}".format(e))
        # 使用默认配置
        self.map_centers = {}
```

## 注意事项

### 1. 地图中心点选择

**重要**：中心点坐标应该：
- 位于地图的几何中心
- Y坐标在地形之上（避免穿模）
- 避开建筑物和障碍物

**错误示例**：
```python
# ❌ 中心点在地下
center_pos = (0, 50, 0)  # 可能在地形内部

# ❌ 中心点太低
center_pos = (0, 60, 0)  # 相机可能看到地形穿模
```

**正确示例**：
```python
# ✅ 中心点在空中
center_pos = (0, 100, 0)

# ✅ 根据地图实际高度调整
center_pos = (0, 120, 0)  # 高层建筑地图
```

### 2. 时机控制

**启动时机**：
- 游戏开始倒计时开始时
- 地图投票预览时

**停止时机**：
- 倒计时结束前（给玩家恢复控制权的时间）
- 地图投票结束时

```python
# 推荐：倒计时10秒，运镜9.5秒后停止
def on_enter(self):
    self.camera_preview.start_preview(center_pos)
    self.add_timer(9.5, lambda: self.camera_preview.stop_preview(), False)
```

### 3. 玩家体验

**避免眩晕**：
- 不要使用过快的角速度（> 0.02）
- 不要使用过大的半径增长率（> 0.2）

**确保流畅**：
- 服务端及时停止运镜
- 客户端Update方法性能优化

### 4. 多维度支持

每个地图维度需要独立配置中心点：

```python
self.map_centers = {
    10000: (0, 100, 0),      # 地图1
    10001: (100, 65, 100),   # 地图2
    10002: (50, 80, 50),     # 地图3
    # ...
}

# 根据维度获取中心点
center_pos = self.map_centers.get(current_dimension)
if center_pos:
    self.camera_preview.start_preview(center_pos=center_pos)
```

## 故障排查

### 问题1：运镜未启动

**症状**：玩家看不到运镜效果

**排查**：
1. 检查客户端系统是否注册（modConfig.py）
2. 确认center_pos参数是否正确传递
3. 查看客户端日志是否有错误

### 问题2：相机运动卡顿

**症状**：运镜画面不流畅

**原因**：
- 客户端帧率过低
- 服务端网络延迟

**解决**：
- 优化客户端渲染性能
- 降低角速度和半径增长率

### 问题3：运镜未停止

**症状**：游戏开始后相机仍然锁定

**排查**：
1. 确认stop_preview()是否被调用
2. 检查客户端是否收到StopCameraPreview事件
3. 验证UnLockCamera()是否执行

## 性能考量

| 指标 | 值 | 说明 |
|------|-----|------|
| 更新频率 | ~20 tick/秒 | 跟随游戏主循环 |
| 计算复杂度 | O(1) | 每帧固定计算量 |
| 内存占用 | < 1KB | 仅存储少量状态变量 |
| 网络流量 | 极低 | 仅发送一次启动事件 |

## 扩展建议

### 1. 多样化轨迹

```python
# 定半径圆周（不扩展）
radius_growth_rate = 0.0

# 椭圆轨迹
x = center_x + radius_x * cos(angle)
z = center_z + radius_z * sin(angle)

# 波浪式运动
y = center_y + height_offset + amplitude * sin(angle)
```

### 2. 缓动函数

```python
# 平滑启动/停止
def ease_in_out(t):
    return t * t * (3.0 - 2.0 * t)

alpha = ease_in_out(elapsed_time / transition_time)
```

### 3. 多相机视角

```python
# 每隔一段时间切换到不同视角
angles = [0, math.pi/4, math.pi/2, 3*math.pi/4]
current_angle = angles[int(tick / 100) % len(angles)]
```
