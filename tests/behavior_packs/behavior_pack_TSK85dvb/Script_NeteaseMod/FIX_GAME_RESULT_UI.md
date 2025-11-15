# 胜利结算UI修复补丁

> **创建时间**: 2025-11-12
> **修复问题**: 对局结束后玩家无法看到胜利结算UI
> **根本原因**: 客户端缺少OpenGameEnd事件监听

---

## 📊 问题分析

### 数据流断裂点

```
服务端 (StageBroadcastScoreState._open_game_end_ui:587)
    ↓ NotifyToClient("OpenGameEnd", {rank, score, ...})
    ↓
客户端 ❌ 没有任何System监听此事件
    ↓
UI显示失败 ❌
```

### 修复方案

添加2个关键组件：
1. **HUDSystem**: 监听OpenGameEnd事件
2. **ECHUDScreenNode**: 实现show_game_end_result方法显示UI

---

## 🔧 修复步骤

### 修复1: HUDSystem添加OpenGameEnd事件监听

**文件**: `systems/HUDSystem.py`

**位置**: `Create()方法`中，在监听HUDControlEvent之后添加

```python
# 在第83行之后添加（self.LogInfo("HUDSystem 已监听HUDControlEvent..."）之后）

# [新增 2025-11-12] 监听结算UI事件
# 服务端在StageBroadcastScoreState._open_game_end_ui中发送此事件
# 用于显示玩家排名、击杀数、破坏水晶数等统计信息
self.ListenForEvent(
    MOD_NAME,
    "RoomManagementSystem",
    'OpenGameEnd',
    self,
    self._on_open_game_end
)
self.LogInfo("HUDSystem 已监听OpenGameEnd事件 (来自 {}:RoomManagementSystem)".format(MOD_NAME))
```

**在_on_hud_control_event方法之后添加新方法**（第186行之后）:

```python
def _on_open_game_end(self, args):
    """
    接收服务端结算UI事件并转发给ScreenNode

    [新增 2025-11-12] 处理游戏结算UI显示
    参考: StageBroadcastScoreState._open_game_end_ui:587发送此事件

    Args:
        args (dict): 事件参数
            - rank (int): 玩家排名（1=第1名，2=第2名，etc.）
            - score (str): 格式化的统计文本（包含图标）
                           格式: "{icon-ec-sword0} {kill}  {icon-ec-sword2} {final_kill}  {icon-ec-crystal-destroy} {bed_destroy}"
            - left_text (str): 奖励类型文本（如: "{icon-ec-coin} 起床战争硬币"）
            - left_delta (str): 奖励变化值（如: "+50"）
    """
    if not self.screen_node:
        self.LogWarn("收到OpenGameEnd事件但ScreenNode尚未就绪，忽略")
        return

    try:
        self.LogInfo("收到结算UI数据 rank={} score={}".format(
            args.get('rank'),
            args.get('score')
        ))

        # 转发给ScreenNode处理
        if hasattr(self.screen_node, 'show_game_end_result'):
            self.screen_node.show_game_end_result(args)
        else:
            self.LogError("ECHUDScreenNode缺少show_game_end_result方法")

    except Exception as e:
        self.LogError("处理OpenGameEnd事件失败: {}".format(str(e)))
        import traceback
        print(traceback.format_exc())
```

---

### 修复2: ECHUDScreenNode添加结算UI显示方法

**文件**: `systems/ui/ECHUDScreenNode.py`

**在OnDestroy方法之后添加**（第102行之后）:

```python
# [新增 2025-11-12] 游戏结算UI显示方法
def show_game_end_result(self, args):
    """
    显示游戏结算UI

    参考: 老项目使用Title + StackMsg组合显示结算信息
    实现: 使用Title API显示排名，使用stack_msg_bottom显示统计数据

    Args:
        args (dict): 结算数据
            - rank (int): 排名
            - score (str): 统计文本（击杀/终结/破坏水晶）
            - left_text (str): 奖励类型文本
            - left_delta (str): 奖励变化值
    """
    try:
        rank = args.get('rank', 0)
        score = args.get('score', '')
        left_text = args.get('left_text', '')
        left_delta = args.get('left_delta', '')

        print("[INFO] [ECHUDScreenNode] 显示结算UI rank={} score={}".format(rank, score))

        # 1. 显示排名Title
        rank_title = self._format_rank_title(rank)
        self._show_title(rank_title, subtitle="", duration=10.0)

        # 2. 使用stack_msg_bottom显示统计信息
        if self.stack_msg_bottom:
            # 清空旧消息
            self.stack_msg_bottom.clear_all()

            # 显示统计（击杀/终结/破坏水晶）
            self.stack_msg_bottom.add_or_set_entry(
                "game_stats",
                score,
                border=True
            )

            # 显示奖励
            reward_text = u"{} {}".format(left_text, left_delta)
            self.stack_msg_bottom.add_or_set_entry(
                "game_reward",
                reward_text,
                border=False
            )

            print("[INFO] [ECHUDScreenNode] 结算数据已显示 - 统计:{} 奖励:{}".format(score, reward_text))

    except Exception as e:
        print("[ERROR] [ECHUDScreenNode] 显示结算UI失败: {}".format(str(e)))
        import traceback
        print(traceback.format_exc())

def _format_rank_title(self, rank):
    """
    格式化排名Title文本

    Args:
        rank (int): 排名（1=第1名，2=第2名，etc.）

    Returns:
        str: 格式化的排名文本（包含颜色代码）
    """
    if rank == 1:
        return u"{gold}{bold}第1名 - 胜利!"
    elif rank == 2:
        return u"{gray}{bold}第2名"
    elif rank == 3:
        return u"{yellow}{bold}第3名"
    else:
        return u"{white}第{}名".format(rank)

def _show_title(self, title, subtitle="", duration=5.0):
    """
    显示Title提示

    使用MODSDK的SetNotifyMsg API显示Title和Subtitle
    参考: MODSDK API - GameComponentClient.SetNotifyMsg

    Args:
        title (str): 主标题文本
        subtitle (str): 副标题文本（可选）
        duration (float): 显示时长（秒）- 注意：实际显示时长由引擎控制
    """
    try:
        comp_factory = clientApi.GetEngineCompFactory()
        local_player = clientApi.GetLocalPlayerId()

        # 获取GameComponent
        comp_game = comp_factory.CreateGame(clientApi.GetLevelId())

        # 显示Title
        # SetNotifyMsg(title, subtitle, "title") - 显示在屏幕中央
        comp_game.SetNotifyMsg(
            title,
            subtitle,
            "title"  # 显示类型: "title"
        )

        print("[INFO] [ECHUDScreenNode] Title已显示: {}".format(title))

    except Exception as e:
        print("[ERROR] [ECHUDScreenNode] 显示Title失败: {}".format(str(e)))
        import traceback
        print(traceback.format_exc())
```

---

## ✅ 验证修复

### 测试步骤

1. 启动游戏，完成一局对战
2. 游戏结束后观察结算阶段（15秒）
3. **预期效果**：
   - ✅ 屏幕中央显示排名Title（第1名/第2名/第3名）
   - ✅ 屏幕底部显示统计数据（击杀数/终结数/破坏水晶数）
   - ✅ 显示奖励信息（起床战争硬币 +XX）

### 日志验证

启动游戏后，检查日志应包含：

```
[INFO] [HUDSystem] HUDSystem 已监听OpenGameEnd事件 (来自 ...)
[INFO] [HUDSystem] 收到结算UI数据 rank=1 score=...
[INFO] [ECHUDScreenNode] 显示结算UI rank=1 score=...
[INFO] [ECHUDScreenNode] Title已显示: 第1名 - 胜利!
[INFO] [ECHUDScreenNode] 结算数据已显示 - 统计:...
```

---

## 🎯 修复覆盖范围

- ✅ 排名显示（Title API）
- ✅ 击杀数显示（通过score文本）
- ✅ 终结数显示（通过score文本）
- ✅ 破坏水晶数显示（通过score文本）
- ✅ 奖励显示（通过stack_msg_bottom）

---

## 📋 相关文件

| 文件 | 修改内容 | 行数变化 |
|------|---------|---------|
| `systems/HUDSystem.py` | 添加OpenGameEnd事件监听 + _on_open_game_end方法 | +35行 |
| `systems/ui/ECHUDScreenNode.py` | 添加show_game_end_result等3个方法 | +90行 |

---

## 🔗 相关代码位置

- **服务端发送事件**: [StageBroadcastScoreState.py:587](systems/room_states/StageBroadcastScoreState.py#L587)
- **结算数据构建**: [StageBroadcastScoreState.py:574-592](systems/room_states/StageBroadcastScoreState.py#L574-L592)
- **统计数据来源**: [BedWarsGameSystem.py] - 游戏过程中的击杀/破坏统计

---

> ⚠️ **注意**: 由于Edit工具遇到文件锁定问题，请手动将上述代码添加到对应文件中。
>
> 建议使用支持UTF-8编码的编辑器（如VSCode、Sublime Text）进行修改。
