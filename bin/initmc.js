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
