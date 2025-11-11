# /enhance-docs - 批量补充文档

批量补充"文档待补充清单"中的内容。

## 描述

读取 `markdown/文档待补充清单.md`，批量补充缺失或不完整的文档。

## 用法

```bash
# 批量补充所有待补充内容
/enhance-docs

# 只补充Layer 2（架构层）
/enhance-docs --layer=2

# 补充指定System的文档
/enhance-docs CombatSystem WeaponSystem
```

---

## 执行流程

### 步骤1：读取待补充清单

```bash
Read(file_path="markdown/文档待补充清单.md")
```

提取所有未完成的待补充项（标记为 `- [ ]` 的项）

### 步骤2：展示待补充清单并确认

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 文档待补充清单
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

发现 X 个待补充项:

Layer 2 - 架构层:
 [ ] systems/CombatSystem.md - 补充业务逻辑和数据流
 [ ] systems/WeaponSystem.md - 补充业务逻辑和数据流
 ...

Layer 3 - 业务层:
 [ ] 补充业务系统详细文档
 ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

选择补充范围:
1. 全部补充（预计Token: Xk, 时间: X分钟）
2. 只补充Layer 2
3. 只补充Layer 3
4. 自定义选择

请选择 [1-4]:
```

### 步骤3：补充文档（使用子代理）

对于每个待补充项，使用Task工具创建子代理进行深度分析：

```python
for 待补充项 in 选中的待补充项:
    if 待补充项类型 == "系统文档":
        使用子代理补充系统文档(待补充项)
    elif 待补充项类型 == "业务文档":
        使用子代理补充业务文档(待补充项)

def 使用子代理补充系统文档(system_name):
    """使用子代理深度分析System并生成详细文档"""

    Task(
        subagent_type="general-purpose",
        description="深度分析{}".format(system_name),
        prompt="""
请深度分析以下System的代码，补充其技术文档：

**System名称**: {system_name}
**当前文档路径**: markdown/systems/{system_name}.md

**任务**:
1. 读取当前文档，了解已有内容
2. 使用Grep/Read分析System的完整代码
3. 补充以下章节：
   - 业务逻辑详细说明
   - 完整的数据流图（使用Mermaid或文字描述）
   - 关键方法的代码示例
   - 常见问题和注意事项

**要求**:
- 文档应包含约1500-3000字
- 包含具体的代码示例
- 说明设计原理（为什么这样设计）
- 引用相关的文档规范

请将补充后的完整文档内容返回。
        """.format(system_name=system_name)
    )
```

### 步骤4：更新文档待补充清单

将已补充的项标记为完成：

```bash
Edit(
    file_path="markdown/文档待补充清单.md",
    old_string="- [ ] systems/CombatSystem.md - 补充业务逻辑和数据流",
    new_string="- [x] systems/CombatSystem.md - 补充业务逻辑和数据流"
)
```

### 步骤5：输出完成报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 文档补充完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

补充统计:
- 已补充: X 个文档
- 待补充: Y 个文档
- 文档覆盖率: Z%

更新的文档:
- markdown/systems/CombatSystem.md ✅
- markdown/systems/WeaponSystem.md ✅
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

下一步:
- 查阅更新后的文档
- 使用 /validate-docs 验证文档质量
- 继续开发，AI会进一步完善文档

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 注意事项

- ⏱️ 补充文档可能耗时较长（取决于待补充项数量）
- 💰 每个System约消耗5-10k tokens
- 🔄 建议分批补充，避免超时
