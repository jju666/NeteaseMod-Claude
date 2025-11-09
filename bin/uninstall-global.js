#!/usr/bin/env node
/**
 * 全局卸载脚本
 * 删除全局工作流和相关配置
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const TARGET_DIR = path.join(os.homedir(), '.claude-modsdk-workflow');
const IS_WINDOWS = process.platform === 'win32';

/**
 * Windows卸载
 */
function uninstallWindows() {
  const cmdPath = path.join(os.homedir(), 'modsdk-deploy.cmd');

  if (fs.existsSync(cmdPath)) {
    fs.unlinkSync(cmdPath);
    console.log('✅ 已删除命令脚本');
  }
}

/**
 * Unix卸载
 */
function uninstallUnix() {
  const configs = [
    path.join(os.homedir(), '.bashrc'),
    path.join(os.homedir(), '.zshrc')
  ];

  for (const config of configs) {
    if (fs.existsSync(config)) {
      let content = fs.readFileSync(config, 'utf8');

      // 移除alias行
      const lines = content.split('\n');
      const filtered = lines.filter(line =>
        !line.includes('modsdk-deploy') &&
        !line.includes('MODSDK Workflow Generator')
      );

      if (filtered.length !== lines.length) {
        fs.writeFileSync(config, filtered.join('\n'));
        console.log(`✅ 已清理 ${path.basename(config)}`);
      }
    }
  }
}

/**
 * 主函数
 */
function main() {
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🗑️  MODSDK工作流生成器 - 卸载');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // 删除全局目录
  if (fs.existsSync(TARGET_DIR)) {
    console.log(`📦 删除全局目录: ${TARGET_DIR}`);
    fs.rmSync(TARGET_DIR, { recursive: true, force: true });
    console.log('✅ 全局目录已删除\n');
  } else {
    console.log('⚠️  全局目录不存在，跳过\n');
  }

  // 平台特定清理
  if (IS_WINDOWS) {
    uninstallWindows();
  } else {
    uninstallUnix();
  }

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('✅ 卸载完成！');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  console.log('📝 注意:');
  console.log('   - 已部署到项目中的 .claude/commands/initmc.md 不会自动删除');
  console.log('   - 如需删除，请手动执行:\n');
  console.log('     rm <project>/.claude/commands/initmc.md\n');
}

// 运行
main();
