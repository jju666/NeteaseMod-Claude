#!/usr/bin/env node
/**
 * 工作流初始化入口
 * 被 /initmc 命令调用
 * v16.0: 新增 --sync 参数支持自动同步更新
 */

const path = require('path');
const { ProjectAnalyzer } = require('./analyzer');
const { DocumentGenerator } = require('./generator');
const { VersionChecker } = require('./version-checker');
const { SymlinkManager } = require('./symlink-manager');
const { MigrationV16 } = require('./migration-v16');
const { MigrationV161 } = require('./migration-v16.1');
const { ObsoleteFileDetector } = require('./obsolete-file-detector');
const { WORKFLOW_HOME } = require('./config');

/**
 * 主函数
 */
async function main() {
  // 解析命令行参数
  const args = process.argv.slice(2);
  const flags = args.filter(arg => arg.startsWith('--'));
  const targetPath = args.find(arg => !arg.startsWith('--')) || process.cwd();

  // 检查是否是同步模式
  const isSyncMode = flags.includes('--sync');
  const isResetMode = flags.includes('--reset');

  try {
    // 模式1: 同步更新（--sync）
    if (isSyncMode) {
      return await syncWorkflow(targetPath, { reset: isResetMode });
    }

    // 模式2: 首次部署或重新部署
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 开始初始化MODSDK工作流');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // 检查是否需要迁移（优先级：v16.0→v16.1 > v15.x→v16.0）
    const migrationV161 = new MigrationV161(WORKFLOW_HOME, targetPath);
    if (migrationV161.needsMigration()) {
      const result = await migrationV161.migrate({ autoConfirm: false });
      if (result.success) {
        return; // 迁移完成，退出
      }
      // 迁移失败或取消，继续常规部署
    }

    const migrationV16 = new MigrationV16(WORKFLOW_HOME, targetPath);
    if (migrationV16.needsMigration()) {
      const result = await migrationV16.migrate({ autoConfirm: false });
      if (result.success) {
        return; // 迁移完成，退出
      }
      // 迁移失败或取消，继续常规部署
    }

    // 步骤1: 分析项目
    console.log('📍 步骤1：分析项目结构...\n');
    const analyzer = new ProjectAnalyzer(targetPath);
    const report = analyzer.analyze();

    // 输出分析报告
    console.log('\n' + report.toMarkdown());

    // 步骤2: 生成文档（只部署Layer 1核心工作流）
    console.log('\n📍 步骤2：部署核心工作流文档...\n');
    const generator = new DocumentGenerator(report, WORKFLOW_HOME);
    await generator.generateAll(targetPath, { minimalMode: true });

    // 步骤3: 创建上游文档引用（v16.0新增）
    console.log('\n📍 步骤3：创建上游文档引用...\n');
    const symlinkManager = new SymlinkManager(WORKFLOW_HOME, targetPath);
    await symlinkManager.createAllSymlinks();

    // 步骤4: 创建markdown/目录的软连接（v16.2新增）
    console.log('\n📍 步骤4：创建markdown/核心文档引用...\n');
    await symlinkManager.createMarkdownSymlinks();

    // 步骤5: 输出完成报告
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 核心工作流部署完成！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📊 部署内容:');
    console.log('- ✅ CLAUDE.md - AI工作流程总览');
    console.log('- ✅ .claude/commands/ - 5个核心命令');
    console.log('  - /mc - 任务执行器');
    console.log('  - /validate-docs - 文档审计与规范化');
    console.log('  - /enhance-docs - 文档批量生成');
    console.log('  - /discover - 项目结构自适应发现');
    console.log('  - /review-design - MODSDK方案深度审核');
    console.log('- ✅ markdown/ - 核心开发文档（软连接）');
    console.log('  - 开发规范.md、问题排查.md、API速查.md等');
    console.log('  - ai/ - AI辅助文档\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('🎯 下一步（重要！）:\n');
    console.log('请在 Claude Code 中执行以下命令：\n');
    console.log('  /validate-docs\n');
    console.log('该命令将：');
    console.log('  1. AI 自动发现项目中的所有组件（Systems/States/Presets等）');
    console.log('  2. 智能推断规范化的中文文档名');
    console.log('  3. 生成文档待补充清单');
    console.log('  4. （可选）创建文档占位符\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📚 完整工作流:');
    console.log('  1. /validate-docs - 发现组件并规范化文档结构');
    console.log('  2. /enhance-docs - 批量生成高质量文档内容');
    console.log('  3. /mc "任务描述" - 开发时自动维护文档\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🎉 开始体验文档驱动的开发工作流吧！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error('\n请确保：');
    console.error('1. 当前目录是MODSDK项目（包含 modMain.py）');
    console.error('2. 已完成全局安装（运行过 npm run install-global）\n');
    process.exit(1);
  }
}

/**
 * 同步工作流更新
 * @param {string} targetPath - 下游项目路径
 * @param {Object} options - 选项
 */
async function syncWorkflow(targetPath, options = {}) {
  const fs = require('fs-extra');

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('🔄 同步工作流更新');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // 步骤1: 版本检测
  const versionChecker = new VersionChecker(WORKFLOW_HOME, targetPath);
  const check = versionChecker.checkVersion();

  console.log(`📊 版本对比:`);
  console.log(`   本地: v${check.local}`);
  console.log(`   上游: v${check.upstream}\n`);

  if (!check.needsUpdate && !options.reset) {
    console.log('✅ 已是最新版本\n');
    return;
  }

  if (check.needsUpdate) {
    console.log('⚠️  检测到新版本！\n');
    console.log(check.changelog);
    console.log('');
  }

  // 步骤2: 更新软连接
  const symlinkManager = new SymlinkManager(WORKFLOW_HOME, targetPath);
  await symlinkManager.updateSymlinks();

  // 步骤3: 检测废弃文件（使用新的检测器）
  console.log('🧹 检测废弃文件...\n');
  const detector = new ObsoleteFileDetector(targetPath);
  const obsoleteFiles = detector.detect(check.local, check.upstream);

  if (obsoleteFiles.length > 0) {
    console.log(`⚠️  发现 ${obsoleteFiles.length} 个废弃文件\n`);

    // 显示摘要
    const grouped = {};
    for (const item of obsoleteFiles) {
      if (!grouped[item.action]) {
        grouped[item.action] = [];
      }
      grouped[item.action].push(item);
    }

    for (const [action, items] of Object.entries(grouped)) {
      console.log(`   [${action.toUpperCase()}] ${items.length} 个文件`);
    }
    console.log('');

    const readline = require('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    const answer = await new Promise(resolve => {
      rl.question('是否自动处理？[Y/n]: ', answer => {
        rl.close();
        resolve(answer.trim().toLowerCase());
      });
    });

    if (answer !== 'n' && answer !== 'no') {
      // 使用新的检测器处理废弃文件
      await detector.process(obsoleteFiles, { autoConfirm: true });
    } else {
      console.log('   ℹ️  跳过废弃文件处理');
      console.log('   💡 可手动执行: detect-obsolete\n');
    }
  } else {
    console.log('   ℹ️  无废弃文件\n');
  }

  // 步骤4: 检测覆盖层冲突
  console.log('🔍 检查项目覆盖层...\n');
  const conflicts = await versionChecker.detectOverrideConflicts();

  if (conflicts.length > 0) {
    console.log(`⚠️  检测到 ${conflicts.length} 个文档上游有更新:\n`);
    conflicts.forEach(c => {
      console.log(`   - ${c.file}: ${c.description}`);
    });

    console.log('\n💡 建议操作:');
    console.log('   执行: merge-conflicts (交互式合并工具)');
    console.log('   或手动: diff .claude/core-docs/[文件] markdown/core/[文件]\n');
  } else {
    const overrideDir = path.join(targetPath, 'markdown', 'core');
    if (fs.existsSync(overrideDir) && fs.readdirSync(overrideDir).length > 0) {
      console.log('   ✅ 项目定制文档无冲突\n');
    } else {
      console.log('   ℹ️  无项目定制文档\n');
    }
  }

  // 步骤5: 更新manifest
  versionChecker.writeManifest({
    version: check.upstream,
    baselineHashes: versionChecker.computeBaselineHashes()
  });

  // 步骤6: 清理旧版本文件（v15.x的workflow-version.json）
  const versionPath = path.join(targetPath, '.claude', 'workflow-version.json');
  if (fs.existsSync(versionPath)) {
    fs.removeSync(versionPath);
    console.log('🗑️  已清理旧版本文件: workflow-version.json\n');
  }

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('✅ 同步完成！');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
}

// 运行
if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { main, syncWorkflow };
