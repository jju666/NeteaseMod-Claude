#!/usr/bin/env node

/**
 * MODSDK 工作流部署命令入口 v16.0
 *
 * 这是全局命令 `initmc` 的入口文件
 * v16.0: 调用lib/init-workflow.js，支持双层文档架构
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

// ⭐ 开发环境预检查：防止在本项目中误执行
const cwd = process.cwd();
const devMarkers = [
  'lib/init-workflow.js',
  'lib/analyzer.js',
  'templates/.claude/settings.json.template',
  'bin/initmc.js'
];

const isDevEnv = devMarkers.every(marker => fs.existsSync(path.join(cwd, marker)));

if (isDevEnv) {
  console.error('\n❌ 错误：不能在 NeteaseMod-Claude 开发环境中执行 initmc');
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  console.error('当前目录: ' + cwd);
  console.error('\n这是工作流生成器的源代码目录，不是 MODSDK 项目。\n');
  console.error('📍 正确用法：');
  console.error('   1. 切换到你的 MODSDK 项目目录');
  console.error('   2. 执行: initmc\n');
  console.error('💡 示例：');
  console.error('   cd D:\\MyProject\\my-game');
  console.error('   initmc\n');
  console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  process.exit(1);
}

// 加载v16.0核心模块
const { main } = require(path.join(workflowHome, 'lib', 'init-workflow'));

// 运行主函数
main().catch(err => {
  console.error('\n❌ 部署失败:', err.message);
  if (err.stack) {
    console.error('\n详细错误信息:');
    console.error(err.stack);
  }
  process.exit(1);
});
