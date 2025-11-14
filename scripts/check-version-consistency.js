#!/usr/bin/env node
/**
 * 版本一致性检查脚本 (v20.2.12)
 * 确保 package.json 和 config.js 中的版本号一致
 *
 * 用于:
 * - CI/CD 流程
 * - pre-publish 钩子
 * - 开发环境验证
 */

const path = require('path');
const fs = require('fs');

function main() {
  console.log('🔍 检查版本一致性...\n');

  try {
    // 读取 package.json
    const pkgPath = path.join(__dirname, '..', 'package.json');
    const pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
    const pkgVersion = pkg.version;

    // 读取 config.js (清除缓存)
    const configPath = path.join(__dirname, '..', 'lib', 'config.js');
    delete require.cache[require.resolve(configPath)];
    const config = require(configPath);
    const configVersion = config.VERSION;

    // 比较版本号
    console.log(`📦 package.json: ${pkgVersion}`);
    console.log(`⚙️  config.js:    ${configVersion}\n`);

    if (pkgVersion !== configVersion) {
      console.error('❌ 版本不一致!');
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
      console.error('可能原因:');
      console.error('1. config.js 中的 VERSION 未从 package.json 读取');
      console.error('2. 存在硬编码的版本号');
      console.error('3. Node.js 模块缓存问题\n');
      console.error('解决方案:');
      console.error('确保 lib/config.js 中:');
      console.error('  const pkg = require(\'../package.json\');');
      console.error('  const VERSION = pkg.version;\n');
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
      process.exit(1);
    }

    console.log('✅ 版本一致性检查通过\n');
    process.exit(0);

  } catch (err) {
    console.error('❌ 检查失败:', err.message);
    process.exit(1);
  }
}

// 运行
if (require.main === module) {
  main();
}

module.exports = { main };
