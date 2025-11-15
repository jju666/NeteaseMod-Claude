#!/usr/bin/env node
/**
 * 工作流初始化入口
 * 被 /initmc 命令调用
 *
 * v20.2.12: 🎯 智能单命令模式
 * - initmc: 自动完成所有操作（检测+清理+迁移+部署+同步）
 *
 * 自动行为:
 * ✅ 清理遗留的全局命令文件 (.cmd)
 * ✅ 自动检测版本更新
 * ✅ 自动清理废弃文件
 * ✅ 自动执行迁移脚本
 * ✅ 自动同步最新工作流
 *
 * v16.0: 新增双层文档架构
 * v18.0: 新增 Hook 系统（任务隔离）
 * v20.2.11: 修复版本号缓存问题
 * v20.2.12: 简化为智能单命令
 */

const path = require('path');
const fs = require('fs-extra');
const { ProjectAnalyzer } = require('./analyzer');
const { DocumentGenerator } = require('./generator');
const { VersionChecker } = require('./version-checker');
const { SymlinkManager } = require('./symlink-manager');
const { MigrationV16 } = require('./migration-v16');
const { MigrationV161 } = require('./migration-v16.1');
const { MigrationV18 } = require('./migration-v18');
const { MigrationV21 } = require('./migration-v21');
const { ObsoleteFileDetector } = require('./obsolete-file-detector');
const { WORKFLOW_HOME } = require('./config');
const { cleanupLegacyGlobalCommands, cleanupAllCaches } = require('./cleanup-utils');

/**
 * 检测是否在开发环境中运行
 * @param {string} targetPath - 目标路径
 * @param {string} workflowHome - 工作流主目录
 * @returns {boolean} - 如果是开发环境返回true
 */
function isDevEnvironment(targetPath, workflowHome) {
  const normalizedTarget = path.resolve(targetPath);
  const normalizedWorkflowHome = path.resolve(workflowHome);

  // 检查1: 目标路径是否包含本项目特征文件
  const devMarkers = [
    'lib/init-workflow.js',
    'lib/analyzer.js',
    'lib/generator.js',
    'templates/.claude/settings.json.template'
  ];

  const hasDevMarkers = devMarkers.every(marker =>
    fs.existsSync(path.join(normalizedTarget, marker))
  );

  // 检查2: 目标路径是否与工作流主目录相同或包含关系
  const isSamePath = normalizedTarget === normalizedWorkflowHome;
  const isParentPath = normalizedWorkflowHome.startsWith(normalizedTarget);

  return hasDevMarkers || isSamePath || isParentPath;
}

/**
 * 主函数（v20.2.12: 智能单命令模式）
 */
async function main() {
  // 解析命令行参数
  const args = process.argv.slice(2);
  const targetPath = args.find(arg => !arg.startsWith('--')) || process.cwd();

  // ⭐ 开发环境拦截：防止在本项目内错误部署
  if (isDevEnvironment(targetPath, WORKFLOW_HOME)) {
    console.error('\n❌ 错误：检测到在开发环境中运行 initmc');
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    console.error('当前目录是 NeteaseMod-Claude 开发环境，不能在此执行 initmc。\n');
    console.error('📍 正确用法：');
    console.error('   1. 切换到你的 MODSDK 项目目录');
    console.error('   2. 在项目根目录执行: initmc\n');
    console.error('💡 示例：');
    console.error('   cd D:\\MyProject\\my-modsdk-game');
    console.error('   initmc\n');
    console.error('⚠️  如果你想测试工作流部署，请：');
    console.error('   1. 创建一个测试用的 MODSDK 项目目录');
    console.error('   2. 在测试项目中执行 initmc\n');
    console.error('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    process.exit(1);
  }

  // ⭐ v20.2.12: 🗑️ 步骤0: 自动清理遗留的全局命令文件
  cleanupLegacyGlobalCommands();

  // ⭐ v20.2.12: 自动启用迁移（无需用户确认）
  const autoMigrateChoice = 1; // 默认选项1

  try {
    // ⭐ v20.2.12: 🔍 步骤1: 版本检测与智能判断
    const versionChecker = new VersionChecker(WORKFLOW_HOME, targetPath);
    const versionInfo = versionChecker.checkVersion();

    const globalVersion = versionInfo.upstream;
    const projectVersion = versionInfo.local;
    const isFirstDeploy = projectVersion === '0.0.0';

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🚀 MODSDK 智能工作流部署');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log(`📦 全局工作流版本: v${globalVersion}`);
    console.log(`📂 项目工作流版本: v${projectVersion}\n`);

    // 判断执行模式
    if (isFirstDeploy) {
      console.log('🆕 检测到首次部署\n');
    } else if (versionInfo.needsUpdate) {
      console.log('⬆️  检测到新版本可用，将自动同步更新\n');
      // 自动执行同步流程
      return await smartSyncWorkflow(targetPath, versionChecker, versionInfo);
    } else {
      console.log('🔄 重新部署当前版本\n');
    }

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // ⭐ v21.0: 检查是否需要迁移（优先级最高）
    const migrationV21 = new MigrationV21(WORKFLOW_HOME, targetPath);
    if (migrationV21.needsMigration()) {
      const migrateOptions = {
        autoConfirm: true  // v21.0自动迁移，无需用户确认
      };

      const result = await migrationV21.migrate(migrateOptions);
      if (result.success) {
        console.log('🔄 正在继续部署工作流...\n');
        // 迁移完成后，继续常规部署
      } else {
        console.warn('⚠️  v21.0迁移遇到错误，但将继续部署\n');
        // 即使迁移失败，也继续部署（让Hook系统自动适配）
      }
    }

    // ⭐ v18.0: 检查是否需要迁移
    const migrationV18 = new MigrationV18(WORKFLOW_HOME, targetPath);
    if (migrationV18.needsMigration()) {
      const migrateOptions = {
        autoConfirm: autoMigrateChoice !== null,
        autoMigrateChoice: autoMigrateChoice
      };

      const result = await migrationV18.migrate(migrateOptions);
      if (result.success) {
        console.log('🔄 正在继续部署工作流...\n');
        // 迁移完成后，继续常规部署
      } else {
        return; // 用户取消，退出
      }
    }

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

    // ⭐ v20.2.12: 🗑️ 自动清理废弃文件（如果检测到版本变更）
    if (!isFirstDeploy) {
      const detector = new ObsoleteFileDetector(targetPath);
      const obsoleteFiles = detector.detect(projectVersion, globalVersion);

      if (obsoleteFiles.length > 0) {
        console.log(`🧹 检测到 ${obsoleteFiles.length} 个废弃文件，正在清理...\n`);
        await detector.process(obsoleteFiles, {
          autoConfirm: true,  // 自动确认，无需用户交互
          dryRun: false
        });
        console.log('');
      }
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

    // 步骤5: v20.2.14 清理残留的工作流状态（防止旧数据污染新任务）
    const workflowStatePath = path.join(targetPath, '.claude', 'workflow-state.json');
    if (fs.existsSync(workflowStatePath)) {
      try {
        fs.removeSync(workflowStatePath);
        console.log('🗑️  已清理旧的工作流状态文件');
      } catch (err) {
        console.warn('⚠️  清理 workflow-state.json 失败:', err.message);
      }
    }

    // 步骤6: 输出完成报告
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 核心工作流部署完成！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📊 部署内容:');
    console.log('- ✅ CLAUDE.md - AI工作流程总览（v18.2：智能文档路由）');
    console.log('- ✅ .claude/commands/ - 6个核心命令');
    console.log('  - /mc - 主命令（任务隔离 + 知识验证机制）');
    console.log('  - /mc-review - 方案审查与优化建议');
    console.log('  - /mc-perf - 性能分析与优化');
    console.log('  - /mc-docs - 文档审计与维护');
    console.log('  - /mc-why - 代码意图追溯');
    console.log('  - /mc-discover - 项目结构发现');
    console.log('- ✅ .claude/core-docs/ - 核心开发文档（软连接）');
    console.log('  - 核心工作流文档/：开发规范、问题排查、快速开始');
    console.log('  - 概念参考/：MODSDK核心概念、API速查');
    console.log('  - 深度指南/：性能优化、事件系统、ECS架构');
    console.log('  - ai/：AI策略配置、知识标记文档\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('🎯 下一步（推荐）:\n');
    console.log('在 Claude Code 中执行以下命令发现项目结构：\n');
    console.log('  /mc-discover\n');
    console.log('该命令将：');
    console.log('  1. AI 自动发现项目中的所有组件（Systems/States/Presets等）');
    console.log('  2. 智能推断规范化的文档结构');
    console.log('  3. 生成项目分析报告\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📚 v18.2 核心工作流:');
    console.log('  1. /mc "任务描述" - 任务执行与方案审核');
    console.log('  2. /mc-discover - 项目结构发现（智能推断文档结构）');
    console.log('  3. /mc-docs - 文档审计与批量维护');
    console.log('  4. /mc-perf - 性能分析与优化建议\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🎉 开始体验智能文档路由与任务隔离机制的开发工作流吧！');
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
 * v20.2.12: 智能同步工作流更新
 * 自动执行所有更新步骤,无需用户交互
 *
 * @param {string} targetPath - 下游项目路径
 * @param {VersionChecker} versionChecker - 版本检测器实例
 * @param {Object} versionInfo - 版本信息
 */
async function smartSyncWorkflow(targetPath, versionChecker, versionInfo) {
  const fs = require('fs-extra');

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('⬆️  自动同步工作流更新');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  console.log(`📊 版本对比:`);
  console.log(`   本地: v${versionInfo.local}`);
  console.log(`   上游: v${versionInfo.upstream}\n`);

  if (versionInfo.changelog) {
    console.log('📝 更新内容:\n');
    console.log(versionInfo.changelog);
    console.log('');
  }

  // 步骤2: 更新软连接
  const symlinkManager = new SymlinkManager(WORKFLOW_HOME, targetPath);
  await symlinkManager.updateSymlinks();

  // 步骤2.5: 更新 Hook 文件（v18.4.0新增）
  console.log('🔄 更新 Hook 文件...\n');
  // 创建最小化的analysisReport以正确初始化DocumentGenerator
  const minimalReport = {
    metadata: { projectName: path.basename(targetPath) },
    codeStructure: {}
  };
  const generator = new DocumentGenerator(minimalReport, WORKFLOW_HOME);
  generator._deployHooks(targetPath, {});
  console.log('   ✅ Hook 文件已更新\n');

  // 步骤2.6: 更新命令文件（v20.0新增）
  console.log('🔄 更新命令文件...\n');
  const replacements = generator._buildReplacements(targetPath);
  const commandFiles = ['mc.md', 'mc-review.md', 'mc-perf.md', 'mc-docs.md', 'mc-why.md', 'mc-discover.md'];
  for (const cmdFile of commandFiles) {
    generator._generateFromTemplate(cmdFile, targetPath, `.claude/commands/${cmdFile}`, replacements);
    console.log(`   ✅ 已更新: ${cmdFile}`);
  }
  console.log('');

  // 步骤3: 自动检测并清理废弃文件（v20.2.12: 无需确认）
  console.log('🧹 检测废弃文件...\n');
  const detector = new ObsoleteFileDetector(targetPath);
  const obsoleteFiles = detector.detect(versionInfo.local, versionInfo.upstream);

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

    // v20.2.12: 自动处理,无需用户确认
    await detector.process(obsoleteFiles, { autoConfirm: true, dryRun: false });
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

  // 步骤4.5: v20.2.14 清理残留的工作流状态（防止旧数据污染新任务）
  const workflowStatePath = path.join(targetPath, '.claude', 'workflow-state.json');
  if (fs.existsSync(workflowStatePath)) {
    try {
      fs.removeSync(workflowStatePath);
      console.log('🗑️  已清理旧的工作流状态文件\n');
    } catch (err) {
      console.warn('⚠️  清理 workflow-state.json 失败:', err.message, '\n');
    }
  }

  // 步骤5: 更新manifest (v20.2.11: 重新读取版本避免缓存问题)
  versionChecker.writeManifest({
    version: versionChecker.getUpstreamVersion(),
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

// v20.2.12: cleanupBeforeDeploy 已废弃,由 ObsoleteFileDetector 替代

// 运行
if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = {
  main,
  smartSyncWorkflow,  // v20.2.12: 替代旧的 syncWorkflow
  isDevEnvironment
};
