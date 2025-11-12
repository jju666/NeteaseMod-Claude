# /mc-discover - 自适应项目结构发现

自动扫描MODSDK项目，发现组件类型和文档组织方式。

---

## 🎯 步骤0：理解项目上下文（新增步骤 v18.0）⭐

在开始结构发现前，**必须**先理解本项目的基本情况和文档组织方式。

### 0.1 读取项目指导文档

```
Read ../../CLAUDE.md
```

**理解目标**：
- 📌 项目基本信息（项目名称、类型、路径）
- 🎯 项目文档组织方式（已有目录结构、命名规范）
- 📝 项目背景和架构特点

**输出**（简短总结）：
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 步骤0检查点：项目上下文理解
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

项目：基于Claude的MODSDK开发工作流
类型：{{PROJECT_TYPE}}
已有文档目录：（列出markdown/下的主要目录）

⚠️ 确认检查点输出完成后，才能进入结构发现！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 0.2 项目文档结构预扫描（v18.0 智能路由）⭐

在发现代码结构前，先扫描现有文档组织方式，确定项目已经采用的文档模式：

```bash
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 现有文档结构扫描"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 扫描markdown/下的所有子目录（排除通用目录）
find ../../markdown -maxdepth 1 -type d ! -name "markdown" ! -name "core" 2>/dev/null | while read dir; do
    dir_name=$(basename "$dir")
    file_count=$(find "$dir" -type f -name "*.md" 2>/dev/null | wc -l)
    if [ $file_count -gt 0 ]; then
        echo "  ├─ $dir_name/ ($file_count 个文档)"
        # 展示前3个文档作为样例
        find "$dir" -type f -name "*.md" 2>/dev/null | head -3 | while read file; do
            echo "     └─ $(basename "$file")"
        done
    fi
done

echo ""
echo "💡 提示：结构发现将参考现有文档组织方式"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## 🎯 功能

1. **自动发现组件类型** - 识别System、Component及任意自定义模式（State、Preset、Manager等）
2. **推断目录结构** - 分析项目实际使用的文档组织方式
3. **生成映射规则** - 为后续文档维护工具提供依据
4. **零配置** - 完全基于代码分析，无需手动配置

---

## 📋 执行流程

### 步骤1：运行自适应发现工具

```bash
node lib/adaptive-doc-discovery.js
```

### 步骤2：查看发现报告

工具会输出：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 自适应发现报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## MODSDK官方核心概念

  📦 Systems: 5个
     - ShopServerSystem
     - TeamServerSystem
     - GameServerSystem
     ... 等5个

## 项目自定义组织模式

  🔹 [State模式] - 12个类
     文档目录: states/ ✅ 已存在
     示例: WaitingState, PlayingState

  🔹 [Preset模式] - 3个类
     文档目录: presets/ 📝 需创建
     示例: ShopPreset, TeamPreset

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 步骤3：自动生成配置

发现结果会保存到 `.claude/mc-discovered-patterns.json`，供其他工具使用：

```json
{
  "timestamp": "2025-11-12T...",
  "projectRoot": "d:/EcWork/基于Claude的MODSDK开发工作流",
  "patterns": {
    "officialConcepts": {
      "systems": [...],
      "components": [...]
    },
    "customPatterns": {
      "state": {
        "suffix": "State",
        "count": 12,
        "docDirCandidate": "states/",
        "docDirExists": true
      },
      "preset": {
        "suffix": "Preset",
        "count": 3,
        "docDirCandidate": "presets/",
        "docDirExists": false
      }
    }
  }
}
```

---

## 🔄 与其他工具的集成

### /mc-docs集成

`/mc-docs` 会自动读取发现结果：

```javascript
// 1. 读取discovered-patterns.json
const patterns = JSON.parse(fs.readFileSync('.claude/mc-discovered-patterns.json'));

// 2. 动态搜索组件
for (const [type, pattern] of Object.entries(patterns.customPatterns)) {
  // 搜索该类型的所有类
  const classes = Grep(`class \\w+${pattern.suffix}`, ...);

  // 推断文档路径
  for (const cls of classes) {
    const docPath = `markdown/${pattern.docDirCandidate}${chineseName}.md`;
    // 检查文档是否存在...
  }
}
```

### /mc-docs --gen集成

`/mc-docs --gen` 会使用发现的映射规则：

```javascript
// 根据类名推断文档路径
function inferDocPath(className, patterns) {
  // 检查是否是System
  if (className.endsWith('ServerSystem') || className.endsWith('ClientSystem')) {
    return `markdown/systems/${chineseName}系统.md`;
  }

  // 检查是否匹配自定义模式
  for (const [type, pattern] of Object.entries(patterns.customPatterns)) {
    if (className.endsWith(pattern.suffix)) {
      return `markdown/${pattern.docDirCandidate}${chineseName}${pattern.suffix}.md`;
    }
  }

  // 默认
  return `markdown/components/${chineseName}.md`;
}
```

---

## 📊 识别逻辑

### MODSDK官方核心概念

| 概念 | 识别规则 | 示例 |
|-----|---------|------|
| **System** | 类名以ServerSystem/ClientSystem结尾 | ShopServerSystem, UIClientSystem |
| **Component** | 调用RegisterComponent注册 | ShopComponent (需代码分析) |

### 项目自定义模式

**识别规则**：
1. 提取所有类名的后缀（大写字母开头的单词）
2. 统计每种后缀的出现次数
3. 出现3次及以上，认为是项目使用的模式

**示例**：
```
发现类名：
- WaitingState
- PlayingState
- EndingState
- ...（共12个）

→ 识别为 [State模式]，文档目录推断为 states/
```

---

## ⚙️ 配置选项

### 手动指定behavior_packs路径

如果自动定位失败，可以修改代码：

```javascript
const discovery = new AdaptiveDocDiscovery('d:/EcWork/基于Claude的MODSDK开发工作流');
discovery.behaviorPackPath = '/custom/path/to/behavior_packs';
await discovery.discoverProjectStructure();
```

### 调整模式识别阈值

默认阈值为3（出现3次及以上认为是模式），可以调整：

```javascript
// 在inferCustomPatterns方法中
if (count >= 2) {  // 改为2
  // ...
}
```

---

## 💡 最佳实践

1. **首次部署工作流时运行**
   ```bash
   /mc-discover  # 了解项目结构
   ```

2. **添加新组件类型后重新运行**
   - 如果项目开始使用新的组织模式（如Manager、Controller）
   - 重新运行/mc-discover更新映射规则

3. **与文档维护工具配合使用**
   ```bash
   /mc-discover          # 步骤1：发现项目结构
   /mc-docs     # 步骤2：验证文档完整性
   /mc-docs --gen      # 步骤3：补充文档内容
   ```

---

## 🐛 故障排查

### 问题1：未找到behavior_packs目录

**原因**：项目结构不标准或不是MODSDK项目

**解决**：
- 确认项目包含`behavior_packs/`目录
- 或手动指定路径

### 问题2：未发现任何自定义模式

**现象**：只有System，没有其他模式

**说明**：这是正常的！说明项目只使用MODSDK官方概念，没有自定义组织方式。

### 问题3：识别了错误的模式

**原因**：类名后缀偶然重复（如：TestData、GameData都以Data结尾）

**解决**：
- 调高识别阈值
- 或在代码中过滤掉特定后缀

---

## 📚 参考

- **核心代码**: `lib/adaptive-doc-discovery.js`
- **输出文件**: `.claude/mc-discovered-patterns.json`
- **CLAUDE.md**: 自适应机制说明
