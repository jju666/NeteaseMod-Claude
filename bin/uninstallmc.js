#!/usr/bin/env node

/**
 * MODSDK 工作流卸载命令全局入口 v16.0
 *
 * 这是全局命令 `uninstallmc` 的入口文件
 * 功能：从下游项目中移除所有由 initmc 部署的工作流文件
 *
 * 使用方式：
 *   cd <MODSDK项目目录>
 *   uninstallmc                    # 执行卸载
 *   uninstallmc --dry-run          # 预览模式（仅查看将删除的文件）
 *   uninstallmc --remove-claude-md # 同时删除 CLAUDE.md
 */

const path = require('path');
const fs = require('fs');

// 查找全局工作流目录
const workflowHome = process.env.NETEASE_CLAUDE_HOME ||
                     path.join(require('os').homedir(), '.claude-modsdk-workflow');

if (!fs.existsSync(workflowHome)) {
  console.error('❌ 错误: 未找到全局工作流目录');
  console.error('   路径: ' + workflowHome);
  console.error('\n请先运行: npm run install-global\n');
  process.exit(1);
}

// 加载 v16.0 核心模块
const { WorkflowUninstaller } = require(path.join(workflowHome, 'lib', 'uninstall-workflow'));

// 解析命令行参数
const args = process.argv.slice(2);
const projectPath = args.find(arg => !arg.startsWith('--')) || process.cwd();
const dryRun = args.includes('--dry-run');
const removeCLAUDE = args.includes('--remove-claude-md');

// 执行卸载
const uninstaller = new WorkflowUninstaller(projectPath);
uninstaller.uninstall({ dryRun, removeCLAUDE }).catch(err => {
  console.error('\n❌ 卸载失败:', err.message);
  if (err.stack) {
    console.error('\n详细错误信息:');
    console.error(err.stack);
  }
  process.exit(1);
});
