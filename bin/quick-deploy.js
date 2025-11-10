#!/usr/bin/env node
/**
 * 快速部署脚本
 * 在目标MODSDK项目中创建 /initmc 命令
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const WORKFLOW_HOME = path.join(os.homedir(), '.claude-modsdk-workflow');
const CURRENT_DIR = process.cwd();
const IS_WINDOWS = process.platform === 'win32';

/**
 * 检测项目提示（不强制）
 * @returns {Array<string>} 检测到的项目特征
 */
function detectProjectHints() {
  const hints = [];

  // 查找 modMain.py（向上3层）
  if (findFileShallow(CURRENT_DIR, 'modMain.py', 3)) {
    hints.push('modMain.py');
  }

  // 检查 behavior_packs/（网易地图）
  if (fs.existsSync(path.join(CURRENT_DIR, 'behavior_packs'))) {
    hints.push('behavior_packs/');
  }

  // 检查 deploy.json（Apollo）
  if (fs.existsSync(path.join(CURRENT_DIR, 'deploy.json'))) {
    hints.push('deploy.json');
  }

  // 检查 .mcs/（网易开发工具）
  if (fs.existsSync(path.join(CURRENT_DIR, '.mcs'))) {
    hints.push('.mcs/');
  }

  // 检查是否有 .py 文件
  try {
    const files = fs.readdirSync(CURRENT_DIR);
    const hasPythonFiles = files.some(f => f.endsWith('.py'));
    if (hasPythonFiles) {
      hints.push('Python文件');
    }
  } catch (err) {
    // 忽略读取错误
  }

  return hints;
}

/**
 * 浅层查找文件（向上查找N层）
 * @param {string} dir - 起始目录
 * @param {string} filename - 文件名
 * @param {number} maxDepth - 最大深度
 * @returns {boolean}
 */
function findFileShallow(dir, filename, maxDepth = 3) {
  for (let i = 0; i < maxDepth; i++) {
    if (fs.existsSync(path.join(dir, filename))) {
      return true;
    }
    const parentDir = path.dirname(dir);
    if (parentDir === dir) break; // 到达根目录
    dir = parentDir;
  }
  return false;
}

/**
 * 创建目录（如果不存在）
 */
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * 部署initmc命令
 */
function deployInitmc() {
  const commandsDir = path.join(CURRENT_DIR, '.claude', 'commands');
  ensureDir(commandsDir);

  const srcPath = path.join(WORKFLOW_HOME, '.claude', 'commands', 'initmc.md');
  const destPath = path.join(commandsDir, 'initmc.md');

  if (!fs.existsSync(srcPath)) {
    console.error('❌ 错误: 全局工作流未安装');
    console.error('   请先运行: npm run install-global');
    process.exit(1);
  }

  // Windows: 复制文件（避免符号链接权限问题）
  if (IS_WINDOWS) {
    fs.copyFileSync(srcPath, destPath);
    console.log('✅ 已复制 initmc.md 命令');
  } else {
    // Unix: 创建符号链接
    if (fs.existsSync(destPath)) {
      fs.unlinkSync(destPath);
    }
    fs.symlinkSync(srcPath, destPath);
    console.log('✅ 已创建 initmc.md 软链接');
  }
}

/**
 * 主函数
 */
function main() {
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('📦 MODSDK工作流 - 快速部署');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // 检测项目特征（提示但不阻止）
  const projectHints = detectProjectHints();

  console.log(`📂 当前目录: ${path.basename(CURRENT_DIR)}`);

  if (projectHints.length > 0) {
    console.log(`✅ 检测到: ${projectHints.join(', ')}`);
    console.log('');
  } else {
    console.log('ℹ️  提示: 未检测到常见MODSDK特征');
    console.log('   (modMain.py, behavior_packs/, deploy.json 等)');
    console.log('   如果这是MODSDK项目，可以继续部署');
    console.log('');
  }

  // 检查全局安装
  if (!fs.existsSync(WORKFLOW_HOME)) {
    console.error('❌ 错误: 全局工作流未安装');
    console.error('   请先运行全局安装:');
    console.error('   cd <工作流生成器目录>');
    console.error('   npm run install-global');
    process.exit(1);
  }

  console.log(`✅ 全局工作流已安装: ${WORKFLOW_HOME}\n`);

  // 部署命令
  console.log('📍 部署 /initmc 命令...\n');
  deployInitmc();

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('✅ 部署完成！');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  console.log('🎯 下一步:');
  console.log('   在Claude Code中运行: /initmc');
  console.log('   这将生成完整的AI工作流文档\n');

  console.log('📝 提示:');
  console.log('   - 如果提示"命令未找到"，请重启Claude Code');
  console.log('   - 首次运行 /initmc 需要3-15分钟');
}

// 运行
main();
