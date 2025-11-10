# /validate-docs - AI驱动的文档审计与规范化

AI驱动的项目文档完整性验证工具。自动发现项目组件，智能推断规范化的文档命名，生成待补充清单。

---

## 🎯 核心功能

1. **自动发现项目组件** - AI扫描项目，发现所有组件（Systems、Components及任意项目自定义组件类型）
2. **智能文档命名** - AI阅读源代码，推断准确的中文文档名（如：XXXServerSystem → "XXX系统.md"）
3. **文档覆盖率分析** - 统计已覆盖/未覆盖/低质量文档
4. **交互式占位符创建** - 可选择创建占位文档，供后续补充
5. **生成待补充清单** - 为 `/enhance-docs` 提供输入

---

## 📋 执行流程

### 步骤0：预检查 - 运行自适应发现工具（必须）⭐

**任务**：确保 `.claude/discovered-patterns.json` 存在且为最新

```bash
# 如果文件不存在或超过1天，重新运行发现工具
if [ ! -f .claude/discovered-patterns.json ] || [ $(find .claude/discovered-patterns.json -mtime +1) ]; then
  node lib/adaptive-doc-discovery.js
fi
```

**重要提示**：
- 必须先运行自适应发现工具，生成 `.claude/discovered-patterns.json`
- 该文件包含项目组件类型、文档目录等关键信息
- 如果项目结构有变化，建议重新运行 `/discover` 命令

---

### 步骤1：读取发现结果并构建组件列表

**任务**：从 discovered-patterns.json 加载组件信息

```javascript
// 1. 运行自适应发现工具（如果 .claude/discovered-patterns.json 不存在或过期）
// 执行: node lib/adaptive-doc-discovery.js
// 这会生成 .claude/discovered-patterns.json

// 2. 读取发现结果
const discoveredPatterns = Read(".claude/discovered-patterns.json");

// 3. 解析组件信息
const { patterns } = JSON.parse(discoveredPatterns);
const { officialConcepts, customPatterns } = patterns;

// 4. 构建组件列表
const components = [];

// MODSDK官方核心概念
for (const system of officialConcepts.systems) {
  components.push({
    className: system.className,
    filePath: system.filePath,
    type: 'system',
    patternType: 'official'
  });
}

for (const component of officialConcepts.components) {
  components.push({
    className: component.className,
    filePath: component.filePath,
    type: 'component',
    patternType: 'official'
  });
}

// 项目自定义模式
for (const [patternKey, pattern] of Object.entries(customPatterns)) {
  for (const example of pattern.examples) {
    components.push({
      className: example.className,
      filePath: example.filePath,
      type: patternKey,  // 'state', 'preset', 等
      patternType: 'custom',
      patternSuffix: pattern.suffix,
      docDir: pattern.docDirCandidate
    });
  }
}
```

**输出示例**：
```
[发现组件]
MODSDK核心：
- 发现 2 个 Systems (ServerSystem/ClientSystem)
- 发现 0 个 自定义Components

项目特定组织（自适应发现）：
- 发现 16 个 [State模式] 组件 → 文档目录: states/
- 发现 2 个 [Preset模式] 组件 → 文档目录: presets/
- 发现 0 个 [Manager模式] 组件
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

**命名规则（自适应）：**
- Systems: "{功能描述}系统.md"（如：XXX业务系统.md）
- Components: "{功能描述}组件.md"（如：XXX功能组件.md）
- 自定义模式组件（根据discovered-patterns.json自动推断）:
  - 对于每个发现的自定义模式，使用其后缀作为类型标识
  - 命名格式: "{功能描述}{后缀对应的中文}.md"
  - 示例:
    - State模式 → "{阶段描述}状态.md"（如：XXX阶段状态.md）
    - Preset模式 → "{配置描述}预设.md"（如：XXX配置预设.md）
    - Manager模式 → "{功能描述}管理器.md"（如：XXX管理器.md）
    - 其他模式 → 根据后缀推断对应的中文词汇

**返回格式（纯文本，一行）：**
中文文档名.md|功能描述（一句话）

**示例：**
XXX业务系统.md|处理玩家XXX功能的服务端逻辑
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
- XXXServerSystem → XXX业务系统.md
  功能：处理XXX业务的服务端逻辑

- YYYServerSystem → YYY业务系统.md
  功能：管理YYY功能和状态

【State模式】(16个)
- XXXState → XXX阶段状态.md
  功能：XXX阶段的业务逻辑

- YYYState → YYY阶段状态.md
  功能：YYY阶段的主要逻辑
...
```

---

### 步骤3：检查文档覆盖率

**任务**：检查每个组件是否已有对应文档，并评估质量

```javascript
// 对于每个组件
for (const comp of components) {
  // 根据组件类型和discovered-patterns.json推断文档路径
  let docDir;
  if (comp.type === 'system') {
    docDir = 'markdown/systems/';
  } else if (comp.patternType === 'custom' && comp.docDir) {
    docDir = `markdown/${comp.docDir}`;
  } else {
    docDir = `markdown/${comp.type}s/`;  // 默认复数化
  }

  const docPath = `${docDir}${comp.chineseName}`;

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

- [ ] `markdown/{推断路径}/XXX业务系统.md`
  - 类名：XXXServerSystem
  - 路径：behavior_packs/.../XXXServerSystem.py
  - 功能：处理XXX业务的服务端逻辑
  - 状态：⚠️ 待补充

- [ ] `markdown/{推断路径}/YYY业务系统.md`
  - 类名：YYYServerSystem
  - 路径：behavior_packs/.../YYYServerSystem.py
  - 功能：管理YYY功能和状态
  - 状态：⚠️ 待补充

### State模式组件 (16个)

- [ ] `markdown/{推断路径}/XXX阶段状态.md`
  - 类名：XXXState
  - 路径：behavior_packs/.../XXXState.py
  - 功能：XXX阶段的业务逻辑
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
- XXXServerSystem → XXX业务系统.md
  功能：处理XXX业务的服务端逻辑

- YYYServerSystem → YYY业务系统.md
  功能：管理YYY功能和状态

【项目特定组织】(16个)
- XXXState → XXX阶段状态.md
- YYYState → YYY阶段状态.md
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
1. XXX业务系统.md
2. YYY业务系统.md

【项目特定组织】
1. XXX阶段状态.md
2. YYY阶段状态.md
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
