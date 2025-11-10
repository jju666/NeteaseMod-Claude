# /initmc

自动部署完整的AI辅助开发工作流到当前项目。

## 支持的参数

- `--detail=<level>`: 设置文档详细度（simple/medium/full），默认medium
- `--parallel=<N>`: 设置并行子代理数量，默认3
- `--mode=auto`: 完全自动模式，不询问确认
- `--overwrite`: 覆盖现有文档

## 使用示例

```bash
# 基本用法（推荐）
/initmc

# 生成详细文档
/initmc --detail=full

# 完全自动模式
/initmc --mode=auto

# 覆盖现有文档
/initmc --overwrite
```

---

## 执行流程

你需要执行以下步骤来初始化工作流：

### 📍 步骤0：准备工作

1. **检查当前目录是否为MODSDK项目**：
   ```bash
   ls modMain.py
   ```
   - 如果不存在modMain.py，提示用户："当前目录不是MODSDK项目，请在项目根目录执行 /initmc"
   - 如果存在，继续下一步

2. **读取参数**（从用户命令中提取）：
   ```python
   # 默认参数
   detail_level = "medium"  # simple / medium / full
   parallel_count = 3
   auto_mode = False
   overwrite = False

   # 解析用户参数（如果有）
   if "--detail=full" in 用户命令:
       detail_level = "full"
   if "--mode=auto" in 用户命令:
       auto_mode = True
   # ... 以此类推
   ```

---

### 📊 步骤1：分析当前项目（5-10分钟）

1. **调用项目分析器**：

   使用Python执行分析脚本：
   ```bash
   # 首先获取工作流项目根目录（通过查找CLAUDE.md的位置）
   # 这样可以支持工作流项目clone到任意位置
   python -c "
import sys
import os

# 查找工作流根目录（向上查找包含workflow-generator目录的位置）
current_dir = os.path.dirname(os.path.abspath('{{CLAUDE_MD_PATH}}'))
workflow_root = current_dir

# 添加workflow-generator到路径
sys.path.append(os.path.join(workflow_root, 'workflow-generator'))
from analyzer import ProjectAnalyzer

analyzer = ProjectAnalyzer('{{CURRENT_PROJECT_PATH}}')
report = analyzer.analyze()
print(report.to_markdown())
"
   ```

   **注意**：
   - `{{CLAUDE_MD_PATH}}` 会被替换为CLAUDE.md的实际路径（自动检测）
   - `{{CURRENT_PROJECT_PATH}}` 会被替换为当前工作目录的绝对路径

2. **保存分析结果**：
   - 将输出的Markdown报告保存到变量中
   - 提取关键信息：项目类型、Systems数量、项目规模等

---

### 🤔 步骤2：展示分析报告并确认

根据项目规模选择交互策略：

**2.1 小项目（≤10 Systems）** - 一次确认模式：

```
输出：
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 项目分析完成
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

项目类型: [项目类型]
项目规模: 小型项目
Systems数量: X个
现有文档: Y个

预计生成:
 - Layer 1（通用层）: 15个文件
 - Layer 2（架构层）: X个系统文档
 - Layer 3（业务层）: 框架文档

预估消耗:
 - Token: 约30k
 - 时间: 约5分钟

是否继续部署工作流？[Y/n]
```

**2.2 中型项目（11-30 Systems）** - 详细报告确认：

输出完整的分析报告（使用步骤1生成的Markdown）
然后询问："是否继续部署工作流？[Y/n]"

**2.3 大型项目（>30 Systems）** - 多步确认（如果不是auto模式）：

第一步：输出分析报告
询问："是否继续深度分析？[Y/n]"

第二步：（用户确认后）展示文档生成计划
询问："是否执行生成？[Y/n]"

**注意**：如果 `auto_mode=True`，跳过所有确认，直接执行

---

### 🚀 步骤3：生成工作流文档（自动执行）

用户确认后，执行以下操作：

#### 3.1 生成Layer 1（通用层）⭐ 核心

**重要说明**：使用内置模板系统自动生成所有文档，无需依赖外部参考项目。

**3.1.1 准备项目信息**：

首先，提取当前项目的关键信息：
```python
# 从步骤1的分析结果中提取
PROJECT_PATH = "{{当前项目绝对路径}}"
PROJECT_NAME = "{{项目名称}}"
BUSINESS_TYPE = "{{项目类型}}"  # RPG / BedWars / General
USES_APOLLO = {{True/False}}
USES_ECPRESET = {{True/False}}
SYSTEMS_COUNT = {{Systems数量}}

# 路径信息
SERVER_CODE_PATH = "{{服务端代码路径}}"  # 通过扫描找到
CLIENT_CODE_PATH = "{{客户端代码路径}}"  # 通过扫描找到
SDK_DOC_PATH = "D:\EcWork\netease-modsdk-wiki"
```

**3.1.2 复制并修改 CLAUDE.md**：

```python
# 读取内置CLAUDE.md模板（使用动态路径）
import sys
sys.path.append('workflow-generator')
from config import TEMPLATES_DIR
import os

模板路径 = os.path.join(TEMPLATES_DIR, "CLAUDE.md.template")
模板内容 = Read(file_path=模板路径)

# 准备占位符替换（占位符生成函数见下方3.1.3后）
替换后内容 = 模板内容.replace("{{PROJECT_PATH}}", PROJECT_PATH)
替换后内容 = 替换后内容.replace("{{PROJECT_NAME}}", PROJECT_NAME)
替换后内容 = 替换后内容.replace("{{CURRENT_DATE}}", 当前日期)
# ... 其他占位符替换

# 写入目标项目
Write(file_path=PROJECT_PATH+"/CLAUDE.md", content=替换后内容)
```

**3.1.3 生成定制化的 `/cc` 命令** ⭐ 最关键：

```bash
# 读取模板（使用动态路径）
模板路径 = os.path.join(TEMPLATES_DIR, ".claude/commands/cc.md.template")
模板内容 = Read(file_path=模板路径)

# 准备替换内容
占位符替换表 = {
    "{{PROJECT_PATH}}": PROJECT_PATH,
    "{{EXAMPLE_TASKS}}": 生成示例任务列表(),  # 见下方函数
    "{{SDK_DOC_PATH}}": SDK_DOC_PATH,
    "{{LOG_FILES}}": 生成日志文件列表(),  # 见下方函数
    "{{ARCHITECTURE_DOCS_SECTION}}": 生成架构文档部分(),  # 见下方函数
    "{{BUSINESS_DOCS_SECTION}}": 生成业务文档部分(),  # 见下方函数
    "{{CRITICAL_RULES}}": 生成CRITICAL规范列表(),  # 见下方函数
    "{{CORE_PATHS}}": 生成核心路径列表(),  # 见下方函数
    "{{NBT_CHECK_SECTION}}": 生成NBT检查部分() if BUSINESS_TYPE=="RPG" else "",
}

# 执行替换
替换后内容 = 模板内容
for 占位符, 替换值 in 占位符替换表.items():
    替换后内容 = 替换后内容.replace(占位符, 替换值)

# 创建目标目录并写入
mkdir -p PROJECT_PATH/.claude/commands
Write(file_path=PROJECT_PATH+"/.claude/commands/cc.md", content=替换后内容)
```

**占位符生成函数**：

```python
def 生成示例任务列表():
    """根据项目类型生成示例任务"""
    if BUSINESS_TYPE == "RPG":
        return """
/cc 修复战斗系统的暴击伤害计算BUG
/cc 为装备系统添加新的饰品充能功能
/cc 优化玩家属性计算性能
/cc 日志显示玩家死亡时出现AttributeError
"""
    elif BUSINESS_TYPE == "BedWars":
        return """
/cc 修复商店预设在打开UI时报错的问题
/cc 为队伍系统添加队伍聊天功能
/cc 优化资源点刷新逻辑
/cc 日志中显示GetComponent返回None
"""
    else:
        return """
/cc 修复System初始化错误
/cc 添加新功能模块
/cc 优化代码性能
/cc 日志显示错误
"""

def 生成日志文件列表():
    """生成日志文件路径列表"""
    日志文件 = []
    可能的日志文件 = ["日志.log", "服务端日志.log", "客户端日志.log", "server.log", "client.log"]

    for 日志 in 可能的日志文件:
        日志路径 = os.path.join(PROJECT_PATH, 日志)
        if os.path.exists(日志路径):
            日志文件.append("     - `{}`".format(日志路径))

    if not 日志文件:
        日志文件.append("     - `{}/日志.log` - 主日志文件".format(PROJECT_PATH))

    return "\n".join(日志文件)

def 生成架构文档部分():
    """生成架构文档查阅部分"""
    if USES_APOLLO:
        return """
4. **Apollo架构文档** - 数据库与网络架构
   - 路径：`D:/EcWork/netease-modsdk-wiki/docs/mcdocs/2-Apollo`
   - 涉及数据存储、Redis、MySQL时查阅
"""
    else:
        return ""

def 生成业务文档部分():
    """生成业务文档查阅部分"""
    if BUSINESS_TYPE == "RPG":
        return """
5. **NEWRPG详细技术文档** - 系统设计原则（涉及RPG模块时强制）⭐
   - 路径：`markdown/NEWRPG/`
   - 使用Grep智能搜索相关文档
   - 优先阅读主系统文档（如15-强化系统.md）
"""
    elif USES_ECPRESET:
        return """
5. **Presets文档** - 预设开发指南
   - 路径：`markdown/presets/`
   - 查阅预设开发规范和示例
"""
    else:
        return """
5. **Systems文档** - 系统实现文档
   - 路径：`markdown/systems/`
   - 查阅对应系统的技术文档
"""

def 生成CRITICAL规范列表():
    """生成CRITICAL规范列表"""
    规范列表 = []

    # 通用规范
    规范列表.append("""
1. **System生命周期**：
   - ❌ 禁止在__init__中调用GetComponent
   - ✅ 在__init__中手动调用self.Create()
   - ✅ 在Create中初始化组件和事件

2. **模块导入规范**：
   - ❌ 禁止使用 `import modConfig`
   - ✅ 同级文件使用 `from modConfig import ...`
   - ✅ 子目录使用 `from MGModScripts.modConfig import ...`

3. **双端隔离原则**：
   - ❌ 禁止跨端GetSystem
   - ✅ 使用NotifyToClient/NotifyToServer通信
""")

    # 项目特定规范
    if USES_APOLLO:
        规范列表.append("""
4. **Apollo1.0架构规范**：
   - ✅ 使用Apollo SDK获取数据库连接
   - ❌ 禁止直接创建数据库连接
""")

    if USES_ECPRESET:
        规范列表.append("""
4. **ECPreset数据存储规范**：
   - ❌ 禁止在PresetDefinition类中存储运行时状态
   - ✅ 使用instance.set_data/get_data存储实例数据
""")

    if BUSINESS_TYPE == "RPG":
        规范列表.append("""
5. **NBT兼容性**：
   - ✅ 涉及装备/物品操作时，必须对比老RPG代码
   - ✅ 确保NBT字段名称100%一致
""")

    return "".join(规范列表)

def 生成核心路径列表():
    """生成核心路径列表"""
    路径列表 = []
    路径列表.append("- **项目根目录**: `{}`".format(PROJECT_PATH))

    if SERVER_CODE_PATH:
        路径列表.append("- **服务端代码**: `{}`".format(SERVER_CODE_PATH))
    if CLIENT_CODE_PATH:
        路径列表.append("- **客户端代码**: `{}`".format(CLIENT_CODE_PATH))

    路径列表.append("- **SDK文档**: `{}`".format(SDK_DOC_PATH))

    if BUSINESS_TYPE == "RPG":
        路径列表.append("- **老RPG项目**: `D:\mg`")

    return "\n".join(路径列表)

def 生成NBT检查部分():
    """生成NBT兼容性检查部分（仅RPG项目）"""
    return """
4. NBT字段兼容性检查（装备/物品操作时强制）:
   - 已对比老RPG代码: [文件路径:行号]
   - NBT字段列表: [field1, field2, field3, ...]
   - 兼容性确认: ✅ 字段名称100%一致
   (如不涉及装备/物品NBT操作，可跳过此项)
"""
```

**3.1.4 复制其他通用文档**：

执行以下操作来复制文档和命令文件（**重要：这些是实际要执行的操作，不是伪代码**）：

**步骤A：复制额外的命令文件** ⭐ 必须执行

1. 读取全局工作流目录中的`enhance-docs.md`：
   ```
   Read(file_path="C:/Users/28114/.claude-modsdk-workflow/.claude/commands/enhance-docs.md")
   ```

2. 将读取的内容写入目标项目：
   ```
   Write(file_path="<项目路径>/.claude/commands/enhance-docs.md", content=<上一步读取的内容>)
   ```

3. 读取全局工作流目录中的`validate-docs.md`：
   ```
   Read(file_path="C:/Users/28114/.claude-modsdk-workflow/.claude/commands/validate-docs.md")
   ```

4. 将读取的内容写入目标项目：
   ```
   Write(file_path="<项目路径>/.claude/commands/validate-docs.md", content=<上一步读取的内容>)
   ```

**步骤B：复制通用文档**

对于以下每个文件，执行Read → Write操作：

全局源目录：`C:/Users/28114/.claude-modsdk-workflow/markdown/`

1. **开发规范.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/开发规范.md`
   - Write: `<项目路径>/markdown/开发规范.md`

2. **问题排查.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/问题排查.md`
   - Write: `<项目路径>/markdown/问题排查.md`

3. **快速开始.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/快速开始.md`
   - Write: `<项目路径>/markdown/快速开始.md`

4. **开发指南.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/开发指南.md`
   - Write: `<项目路径>/markdown/开发指南.md`

5. **API速查.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/API速查.md`
   - Write: `<项目路径>/markdown/API速查.md`

6. **MODSDK核心概念.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/MODSDK核心概念.md`
   - Write: `<项目路径>/markdown/MODSDK核心概念.md`

**步骤C：复制AI辅助文档**

1. **任务类型决策表.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/ai/任务类型决策表.md`
   - Write: `<项目路径>/markdown/ai/任务类型决策表.md`

2. **快速通道流程.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/ai/快速通道流程.md`
   - Write: `<项目路径>/markdown/ai/快速通道流程.md`

3. **上下文管理规范.md**：
   - Read: `C:/Users/28114/.claude-modsdk-workflow/markdown/ai/上下文管理规范.md`
   - Write: `<项目路径>/markdown/ai/上下文管理规范.md`

**步骤D：创建README.md**

使用Write工具创建项目README：
```
Write(file_path="<项目路径>/README.md", content=<根据项目信息生成的README内容>)
```

**步骤E：创建项目状态文档**

```
Write(file_path="<项目路径>/markdown/项目状态.md", content="# 项目状态\n\n⚠️ **待补充**\n")
```

**步骤F：创建tasks目录说明**

```
Write(file_path="<项目路径>/tasks/README.md", content=<生成tasks说明文档>)
```

---

#### 3.2 生成Layer 2（架构层）- 系统文档

对于每个System，生成中等详细度的文档：

```python
# 读取步骤1分析得到的Systems列表
for system_name, system_info in 分析结果.systems.items():
    生成系统文档(system_name, system_info)

def 生成系统文档(system_name, system_info):
    """生成单个System的中等详细度文档"""

    详细度 = system_info.get_detail_level()  # simple / medium / detailed

    # 生成文档内容
    文档内容 = """
# {system_name}

> **类型**: {system_type}
> **文件路径**: `{file_path}`
> **代码行数**: {lines}
> **复杂度**: {complexity}/10
> **推荐详细度**: {detail_level}

---

## 📋 概述

{system_name} 是项目中的 {system_type}，主要负责...

⚠️ **待补充**: 请在后续开发中补充该系统的详细业务逻辑。

---

## 🏗️ 架构设计

### 类结构

```python
class {system_name}({system_type}):
    # 主要方法（通过代码分析提取）
{methods}
```

---

## 🔧 主要方法

{method_list}

⚠️ **待补充**: 请在后续开发中补充主要方法的详细说明和示例。

---

## 📊 数据流

⚠️ **待补充**: 请在理解完整业务逻辑后补充数据流图。

---

## ❓ 常见问题

⚠️ **待补充**: 在开发过程中遇到问题时补充到此处。

---

## 📚 相关文档

- [开发规范](../开发规范.md)
- [问题排查](../问题排查.md)

---

_最后更新: {date} | 自动生成_
""".format(
        system_name=system_name,
        system_type=system_info.type,
        file_path=system_info.file_path,
        lines=system_info.lines_of_code,
        complexity=system_info.complexity_score,
        detail_level=详细度,
        methods=提取方法签名(system_info.content),
        method_list=生成方法列表(system_info.content),
        date=当前日期
    )

    # 写入文件
    Write(file_path=PROJECT_PATH+"/markdown/systems/{}.md".format(system_name),
          content=文档内容)

def 提取方法签名(content):
    """提取所有方法签名"""
    methods = re.findall(r'(def\s+\w+\s*\([^)]*\))', content)
    return "\n".join("    " + m for m in methods[:15])  # 只显示前15个

def 生成方法列表(content):
    """生成方法列表"""
    methods = re.findall(r'def\s+(\w+)\s*\(', content)
    return "\n".join("- `{}()` - 待补充说明".format(m) for m in methods[:20])
```

---

#### 3.3 生成Layer 3（业务层框架）

根据项目类型创建对应的目录结构：

```bash
if BUSINESS_TYPE == "RPG":
    mkdir -p PROJECT_PATH/markdown/NEWRPG
    Write(file_path=PROJECT_PATH+"/markdown/NEWRPG/README.md",
          content="# NEWRPG 系统文档\n\n⚠️ **待补充**: AI将在开发过程中逐步完善。\n")
elif USES_ECPRESET:
    mkdir -p PROJECT_PATH/markdown/presets
    Write(file_path=PROJECT_PATH+"/markdown/presets/README.md",
          content="# Presets 文档\n\n⚠️ **待补充**: AI将在开发过程中逐步完善。\n")
```

---

#### 3.4 生成文档待补充清单

```python
清单内容 = """
# 📝 文档待补充清单

> 本清单由 `/initmc` 自动生成于 {date}
> AI在开发过程中会逐步补充这些内容

---

## 🔴 Layer 2 - 架构层待补充

{layer2_items}

---

## 🟡 Layer 3 - 业务层待补充

- [ ] 补充业务系统详细文档
- [ ] 补充配置文档说明

---

## 📖 使用说明

1. 在开发过程中，AI会自动检测文档缺失
2. 在任务收尾时（步骤3.6），AI会询问是否更新文档
3. 批量补充：使用 `/enhance-docs` 命令

---

_最后更新: {date}_
""".format(
    date=当前日期,
    layer2_items=生成layer2待补充项()
)

Write(file_path=PROJECT_PATH+"/markdown/文档待补充清单.md", content=清单内容)

def 生成layer2待补充项():
    """生成Layer 2待补充项列表"""
    items = []
    for system_name, system_info in 分析结果.systems.items():
        if system_info.get_detail_level() in ["medium", "detailed"]:
            items.append("- [ ] `systems/{}.md` - 补充业务逻辑和数据流".format(system_name))
    return "\n".join(items)
```

---

### ✅ 步骤4：输出完成报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 工作流部署完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 生成统计:
- Layer 1（通用层）: 15个文件 ✅
  - CLAUDE.md
  - .claude/commands/cc.md ⭐
  - .claude/commands/enhance-docs.md ⭐
  - .claude/commands/validate-docs.md ⭐
  - markdown/开发规范.md
  - markdown/问题排查.md
  - markdown/ai/（3个AI文档）
  - 等...

- Layer 2（架构层）: {systems_count}个文件 ✅
  - markdown/systems/ ({systems_count}个系统文档)

- Layer 3（业务层）: 框架已创建 ✅
  - markdown/文档待补充清单.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 后续步骤:
1. ✅ 查阅 CLAUDE.md 了解AI工作流程
2. ✅ 使用 /cc "任务描述" 快速创建/继续任务
3. ✅ 查阅 markdown/文档待补充清单.md 了解待补充内容
4. ✅ AI会在开发过程中自动完善文档

🎯 可用命令:
- /cc "任务描述" - 快速任务执行器 ⭐
- /enhance-docs - 批量补充文档
- /validate-docs - 验证文档完整性

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 工作流已就绪，开始高效开发吧！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 错误处理

### 1. 未检测到modMain.py
```
❌ 错误: 当前目录不是MODSDK项目

请在项目根目录执行 /initmc 命令。
项目根目录应包含 modMain.py 文件。
```

### 2. markdown/目录已存在
```
⚠️  检测到现有文档

发现 markdown/ 目录已存在，包含 X 个文档。

选项:
1. 备份后继续（推荐）
2. 覆盖现有文档（需 --overwrite 参数）
3. 取消操作

是否备份现有文档后继续？[Y/n]
```

### 3. Python模块导入失败
```
❌ 错误: 无法导入项目分析器

请确保以下路径存在:
D:\EcWork\基于Claude的MODSDK开发工作流\workflow-generator\analyzer.py

如果问题持续，请检查Python环境配置。
```

---

## 注意事项

1. ⏱️ **首次执行耗时**: 小项目5分钟，大项目可能需要30分钟
2. 💰 **Token消耗**: 预计30k-120k，请确保预算充足
3. 📝 **文档质量**: Layer 1直接可用，Layer 2需补充，Layer 3是框架
4. 🔄 **自学习**: AI会在后续开发中逐步完善文档

---

现在开始执行 /initmc 命令！
