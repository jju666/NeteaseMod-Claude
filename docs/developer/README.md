# NeteaseMod-Claude 开发者文档

> **版本**: v25.0
> **更新时间**: 2025-11-20
> **架构版本**: v21.0（单一数据源） + v3.0 Final（4步状态机） + v25.0（Claude LLM）

---

## 📖 文档导航

本项目是基于 Claude Code Hooks 的**AI驱动MODSDK开发工作流系统**，核心通过8个Hook协同工作实现智能化开发辅助。

### 🚀 快速开始

- **[快速开始](./快速开始.md)** - 5分钟完成部署和使用
  - 安装部署步骤（initmc命令）
  - 基本命令使用（/mc系列命令）
  - 任务工作流演示
  - 常见问题解决

### 🏗️ 核心架构

- **[架构概览](./架构概览.md)** - 系统整体架构与核心概念
  - 8个Hook的协同工作机制
  - 4步状态机工作流（Activation → Planning → Implementation → Finalization）
  - task-meta.json单一数据源设计（v21.0架构）
  - 并发控制与文件锁机制（portalocker + atomic_update）

### 🔧 Hook开发

- **[HOOK正确用法文档](./HOOK正确用法文档.md)** ⭐ **开发必读**
  - Hook类型完整说明（Lifecycle、Orchestrator、Archiver等）
  - 标准实现方式（PreToolUse、PostToolUse、Stop等）
  - 实战案例与最佳实践
  - 与Claude Code官方文档对齐的验证代码

### 🤖 LLM集成（v25.0核心）

- **[Claude语义分析器使用指南](./Claude语义分析器使用指南.md)**
  - LLM语义分析系统（Claude Sonnet 4.5）
  - 96.15%准确率的用户意图识别（vs 传统关键词85%）
  - 从规则驱动到智能驱动的升级

- **[Hook状态机功能实现](./Hook状态机功能实现.md)** - 完整工作流实现
  - 4步状态机详细说明
  - 状态转移规则与验证（硬编码转移表）
  - Hook系统协同工作流程

### 🔍 常见问题

- **[FAQ](./FAQ.md)** - 常见问题与解决方案
  - Windows UTF-8编码配置
  - 桌面通知功能安装
  - Hook调试方法
  - 常见错误排查

---

## ⚡ 核心特性

### 1. Claude LLM语义分析（v25.0突破）

**从传统关键词匹配升级到Claude Sonnet 4.5驱动的语义理解**

| 指标 | v24.2（关键词） | v25.0（LLM） | 提升 |
|------|---------------|-------------|-----|
| complete_success | 64.3% | **100%** | +35.7% |
| partial_success | 64.3% | **100%** | +35.7% |
| **总体平均** | **85%** | **96.15%** | **+11.15%** |

**关键改进**：
- ✅ 完美识别转折语义（"基本正确,但还有BUG" → partial_success）
- ✅ 自动理解新表达（如"都正确了"），无需手动添加关键词
- ✅ 零维护成本，自动适应用户表达习惯

### 2. 8个Hook协同工作

| Hook | 职责 | 触发时机 |
|------|------|---------|
| **SessionStart** | 会话初始化与状态恢复 | Claude Code启动时 |
| **UserPromptHandler** | 任务初始化与状态转移 | 用户输入/mc或确认反馈 |
| **PreToolUse** | 工具调用拦截（4层验证） | AI调用工具前 |
| **PostToolUse** | 状态更新与步骤推进 | AI调用工具后 |
| **Stop** | 轮次边界与完成检查 | AI准备结束会话时 |
| **SubagentStop** | 子代理结果提取 | 子代理执行完成后 |
| **PreCompact** | 会话压缩准备 | Claude Code压缩会话前 |
| **PostArchive** | 任务归档处理 | 任务完成后 |

### 3. 4步语义化状态机（v3.0 Final）

```
Activation（任务激活）
    ↓ 自动推进
Planning（方案制定）
    ↓ 用户确认
Implementation（代码实施）
    ↓ 用户确认完成
Finalization（收尾归档）
```

**状态转移规则**（硬编码保证100%安全）：
- activation → planning（自动）
- planning → implementation（需用户确认）
- implementation → finalization（需用户确认完成）
- implementation → planning（允许回退重新设计）

### 4. 单一数据源架构（v21.0）

**从三文件同步升级到单一数据源**：

| 特性 | v20.x | v21.0 |
|-----|-------|-------|
| 数据源数量 | 3个文件 | 2个文件 |
| 权威数据源 | workflow-state.json | task-meta.json |
| 同步机制 | 手动同步 | 无需同步 |
| 并发安全 | 无锁 | portalocker文件锁 |
| 更新方式 | 直接写入 | atomic_update()闭包 |
| 数据一致性 | 风险高 | 保证一致 |

**核心组件**：
- **task-meta.json** - 唯一权威数据源
- **TaskMetaManager** - 统一管理接口
- **portalocker文件锁** - 跨平台并发安全
- **atomic_update()** - 原子更新操作（读-改-写在同一锁内）

---

## 📦 项目结构

```
NeteaseMod-Claude/
├── templates/.claude/           # Hook系统模板
│   ├── hooks/                  # Hook脚本（28个文件）
│   │   ├── core/              # 核心模块（12个）
│   │   │   ├── task_meta_manager.py          # 任务元数据管理
│   │   │   ├── claude_semantic_analyzer.py   # Claude LLM分析器
│   │   │   ├── state_transition_validator.py # 状态转移验证
│   │   │   ├── tool_matrix.py                # 工具矩阵配置
│   │   │   └── ...
│   │   ├── lifecycle/         # 生命周期Hook（5个）
│   │   ├── orchestrator/      # 编排Hook（4个）
│   │   └── archiver/          # 归档Hook（1个）
│   ├── commands/              # 斜杠命令模板
│   ├── rules/                 # 4个阶段规则（YAML）
│   └── config/                # 配置文件
├── lib/                       # Node.js工具链（仅initmc时使用）
│   ├── init-workflow.js       # 初始化主流程
│   ├── analyzer.js            # 项目分析器
│   ├── generator.js           # 文档生成器
│   └── ...
├── tests/                     # 测试项目
└── docs/developer/            # 开发者文档（本目录）
```

---

## 🎯 性能指标

### LLM延迟

- **P50延迟**: 3-5秒
- **P95延迟**: 8-12秒
- **超时阈值**: 15秒（超时后友好降级）
- **超时率**: <5%

### 成本

- **单次API调用**: ~$0.0015
- **月度成本**（10个任务，每任务3次反馈）: ~$0.045
- **年度成本**: ~$0.54（可忽略不计）

### 并发控制

- **文件锁**: portalocker（Windows/Linux兼容）
- **重试机制**: 最多3次，100ms延迟
- **原子性**: 读-改-写在同一锁内完成
- **可靠性**: 异常隔离机制，防止单点故障

---

## 🔗 外部资源

- **Claude Code官方文档**: https://code.claude.com/docs/zh-CN/overview
- **项目仓库**: https://github.com/jju666/NeteaseMod-Claude
- **MODSDK Wiki**: https://github.com/EaseCation/netease-modsdk-wiki
- **问题反馈**: GitHub Issues

---

## 📝 版本说明

### 当前版本

- **v25.0** (2025-11-20) - Claude LLM语义分析系统
- **v21.0** (2025-11-15) - 单一数据源架构
- **v3.0 Final** (2025-11-15) - 4步语义化状态机

### 架构演进

```
v15.x-v20.x  三文件同步 + workflow-state.json（已废弃）
     ↓ v21.0重构
v21.x        单一数据源 + task-meta.json
     ↓ v25.0升级
v25.x        Claude LLM语义分析 + 状态机强制验证（当前版本）
```

### 迁移指南

**从v20.x升级到v21.0+**：
```bash
# 自动迁移（initmc内置）
npm run mc:deploy
# 或
initmc
```

迁移脚本会自动：
1. 合并workflow-state.json到task-meta.json
2. 删除workflow-state.json
3. 添加architecture_version: "21.0"
4. 删除冗余字段

---

## 🤝 贡献指南

欢迎贡献代码和文档！请确保：

1. **Hook开发** - 必须遵循[HOOK正确用法文档](./HOOK正确用法文档.md)
2. **代码风格** - 保持与现有代码一致（Python: PEP8，JavaScript: ES6+）
3. **测试验证** - 在tests/目录下测试功能
4. **文档更新** - 同步更新相关文档

---

## 📄 许可证

MIT License - 详见 [LICENSE](../../LICENSE)

---

**文档维护**: Claude Code Development Team
**最后更新**: 2025-11-20
**适用版本**: v25.0+Human: 继续