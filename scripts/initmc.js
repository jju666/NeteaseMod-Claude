#!/usr/bin/env node

/**
 * MODSDK 工作流部署脚本
 *
 * 功能：在 MODSDK 项目目录中部署 Claude Code 工作流
 *
 * 使用方式：
 *   1. 在 MODSDK 项目根目录打开 cmd
 *   2. 输入：initmc
 *   3. 等待部署完成
 *
 * 作者：Claude Code Workflow
 * 版本：2.0.0
 */

const fs = require('fs-extra');
const path = require('path');
const os = require('os');

// ANSI 颜色代码
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function error(message) {
  log(`❌ 错误: ${message}`, 'red');
}

function success(message) {
  log(`✅ ${message}`, 'green');
}

function info(message) {
  log(`ℹ️  ${message}`, 'cyan');
}

function warning(message) {
  log(`⚠️  ${message}`, 'yellow');
}

/**
 * 检测全局工作流目录
 */
function detectGlobalWorkflowDir() {
  // 方法1: 默认位置
  const defaultDir = path.join(os.homedir(), '.claude-modsdk-workflow');
  if (fs.existsSync(path.join(defaultDir, 'CLAUDE.md'))) {
    return defaultDir;
  }

  // 方法2: 环境变量
  if (process.env.CLAUDE_WORKFLOW_ROOT) {
    const envDir = process.env.CLAUDE_WORKFLOW_ROOT;
    if (fs.existsSync(path.join(envDir, 'CLAUDE.md'))) {
      return envDir;
    }
  }

  return null;
}

/**
 * 检测当前项目类型
 */
function detectProjectType(projectDir) {
  const hasModMain = fs.existsSync(path.join(projectDir, 'modMain.py'));
  const hasCLAUDE = fs.existsSync(path.join(projectDir, 'CLAUDE.md'));
  const hasInitmc = fs.existsSync(path.join(projectDir, '.claude', 'commands', 'initmc.md'));

  if (hasCLAUDE && hasInitmc) {
    return 'workflow'; // 工作流项目本身
  }

  if (hasModMain) {
    return 'modsdk'; // MODSDK 项目
  }

  return 'unknown';
}

/**
 * 复制文件并验证
 */
function copyFileWithValidation(src, dest, minSize = 1000) {
  const fileName = path.basename(dest);

  try {
    // 确保目标目录存在
    fs.ensureDirSync(path.dirname(dest));

    // 复制文件
    fs.copyFileSync(src, dest);

    // 验证文件大小
    const stat = fs.statSync(dest);
    if (stat.size < minSize) {
      throw new Error(`文件过小 (${stat.size} bytes)`);
    }

    log(`  ✅ ${fileName} - ${(stat.size / 1024).toFixed(1)} KB`, 'green');
    return true;
  } catch (err) {
    error(`  复制 ${fileName} 失败: ${err.message}`);
    return false;
  }
}

/**
 * 生成定制化的 cc.md
 */
function generateCustomizedCC(globalDir, projectDir) {
  const templatePath = path.join(globalDir, '.claude', 'commands', 'cc.md');

  if (!fs.existsSync(templatePath)) {
    error('找不到 cc.md 模板文件');
    return false;
  }

  try {
    let content = fs.readFileSync(templatePath, 'utf-8');

    // 替换项目路径占位符
    // 注意: Windows 路径需要转换为正斜杠
    const normalizedPath = projectDir.replace(/\\/g, '/');
    content = content.replace(/D:\/EcWork\/NetEaseMapECBedWars_备份/g, normalizedPath);

    // 写入目标文件
    const destPath = path.join(projectDir, '.claude', 'commands', 'cc.md');
    fs.ensureDirSync(path.dirname(destPath));
    fs.writeFileSync(destPath, content, 'utf-8');

    const stat = fs.statSync(destPath);
    log(`  ✅ cc.md - ${(stat.size / 1024).toFixed(1)} KB (定制化)`, 'green');
    return true;
  } catch (err) {
    error(`生成 cc.md 失败: ${err.message}`);
    return false;
  }
}

/**
 * 生成定制化的 CLAUDE.md
 */
function generateCustomizedCLAUDE(globalDir, projectDir) {
  const templatePath = path.join(globalDir, 'CLAUDE.md');

  if (!fs.existsSync(templatePath)) {
    error('找不到 CLAUDE.md 模板文件');
    return false;
  }

  try {
    let content = fs.readFileSync(templatePath, 'utf-8');

    // 替换项目路径占位符
    const normalizedPath = projectDir.replace(/\\/g, '/');
    content = content.replace(/\{\{PROJECT_ROOT\}\}/g, normalizedPath);

    // 替换当前日期
    const currentDate = new Date().toISOString().split('T')[0];
    content = content.replace(/\{\{CURRENT_DATE\}\}/g, currentDate);

    // 写入目标文件
    const destPath = path.join(projectDir, 'CLAUDE.md');
    fs.writeFileSync(destPath, content, 'utf-8');

    const stat = fs.statSync(destPath);
    log(`  ✅ CLAUDE.md - ${(stat.size / 1024).toFixed(1)} KB`, 'green');
    return true;
  } catch (err) {
    error(`生成 CLAUDE.md 失败: ${err.message}`);
    return false;
  }
}

/**
 * 主部署函数
 */
async function deployWorkflow() {
  console.log('');
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan');
  log('  MODSDK 工作流部署工具 v2.0', 'cyan');
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan');
  console.log('');

  // 1. 检测当前目录
  const currentDir = process.cwd();
  info(`当前目录: ${currentDir}`);
  console.log('');

  const projectType = detectProjectType(currentDir);

  if (projectType === 'workflow') {
    error('检测到工作流项目本身');
    console.log('');
    console.log('initmc 命令仅用于在 MODSDK 项目中部署工作流。');
    console.log('当前目录是工作流项目本身，无需部署。');
    console.log('');
    console.log('使用说明:');
    console.log('  1. 在需要部署工作流的 MODSDK 项目根目录打开 cmd');
    console.log('  2. 输入: initmc');
    console.log('  3. 等待部署完成');
    console.log('');
    process.exit(1);
  }

  if (projectType === 'unknown') {
    error('当前目录不是 MODSDK 项目');
    console.log('');
    console.log('请在项目根目录（包含 modMain.py 的目录）执行 initmc');
    console.log('');
    process.exit(1);
  }

  success('检测到 MODSDK 项目');
  console.log('');

  // 2. 检测全局工作流目录
  log('🔍 检测全局工作流目录...', 'blue');
  const globalDir = detectGlobalWorkflowDir();

  if (!globalDir) {
    error('找不到全局工作流目录');
    console.log('');
    console.log('可能原因:');
    console.log('  1. 未执行全局安装（npm run install-global）');
    console.log('  2. 环境变量 CLAUDE_WORKFLOW_ROOT 未设置');
    console.log('');
    console.log('解决方案:');
    console.log('  cd <工作流项目目录>');
    console.log('  npm run install-global');
    console.log('');
    process.exit(1);
  }

  success(`找到全局工作流目录: ${globalDir}`);
  console.log('');

  // 3. 复制命令文件
  log('📋 复制命令文件...', 'blue');

  let allSuccess = true;

  allSuccess &= copyFileWithValidation(
    path.join(globalDir, '.claude', 'commands', 'enhance-docs.md'),
    path.join(currentDir, '.claude', 'commands', 'enhance-docs.md'),
    5000
  );

  allSuccess &= copyFileWithValidation(
    path.join(globalDir, '.claude', 'commands', 'validate-docs.md'),
    path.join(currentDir, '.claude', 'commands', 'validate-docs.md'),
    6000
  );

  // 生成定制化 cc.md
  allSuccess &= generateCustomizedCC(globalDir, currentDir);

  console.log('');

  if (!allSuccess) {
    error('命令文件复制失败');
    process.exit(1);
  }

  // 4. 复制通用文档
  log('📚 复制通用文档...', 'blue');

  const docsToCopy = [
    { src: 'markdown/开发规范.md', minSize: 10000 },
    { src: 'markdown/问题排查.md', minSize: 5000 },
    { src: 'markdown/快速开始.md', minSize: 3000 },
    { src: 'markdown/开发指南.md', minSize: 10000 },
    { src: 'markdown/API速查.md', minSize: 3000 },
    { src: 'markdown/MODSDK核心概念.md', minSize: 3000 }
  ];

  docsToCopy.forEach(doc => {
    allSuccess &= copyFileWithValidation(
      path.join(globalDir, doc.src),
      path.join(currentDir, doc.src),
      doc.minSize
    );
  });

  console.log('');

  if (!allSuccess) {
    error('通用文档复制失败');
    process.exit(1);
  }

  // 5. 复制 AI 辅助文档
  log('🤖 复制 AI 辅助文档...', 'blue');

  const aiDocsToCopy = [
    { src: 'markdown/ai/任务类型决策表.md', minSize: 2000 },
    { src: 'markdown/ai/快速通道流程.md', minSize: 2000 },
    { src: 'markdown/ai/上下文管理规范.md', minSize: 2000 }
  ];

  aiDocsToCopy.forEach(doc => {
    allSuccess &= copyFileWithValidation(
      path.join(globalDir, doc.src),
      path.join(currentDir, doc.src),
      doc.minSize
    );
  });

  console.log('');

  if (!allSuccess) {
    error('AI 辅助文档复制失败');
    process.exit(1);
  }

  // 6. 生成 CLAUDE.md
  log('⚙️  生成定制化配置...', 'blue');
  allSuccess &= generateCustomizedCLAUDE(globalDir, currentDir);
  console.log('');

  if (!allSuccess) {
    error('配置生成失败');
    process.exit(1);
  }

  // 7. 创建必要的目录结构
  log('📁 创建目录结构...', 'blue');

  try {
    fs.ensureDirSync(path.join(currentDir, 'tasks'));
    log('  ✅ tasks/', 'green');

    fs.ensureDirSync(path.join(currentDir, 'markdown', 'systems'));
    log('  ✅ markdown/systems/', 'green');

    console.log('');
  } catch (err) {
    error(`创建目录失败: ${err.message}`);
    process.exit(1);
  }

  // 8. 最终验证
  log('🔍 验证部署结果...', 'blue');

  const filesToVerify = [
    { path: '.claude/commands/cc.md', minSize: 10000 },
    { path: '.claude/commands/enhance-docs.md', minSize: 5000 },
    { path: '.claude/commands/validate-docs.md', minSize: 6000 },
    { path: 'CLAUDE.md', minSize: 10000 },
    { path: 'markdown/开发规范.md', minSize: 10000 },
    { path: 'markdown/问题排查.md', minSize: 5000 }
  ];

  let allValid = true;

  filesToVerify.forEach(file => {
    const filePath = path.join(currentDir, file.path);

    if (!fs.existsSync(filePath)) {
      error(`  ${file.path} - 文件不存在`);
      allValid = false;
      return;
    }

    const stat = fs.statSync(filePath);

    if (stat.size < file.minSize) {
      error(`  ${file.path} - 文件过小 (${stat.size} bytes)`);
      allValid = false;
    } else {
      log(`  ✅ ${file.path} - ${(stat.size / 1024).toFixed(1)} KB`, 'green');
    }
  });

  console.log('');

  if (!allValid) {
    error('部署验证失败');
    console.log('');
    console.log('可能原因:');
    console.log('  1. 全局工作流目录文件损坏');
    console.log('  2. 磁盘空间不足');
    console.log('  3. 文件权限问题');
    console.log('');
    process.exit(1);
  }

  // 9. 输出完成报告
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
  log('  ✅ 工作流部署完成！', 'green');
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
  console.log('');

  console.log('📊 部署统计:');
  console.log('  ✅ 命令文件: 3 个');
  console.log('  ✅ 通用文档: 6 个');
  console.log('  ✅ AI 文档: 3 个');
  console.log('  ✅ 配置文件: 1 个');
  console.log('');

  console.log('📝 后续步骤:');
  console.log('  1. 查阅 CLAUDE.md 了解 AI 工作流程');
  console.log('  2. 使用 /cc "任务描述" 快速创建/继续任务');
  console.log('  3. 查阅 markdown/ 目录下的文档');
  console.log('');

  console.log('🎯 可用命令:');
  console.log('  /cc "任务描述" - 快速任务执行器');
  console.log('  /enhance-docs - 批量补充文档');
  console.log('  /validate-docs - 验证文档完整性');
  console.log('');

  log('🎉 开始高效开发吧！', 'cyan');
  console.log('');
}

// 执行部署
deployWorkflow().catch(err => {
  console.log('');
  error(`部署过程出现异常: ${err.message}`);
  console.error(err.stack);
  console.log('');
  process.exit(1);
});
