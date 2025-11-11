# MODSDK核心概念速查

> **网易我的世界MODSDK核心概念快速参考**
>
> System | Component | Event | Entity 四大核心体系

---

## 🎯 文档定位

本文档提供MODSDK四大核心概念的**快速参考**，适合：
- 🔍 快速查询API用法
- 📖 理解架构设计
- 🚀 加速开发流程

**深入学习**: 查阅[开发指南.md](./开发指南.md)完整章节

---

## 📦 一、System系统

### 1.1 概念

**System**是MODSDK的核心逻辑单元，分为两类：

| 类型 | 继承类 | 运行端 | 用途 |
|------|--------|--------|------|
| **ServerSystem** | `ServerSystem` | 服务端进程 | 游戏逻辑、数据管理、权限控制 |
| **ClientSystem** | `ClientSystem` | 客户端进程 | UI渲染、输入处理、视觉效果 |

**⚠️ CRITICAL**: Server和Client运行在**不同进程**中，无法跨端GetSystem！

### 1.2 生命周期

```python
class MyServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        """1. 初始化（自动调用）"""
        ServerSystem.__init__(self, namespace, systemName)
        self.gameComp = None  # 只声明变量
        self.Create()         # ⚠️ CRITICAL: 手动调用Create

    def Create(self):
        """2. 创建（手动调用，安全的初始化位置）"""
        levelId = serverApi.GetLevelId()
        self.gameComp = serverApi.GetEngineCompFactory().CreateGame(levelId)
        self.ListenForEvent(...)  # 注册事件监听

    def Update(self):
        """3. 更新（自动调用，20次/秒）"""
        # 每帧执行的逻辑
        pass

    def Destroy(self):
        """4. 销毁（自动调用）"""
        # 清理资源
        pass
```

**规则**:
- ✅ `__init__`: 只声明变量，最后调用`self.Create()`
- ✅ `Create()`: 初始化组件、注册事件
- ✅ `Update()`: 每帧逻辑（可选实现）
- ✅ `Destroy()`: 清理资源（可选实现）

### 1.3 双端通信

**服务端→客户端**:
```python
# ServerSystem中
self.NotifyToClient(playerId, "EventName", {"key": "value"})
```

**客户端→服务端**:
```python
# ClientSystem中
self.NotifyToServer("EventName", {"key": "value"})
```

**监听跨端事件**:
```python
# ServerSystem监听来自ClientSystem的事件
def Create(self):
    self.ListenForEvent("ModName", "ClientSystemName", "EventName", self, self.OnEvent)

def OnEvent(self, args):
    playerId = args['__id__']  # ⚠️ 自动包含发送者ID
    # 处理事件
```

---

## 🧩 二、Component组件

### 2.1 概念

**Component**是实体的功能模块，分为两类：

| 类型 | 来源 | 数量 | 示例 |
|------|------|------|------|
| **引擎组件** | MODSDK内置 | 271个 | GameComp, ItemComp, AttrComp |
| **自定义组件** | 开发者定义 | 无限 | PlayerDataComp, ShopComp |

### 2.2 引擎组件使用

**获取组件工厂**:
```python
# 服务端
comp_factory = serverApi.GetEngineCompFactory()

# 客户端
comp_factory = clientApi.GetEngineCompFactory()
```

**创建和使用组件**:
```python
# 示例：操作玩家物品
def Create(self):
    self.itemComp = serverApi.GetEngineCompFactory().CreateItem(levelId)

def GiveItem(self, playerId):
    itemDict = {
        'itemName': 'minecraft:diamond_sword',
        'count': 1,
        'enchantData': [(0, 5)]  # 锋利5
    }
    self.itemComp.SpawnItemToPlayerInv(itemDict, playerId, 0)
```

### 2.3 常用引擎组件

| 组件名 | 用途 | 常用方法 |
|--------|------|---------|
| **GameComp** | 游戏基础操作 | `SetTime()`, `SetWeather()`, `AddTimer()` |
| **ItemComp** | 物品操作 | `SpawnItemToPlayerInv()`, `GetPlayerItem()` |
| **AttrComp** | 属性管理 | `SetAttr()`, `GetAttr()` |
| **PosComp** | 位置操作 | `GetPos()`, `SetPos()`, `GetRot()` |
| **NameComp** | 名称操作 | `GetName()`, `SetShowName()` |
| **MsgComp** | 消息发送 | `NotifyOneMessage()` |

**完整列表**: 查阅[官方MODSDK Wiki](https://github.com/EaseCation/netease-modsdk-wiki)

### 2.4 自定义组件

```python
# 注册自定义组件
@ComponentRegister("player_data")
class PlayerDataComponent(object):
    def __init__(self):
        self.kill_count = 0
        self.death_count = 0

    def AddKill(self):
        self.kill_count += 1

    def GetKD(self):
        if self.death_count == 0:
            return float(self.kill_count)
        return float(self.kill_count) / self.death_count

# 使用自定义组件
player_data = entity.GetComponent("player_data")
player_data.AddKill()
```

---

## 📡 三、Event事件

### 3.1 概念

**Event**是MODSDK的通信机制，分为三类：

| 类型 | 来源 | 数量 | 示例 |
|------|------|------|------|
| **引擎事件** | MODSDK内置 | 271个 | PlayerJumpEvent, DamageEvent |
| **自定义事件** | 开发者定义 | 无限 | PurchaseEvent, TeamChangeEvent |
| **跨端事件** | NotifyToClient/Server | 无限 | OpenUIEvent, SyncDataEvent |

### 3.2 监听事件

**监听引擎事件**:
```python
def Create(self):
    # 监听玩家加入事件
    self.ListenForEvent(
        serverApi.GetEngineNamespace(),  # 命名空间
        serverApi.GetEngineSystemName(),  # 系统名
        "AddServerPlayerEvent",            # 事件名
        self,                              # 监听者
        self.OnPlayerJoin                  # 回调函数
    )

def OnPlayerJoin(self, args):
    playerId = args['id']
    print "Player joined:", playerId
```

**监听自定义事件**:
```python
def Create(self):
    self.ListenForEvent(
        "MyMod",           # 命名空间
        "MyServerSystem",  # 系统名
        "PurchaseEvent",   # 事件名
        self,
        self.OnPurchase
    )
```

### 3.3 触发事件

**触发自定义事件**:
```python
def TriggerPurchase(self, playerId, itemId):
    data = self.CreateEventData()
    data["playerId"] = playerId
    data["itemId"] = itemId
    data["price"] = [100, 64, 100]  # ⚠️ 使用list，不用tuple

    self.NotifyToModules(self, "PurchaseEvent", data)
```

### 3.4 EventData限制 ⚠️

**支持类型**:
- ✅ dict, list, str, int, float, bool

**禁止类型**:
- ❌ tuple (会导致序列化失败)

```python
# ❌ 错误
data["position"] = (100, 64, 100)  # 序列化失败!

# ✅ 正确
data["position"] = [100, 64, 100]  # 使用list
```

### 3.5 事件优先级

```python
# 优先级范围: 0-10 (数字越小越先执行)
self.ListenForEvent(
    namespace, systemName, eventName,
    self, callback,
    priority=5  # 默认为5
)
```

**优先级用途**:
- **0-2**: 最高优先级（拦截/修改事件）
- **3-7**: 正常优先级（业务逻辑）
- **8-10**: 低优先级（日志/统计）

---

## 🎮 四、Entity实体

### 4.1 概念

**Entity**是游戏世界中的对象，分为两类：

| 类型 | 创建端 | 同步 | 用途 |
|------|--------|------|------|
| **服务端实体** | ServerSystem | 自动同步到所有客户端 | 游戏逻辑实体 |
| **客户端实体** | ClientSystem | 仅本地可见 | 视觉效果实体 |

### 4.2 创建实体

**服务端创建**:
```python
def SpawnNPC(self, pos):
    """创建NPC（所有玩家可见）"""
    playerId = serverApi.GetLevelId()
    entityId = self.gameComp.CreateEngineEntityByTypeStr(
        playerId,
        "minecraft:villager",
        pos,
        [0, 0],
        {"minecraft:scale": {"value": 1.2}}  # 实体属性
    )
    return entityId
```

**客户端创建**:
```python
def SpawnEffect(self, pos):
    """创建视觉效果（仅本地可见）"""
    playerId = clientApi.GetLocalPlayerId()
    entityId = self.gameComp.CreateEngineEntityByTypeStr(
        playerId,
        "minecraft:lightning_bolt",
        pos,
        [0, 0],
        {}
    )
    return entityId
```

### 4.3 实体操作

**获取/销毁实体**:
```python
# 检查实体是否存在
if self.gameComp.IsEntityAlive(entityId):
    # 获取实体位置
    pos = self.posComp.GetPos(entityId)

    # 销毁实体
    self.gameComp.DestroyEntity(entityId)
```

**批量操作**:
```python
# 获取所有玩家
players = self.gameComp.GetAllPlayers()

# 获取指定类型的实体
zombies = self.gameComp.GetEntitiesInSquareArea(
    dimId, x, z, radius, "minecraft:zombie"
)
```

### 4.4 AOI感应区

**概念**: AOI (Area of Interest) 感应区用于检测实体进入/离开指定区域。

**创建感应区**:
```python
def CreateAOI(self, pos):
    """创建AOI感应区"""
    aoiComp = serverApi.GetEngineCompFactory().CreateAOI(levelId)

    # ⚠️ CRITICAL: 每个维度最大2000格
    dimension = [2000, 2000, 2000]  # [长, 宽, 高]

    aoiId = aoiComp.AddAoi(pos, dimension)

    # 监听进入/离开事件
    self.ListenForEvent(
        serverApi.GetEngineNamespace(),
        serverApi.GetEngineSystemName(),
        "EntityEnterAOIEvent",
        self,
        self.OnEntityEnterAOI
    )

    return aoiId
```

**AOI限制** ⚠️:
- 每个维度最大2000格
- 超过限制会导致感应区不生效
- 解决方案：使用多个小感应区

---

## 🔍 五、快速参考表

### 5.1 API命名空间

```python
# 服务端
serverApi.GetEngineNamespace()      # "Minecraft"
serverApi.GetEngineSystemName()     # "Minecraft"
serverApi.GetLevelId()              # 世界ID

# 客户端
clientApi.GetEngineNamespace()      # "Minecraft"
clientApi.GetEngineSystemName()     # "Minecraft"
clientApi.GetLocalPlayerId()        # 本地玩家ID
```

### 5.2 常用组件速查

| 需求 | 组件 | 方法 |
|------|------|------|
| 发送消息 | MsgComp | `NotifyOneMessage(playerId, msg)` |
| 给物品 | ItemComp | `SpawnItemToPlayerInv(itemDict, playerId, slot)` |
| 传送玩家 | PosComp | `SetPos(playerId, pos)` |
| 修改生命 | AttrComp | `SetAttr(playerId, serverApi.AttrType.HEALTH, value)` |
| 设置时间 | GameComp | `SetTime(tickTime)` |
| 添加定时器 | GameComp | `AddTimer(delay, callback, *args)` |
| 创建实体 | GameComp | `CreateEngineEntityByTypeStr(...)` |
| 播放音效 | GameComp | `PlaySound(pos, soundName, volume, pitch)` |

### 5.3 常用事件速查

| 需求 | 事件名 | 关键参数 |
|------|--------|---------|
| 玩家加入 | AddServerPlayerEvent | `id` |
| 玩家离开 | DelServerPlayerEvent | `id` |
| 玩家跳跃 | PlayerJumpEvent | `playerId` |
| 玩家受伤 | DamageEvent | `entityId`, `damage` |
| 玩家死亡 | PlayerDieEvent | `id`, `attacker` |
| 方块破坏 | ServerBlockUseEvent | `playerId`, `blockName`, `x`, `y`, `z` |
| 物品使用 | ServerItemUseEvent | `playerId`, `itemDict` |
| 实体进入AOI | EntityEnterAOIEvent | `aoiId`, `entityId` |

**完整事件列表**: 查阅[官方MODSDK Wiki - Events](https://github.com/EaseCation/netease-modsdk-wiki)

---

## ⚠️ CRITICAL规范速查

### 规范1: 双端隔离
```python
# ❌ 错误
shop_client = self.GetSystem("ShopClientSystem")  # 返回None!

# ✅ 正确
self.NotifyToClient(playerId, "OpenShop", {})
```

### 规范2: System生命周期
```python
# ✅ 正确
def __init__(self, namespace, systemName):
    ServerSystem.__init__(self, namespace, systemName)
    self.comp = None
    self.Create()  # 手动调用

def Create(self):
    self.comp = serverApi.GetEngineCompFactory().CreateGame(levelId)
```

### 规范3: EventData序列化
```python
# ❌ 错误
data["pos"] = (100, 64, 100)  # tuple不支持!

# ✅ 正确
data["pos"] = [100, 64, 100]  # 使用list
```

### 规范4: AOI范围限制
```python
# ❌ 错误
aoiComp.AddAoi(pos, [3000, 3000, 3000])  # 超过2000!

# ✅ 正确
aoiComp.AddAoi(pos, [2000, 2000, 2000])
```

---

## 📚 延伸阅读

| 主题 | 文档 | 章节 |
|------|------|------|
| System开发完整流程 | 开发指南.md | 第3章 |
| Component开发详解 | 开发指南.md | 第4章 |
| Event系统深入 | 开发指南.md | 第5章 |
| Entity开发实战 | 开发指南.md | 第6章 |
| 双端通信案例 | 开发指南.md | 第9.2节 |
| 常见问题排查 | 问题排查.md | 全文 |
| CRITICAL规范 | 开发规范.md | 全文 |

---

## 🌐 官方资源

- **网易MODSDK Wiki**: https://github.com/EaseCation/netease-modsdk-wiki
- **基岩版Wiki**: https://github.com/Bedrock-OSS/bedrock-wiki
- **Claude Code**: 使用WebFetch自动查询官方文档

---

_最后更新: 2025-11-09 | 文档版本: 1.0_
