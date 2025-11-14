#!/usr/bin/env node
/**
 * 全局安装脚本
 * 将工作流生成器复制到用户目录，并配置全局命令
 */

const fs = require('fs');
const path = require('path');
const os = require('os');
const { execSync } = require('child_process');

const SOURCE_DIR = path.resolve(__dirname, '..');
const TARGET_DIR = path.join(os.homedir(), '.claude-modsdk-workflow');
const IS_WINDOWS = process.platform === 'win32';

/**
 * 检查依赖是否已安装
 */
function checkDependencies() {
  const requiredDeps = ['fs-extra'];
  const missingDeps = [];

  for (const dep of requiredDeps) {
    try {
      require.resolve(dep, { paths: [SOURCE_DIR] });
    } catch (err) {
      missingDeps.push(dep);
    }
  }

  return missingDeps;
}

/**
 * 安装缺失的依赖
 */
function installDependencies() {
  console.log('\n⚠️  检测到缺失依赖，正在自动安装...\n');

  try {
    console.log('📦 执行: npm install\n');

    // 在工作流项目目录执行 npm install
    execSync('npm install', {
      cwd: SOURCE_DIR,
      stdio: 'inherit',
      shell: true
    });

    console.log('\n✅ 依赖安装完成\n');
    return true;
  } catch (err) {
    console.error('\n❌ 依赖安装失败:', err.message);
    console.error('\n请手动执行:');
    console.error(`   cd ${SOURCE_DIR}`);
    console.error('   npm install\n');
    return false;
  }
}

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

    // 跳过符号链接（避免Windows权限问题）
    if (entry.isSymbolicLink()) {
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

  // 创建 initmc.cmd（部署命令）
  const initCmdContent = `@echo off
node "%USERPROFILE%\\.claude-modsdk-workflow\\bin\\initmc.js" %*
`;

  const initCmdPath = path.join(os.homedir(), 'initmc.cmd');
  fs.writeFileSync(initCmdPath, initCmdContent);

  // 创建 uninstallmc.cmd（卸载命令）⭐ v16.0
  const uninstallCmdContent = `@echo off
node "%USERPROFILE%\\.claude-modsdk-workflow\\bin\\uninstallmc.js" %*
`;

  const uninstallCmdPath = path.join(os.homedir(), 'uninstallmc.cmd');
  fs.writeFileSync(uninstallCmdPath, uninstallCmdContent);

  console.log('✅ 已创建命令脚本:');
  console.log(`   ${initCmdPath}`);
  console.log(`   ${uninstallCmdPath}\n`);

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
  console.log('   initmc\n');
}

/**
 * Unix: 添加alias到shell配置
 */
function installUnix() {
  console.log('\n📦 Unix/Linux/Mac安装模式\n');

  const shellConfig = path.join(os.homedir(), '.bashrc');
  const aliasLines = `\n# MODSDK Workflow Generator
alias initmc="node ~/.claude-modsdk-workflow/bin/initmc.js"
alias uninstallmc="node ~/.claude-modsdk-workflow/bin/uninstallmc.js"
`;

  // 检查是否已添加
  if (fs.existsSync(shellConfig)) {
    const content = fs.readFileSync(shellConfig, 'utf8');
    if (content.includes('initmc') && content.includes('uninstallmc')) {
      console.log('✅ Alias已存在于 ~/.bashrc\n');
    } else {
      // 如果只有旧的 initmc，先移除旧版本
      let newContent = content;
      if (content.includes('alias initmc=') && !content.includes('uninstallmc')) {
        newContent = content.replace(/# MODSDK Workflow Generator\nalias initmc=.*\n/g, '');
      }
      fs.writeFileSync(shellConfig, newContent + aliasLines);
      console.log('✅ 已更新alias到 ~/.bashrc\n');
    }
  } else {
    fs.writeFileSync(shellConfig, aliasLines);
    console.log('✅ 已创建 ~/.bashrc 并添加alias\n');
  }

  // 如果是Mac，同时添加到.zshrc
  if (process.platform === 'darwin') {
    const zshConfig = path.join(os.homedir(), '.zshrc');
    if (fs.existsSync(zshConfig)) {
      const content = fs.readFileSync(zshConfig, 'utf8');
      if (!content.includes('initmc') || !content.includes('uninstallmc')) {
        // 移除旧版本
        let newContent = content;
        if (content.includes('alias initmc=') && !content.includes('uninstallmc')) {
          newContent = content.replace(/# MODSDK Workflow Generator\nalias initmc=.*\n/g, '');
        }
        fs.writeFileSync(zshConfig, newContent + aliasLines);
        console.log('✅ 已更新alias到 ~/.zshrc（Mac）\n');
      }
    }
  }

  console.log('📝 激活命令:');
  console.log('   source ~/.bashrc\n');

  console.log('📝 使用方法:');
  console.log('   cd your-modsdk-project');
  console.log('   initmc       # 部署工作流');
  console.log('   uninstallmc  # 卸载工作流\n');
}

/**
 * 主函数
 */
function main() {
  // v20.2.12: 从 package.json 动态读取版本号
  const pkg = require('../package.json');
  const version = pkg.version;

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log(`🚀 MODSDK工作流生成器 - 全局部署 v${version}`);
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // ⚠️ v20.2.12: install-global.js 已废弃,推荐使用 npm link
  console.warn('⚠️  警告: 此部署方式已废弃!\n');
  console.warn('推荐使用更简洁的 npm link 方式:');
  console.warn('  npm link');
  console.warn('  # 或');
  console.warn('  npm install -g .\n');
  console.warn('优点: 实时更新、无残留文件、自动清理\n');
  console.warn('按 Ctrl+C 取消,或等待 5 秒继续使用旧方式...\n');

  // 延迟 5 秒,给用户思考时间
  const startTime = Date.now();
  while (Date.now() - startTime < 5000) {
    // 同步等待
  }

  // 检查依赖
  console.log('🔍 检查依赖...\n');
  const missingDeps = checkDependencies();

  if (missingDeps.length > 0) {
    console.log('⚠️  缺失依赖:', missingDeps.join(', '));
    console.log('   这通常是因为跳过了 npm install 步骤\n');

    const success = installDependencies();
    if (!success) {
      console.log('❌ 全局安装失败：无法安装依赖\n');
      console.log('请先执行以下步骤:');
      console.log(`   1. cd ${SOURCE_DIR}`);
      console.log('   2. npm install');
      console.log('   3. npm run install-global\n');
      process.exit(1);
    }
  } else {
    console.log('✅ 依赖检查通过\n');
  }

  // 检查目标目录
  if (fs.existsSync(TARGET_DIR)) {
    console.log('⚠️  目标目录已存在，将覆盖...');
    fs.rmSync(TARGET_DIR, { recursive: true, force: true });
  }

  // 复制文件
  console.log('📦 复制文件到全局目录...');
  console.log(`   源: ${SOURCE_DIR}`);
  console.log(`   目标: ${TARGET_DIR}\n`);

  try {
    copyDirRecursive(SOURCE_DIR, TARGET_DIR);
    console.log('✅ 文件复制完成\n');
  } catch (err) {
    // 检测是否为Windows权限错误
    if (IS_WINDOWS && err.code === 'EPERM') {
      console.error('\n❌ 安装失败：权限不足\n');
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.error('⚠️  Windows需要管理员权限来创建符号链接\n');
      console.error('解决方案（任选其一）：\n');
      console.error('方案1：以管理员身份运行（推荐）');
      console.error('   1. 关闭当前终端');
      console.error('   2. 右键点击 "Windows PowerShell" → "以管理员身份运行"');
      console.error('   3. 切换到项目目录（注意使用引号处理空格）:');
      console.error(`      cd "${SOURCE_DIR}"`);
      console.error('   4. 重新运行: npm run install-global\n');
      console.error('方案2：启用开发者模式（Windows 10+）');
      console.error('   1. 设置 → 更新和安全 → 开发者选项');
      console.error('   2. 打开"开发人员模式"');
      console.error('   3. 重启终端后重试\n');
      console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
      console.error('详细说明：./docs/INSTALLATION.md#问题3windows软连接权限不足\n');
      process.exit(1);
    } else {
      // 其他错误
      console.error('\n❌ 文件复制失败:', err.message);
      console.error('错误代码:', err.code);
      console.error('错误路径:', err.path || '未知\n');
      process.exit(1);
    }
  }

  // 在目标目录安装依赖（v16.0新增）
  console.log('📦 在全局目录安装依赖...\n');
  console.log('⏳ 正在安装npm依赖包...');
  console.log('⏳ 正在下载官方文档（Git Submodule）...');
  console.log('   这可能需要1-3分钟，取决于网络速度');
  console.log('   请耐心等待，不要关闭终端\n');

  try {
    execSync('npm install --production', {
      cwd: TARGET_DIR,
      stdio: 'inherit',
      shell: true
    });
    console.log('\n✅ 依赖安装完成\n');
  } catch (err) {
    console.error('\n❌ 依赖安装失败:', err.message);
    console.error('\n请手动执行:');
    console.error(`   cd ${TARGET_DIR}`);
    console.error('   npm install --production\n');
    process.exit(1);
  }

  // 修复：确保ai文档被正确复制（修复BUG）
  console.log('📝 验证核心文档完整性...\n');
  const aiSourceDir = path.join(SOURCE_DIR, 'markdown', 'ai');
  const aiTargetDir = path.join(TARGET_DIR, 'markdown', 'ai');

  if (fs.existsSync(aiSourceDir)) {
    const aiFiles = fs.readdirSync(aiSourceDir).filter(f => f.endsWith('.md'));
    const targetFiles = fs.existsSync(aiTargetDir) ? fs.readdirSync(aiTargetDir).filter(f => f.endsWith('.md')) : [];

    if (aiFiles.length > targetFiles.length) {
      console.log(`⚠️  检测到ai文档不完整(${targetFiles.length}/${aiFiles.length}),正在修复...`);
      fs.mkdirSync(aiTargetDir, { recursive: true });

      for (const file of aiFiles) {
        const srcFile = path.join(aiSourceDir, file);
        const destFile = path.join(aiTargetDir, file);
        if (!fs.existsSync(destFile)) {
          fs.copyFileSync(srcFile, destFile);
          console.log(`   ✅ 复制: ${file}`);
        }
      }
      console.log('✅ ai文档修复完成\n');
    } else {
      console.log(`✅ ai文档完整(${aiFiles.length}个文件)\n`);
    }
  }

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
  console.log('   2. 运行: initmc');
  console.log('   3. 开始使用Claude Code开发\n');

  console.log('📚 更多信息:');
  console.log('   README: ' + path.join(TARGET_DIR, 'README.md') + '\n');
}

// 运行
main();
