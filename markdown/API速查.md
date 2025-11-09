# API速查手册

> **网易我的世界MODSDK常用API快速参考**
>
> 复制即用的API代码片段

---

## 🎯 使用说明

本文档收录**最常用的MODSDK API**，按功能分类，提供**可直接复制的代码片段**。

**完整API文档**: 查阅[官方MODSDK Wiki](https://github.com/EaseCation/netease-modsdk-wiki)

---

## 📦 一、玩家管理API

### 1.1 获取玩家信息

```python
# 获取所有在线玩家
players = self.gameComp.GetAllPlayers()

# 获取玩家名称
nameComp = serverApi.GetEngineCompFactory().CreateName(levelId)
playerName = nameComp.GetName(playerId)

# 获取本地玩家ID（客户端）
localPlayerId = clientApi.GetLocalPlayerId()
```

### 1.2 玩家位置操作

```python
# 创建位置组件
posComp = serverApi.GetEngineCompFactory().CreatePos(levelId)

# 获取玩家位置
pos = posComp.GetPos(playerId)  # 返回: (x, y, z)

# 设置玩家位置（传送）
posComp.SetPos(playerId, (100.5, 64.0, 200.5))

# 获取玩家朝向
rot = posComp.GetRot(playerId)  # 返回: (pitch, yaw)

# 设置玩家朝向
posComp.SetRot(playerId, (0, 90))  # (俯仰角, 偏航角)

# 获取玩家脚底方块
footPos = posComp.GetFootPos(playerId)
```

### 1.3 玩家属性操作

```python
# 创建属性组件
attrComp = serverApi.GetEngineCompFactory().CreateAttr(levelId)

# 获取生命值
health = attrComp.GetAttr(playerId, serverApi.AttrType.HEALTH)

# 设置生命值
attrComp.SetAttr(playerId, serverApi.AttrType.HEALTH, 20)

# 获取最大生命值
maxHealth = attrComp.GetAttr(playerId, serverApi.AttrType.MAX_HEALTH)

# 常用属性类型
"""
serverApi.AttrType.HEALTH        # 生命值
serverApi.AttrType.MAX_HEALTH    # 最大生命值
serverApi.AttrType.HUNGER        # 饥饿值
serverApi.AttrType.ABSORPTION    # 伤害吸收
serverApi.AttrType.ARMOR         # 护甲值
serverApi.AttrType.ATTACK        # 攻击力
serverApi.AttrType.SPEED         # 移动速度
"""
```

### 1.4 玩家游戏模式

```python
# 创建游戏模式组件
gameModeComp = serverApi.GetEngineCompFactory().CreateGameMode(levelId)

# 获取游戏模式
gameMode = gameModeComp.GetGameMode(playerId)

# 设置游戏模式
gameModeComp.SetGameMode(playerId, 1)

# 游戏模式常量
"""
0 = 生存模式
1 = 创造模式
2 = 冒险模式
3 = 旁观模式
"""
```

---

## 🎒 二、物品管理API

### 2.1 给予物品

```python
# 创建物品组件
itemComp = serverApi.GetEngineCompFactory().CreateItem(levelId)

# 给予物品到背包
itemDict = {
    'itemName': 'minecraft:diamond_sword',
    'count': 1,
    'auxValue': 0,
    'enchantData': [
        (0, 5),   # 锋利5 (enchant_id, level)
        (9, 2)    # 耐久2
    ]
}
itemComp.SpawnItemToPlayerInv(itemDict, playerId, 0)

# 给予物品到指定槽位
"""
槽位编号:
0-8   快捷栏
9-35  主背包
36    副手
"""
```

### 2.2 获取玩家物品

```python
# 获取主手物品
mainHandItem = itemComp.GetPlayerItem(playerId, serverApi.GetMinecraftEnum().ItemPosType.CARRIED, True)

# 获取副手物品
offHandItem = itemComp.GetPlayerItem(playerId, serverApi.GetMinecraftEnum().ItemPosType.OFFHAND, True)

# 获取背包指定槽位物品
slotItem = itemComp.GetPlayerItem(playerId, serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, slotId, True)

# 返回格式: {'itemName': str, 'count': int, 'auxValue': int, ...}
```

### 2.3 移除物品

```python
# 移除指定数量物品
itemComp.RemoveItemFromInv(playerId, 'minecraft:diamond', 10)

# 清空背包指定槽位
itemComp.SetInvItemNum(playerId, slotId, 0)
```

### 2.4 物品附魔

```python
# 常用附魔ID
"""
0  = 锋利 (Sharpness)
1  = 击退 (Knockback)
2  = 火焰附加 (Fire Aspect)
3  = 抢夺 (Looting)
4  = 保护 (Protection)
5  = 火焰保护 (Fire Protection)
9  = 耐久 (Unbreaking)
16 = 效率 (Efficiency)
17 = 精准采集 (Silk Touch)
19 = 力量 (Power)
20 = 冲击 (Punch)
32 = 经验修补 (Mending)
"""

# 应用附魔示例
enchantedItem = {
    'itemName': 'minecraft:diamond_pickaxe',
    'count': 1,
    'enchantData': [
        (9, 3),   # 耐久3
        (16, 5),  # 效率5
        (32, 1)   # 经验修补
    ]
}
```

---

## 💬 三、消息与UI API

### 3.1 发送聊天消息

```python
# 创建消息组件
msgComp = serverApi.GetEngineCompFactory().CreateMsg(levelId)

# 发送消息给指定玩家
msgComp.NotifyOneMessage(playerId, "欢迎来到服务器！", "§a")

# 发送消息给所有玩家
for player in self.gameComp.GetAllPlayers():
    msgComp.NotifyOneMessage(player, "全服公告", "§e")

# 颜色代码
"""
§0 = 黑色    §1 = 深蓝    §2 = 深绿    §3 = 深青
§4 = 深红    §5 = 紫色    §6 = 金色    §7 = 灰色
§8 = 深灰    §9 = 蓝色    §a = 绿色    §b = 青色
§c = 红色    §d = 粉色    §e = 黄色    §f = 白色
§l = 粗体    §o = 斜体    §r = 重置
"""
```

### 3.2 ActionBar消息

```python
# 显示ActionBar（屏幕下方）
msgComp.NotifyOneMessage(playerId, "血量: 20/20", "§c", msgType=1)

# msgType参数
"""
0 = 聊天栏消息（默认）
1 = ActionBar消息
9 = Title消息
"""
```

### 3.3 Title消息

```python
# 显示Title
msgComp.NotifyOneMessage(playerId, "§e任务完成！", "", msgType=9)
```

---

## 🌍 四、世界管理API

### 4.1 时间与天气

```python
# 创建游戏组件
gameComp = serverApi.GetEngineCompFactory().CreateGame(levelId)

# 设置时间
gameComp.SetTime(6000)  # 0=日出, 6000=正午, 12000=日落, 18000=午夜

# 获取时间
currentTime = gameComp.GetTime()

# 设置天气
gameComp.SetWeather(1, 100)  # (天气类型, 持续tick数)

# 天气类型
"""
0 = 晴天
1 = 雨天
2 = 雷暴
"""
```

### 4.2 方块操作

```python
# 创建方块组件
blockComp = serverApi.GetEngineCompFactory().CreateBlockInfo(levelId)

# 获取方块
blockDict = blockComp.GetBlockNew((x, y, z), dimId)
blockName = blockDict['name']  # 例: 'minecraft:stone'

# 设置方块
blockComp.SetBlockNew((x, y, z), {'name': 'minecraft:diamond_block', 'aux': 0}, dimId)

# 删除方块（设置为空气）
blockComp.SetBlockNew((x, y, z), {'name': 'minecraft:air', 'aux': 0}, dimId)
```

### 4.3 爆炸效果

```python
# 创建爆炸
gameComp.CreateExplosion(
    pos=(100, 64, 100),     # 爆炸位置
    radius=5.0,             # 爆炸半径
    fire=False,             # 是否产生火焰
    breaks=True,            # 是否破坏方块
    sourceId=None           # 爆炸源实体ID
)
```

### 4.4 音效播放

```python
# 播放音效
gameComp.PlaySound(
    pos=(100, 64, 100),           # 音效位置
    soundName='random.explode',   # 音效名称
    volume=1.0,                   # 音量
    pitch=1.0                     # 音调
)

# 常用音效
"""
'random.explode'        # 爆炸
'mob.enderdragon.growl' # 末影龙吼叫
'random.levelup'        # 升级
'random.orb'            # 经验球
'mob.chicken.say'       # 鸡叫
'random.click'          # 点击
"""
```

---

## 🎮 五、实体管理API

### 5.1 创建实体

```python
# 创建实体
entityId = gameComp.CreateEngineEntityByTypeStr(
    levelId,                    # 世界ID
    'minecraft:zombie',         # 实体类型
    (100, 64, 100),            # 位置
    (0, 0),                    # 朝向(pitch, yaw)
    {                           # 实体属性（可选）
        'minecraft:scale': {'value': 1.5},  # 缩放1.5倍
        'minecraft:is_baby': {}              # 幼年体
    }
)

# 常用实体类型
"""
'minecraft:zombie'          # 僵尸
'minecraft:skeleton'        # 骷髅
'minecraft:villager'        # 村民
'minecraft:iron_golem'      # 铁傀儡
'minecraft:ender_dragon'    # 末影龙
'minecraft:lightning_bolt'  # 闪电
'minecraft:tnt'             # TNT
"""
```

### 5.2 实体生命周期

```python
# 检查实体是否存在
if gameComp.IsEntityAlive(entityId):
    print "Entity is alive"

# 销毁实体
gameComp.DestroyEntity(entityId)
```

### 5.3 范围查询实体

```python
# 获取方形范围内的实体
entities = gameComp.GetEntitiesInSquareArea(
    dimId=0,              # 维度ID (0=主世界, 1=下界, 2=末地)
    x=100,                # 中心X
    z=100,                # 中心Z
    radius=50,            # 半径
    entityType='minecraft:zombie'  # 实体类型（可选，None=所有实体）
)

# 获取球形范围内的实体
entities = gameComp.GetEntitiesAroundPos(
    pos=(100, 64, 100),
    radius=20,
    dimId=0
)
```

---

## ⏰ 六、定时器API

### 6.1 添加定时器

```python
# 单次定时器
def DelayedCallback(self):
    print "3秒后执行"

self.gameComp.AddTimer(3.0, self.DelayedCallback)

# 带参数的定时器
def CallbackWithArgs(self, playerId, message):
    msgComp.NotifyOneMessage(playerId, message, "§a")

self.gameComp.AddTimer(5.0, self.CallbackWithArgs, playerId, "时间到！")
```

### 6.2 重复定时器

```python
# 使用定时器实现重复任务
def RepeatTask(self):
    print "每5秒执行一次"
    # 重新添加定时器，形成循环
    self.gameComp.AddTimer(5.0, self.RepeatTask)

# 启动重复任务
self.gameComp.AddTimer(5.0, self.RepeatTask)
```

### 6.3 取消定时器

```python
# 保存定时器ID
self.timerId = self.gameComp.AddTimer(10.0, self.MyCallback)

# 取消定时器
self.gameComp.CancelTimer(self.timerId)
```

---

## 🎯 七、AOI感应区API

### 7.1 创建AOI

```python
# 创建AOI组件
aoiComp = serverApi.GetEngineCompFactory().CreateAOI(levelId)

# 创建感应区
aoiId = aoiComp.AddAoi(
    center=(100, 64, 100),        # 中心位置
    dimension=[50, 50, 50]        # 尺寸[长, 宽, 高] ⚠️ 每维度最大2000
)

# 保存aoiId用于后续操作
self.aoiDict[aoiId] = {"center": (100, 64, 100)}
```

### 7.2 监听AOI事件

```python
def Create(self):
    # 监听实体进入AOI
    self.ListenForEvent(
        serverApi.GetEngineNamespace(),
        serverApi.GetEngineSystemName(),
        "EntityEnterAOIEvent",
        self,
        self.OnEntityEnterAOI
    )

    # 监听实体离开AOI
    self.ListenForEvent(
        serverApi.GetEngineNamespace(),
        serverApi.GetEngineSystemName(),
        "EntityLeaveAOIEvent",
        self,
        self.OnEntityLeaveAOI
    )

def OnEntityEnterAOI(self, args):
    aoiId = args['aoi']
    entityId = args['id']
    print "Entity", entityId, "entered AOI", aoiId

def OnEntityLeaveAOI(self, args):
    aoiId = args['aoi']
    entityId = args['id']
    print "Entity", entityId, "left AOI", aoiId
```

### 7.3 移除AOI

```python
# 移除指定AOI
aoiComp.RemoveAoi(aoiId)
```

---

## 🔧 八、工具函数API

### 8.1 方向向量

```python
# 创建方向组件
dirComp = serverApi.GetEngineCompFactory().CreateDir(levelId)

# 获取玩家朝向的方向向量
dirVector = dirComp.GetDirFromRot(rot)  # 输入rot=(pitch, yaw), 返回(x, y, z)

# 获取两点之间的方向向量
dirVector = dirComp.GetDirBetweenPos(fromPos, toPos)
```

### 8.2 维度操作

```python
# 获取玩家所在维度
dimComp = serverApi.GetEngineCompFactory().CreateDimension(levelId)
dimId = dimComp.GetEntityDimensionId(playerId)

# 切换玩家维度
dimComp.ChangePlayerDimension(playerId, dimId, (x, y, z))

# 维度ID
"""
0 = 主世界
1 = 下界
2 = 末地
"""
```

### 8.3 重力操作

```python
# 创建重力组件
gravityComp = serverApi.GetEngineCompFactory().CreateGravity(levelId)

# 设置重力（默认为1.0）
gravityComp.SetGravity(playerId, 0.5)  # 减半重力
gravityComp.SetGravity(playerId, 0.0)  # 无重力
gravityComp.SetGravity(playerId, 2.0)  # 双倍重力

# 恢复默认重力
gravityComp.SetGravity(playerId, 1.0)
```

---

## 📡 九、事件监听API

### 9.1 监听引擎事件

```python
def Create(self):
    # 监听玩家加入
    self.ListenForEvent(
        serverApi.GetEngineNamespace(),
        serverApi.GetEngineSystemName(),
        "AddServerPlayerEvent",
        self,
        self.OnPlayerJoin
    )

def OnPlayerJoin(self, args):
    playerId = args['id']
    # 处理玩家加入逻辑
```

### 9.2 监听自定义事件

```python
def Create(self):
    # 监听自定义事件
    self.ListenForEvent(
        "MyMod",              # 命名空间
        "MyServerSystem",     # 系统名
        "CustomEvent",        # 事件名
        self,
        self.OnCustomEvent,
        priority=5            # 优先级(0-10, 默认5)
    )
```

### 9.3 取消监听

```python
# 取消监听事件
self.UnListenForEvent(
    namespace,
    systemName,
    eventName,
    self,
    callback
)
```

---

## 🔄 十、双端通信API

### 10.1 服务端→客户端

```python
# ServerSystem中
def NotifyClient(self, playerId, data):
    eventData = self.CreateEventData()
    eventData["message"] = "Hello Client"
    eventData["value"] = [1, 2, 3]  # ⚠️ 使用list，不用tuple

    self.NotifyToClient(playerId, "ServerToClientEvent", eventData)
```

### 10.2 客户端→服务端

```python
# ClientSystem中
def NotifyServer(self):
    eventData = self.CreateEventData()
    eventData["action"] = "purchase"
    eventData["itemId"] = 100

    self.NotifyToServer("ClientToServerEvent", eventData)
```

### 10.3 监听跨端事件

```python
# ServerSystem监听来自ClientSystem的事件
def Create(self):
    self.ListenForEvent(
        "MyMod",
        "MyClientSystem",
        "ClientToServerEvent",
        self,
        self.OnClientEvent
    )

def OnClientEvent(self, args):
    playerId = args['__id__']  # ⚠️ 自动包含发送者ID
    action = args['action']
    # 处理逻辑
```

---

## ⚠️ 常见陷阱

### 陷阱1: EventData使用tuple

```python
# ❌ 错误
data["pos"] = (100, 64, 100)  # tuple序列化失败!

# ✅ 正确
data["pos"] = [100, 64, 100]  # 使用list
```

### 陷阱2: 在__init__中使用API

```python
# ❌ 错误
def __init__(self, namespace, systemName):
    ServerSystem.__init__(self, namespace, systemName)
    self.gameComp = serverApi.GetEngineCompFactory().CreateGame(levelId)  # 返回None!

# ✅ 正确
def __init__(self, namespace, systemName):
    ServerSystem.__init__(self, namespace, systemName)
    self.gameComp = None
    self.Create()

def Create(self):
    levelId = serverApi.GetLevelId()
    self.gameComp = serverApi.GetEngineCompFactory().CreateGame(levelId)
```

### 陷阱3: 跨端GetSystem

```python
# ❌ 错误（在ServerSystem中）
clientSystem = self.GetSystem("MyClientSystem")  # 返回None!

# ✅ 正确
self.NotifyToClient(playerId, "EventName", {})
```

### 陷阱4: AOI超过2000格

```python
# ❌ 错误
aoiComp.AddAoi(pos, [3000, 3000, 3000])  # 不生效!

# ✅ 正确
aoiComp.AddAoi(pos, [2000, 2000, 2000])
```

---

## 📚 延伸阅读

- **完整API文档**: [官方MODSDK Wiki](https://github.com/EaseCation/netease-modsdk-wiki)
- **核心概念**: [MODSDK核心概念.md](./MODSDK核心概念.md)
- **开发指南**: [开发指南.md](./开发指南.md)
- **问题排查**: [问题排查.md](./问题排查.md)

---

_最后更新: 2025-11-09 | 文档版本: 1.0_
