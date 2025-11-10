# /initmc

请自动部署完整的AI辅助开发工作流到当前项目。

## 你的任务

按照以下步骤执行工作流部署：

1. **检查当前目录** - 验证是否为MODSDK项目（包含modMain.py）
2. **分析项目结构** - 扫描Systems、代码规模
3. **展示分析报告** - 根据项目规模选择交互策略
4. **生成工作流文档** - 创建三层文档结构
5. **输出完成报告** - 展示生成统计和后续步骤

## 参数说明

- `--detail=<level>`: 设置文档详细度（simple/medium/full），默认medium
- `--parallel=<N>`: 设置并行子代理数量，默认3
- `--mode=auto`: 完全自动模式，不询问确认
- `--overwrite`: 覆盖现有文档

---

## 详细执行流程

### 📍 步骤0：准备工作

1. **检查当前目录类型**：
   ```bash
   # 检查是否为工作流项目本身
   ls CLAUDE.md && ls .claude/commands/initmc.md
   ```
   - 如果两者都存在 → **工作流项目本身**，输出提示并终止：
     ```
     ⚠️  检测到工作流项目本身

     /initmc 命令仅用于初始化新的MODSDK项目。
     当前目录是工作流项目本身，无需初始化。

     使用说明：
     1. 在需要初始化的MODSDK项目根目录执行 /initmc
     2. 工作流文件将从全局目录自动复制到目标项目

     全局工作流目录：~/.claude-modsdk-workflow/
     (Windows示例：C:/Users/<你的用户名>/.claude-modsdk-workflow/)
     ```

   - 否则，检查是否为MODSDK项目：
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

**步骤A：动态检测全局工作流目录** ⭐ 关键

```python
# 定位全局工作流目录（优先级顺序）
全局工作流目录 = None

# 方法1：检查默认全局目录（用户主目录）
默认目录 = os.path.join(os.path.expanduser("~"), ".claude-modsdk-workflow")
if os.path.exists(os.path.join(默认目录, "CLAUDE.md")):
    全局工作流目录 = 默认目录

# 方法2：通过环境变量（如果设置）
if not 全局工作流目录 and "CLAUDE_WORKFLOW_ROOT" in os.environ:
    env_dir = os.environ["CLAUDE_WORKFLOW_ROOT"]
    if os.path.exists(os.path.join(env_dir, "CLAUDE.md")):
        全局工作流目录 = env_dir

# 方法3：搜索用户主目录
if not 全局工作流目录:
    可能位置 = [
        os.path.expanduser("~/.claude-modsdk-workflow"),
    ]
    for 位置 in 可能位置:
        if os.path.exists(os.path.join(位置, "CLAUDE.md")):
            全局工作流目录 = 位置
            break

# 验证
if not 全局工作流目录:
    输出错误("无法找到全局工作流目录，请检查安装")
    终止执行

print(f"✓ 检测到全局工作流目录: {全局工作流目录}")
```

**步骤B：复制额外的命令文件** ⭐ 必须执行

1. 读取全局工作流目录中的`enhance-docs.md`：
   ```
   Read(file_path="{全局工作流目录}/.claude/commands/enhance-docs.md")
   ```

2. 将读取的内容写入目标项目：
   ```
   Write(file_path="<项目路径>/.claude/commands/enhance-docs.md", content=<上一步读取的内容>)
   ```

3. 读取全局工作流目录中的`validate-docs.md`：
   ```
   Read(file_path="{全局工作流目录}/.claude/commands/validate-docs.md")
   ```

4. 将读取的内容写入目标项目：
   ```
   Write(file_path="<项目路径>/.claude/commands/validate-docs.md", content=<上一步读取的内容>)
   ```

**步骤C：复制通用文档**

对于以下每个文件，执行Read → Write操作：

全局源目录：`{全局工作流目录}/markdown/`

1. **开发规范.md**：
   - Read: `{全局工作流目录}/markdown/开发规范.md`
   - Write: `<项目路径>/markdown/开发规范.md`

2. **问题排查.md**：
   - Read: `{全局工作流目录}/markdown/问题排查.md`
   - Write: `<项目路径>/markdown/问题排查.md`

3. **快速开始.md**：
   - Read: `{全局工作流目录}/markdown/快速开始.md`
   - Write: `<项目路径>/markdown/快速开始.md`

4. **开发指南.md**：
   - Read: `{全局工作流目录}/markdown/开发指南.md`
   - Write: `<项目路径>/markdown/开发指南.md`

5. **API速查.md**：
   - Read: `{全局工作流目录}/markdown/API速查.md`
   - Write: `<项目路径>/markdown/API速查.md`

6. **MODSDK核心概念.md**：
   - Read: `{全局工作流目录}/markdown/MODSDK核心概念.md`
   - Write: `<项目路径>/markdown/MODSDK核心概念.md`

**步骤D：复制AI辅助文档**

1. **任务类型决策表.md**：
   - Read: `{全局工作流目录}/markdown/ai/任务类型决策表.md`
   - Write: `<项目路径>/markdown/ai/任务类型决策表.md`

2. **快速通道流程.md**：
   - Read: `{全局工作流目录}/markdown/ai/快速通道流程.md`
   - Write: `<项目路径>/markdown/ai/快速通道流程.md`

3. **上下文管理规范.md**：
   - Read: `{全局工作流目录}/markdown/ai/上下文管理规范.md`
   - Write: `<项目路径>/markdown/ai/上下文管理规范.md`

**步骤F：创建README.md**

使用Write工具创建项目README：
```
Write(file_path="<项目路径>/README.md", content=<根据项目信息生成的README内容>)
```

**步骤G：创建项目状态文档**

```
Write(file_path="<项目路径>/markdown/项目状态.md", content="# 项目状态\n\n⚠️ **待补充**\n")
```

**步骤H：创建tasks目录说明**

```
Write(file_path="<项目路径>/tasks/README.md", content=<生成tasks说明文档>)
```

---

#### 3.2 生成Layer 2（架构层）- 系统文档 ⭐ 智能文档检测

**新增功能**: 智能检测现有系统文档，避免重复生成

**三级智能匹配策略**：

1. **级别1 - 精确文件名匹配**：
   - 查找 `{SystemName}.md`（如 `ShopServerSystem.md`）

2. **级别2 - 内容智能匹配**：
   - 标题包含系统名（如 `# 商店系统 (Shop System)` 匹配 `ShopServerSystem`）
   - Front Matter声明系统名
   - 类定义引用系统名（如 `class ShopServerSystem`）
   - 中文文档关键词匹配（如 `商店系统` 匹配 `ShopServerSystem`）

3. **级别3 - 文档质量评估（0-5分）**：
   - 包含代码块示例 (+1)
   - 包含图表/mermaid (+1)
   - 包含使用示例 (+1)
   - 内容丰富 >500字符 (+1)
   - 非"待补充"模板 (+1)

**智能决策规则**：
- **高质量文档（≥3分）**: ✅ 保留现有文档，跳过生成
- **低质量文档（<3分）**: ⚠️ 覆盖生成新文档
- **无匹配文档**: 📝 生成新文档
- **多个匹配**: 选择质量最高的文档

**示例输出**：
```
[生成器] 检测到现有文档: 商店系统.md (质量评分: 5/5)
[生成器] ✓ 保留高质量文档: 商店系统.md
[生成器] 生成了 8 个系统文档，跳过 2 个现有文档 ✅
```

对于每个System，生成中等详细度的文档：

```python
# 读取步骤1分析得到的Systems列表
for system_name, system_info in 分析结果.systems.items():
    # ⭐ 新增: 智能检测现有文档
    existing_doc = 检测现有系统文档(system_name, systems_dir)

    if existing_doc and existing_doc.quality >= 3:
        print(f"✓ 保留高质量文档: {existing_doc.fileName}")
        continue  # 跳过生成

    # 生成或覆盖文档
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

### 📝 步骤3.5：智能文档重命名 ⭐ 新增

**目标**：将所有英文文档名重命名为清晰的中文名称

**触发条件**：步骤3生成文档完成后自动执行

#### 3.5.1 扫描文档目录

扫描以下目录的所有.md文件（排除README.md）：
```python
doc_dirs = [
  'markdown/systems',
  'markdown/states',
  'markdown/presets',
  'markdown/config',
  # 其他自适应发现的组件目录
]

all_docs = []
for dir_path in doc_dirs:
  if os.path.exists(dir_path):
    files = [f for f in os.listdir(dir_path) if f.endswith('.md') and f != 'README.md']
    for file in files:
      all_docs.append({
        'dir': dir_path,
        'filename': file,
        'path': os.path.join(dir_path, file)
      })

print(f"[扫描] 发现 {len(all_docs)} 个文档待重命名")
```

#### 3.5.2 深度分析每个文档

对每个文档执行AI深度分析：

```python
rename_plan = []

for doc in all_docs:
  # 读取文档内容
  content = Read(doc['path'])

  # 提取关键信息
  info = extract_doc_info(content)
  # info包含:
  # - class_name: 类名
  # - component_type: 组件类型(system/state/preset/等)
  # - methods: 主要方法列表
  # - file_path: 原始Python文件路径

  # AI分析推断中文名
  chinese_name = infer_chinese_name(info)

  # 记录重命名计划
  rename_plan.append({
    'old_name': doc['filename'],
    'new_name': chinese_name,
    'dir': doc['dir'],
    'reason': info['inferred_purpose']  # AI推断的业务职责
  })
```

**AI分析示例**：

```python
# 示例1: ShopServerSystem.md
info = {
  'class_name': 'ShopServerSystem',
  'component_type': 'system',
  'methods': ['handle_buy', 'handle_sell', 'show_shop', 'get_item_price'],
  'file_path': 'systems/ShopServerSystem.py'
}

# AI分析:
# - 类名: ShopServerSystem → Shop(商店) + Server + System(系统)
# - 方法: handle_buy/handle_sell → 购买/销售功能
# - 业务职责: 管理游戏商店,处理玩家购买和销售物品
# - 推断中文名: 商店系统.md

chinese_name = "商店系统.md"
```

```python
# 示例2: BedWarsEndingState.md
info = {
  'class_name': 'BedWarsEndingState',
  'component_type': 'state',
  'methods': ['_on_enter', '_display_victory', '_play_victory_dance', '_switch_all_to_spectator'],
  'file_path': 'Parts/ECBedWars/state/BedWarsEndingState.py'
}

# AI分析:
# - 类名: BedWarsEndingState → BedWars(起床战争) + Ending(结束) + State(状态)
# - 方法: _display_victory/play_victory_dance → 展示胜利/胜利动画(结束阶段特征)
# - 业务职责: 起床战争游戏的结束阶段状态,展示胜利信息
# - 推断中文名: 起床战争结束状态.md

chinese_name = "起床战争结束状态.md"
```

```python
# 示例3: RootGamingState.md
info = {
  'class_name': 'RootGamingState',
  'component_type': 'state',
  'methods': ['__init__', 'get_part', '_on_no_such_next_sub_state'],
  'file_path': 'Parts/GamingState/state/RootGamingState.py'
}

# AI分析:
# - 类名: RootGamingState → Root(根) + Gaming(游戏) + State(状态)
# - 方法: _on_no_such_next_sub_state → 处理子状态(状态机特征)
# - 文件路径: GamingState目录,状态机根节点
# - 业务职责: 游戏状态机的根节点状态,管理子状态转换
# - 推断中文名: 根游戏状态.md 或 游戏状态机根节点.md

chinese_name = "根游戏状态.md"
```

**命名原则**（AI遵循）：
1. **清晰性**: 一眼看出职责
2. **简洁性**: 保持5-8个汉字,避免冗长
3. **规范性**: 统一格式"XXX系统/状态/预设/管理器"
4. **准确性**: 反映真实业务含义
5. **唯一性**: 避免重复文件名

#### 3.5.3 展示重命名计划

生成格式化的重命名计划表：

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 智能重命名计划
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Systems (13个):
  ShopServerSystem.md          → 商店系统.md
  IronGolemAISystem.md         → 铁傀儡AI系统.md
  ScoreboardSystem.md          → 计分板系统.md
  FormBuilderSystem.md         → 表单构建器系统.md
  TeamServerSystem.md          → 队伍系统.md
  WaypointServerSystem.md      → 路径点系统.md
  OrnamentServerSystem.md      → 装饰系统.md
  CoreServerSystem.md          → 核心系统.md
  ... (显示所有)

States (12个):
  BedWarsEndingState.md        → 起床战争结束状态.md
  BedWarsStartingState.md      → 起床战争开始状态.md
  BedWarsRunningState.md       → 起床战争进行中状态.md
  BedWarsWaitingState.md       → 起床战争等待状态.md
  RootGamingState.md           → 根游戏状态.md
  TimedGamingState.md          → 计时游戏状态.md
  ... (显示所有)

Presets (9个):
  BedPresetDefServer.md        → 床位预设.md
  GeneratorPresetDefServer.md  → 生成器预设.md
  ... (显示所有)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
总计: 34 个文档将被重命名
中文文档比例: 100%

⚠️  请仔细审查上述重命名计划

是否执行重命名？(y/n): _
```

**注意**：
- 使用AskUserQuestion工具等待用户输入
- 明确提示"y"表示执行,"n"表示跳过

#### 3.5.4 等待用户确认

```python
# 使用AskUserQuestion工具
user_response = AskUserQuestion("是否执行上述重命名计划？(输入 y 执行, n 跳过)")

if user_response.lower() == 'y':
  # 执行重命名
  execute_rename(rename_plan)
  show_success_report()
elif user_response.lower() == 'n':
  print("\n⚠️  已跳过重命名步骤")
  print("文档保留英文名称,可稍后手动重命名")
  print("提示: 可使用系统文件管理器批量重命名\n")
else:
  # 无效输入,询问重试
  print("输入无效,请输入 y 或 n")
```

#### 3.5.5 执行重命名

如果用户确认执行,批量重命名所有文档：

```bash
# 使用Bash工具执行重命名
cd {PROJECT_PATH}

# Systems
cd markdown/systems
mv "ShopServerSystem.md" "商店系统.md"
mv "IronGolemAISystem.md" "铁傀儡AI系统.md"
mv "ScoreboardSystem.md" "计分板系统.md"
...

# States
cd ../states
mv "BedWarsEndingState.md" "起床战争结束状态.md"
mv "BedWarsStartingState.md" "起床战争开始状态.md"
...

# Presets
cd ../presets
mv "BedPresetDefServer.md" "床位预设.md"
...
```

**错误处理**：
- 如果文件不存在,记录警告但继续
- 如果目标文件名已存在,添加序号(如"商店系统(2).md")
- 所有错误记录到重命名日志

#### 3.5.6 输出重命名报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 文档重命名完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Systems:
  ✓ ShopServerSystem.md → 商店系统.md
  ✓ IronGolemAISystem.md → 铁傀儡AI系统.md
  ✓ ScoreboardSystem.md → 计分板系统.md
  ... (显示所有成功的重命名)

States:
  ✓ BedWarsEndingState.md → 起床战争结束状态.md
  ✓ BedWarsStartingState.md → 起床战争开始状态.md
  ... (显示所有成功的重命名)

Presets:
  ✓ BedPresetDefServer.md → 床位预设.md
  ... (显示所有成功的重命名)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 重命名统计:
   总文档数: 34
   重命名成功: 34
   重命名失败: 0
   中文文档比例: 100%

✨ 所有文档现已使用清晰的中文名称！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

### 1. 在工作流项目本身执行 /initmc ⭐ 新增
```
⚠️  检测到工作流项目本身

/initmc 命令仅用于初始化新的MODSDK项目。
当前目录是工作流项目本身，无需初始化。

使用说明：
1. 在需要初始化的MODSDK项目根目录执行 /initmc
2. 工作流文件将从全局目录自动复制到目标项目

全局工作流目录：~/.claude-modsdk-workflow/
(Windows示例：C:/Users/<你的用户名>/.claude-modsdk-workflow/)
```

**原因**：用户在工作流项目本身运行了 `/initmc`，这会导致文件循环复制。

**解决方案**：切换到目标MODSDK项目根目录，然后执行 `/initmc`。

---

### 2. 未检测到modMain.py
```
❌ 错误: 当前目录不是MODSDK项目

请在项目根目录执行 /initmc 命令。
项目根目录应包含 modMain.py 文件。
```

### 3. markdown/目录已存在
```
⚠️  检测到现有文档

发现 markdown/ 目录已存在，包含 X 个文档。

选项:
1. 备份后继续（推荐）
2. 覆盖现有文档（需 --overwrite 参数）
3. 取消操作

是否备份现有文档后继续？[Y/n]
```

### 4. Python模块导入失败
```
❌ 错误: 无法导入项目分析器

请确保以下路径存在:
D:\EcWork\基于Claude的MODSDK开发工作流\workflow-generator\analyzer.py

如果问题持续，请检查Python环境配置。
```

### 5. 无法检测到全局工作流目录 ⭐ 新增
```
❌ 错误: 无法找到全局工作流目录

已尝试以下位置:
- ~/.claude-modsdk-workflow （默认全局目录，在用户主目录下）
  Windows: C:/Users/<你的用户名>/.claude-modsdk-workflow
  Linux/Mac: /home/<你的用户名>/.claude-modsdk-workflow
- 环境变量 CLAUDE_WORKFLOW_ROOT

请确保工作流已正确安装。
```

**原因**：AI无法自动定位全局工作流目录。

**解决方案**：
1. 检查工作流是否已安装到 `~/.claude-modsdk-workflow`
   - Windows: `C:/Users/<你的用户名>/.claude-modsdk-workflow`
   - Linux/Mac: `/home/<你的用户名>/.claude-modsdk-workflow`
2. 或设置环境变量 `CLAUDE_WORKFLOW_ROOT` 指向工作流目录

---

## 注意事项

1. ⏱️ **首次执行耗时**: 小项目5分钟，大项目可能需要30分钟
2. 💰 **Token消耗**: 预计30k-120k，请确保预算充足
3. 📝 **文档质量**: Layer 1直接可用，Layer 2需补充，Layer 3是框架
4. 🔄 **自学习**: AI会在后续开发中逐步完善文档

---

现在开始执行 /initmc 命令！
