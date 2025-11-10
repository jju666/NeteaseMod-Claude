# /enhance-docs - AI驱动的文档内容生成

批量补充文档待补充清单中的内容，AI深度分析源代码，生成高质量文档。

---

## 🎯 核心功能

1. **智能前置检查** - 自动检测是否需要先运行 `/validate-docs`
2. **高质量文档生成** - AI深度阅读源代码，生成完整文档内容（非占位符）
3. **智能批量处理** - 支持按组件类型、按优先级批量生成
4. **进度追踪** - 实时显示生成进度，自动更新待补充清单

---

## 📋 执行流程

### 步骤0：前置检查（新增⭐）

**任务**：检查是否存在必要的前置文件

```javascript
// 1. 检查discovered-patterns.json是否存在
if (!exists(".claude/discovered-patterns.json")) {
  console.log("❌ 未找到自适应发现结果文件");
  console.log("");
  console.log("请先运行以下命令：");
  console.log("  /discover");
  console.log("  或: node lib/adaptive-doc-discovery.js");
  console.log("");
  return; // 终止执行
}

// 2. 检查清单文件是否存在
const todoListPath = "markdown/文档待补充清单.md";

if (!exists(todoListPath)) {
  // 清单不存在，提示用户先运行 /validate-docs
  console.log("❌ 未找到文档待补充清单");
  console.log("");
  console.log("请先运行以下命令：");
  console.log("  /validate-docs");
  console.log("");
  console.log("该命令将：");
  console.log("  - 自动发现项目组件");
  console.log("  - AI推断规范化的文档名");
  console.log("  - 生成文档待补充清单");

  return; // 终止执行
}
```

---

### 步骤1：读取待补充清单

**任务**：读取 `markdown/文档待补充清单.md`，提取所有未完成的待补充项

```javascript
// 读取清单文件
const content = Read(file_path="markdown/文档待补充清单.md");

// 解析未完成的项（标记为 `- [ ]` 的项）
const todoItems = [];

// 正则匹配：- [ ] `markdown/{推断路径}/XXX系统.md`
const regex = /- \[ \] `(markdown\/[^`]+)`\s+- 类名：(\w+)\s+- 路径：(.+)\s+- 功能：(.+)/g;

let match;
while ((match = regex.exec(content)) !== null) {
  todoItems.push({
    docPath: match[1],
    className: match[2],
    sourcePath: match[3],
    description: match[4],
    type: inferTypeFromClassName(match[2]) // 从类名推断类型，而非路径
  });
}

// inferTypeFromClassName实现（使用discovered-patterns.json）：
function inferTypeFromClassName(className) {
  // 读取discovered-patterns.json
  const discovered = JSON.parse(Read(".claude/discovered-patterns.json"));
  const { officialConcepts, customPatterns } = discovered.patterns;

  // 检查是否是System
  if (className.endsWith('ServerSystem') || className.endsWith('ClientSystem')) {
    return 'system';
  }

  // 检查是否是Component
  if (officialConcepts.components.some(c => c.className === className)) {
    return 'component';
  }

  // 检查自定义模式
  for (const [patternKey, pattern] of Object.entries(customPatterns)) {
    if (className.endsWith(pattern.suffix)) {
      return patternKey;  // 'state', 'preset', 'manager' 等
    }
  }

  // 默认
  return 'unknown';
}

// 示例结果：
// ShopServerSystem → 'system'
// WaitingState → 'state' (如果项目实际使用State模式)
// PayManager → 'manager' (如果项目实际使用Manager模式)
```

**输出示例**：
```
[读取待补充清单]
- 发现 18 个待补充项
  - Systems: 2 个
  - [State模式]: 16 个
  - [Preset模式]: 2 个
```

---

### 步骤2：智能分组和优先级排序（新增⭐）

**任务**：按组件类型分组，标记核心组件

```javascript
// 1. 按类型分组（动态识别项目中实际使用的组件类型）
const grouped = {};

// 自动提取所有唯一的组件类型
const uniqueTypes = [...new Set(todoItems.map(item => item.type))];

// 为每种类型创建分组
for (const type of uniqueTypes) {
  grouped[type] = todoItems.filter(item => item.type === type);
}

// grouped可能包含：
// { system: [...], state: [...], preset: [...], manager: [...], ... }

// 2. 标记核心组件（可选，供用户选择优先生成）
// 核心组件定义：被多处引用的组件
for (const item of todoItems) {
  // 使用 Grep 搜索引用次数
  const references = Grep(item.className, output_mode="count");
  item.priority = references > 5 ? 'high' : 'normal';
}
```

---

### 步骤3：展示清单并询问用户

**任务**：使用 AskUserQuestion 工具询问补充范围

```javascript
// 动态生成选项（基于实际发现的组件类型）
const options = [
  {
    label: "全部补充",
    description: `补充所有 ${todoItems.length} 个文档（预计Token: ${todoItems.length * 5}-${todoItems.length * 10}k）`
  },
  {
    label: "只补充核心组件",
    description: "优先补充被频繁引用的核心组件（预计Token: 30-50k, 时间: 30分钟）"
  }
];

// 为每种组件类型添加选项（基于discovered-patterns.json动态生成）
for (const [type, items] of Object.entries(grouped)) {
  let typeName;
  if (type === 'system') {
    typeName = 'Systems';
  } else if (type === 'component') {
    typeName = 'Components';
  } else {
    // 从discovered-patterns.json获取后缀名，转换为中文
    const discovered = JSON.parse(Read(".claude/discovered-patterns.json"));
    const pattern = discovered.patterns.customPatterns[type];
    typeName = pattern ? `[${pattern.suffix}模式]组件` : `[${type}]组件`;
  }

  options.push({
    label: `只补充 ${typeName}`,
    description: `只补充 ${items.length} 个${typeName}（预计Token: ${items.length * 5}-${items.length * 10}k）`
  });
}

options.push({
  label: "自定义选择",
  description: "让我选择具体要补充的文档"
});

AskUserQuestion({
  questions: [{
    question: `发现 ${todoItems.length} 个待补充项，请选择补充范围：`,
    header: "补充范围",
    multiSelect: false,
    options: options
  }]
})
```

**根据用户选择确定任务列表**：
- "全部补充" → `tasksToComplete = todoItems`
- "只补充核心组件" → `tasksToComplete = todoItems.filter(item => item.priority === 'high')`
- "只补充 {类型}" → `tasksToComplete = grouped[对应类型]`
- "自定义选择" → 展示列表，让用户勾选

---

### 步骤4：批量生成文档（使用Task工具并行处理）

**任务**：对每个待补充项，使用AI深度分析源代码并生成完整文档

**实现方式**：使用 Task 工具并行处理（推荐每批 5-10 个组件）

```javascript
// 分批处理（避免超时）
const batchSize = 5;
const batches = chunk(tasksToComplete, batchSize);

let completed = 0;
let failed = 0;

for (const batch of batches) {
  // 并行处理一批
  const results = await Promise.all(
    batch.map(item => generateDocForComponent(item))
  );

  // 统计结果
  results.forEach(result => {
    if (result.success) {
      completed++;
      console.log(`✅ ${result.docPath}`);
    } else {
      failed++;
      console.log(`❌ ${result.docPath} - ${result.error}`);
    }
  });

  console.log(`进度: ${completed}/${tasksToComplete.length}`);
}
```

**单个文档生成函数**：

```javascript
async function generateDocForComponent(item) {
  return Task({
    subagent_type: "general-purpose",
    model: "sonnet",  // 使用 sonnet 保证质量
    description: `为 ${item.className} 生成详细文档`,
    prompt: `
你是MODSDK文档撰写专家。请为以下组件生成详细的技术文档。

**组件信息：**
- 类名：${item.className}
- 源码路径：${item.sourcePath}
- 文档路径：${item.docPath}
- 功能描述：${item.description}

**任务：**
1. 使用 Read 工具读取源代码（${item.sourcePath}）
2. 深度分析代码结构：
   - 类的职责和设计目的
   - 关键方法的实现逻辑
   - 数据流和调用关系
   - 与其他组件的交互
3. 生成完整的技术文档

**文档结构要求：**

# ${item.className.replace(/System|State|Preset/g, '')}

> **类名**：${item.className}
> **文件路径**：${item.sourcePath}
> **功能描述**：${item.description}

## 概述

[200-300字]
- 该组件的核心职责
- 在项目中的角色定位
- 主要解决的问题

## 架构设计

### 设计原理

[300-500字]
- 为什么这样设计？
- 关键设计决策及原因
- 与MODSDK架构的契合点

### 核心流程

[使用Mermaid流程图或文字描述]

\`\`\`mermaid
graph TD
    A[开始] --> B[步骤1]
    B --> C[步骤2]
    C --> D[结束]
\`\`\`

## API文档

### 核心方法

#### 方法1：methodName()

**功能**：[一句话描述]

**参数**：
- \`param1\` (类型) - 说明
- \`param2\` (类型) - 说明

**返回值**：[类型] - 说明

**示例代码**：
\`\`\`python
# 使用示例
result = self.methodName(param1, param2)
\`\`\`

[为所有公开方法重复此结构]

## 数据流分析

[300-500字]
- 输入数据来源
- 数据处理流程
- 输出数据去向
- 关键数据结构

## 使用示例

### 示例1：[常见场景]

\`\`\`python
# 完整的使用示例代码
class MySystem(ServerSystem):
    def __init__(self, namespace, systemName):
        super(MySystem, self).__init__(namespace, systemName)
        # 初始化逻辑
\`\`\`

### 示例2：[进阶场景]

...

## 常见问题

### 问题1：[标题]

**现象**：[描述问题现象]

**原因**：[分析原因]

**解决方案**：
\`\`\`python
# 解决代码
\`\`\`

### 问题2：[标题]

...

## 注意事项

- ⚠️ [重要注意事项1]
- ⚠️ [重要注意事项2]
- 💡 [最佳实践建议]

## 相关文档

- [开发规范.md](../开发规范.md) - 开发规范
- [问题排查.md](../问题排查.md) - 问题排查
- [其他相关System文档]

---

**要求：**
1. 文档总字数 1500-3000 字
2. 必须包含至少 2 个代码示例
3. 数据流必须清晰（流程图或文字描述）
4. 常见问题至少 2 个
5. 引用相关的开发规范（如果代码涉及CRITICAL规范）

**输出格式：**
直接返回完整的Markdown文档内容（不要包含额外说明）
`
  });
}
```

---

### 步骤5：更新文档待补充清单

**任务**：将已补充的项标记为完成 `- [x]`

```javascript
// 对于每个成功生成的文档
for (const item of completedItems) {
  Edit(
    file_path="markdown/文档待补充清单.md",
    old_string=`- [ ] \`${item.docPath}\``,
    new_string=`- [x] \`${item.docPath}\``
  );
}
```

---

### 步骤6：输出完成报告

**输出报告格式**：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 文档补充完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📊 补充统计

- 已补充：18 个文档
- 失败：0 个
- 剩余待补充：0 个
- 文档覆盖率：100%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 📝 更新的文档

【Systems】(2个)
- ✅ markdown/{推断路径}/XXX业务系统.md (2850字)
- ✅ markdown/{推断路径}/YYY业务系统.md (2640字)

【项目特定组织】(16个)
- ✅ markdown/{推断路径}/XXX阶段状态.md (1890字)
- ✅ markdown/{推断路径}/YYY阶段状态.md (2120字)
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 💡 下一步

**验证文档质量**：
/validate-docs

**开始开发**：
/cc "任务描述"

开发过程中，AI会自动维护相关文档，使文档越来越完善。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## ⚠️ 重要提示

1. **Token成本**：
   - 每个文档生成约 5-10k tokens（使用 sonnet 模型）
   - 18个文档预计消耗 90-180k tokens
   - 建议分批补充，避免一次性消耗过多

2. **生成质量**：
   - 使用 sonnet 模型确保高质量输出
   - 每个文档包含完整的架构分析、代码示例、常见问题
   - 文档字数控制在 1500-3000 字

3. **并行处理**：
   - 分批处理（每批 5-10 个），避免超时
   - 显示实时进度，提升用户体验

4. **错误处理**：
   - 如果单个文档生成失败，不影响其他文档
   - 记录失败的文档，供人工处理

5. **与 /validate-docs 配合**：
   - validate-docs 负责"发现 + 规范化"
   - enhance-docs 负责"内容生成"
   - 两者配合实现完整的文档工作流

---

## 📚 文档模板参考

生成的文档应遵循以下质量标准：

- ✅ **完整性**：包含概述、架构、API、示例、问题、注意事项
- ✅ **实用性**：代码示例可直接运行，问题解决方案经过验证
- ✅ **准确性**：基于源代码分析，而非臆测
- ✅ **可读性**：结构清晰，层次分明，重点突出
- ✅ **维护性**：包含相关文档引用，便于查阅

---

## 🔄 持续维护

文档生成后，通过 `/cc` 命令在开发过程中自动维护：

1. **任务开始时**：查阅相关文档，避免错误
2. **任务执行中**：记录代码修改和新增知识
3. **任务完成时**：自动更新相关文档

**真正实现"文档越用越完善"的理念。**
