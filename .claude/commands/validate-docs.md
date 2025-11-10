# /validate-docs - AI驱动的文档审计与规范化

AI驱动的项目文档完整性验证工具。自动发现项目组件，智能推断规范化的文档命名，生成待补充清单。

---

## 🎯 核心功能

1. **自动发现项目组件** - AI扫描项目，发现所有Systems、States、Presets、Managers等组件
2. **智能文档命名** - AI阅读源代码，推断准确的中文文档名（如：ShopServerSystem → "商店购买系统.md"）
3. **文档覆盖率分析** - 统计已覆盖/未覆盖/低质量文档
4. **交互式占位符创建** - 可选择创建占位文档，供后续补充
5. **生成待补充清单** - 为 `/enhance-docs` 提供输入

---

## 📋 执行流程

### 步骤1：扫描项目结构（自动发现组件）

**任务**：使用现有的项目分析逻辑，发现所有组件

```javascript
// 1. 扫描所有Python文件
Grep("class.*System|State|Preset|Manager|Handler",
     path="behavior_packs/",
     output_mode="files_with_matches")

// 2. 识别组件类型
// - Systems: class XXXServerSystem/XXXClientSystem
// - States: class XXXState
// - Presets: class XXXPreset/XXXPresetDef
// - 其他自定义组件
```

**输出示例**：
```
[发现组件]
- 发现 2 个 Systems
- 发现 16 个 States
- 发现 2 个 Presets
- 发现 0 个 Managers
```

---

### 步骤2：AI智能命名规范化（核心创新⭐）

**任务**：对每个发现的组件，使用AI分析源代码并推断准确的中文文档名

**实现方式**：使用 Task 工具并行处理（推荐使用 haiku 模型降低成本）

```javascript
// 为每个组件创建分析任务
const components = [
  { name: 'ShopServerSystem', path: 'behavior_packs/.../ShopServerSystem.py', type: 'system' },
  { name: 'WaitingState', path: 'behavior_packs/.../WaitingState.py', type: 'state' },
  // ...
];

// 并行分析（示例伪代码）
for (const comp of components) {
  const analysis = await Task({
    subagent_type: "general-purpose",
    model: "haiku",  // 使用 haiku 降低成本
    description: `分析组件 ${comp.name} 并推断中文文档名`,
    prompt: `
请分析以下Python组件文件，推断准确的中文文档名。

**组件信息：**
- 类名：${comp.name}
- 文件路径：${comp.path}
- 组件类型：${comp.type}

**任务：**
1. 使用 Read 工具读取源代码
2. 分析代码中的：
   - 类的 docstring（如有）
   - 注释中的中文说明
   - 关键方法名称（推断功能）
   - 引用的其他组件
3. 推断该组件的核心业务功能
4. 生成规范化的中文文档名

**命名规则：**
- Systems: "{功能描述}系统.md"（如：商店购买系统.md）
- States: "{阶段描述}状态.md"（如：等待阶段状态.md）
- Presets: "{配置描述}预设.md"（如：商店配置预设.md）
- 其他: "{功能描述}{类型}.md"

**返回格式（纯文本，一行）：**
中文文档名.md|功能描述（一句话）

**示例：**
商店购买系统.md|处理玩家购买道具的服务端逻辑
`
  });

  // 解析返回结果
  const [chineseName, description] = analysis.split('|');
  comp.chineseName = chineseName.trim();
  comp.description = description.trim();
}
```

**输出示例**：
```
[AI命名规范化完成]

【Systems】(2个)
- ShopServerSystem → 商店购买系统.md
  功能：处理玩家购买道具的服务端逻辑

- TeamServerSystem → 队伍管理系统.md
  功能：管理玩家队伍分配和队伍状态

【States】(16个)
- WaitingState → 等待阶段状态.md
  功能：游戏开始前的等待阶段逻辑

- PlayingState → 游戏进行状态.md
  功能：游戏进行中的主要逻辑
...
```

---

### 步骤3：检查文档覆盖率

**任务**：检查每个组件是否已有对应文档，并评估质量

```javascript
// 对于每个组件
for (const comp of components) {
  const docPath = `markdown/${comp.type}s/${comp.chineseName}`;

  if (exists(docPath)) {
    // 评估文档质量
    const quality = assessDocQuality(docPath);
    comp.docStatus = quality >= 50 ? 'covered' : 'low_quality';
    comp.quality = quality;
  } else {
    comp.docStatus = 'missing';
  }
}
```

**文档质量评分标准（0-100分）**：
- 存在性：20分
- 字数：25分（>=1500字满分，>=800字15分，>=300字10分）
- 章节完整度：25分（是否包含"概述"、"架构"、"API"等）
- 代码示例：15分（是否包含 ``` 代码块）
- 更新时间：15分（<30天15分，<90天10分，<180天5分）

---

### 步骤4：询问用户是否创建占位文档（交互式⭐）

**任务**：使用 AskUserQuestion 工具询问用户

```javascript
AskUserQuestion({
  questions: [{
    question: "发现 18 个组件缺少文档，是否创建占位文档？",
    header: "占位文档",
    multiSelect: false,
    options: [
      {
        label: "创建所有占位文档",
        description: "为 18 个缺失组件创建占位文档（简单模板），供 /enhance-docs 补充内容"
      },
      {
        label: "只创建缺失的",
        description: "保留已有文档，只为缺失的组件创建占位符"
      },
      {
        label: "不创建",
        description: "只生成待补充清单，稍后手动创建或使用 /enhance-docs"
      }
    ]
  }]
})
```

**根据用户选择执行**：
- 选项1/2：创建占位文档
  ```markdown
  # {中文文档名}

  > **类名**：{原始类名}
  > **文件路径**：{源码路径}
  > **功能描述**：{AI推断的功能描述}

  ## 概述

  ⚠️ **待补充** - 使用 `/enhance-docs` 命令自动生成详细内容

  ## 架构设计

  ⚠️ **待补充**

  ## API文档

  ⚠️ **待补充**
  ```

- 选项3：跳过创建

---

### 步骤5：生成文档待补充清单

**任务**：生成 `markdown/文档待补充清单.md`，供 `/enhance-docs` 使用

```markdown
# 文档待补充清单

> **生成时间**：2025-11-10
> **总组件数**：18
> **已覆盖**：0 (0%)
> **未覆盖**：18 (100%)
> **低质量**：0

---

## Layer 2 - 架构层

### Systems (2个)

- [ ] `markdown/systems/商店购买系统.md`
  - 类名：ShopServerSystem
  - 路径：behavior_packs/.../ShopServerSystem.py
  - 功能：处理玩家购买道具的服务端逻辑
  - 状态：⚠️ 待补充

- [ ] `markdown/systems/队伍管理系统.md`
  - 类名：TeamServerSystem
  - 路径：behavior_packs/.../TeamServerSystem.py
  - 功能：管理玩家队伍分配和队伍状态
  - 状态：⚠️ 待补充

### States (16个)

- [ ] `markdown/states/等待阶段状态.md`
  - 类名：WaitingState
  - 路径：behavior_packs/.../WaitingState.py
  - 功能：游戏开始前的等待阶段逻辑
  - 状态：⚠️ 待补充

...

---

## 📝 使用说明

**批量补充文档**：
```bash
/enhance-docs
```

**手动补充单个文档**：
直接编辑对应的 markdown 文件，补充完成后将 `- [ ]` 改为 `- [x]`
```

---

### 步骤6：生成验证报告

**输出报告格式**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 文档完整性验证报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 🔍 项目结构发现

发现以下组件：

【Systems】(2个)
- ShopServerSystem → 商店购买系统.md
  功能：处理玩家购买道具的服务端逻辑

- TeamServerSystem → 队伍管理系统.md
  功能：管理玩家队伍分配和队伍状态

【States】(16个)
- WaitingState → 等待阶段状态.md
- PlayingState → 游戏进行状态.md
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📈 文档覆盖率

- 总组件数：18
- 已覆盖：0 (0%)
- 未覆盖：18 (100%)
- 低质量：0 (0%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ❌ 缺失文档（18个）

【Systems】
1. 商店购买系统.md
2. 队伍管理系统.md

【States】
1. 等待阶段状态.md
2. 游戏进行状态.md
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## ✅ 已完成

- ✅ 项目结构发现完成
- ✅ AI智能命名规范化完成
- ✅ 文档待补充清单已生成：markdown/文档待补充清单.md
- ✅ 占位文档创建完成（根据用户选择）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 💡 下一步

**批量生成文档内容**：
/enhance-docs

该命令将：
- 读取文档待补充清单
- AI深度分析源代码
- 生成高质量文档内容（1500-3000字）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

将报告保存到 `markdown/文档验证报告.md`

---

## ⚠️ 重要提示

1. **Token成本**：
   - 每个组件分析约 0.5-1k tokens（使用 haiku 模型）
   - 18个组件预计消耗 10-15k tokens
   - 首次执行建议使用 haiku 模型降低成本

2. **并行处理**：
   - 使用 Task 工具并行分析组件，提升速度
   - 建议每批处理 5-10 个组件，避免超时

3. **错误处理**：
   - 如果AI无法推断中文名称，使用默认规则（类名 + 类型后缀）
   - 记录推断失败的组件，供人工review

4. **与 /enhance-docs 配合**：
   - validate-docs 负责"发现 + 规范化"
   - enhance-docs 负责"内容生成"
   - 两者配合实现完整的文档工作流

---

## 📚 参考资料

- 项目结构发现：lib/project-discovery.js
- AI命名逻辑：lib/intelligent-doc-maintenance.js
- 文档质量评估：参考现有的 assessDocQuality 方法
