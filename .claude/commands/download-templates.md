# /download-templates - 下载参考项目示例

从本地参考项目下载完整的工作流示例供学习参考。

## 描述

下载起床战争和RPG项目的完整CLAUDE.md、/cc命令和文档示例，保存到 `examples/` 目录供学习参考。

⚠️ **注意**：此命令是**可选的**，仅用于学习参考。本工作流生成器已内置所有必要模板，无需参考项目即可正常使用。

## 用法

```bash
# 下载所有可用的示例
/download-templates

# 只下载特定项目的示例
/download-templates --project=bedwars
/download-templates --project=rpg
```

---

## 执行流程

### 步骤1：检查参考项目是否存在

```python
import os

# 检查参考项目路径
BEDWARS_PROJECT = r"D:\EcWork\NetEaseMapECBedWars"
RPG_PROJECT = r"D:\new-mg"

bedwars_exists = os.path.exists(BEDWARS_PROJECT)
rpg_exists = os.path.exists(RPG_PROJECT)

if not bedwars_exists and not rpg_exists:
    print("❌ 错误：未找到参考项目")
    print("")
    print("本机上不存在参考项目目录：")
    print("- 起床战争项目: {}".format(BEDWARS_PROJECT))
    print("- RPG项目: {}".format(RPG_PROJECT))
    print("")
    print("💡 提示：")
    print("1. 本工作流生成器已内置所有必要模板")
    print("2. 无需参考项目即可正常使用 /initmc 命令")
    print("3. 此命令仅用于学习参考，不是必需的")
    exit(1)

print("📋 发现的参考项目：")
if bedwars_exists:
    print("- ✅ 起床战争项目: {}".format(BEDWARS_PROJECT))
if rpg_exists:
    print("- ✅ RPG项目: {}".format(RPG_PROJECT))
print("")
```

---

### 步骤2：创建examples目录结构

```bash
mkdir -p examples/bedwars
mkdir -p examples/rpg
```

---

### 步骤3：下载起床战争项目示例（如果存在）

```python
if bedwars_exists:
    print("📦 下载起床战争项目示例...")

    # 1. 复制CLAUDE.md
    Read(file_path=BEDWARS_PROJECT+"/CLAUDE.md")
    Write(file_path="examples/bedwars/CLAUDE.md", content=读取的内容)
    print("  ✅ CLAUDE.md")

    # 2. 复制/cc命令
    if os.path.exists(BEDWARS_PROJECT+"/.claude/commands/cc.md"):
        Read(file_path=BEDWARS_PROJECT+"/.claude/commands/cc.md")
        Write(file_path="examples/bedwars/cc.md", content=读取的内容)
        print("  ✅ cc.md")

    # 3. 复制开发规范.md
    if os.path.exists(BEDWARS_PROJECT+"/markdown/开发规范.md"):
        Read(file_path=BEDWARS_PROJECT+"/markdown/开发规范.md")
        Write(file_path="examples/bedwars/开发规范.md", content=读取的内容)
        print("  ✅ 开发规范.md")

    # 4. 复制问题排查.md
    if os.path.exists(BEDWARS_PROJECT+"/markdown/问题排查.md"):
        Read(file_path=BEDWARS_PROJECT+"/markdown/问题排查.md")
        Write(file_path="examples/bedwars/问题排查.md", content=读取的内容)
        print("  ✅ 问题排查.md")

    # 5. 创建README说明
    readme_content = """# 起床战争项目示例

> **参考项目**: NetEaseMapECBedWars
> **下载时间**: {当前时间}

## 文件说明

- **CLAUDE.md** - AI工作流程参考（v11.0，三步流程）
- **cc.md** - /cc命令实现示例
- **开发规范.md** - CRITICAL规范（ECPreset架构）
- **问题排查.md** - 已知问题和调试技巧

## 如何使用

这些文件仅供学习参考，了解完整工作流的结构。

**不要直接复制**，请使用 `/initmc` 命令为你的项目生成定制化的工作流。

## 项目特点

- ECPreset框架
- PVP小游戏
- 状态机架构
- 完整的预设系统文档

---

_参考项目路径: {BEDWARS_PROJECT}_
"""
    Write(file_path="examples/bedwars/README.md", content=readme_content)
    print("  ✅ README.md")
    print("")
```

---

### 步骤4：下载RPG项目示例（如果存在）

```python
if rpg_exists:
    print("📦 下载RPG项目示例...")

    # 1. 复制CLAUDE.md
    Read(file_path=RPG_PROJECT+"/CLAUDE.md")
    Write(file_path="examples/rpg/CLAUDE.md", content=读取的内容)
    print("  ✅ CLAUDE.md")

    # 2. 复制/cc命令
    if os.path.exists(RPG_PROJECT+"/.claude/commands/cc.md"):
        Read(file_path=RPG_PROJECT+"/.claude/commands/cc.md")
        Write(file_path="examples/rpg/cc.md", content=读取的内容)
        print("  ✅ cc.md")

    # 3. 复制开发规范.md
    if os.path.exists(RPG_PROJECT+"/markdown/开发规范.md"):
        Read(file_path=RPG_PROJECT+"/markdown/开发规范.md")
        Write(file_path="examples/rpg/开发规范.md", content=读取的内容)
        print("  ✅ 开发规范.md")

    # 4. 复制问题排查.md
    if os.path.exists(RPG_PROJECT+"/markdown/问题排查.md"):
        Read(file_path=RPG_PROJECT+"/markdown/问题排查.md")
        Write(file_path="examples/rpg/问题排查.md", content=读取的内容)
        print("  ✅ 问题排查.md")

    # 5. 创建README说明
    readme_content = """# RPG项目示例

> **参考项目**: new-mg (NEWRPG)
> **下载时间**: {当前时间}

## 文件说明

- **CLAUDE.md** - AI工作流程参考（v2.2，文档查阅强制化）
- **cc.md** - /cc命令实现示例
- **开发规范.md** - CRITICAL规范（Apollo架构）
- **问题排查.md** - 已知问题和调试技巧

## 如何使用

这些文件仅供学习参考，了解完整工作流的结构。

**不要直接复制**，请使用 `/initmc` 命令为你的项目生成定制化的工作流。

## 项目特点

- Apollo 1.0架构
- RPG游戏系统
- 完整的NEWRPG业务文档（24个）
- NBT兼容性处理

---

_参考项目路径: {RPG_PROJECT}_
"""
    Write(file_path="examples/rpg/README.md", content=readme_content)
    print("  ✅ README.md")
    print("")
```

---

### 步骤5：输出完成报告

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 示例下载完成！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 已保存到:
- examples/bedwars/  (起床战争项目示例)
- examples/rpg/      (RPG项目示例)

📖 查阅方式:
```bash
# 查看起床战争项目的CLAUDE.md
Read(file_path="examples/bedwars/CLAUDE.md")

# 查看RPG项目的/cc命令
Read(file_path="examples/rpg/cc.md")
```

💡 使用建议:
1. 这些示例仅供学习参考
2. 了解完整工作流的结构和最佳实践
3. 使用 /initmc 为你的项目生成定制化工作流
4. 不要直接复制，因为路径和配置不同

🎯 下一步:
- 查阅示例文件，了解工作流结构
- 在你的项目目录执行 /initmc
- 使用 /cc 命令开始高效开发

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 注意事项

1. **可选功能**：此命令不是必需的，仅用于学习参考
2. **本地依赖**：需要本机存在参考项目目录
3. **仅供参考**：下载的文件不应直接用于其他项目
4. **推荐方式**：使用 `/initmc` 生成定制化工作流

---

## 常见问题

### Q1: 为什么找不到参考项目？

A: 参考项目仅存在于开发者的本地环境。如果你是其他开发者：
- ✅ 本工作流生成器已内置所有必要模板
- ✅ 无需参考项目即可正常使用
- ✅ 直接使用 `/initmc` 命令部署工作流

### Q2: 下载的示例如何使用？

A: 仅供学习参考，了解：
- 完整的CLAUDE.md结构
- /cc命令的实现方式
- CRITICAL规范的写法
- 文档体系的组织

### Q3: 可以直接复制示例到我的项目吗？

A: ❌ 不推荐！因为：
- 路径不同（硬编码了参考项目路径）
- 项目类型不同（ECPreset vs Apollo vs 标准）
- 业务逻辑不同（起床战争 vs RPG vs 其他）

**推荐做法**：使用 `/initmc` 自动生成定制化工作流。

---

现在开始执行下载！
