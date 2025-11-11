#!/usr/bin/env node

/**
 * 废弃文件检测命令 v16.0
 * 用途: 检测和处理版本升级时的废弃文件
 *
 * 使用方式:
 *   detect-obsolete                    # 检测并交互式处理废弃文件
 *   detect-obsolete --list             # 只列出废弃文件
 *   detect-obsolete --dry-run          # 模拟运行（不实际修改）
 *   detect-obsolete --auto-confirm     # 自动确认所有操作
 *   detect-obsolete --from 15.0.0 --to 16.0.0  # 指定版本范围
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

// 加载检测器
const { ObsoleteFileDetector } = require(path.join(workflowHome, 'lib', 'obsolete-file-detector'));
const { VersionChecker } = require(path.join(workflowHome, 'lib', 'version-checker'));

// 解析命令行参数
const args = process.argv.slice(2);

const listOnly = args.includes('--list');
const dryRun = args.includes('--dry-run');
const autoConfirm = args.includes('--auto-confirm');

let fromVersion = null;
let toVersion = null;

// 解析版本参数
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--from' && args[i + 1]) {
    fromVersion = args[i + 1];
  }
  if (args[i] === '--to' && args[i + 1]) {
    toVersion = args[i + 1];
  }
}

async function main() {
  const downstreamPath = process.cwd();

  // 如果未指定版本，自动检测
  if (!fromVersion || !toVersion) {
    const checker = new VersionChecker(workflowHome, downstreamPath);
    fromVersion = fromVersion || checker.getLocalVersion();
    toVersion = toVersion || checker.getUpstreamVersion();
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🔍 废弃文件检测');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  console.log(`版本范围: v${fromVersion} → v${toVersion}\n`);

  // 检测废弃文件
  const detector = new ObsoleteFileDetector(downstreamPath);
  const obsoleteFiles = detector.detect(fromVersion, toVersion);

  if (obsoleteFiles.length === 0) {
    console.log('✅ 未发现废弃文件\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    return;
  }

  console.log(`⚠️  发现 ${obsoleteFiles.length} 个废弃文件:\n`);

  // 按动作分组显示
  const grouped = {};
  for (const item of obsoleteFiles) {
    if (!grouped[item.action]) {
      grouped[item.action] = [];
    }
    grouped[item.action].push(item);
  }

  for (const [action, items] of Object.entries(grouped)) {
    console.log(`[${action.toUpperCase()}] ${items.length} 个文件:`);
    items.forEach(item => {
      console.log(`  - ${item.file}`);
      console.log(`    原因: ${item.reason}`);
    });
    console.log('');
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // 如果是只列出模式，直接退出
  if (listOnly) {
    console.log('💡 执行 `detect-obsolete` 开始处理流程\n');
    return;
  }

  // 执行处理
  await detector.process(obsoleteFiles, { autoConfirm, dryRun });
}

main().catch(err => {
  console.error('❌ 执行失败:', err.message);
  process.exit(1);
});
