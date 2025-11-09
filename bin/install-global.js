#!/usr/bin/env node
/**
 * 全局安装脚本
 * 将工作流生成器复制到用户目录，并配置全局命令
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const SOURCE_DIR = path.resolve(__dirname, '..');
const TARGET_DIR = path.join(os.homedir(), '.claude-modsdk-workflow');
const IS_WINDOWS = process.platform === 'win32';

/**
 * 递归复制目录
 */
function copyDirRecursive(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    // 跳过不需要复制的目录
    const skipDirs = ['node_modules', '.git', '__pycache__', 'tests', 'examples', 'workflow-generator'];
    if (entry.isDirectory() && skipDirs.includes(entry.name)) {
      continue;
    }

    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

/**
 * Windows: 创建批处理脚本
 */
function installWindows() {
  console.log('\n📦 Windows安装模式\n');

  // 创建 modsdk-deploy.cmd
  const cmdContent = `@echo off
node "%USERPROFILE%\\.claude-modsdk-workflow\\bin\\quick-deploy.js" %*
`;

  const cmdPath = path.join(os.homedir(), 'modsdk-deploy.cmd');
  fs.writeFileSync(cmdPath, cmdContent);

  console.log('✅ 已创建命令脚本:');
  console.log(`   ${cmdPath}\n`);

  // 检查PATH中是否包含用户目录
  const userPath = process.env.PATH.split(';');
  const homeInPath = userPath.some(p => p.toLowerCase().includes(os.homedir().toLowerCase()));

  if (!homeInPath) {
    console.log('⚠️  需要手动添加到PATH:');
    console.log(`   1. 打开"环境变量"设置`);
    console.log(`   2. 在"用户变量"中找到"Path"`);
    console.log(`   3. 添加: ${os.homedir()}`);
    console.log(`   4. 重启终端\n`);
  } else {
    console.log('✅ 用户目录已在PATH中\n');
  }

  console.log('📝 使用方法:');
  console.log('   cd your-modsdk-project');
  console.log('   modsdk-deploy\n');
}

/**
 * Unix: 添加alias到shell配置
 */
function installUnix() {
  console.log('\n📦 Unix/Linux/Mac安装模式\n');

  const shellConfig = path.join(os.homedir(), '.bashrc');
  const aliasLine = `\n# MODSDK Workflow Generator\nalias modsdk-deploy="node ~/.claude-modsdk-workflow/bin/quick-deploy.js"\n`;

  // 检查是否已添加
  if (fs.existsSync(shellConfig)) {
    const content = fs.readFileSync(shellConfig, 'utf8');
    if (content.includes('modsdk-deploy')) {
      console.log('✅ Alias已存在于 ~/.bashrc\n');
    } else {
      fs.appendFileSync(shellConfig, aliasLine);
      console.log('✅ 已添加alias到 ~/.bashrc\n');
    }
  } else {
    fs.writeFileSync(shellConfig, aliasLine);
    console.log('✅ 已创建 ~/.bashrc 并添加alias\n');
  }

  // 如果是Mac，同时添加到.zshrc
  if (process.platform === 'darwin') {
    const zshConfig = path.join(os.homedir(), '.zshrc');
    if (fs.existsSync(zshConfig)) {
      const content = fs.readFileSync(zshConfig, 'utf8');
      if (!content.includes('modsdk-deploy')) {
        fs.appendFileSync(zshConfig, aliasLine);
        console.log('✅ 已添加alias到 ~/.zshrc（Mac）\n');
      }
    }
  }

  console.log('📝 激活命令:');
  console.log('   source ~/.bashrc\n');

  console.log('📝 使用方法:');
  console.log('   cd your-modsdk-project');
  console.log('   modsdk-deploy\n');
}

/**
 * 主函数
 */
function main() {
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🚀 MODSDK工作流生成器 - 全局安装');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // 检查目标目录
  if (fs.existsSync(TARGET_DIR)) {
    console.log('⚠️  目标目录已存在，将覆盖...');
    fs.rmSync(TARGET_DIR, { recursive: true, force: true });
  }

  // 复制文件
  console.log('📦 复制文件到全局目录...');
  console.log(`   源: ${SOURCE_DIR}`);
  console.log(`   目标: ${TARGET_DIR}\n`);

  copyDirRecursive(SOURCE_DIR, TARGET_DIR);

  console.log('✅ 文件复制完成\n');

  // 平台特定安装
  if (IS_WINDOWS) {
    installWindows();
  } else {
    installUnix();
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('✅ 全局安装完成！');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  console.log('🎯 下一步:');
  console.log('   1. 进入任意MODSDK项目目录');
  console.log('   2. 运行: modsdk-deploy');
  console.log('   3. 使用: /initmc 初始化工作流\n');

  console.log('📚 更多信息:');
  console.log('   README: ' + path.join(TARGET_DIR, 'README.md') + '\n');
}

// 运行
main();
