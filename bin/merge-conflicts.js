#!/usr/bin/env node

/**
 * 覆盖层冲突合并命令 v16.0
 * 用途: 检测并合并markdown/core/中的覆盖层文件与上游更新的冲突
 *
 * 使用方式:
 *   merge-conflicts           # 交互式合并冲突
 *   merge-conflicts --list    # 只列出冲突，不合并
 */

const path = require('path');
const fs = require('fs');

// 查找全局工作流目录
const workflowHome = process.env.NETEASE_CLAUDE_HOME ||
                     path.join(require('os').homedir(), '.claude-modsdk-workflow');

if (!fs.existsSync(workflowHome)) {
  console.error('❌ 错误: 未找到全局工作流目录');
  console.error('请先运行: npm run install-global');
  process.exit(1);
}

// 加载合并工具
const { OverrideMergeTool } = require(path.join(workflowHome, 'lib', 'merge-override-conflicts'));
const { VersionChecker } = require(path.join(workflowHome, 'lib', 'version-checker'));

// 解析命令行参数
const args = process.argv.slice(2);
const listOnly = args.includes('--list');

async function main() {
  const downstreamPath = process.cwd();

  if (listOnly) {
    // 只列出冲突
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📋 覆盖层冲突检测');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    const checker = new VersionChecker(workflowHome, downstreamPath);
    const conflicts = await checker.detectOverrideConflicts();

    if (conflicts.length === 0) {
      console.log('✅ 未发现冲突\n');
    } else {
      console.log(`⚠️  发现 ${conflicts.length} 个冲突:\n`);

      conflicts.forEach((conflict, index) => {
        console.log(`${index + 1}. ${conflict.file}`);
        console.log(`   ${conflict.description}\n`);
      });

      console.log('💡 执行 `merge-conflicts` 开始合并流程\n');
    }

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  } else {
    // 交互式合并
    const tool = new OverrideMergeTool(workflowHome, downstreamPath);
    await tool.run();
  }
}

main().catch(err => {
  console.error('❌ 执行失败:', err.message);
  process.exit(1);
});
