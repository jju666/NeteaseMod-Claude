# 使用示例

> NeteaseMod-Claude 实际开发案例

---

## 📋 目录

1. [示例1：修复常见错误（双端隔离）](#示例1修复常见错误双端隔离)
2. [示例2：添加新功能（排行榜系统）](#示例2添加新功能排行榜系统)
3. [更多示例](#更多示例)

---

## 示例1：修复常见错误（双端隔离）

### 用户输入

```
修复ShopServerSystem中点击商店按钮无响应的问题
```

### Claude Code执行流程

#### 步骤1: 理解任务

```markdown
🎯 任务级别: 🟡 标准任务（涉及3个文件）
```

#### 步骤2: 查阅文档

```markdown
✅ 已查阅: 开发规范.md (📝项目定制版), ShopServerSystem.md (项目文档)
🎯 提取原则:
  ⛔ 禁止: 服务端GetSystem获取客户端系统
  ✅ 应该: 使用NotifyToClient通信
  📚 原因: Server和Client进程分离，跨端GetSystem返回None
```

#### 步骤3: 定位问题

```markdown
📄 文件: behavior_packs/behavior_pack_test/scripts/ShopServerSystem.py:78
❌ 错误代码:
   ```python
   shop_client = self.GetSystem("ShopClientSystem")  # 运行时返回None!
   shop_client.ShowUI(playerId)
   ```
```

#### 步骤4: 修复方案

```python
# 服务端发送事件
self.NotifyToClient(playerId, "ShowShopUI", {"shopId": shopId})

# 客户端监听事件（ShopClientSystem.py）
@Listen("ShowShopUI")
def OnShowShopUI(self, args):
    shopId = args["shopId"]
    self.ShowUI(shopId)
```

#### 步骤5: 验证

```markdown
✅ 编译通过
✅ 功能测试通过
✅ Git commit完成
```

---

## 示例2：添加新功能（排行榜系统）

### 用户输入

```
添加一个排行榜系统，显示玩家击杀数Top10
```

### Claude Code执行流程

#### 步骤1: 理解任务

```markdown
🎯 任务级别: 🔴 复杂任务（需要创建6个新文件）
```

#### 步骤2: 查阅文档

```markdown
✅ 已查阅: 开发规范.md, API速查.md, MODSDK核心概念.md
🌐 官方文档查阅:
   - WebFetch: netease-modsdk-wiki/UI组件文档
   - WebFetch: bedrock-wiki/记分板系统
```

#### 步骤3: 创建任务（9章模板）

```markdown
📁 tasks/添加排行榜系统_20251111/
   ├── 1-需求分析.md
   ├── 2-技术方案.md
   ├── 3-架构设计.md
   ├── 4-实施计划.md
   ├── 5-代码实现.md
   ├── 6-测试验证.md
   ├── 7-文档更新.md
   ├── 8-总结反思.md
   └── 9-知识沉淀.md
```

#### 步骤4: 分阶段实施

```markdown
阶段1: 数据存储（RankServerSystem.py）✅
阶段2: UI显示（RankClientSystem.py）✅
阶段3: 数据更新（监听PlayerKillEvent）✅
阶段4: 排序算法（Top10计算）✅
阶段5: 集成测试 ✅
```

#### 步骤5: 更新文档

```markdown
✅ 创建: markdown/systems/RankSystem.md
✅ 更新: markdown/文档待补充清单.md
✅ Git commit完成
```

---

## 更多示例

### 微任务示例

```
你：调整钻石剑价格为1000金币

Claude：
✅ 已查阅: ShopPreset.md
✅ 定位: presets/ShopPreset.py:42
✅ 修改完成
✅ Git commit: "chore: 调整钻石剑价格为1000金币"
```

### 标准任务示例

```
你：修复倒计时在某些情况下不显示的问题

Claude：
✅ 已查阅: 开发规范.md, TimerSystem.md
🔍 定位问题: TimerSystem.py:156 未检查玩家在线状态
✅ 修复方案: 添加玩家在线检查
✅ 测试通过
✅ Git commit完成
```

### 复杂任务示例

```
你：重构商店系统，支持多货币类型

Claude：
✅ 创建任务: tasks/重构商店系统_20251111/
✅ 架构设计: 抽象货币接口
✅ 实施阶段1-5
✅ 文档更新: ShopSystem.md, CurrencySystem.md
✅ Git commit完成
```

---

## 关键特性展示

### 1. 自动遵守CRITICAL规范

Claude Code会自动检测并避免常见错误：

```python
# ❌ Claude会拒绝这样写
class ServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        # 错误：未调用Create()
        pass

# ✅ Claude会这样修正
class ServerSystem(ServerSystem):
    def __init__(self, namespace, systemName):
        ServerSystem.__init__(self, namespace, systemName)
        self.Create()  # 手动调用Create()
```

### 2. 智能文档查阅

```
你：如何使用粒子效果？

Claude：
📚 查阅本地文档: API速查.md
🌐 查阅官方文档: netease-modsdk-wiki/粒子系统
✅ 提取示例代码:
   ```python
   comp = self.GetComponent("Minecraft", "particleSystem")
   comp.CreateParticle("minecraft:flame", pos)
   ```
```

### 3. 任务历史追踪

所有任务都会自动记录到 `tasks/` 目录：

```
tasks/
├── 修复商店系统_20251111/
│   ├── 1-任务概述.md
│   ├── 2-前期调研.md
│   ├── 3-实施记录.md
│   ├── 4-验证结果.md
│   └── 5-任务总结.md
└── completed/
    └── 2025-11/
        └── 添加排行榜系统_20251110/
```

---

## 下一步

- 📖 [快速开始](./markdown/快速开始.md) - 5分钟上手
- 📚 [完整文档](./README.md#-完整文档) - 文档导航
- 🐛 [故障排查](./TROUBLESHOOTING.md) - 问题解决

---

_使用示例 | 最后更新: 2025-11-11_
