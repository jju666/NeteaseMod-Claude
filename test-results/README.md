# 测试结果目录

本目录用于存储下游项目（`tests/`）的测试结果和分析报告。

## 文件说明

- **`latest.log`** - 最新测试的完整日志（纯文本格式）
- **`latest.json`** - 测试结果的结构化数据（JSON 格式）
- **`conversation.txt`** - 下游项目的 Claude 会话记录（从 `tests/YYYY-MM-DD-*.txt` 自动收集）
- **`analysis.md`** - Claude 生成的综合分析报告（包括会话分析、测试结果、上下游对比）
- **`.ready`** - 测试完成标记文件（触发自动分析）
- **`.timestamp`** - 最后更新时间戳
- **`auto-analyze.log`** - 自动分析脚本的日志
- **`claude-output.json`** - Claude headless 模式的原始输出

## 工作流程

1. 运行 `/deploy-downstream` 部署并测试下游项目
2. 测试结果自动保存到此目录
3. 运行 `/check-downstream` 分析结果并生成报告
4. 查看 `analysis.md` 获取详细的问题诊断和修复建议

## 注意事项

- 此目录中的文件会被自动覆盖
- 重要的测试结果应手动备份
- 文件已添加到 `.gitignore`，不会提交到版本控制

## 相关文档

- 工作流使用说明：`../.claude/CLAUDE.md`
- 自动分析脚本：`../auto-analyze.sh`
