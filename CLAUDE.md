# NeteaseMod-Claude 工作流生成器

> **AI驱动的MODSDK开发工作流系统**
>
> 本项目为网易我的世界MODSDK提供智能开发辅助工具链

---

## 📚 文档导航

### 🚀 快速开始
- [安装指南](./docs/developer/安装指南.md) - 5分钟快速部署
- [快速上手](./docs/developer/快速上手.md) - 核心命令与使用场景

### 🏗️ 核心架构
- [技术架构](./docs/developer/技术架构.md) - 系统设计与模块划分
- [数据流设计](./docs/developer/数据流设计.md) - 工作流执行流程
- [Hook机制](./docs/developer/Hook机制.md) - 任务隔离与上下文管理
- [通知系统](./docs/developer/通知系统.md) - 🔔 跨平台桌面通知(v18.4+)

### 📦 核心模块
- [项目分析器](./docs/developer/项目分析器.md) - ProjectAnalyzer 模块
- [文档生成器](./docs/developer/文档生成器.md) - DocumentGenerator 模块
- [智能文档维护](./docs/developer/智能文档维护.md) - 自适应文档系统
- [版本管理](./docs/developer/版本管理.md) - 迁移与同步机制

### 🔧 开发指南
- [贡献指南](./docs/developer/贡献指南.md) - 如何参与项目开发
- [测试指南](./docs/developer/测试指南.md) - 手动测试方法与验证脚本

### 📖 用户文档
- [README.md](./README.md) - 项目概述
- [CHANGELOG.md](./CHANGELOG.md) - 版本更新记录

---

## ⚠️ 重要注意事项

### Windows 中文路径问题 (v20.2.5)

**关键事实：Python 3.6+ 完全支持 Windows 中文目录创建**

在 v20.2.5 修复过程中发现了一个容易误判的问题：

#### ❌ 错误判断
- 如果看到乱码的任务目录（如 `任务-1113-214915-淇���澶嶇帺瀹舵���`）
- **不要**立即认为是 `os.makedirs()` 无法创建中文路径
- **不要**尝试使用 Windows UNC 前缀 `\\?\` 或短路径名 API

#### ✅ 正确诊断
1. **Python 文件系统 API 完全支持中文**
   - `os.makedirs("任务-1113-测试中文")` 在 Windows 上正常工作
   - 如果你成功创建了中文目录，说明文件系统没有问题

2. **乱码的真正原因：stdin 编码**
   - 问题出在读取用户输入时引入了代理字符 (surrogate characters U+D800-U+DFFF)
   - 这些无效的 Unicode 字符传播到了文件路径中

3. **解决方案：修复 stdin 编码**
   ```python
   # user-prompt-submit-hook.py 开头添加
   if sys.platform == 'win32':
       import io
       sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
       sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
       sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
   ```

#### 📊 验证方法
```bash
# 如果看到成功创建的中文目录，说明文件系统没问题
ls tasks/
# 输出：
# ✅ 测试-Python-中文目录         # 文件系统正常
# ❌ 任务-1113-淇���澶�          # stdin 编码问题导致
```

#### 🔍 详细报告
- [BUGFIX-v20.2.5.md](./BUGFIX-v20.2.5.md) - 完整的问题分析与修复过程
- [CHANGELOG.md](./CHANGELOG.md#20.2.5) - v20.2.5 版本更新记录

---

## 📄 许可证

MIT License - 详见 [LICENSE](./LICENSE)

---

_最后更新: 2025-11-14 | v20.2.10_
