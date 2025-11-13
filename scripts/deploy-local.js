#!/usr/bin/env node
/**
 * 本地快速部署脚本 v20.2.5
 *
 * 用法：
 *   node scripts/deploy-local.js <目标项目路径>
 *
 * 示例：
 *   node scripts/deploy-local.js D:\EcWork\NetEaseMapECBedWars
 */

const path = require('path');
const fs = require('fs-extra');

// 获取目标项目路径
const targetDir = process.argv[2];

if (!targetDir) {
  console.error('❌ 错误：请提供目标项目路径');
  console.error('\n用法：');
  console.error('  node scripts/deploy-local.js <目标项目路径>');
  console.error('\n示例：');
  console.error('  node scripts/deploy-local.js D:\\EcWork\\NetEaseMapECBedWars\n');
  process.exit(1);
}

const absoluteTargetDir = path.resolve(targetDir);

if (!fs.existsSync(absoluteTargetDir)) {
  console.error(`❌ 错误：目标目录不存在: ${absoluteTargetDir}\n`);
  process.exit(1);
}

console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
console.log('🚀 本地快速部署 v20.2.7');
console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
console.log(`源目录: ${__dirname}`);
console.log(`目标项目: ${absoluteTargetDir}\n`);

// 设置临时环境变量，模拟全局安装
const workflowSourceDir = path.resolve(__dirname, '..');
process.env.NETEASE_CLAUDE_HOME = workflowSourceDir;

// 切换到目标目录
process.chdir(absoluteTargetDir);
console.log(`✅ 已切换到: ${process.cwd()}\n`);

// 加载init-workflow模块
const { main } = require(path.join(workflowSourceDir, 'lib', 'init-workflow'));

// 执行部署
console.log('开始部署工作流...\n');
main()
  .then(() => {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 部署完成！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    console.log('💡 提示：');
    console.log('  - 修改源代码后，再次运行此脚本即可更新');
    console.log('  - 无需 npm publish 或 npm link');
    console.log('  - 适合快速迭代开发\n');
  })
  .catch(err => {
    console.error('\n❌ 部署失败:', err.message);
    if (err.stack) {
      console.error('\n详细错误信息:');
      console.error(err.stack);
    }
    process.exit(1);
  });
