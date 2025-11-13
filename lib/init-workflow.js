#!/usr/bin/env node
/**
 * 工作流初始化入口
 * 被 /initmc 命令调用
 *
 * 支持的命令行参数:
 * - initmc              : 初始化/部署工作流到MODSDK项目
 * - initmc --sync       : 同步上游更新
 * - initmc --force      : 强制重新初始化（清除缓存）
 * - initmc --reset      : 同 --force（别名）
 * - initmc --clean      : 清理旧版本文件后全新部署
 * - initmc --auto-migrate[=N] : 自动迁移模式（可选：指定选项编号）
 *
 * v16.0: 新增双层文档架构与 --sync 参数
 * v18.4: 统一 --force/--reset 参数（功能相同）
 * v20.0.4: 新增 --clean 选项（清理旧文件后部署）
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
const { ObsoleteFileDetector } = require('./obsolete-file-detector');
const { WORKFLOW_HOME } = require('./config');

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
 * 主函数
 */
async function main() {
  // 解析命令行参数
  const args = process.argv.slice(2);
  const flags = args.filter(arg => arg.startsWith('--'));
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

  // 检查是否是同步模式
  const isSyncMode = flags.includes('--sync');
  // 支持 --reset 和 --force（别名，功能相同）
  const isResetMode = flags.includes('--reset') || flags.includes('--force');
  // ⭐ v20.0.4: 检查是否启用清理模式
  const isCleanMode = flags.includes('--clean');

  // ⭐ v18.0: 检查是否启用自动迁移
  const autoMigrateFlag = flags.find(f => f.startsWith('--auto-migrate'));
  let autoMigrateChoice = null;
  if (autoMigrateFlag) {
    const match = autoMigrateFlag.match(/--auto-migrate(?:=(\d))?/);
    autoMigrateChoice = match && match[1] ? parseInt(match[1]) : 1; // 默认选项1
  }

  // 检查环境变量（备用方案）
  if (!autoMigrateChoice && process.env.CLAUDE_AUTO_MIGRATE) {
    autoMigrateChoice = parseInt(process.env.CLAUDE_AUTO_MIGRATE) || 1;
  }

  try {
    // ⭐ v20.2.7: 版本检测与更新提示（除非是 --sync 模式）
    if (!isSyncMode) {
      const versionChecker = new VersionChecker(WORKFLOW_HOME, targetPath);
      const versionInfo = versionChecker.checkVersion();

      // 检查全局工作流版本
      const globalVersion = versionInfo.upstream;
      const projectVersion = versionInfo.local;

      // 如果项目已部署，检查是否需要更新
      if (projectVersion !== '0.0.0') {
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
        console.log('🔍 版本检测');
        console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
        console.log(`📦 全局工作流版本: v${globalVersion}`);
        console.log(`📂 项目工作流版本: v${projectVersion}\n`);

        if (versionInfo.needsUpdate) {
          console.log('⚠️  检测到新版本可用！\n');
          console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
          console.log(`🎉 v${globalVersion} 更新内容`);
          console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

          // 显示更新内容摘要（根据版本）
          if (globalVersion === '20.2.7') {
            console.log('🔴 **BUG修复工作流用户体验增强**\n');
            console.log('  • ✅ 三文件状态同步机制（workflow-state.json）');
            console.log('  • ✅ Stop Hook 防止重复询问（10分钟静默）');
            console.log('  • ✅ AI 主动引导用户测试验证');
            console.log('  • ✅ 收尾意愿智能检测与自动推进');
            console.log('  • ✅ 任务目录名长度提升到16字符\n');
            console.log('  📊 改进：AI引导 +100% | 重复询问 -66% | 状态一致性 +33%\n');
          } else {
            console.log('  详见: CHANGELOG.md\n');
          }

          console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
          console.log('💡 更新方法：');
          console.log('   1. 首先更新全局工作流：');
          console.log('      cd <工作流项目目录>');
          console.log('      npm run install-global');
          console.log('');
          console.log('   2. 然后在本项目中执行：');
          console.log('      initmc --sync');
          console.log('');
          console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

          // 继续正常部署流程（用户可能只是想重新部署）
          console.log('⏳ 继续当前部署流程...\n');
        } else if (projectVersion === globalVersion) {
          console.log('✅ 项目工作流已是最新版本\n');
        }
      }
    }

    // 模式1: 同步更新（--sync）
    if (isSyncMode) {
      return await syncWorkflow(targetPath, { reset: isResetMode });
    }

    // 模式2: 首次部署或重新部署
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 开始初始化MODSDK工作流');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // ⭐ v18.0: 检查是否需要迁移（优先级最高）
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

    // ⭐ v20.0.4: 清理模式（在部署前清理旧文件）
    if (isCleanMode) {
      console.log('🧹 清理模式：删除旧版本文件...\n');
      await cleanupBeforeDeploy(targetPath, WORKFLOW_HOME);
      console.log('');
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
 * 同步工作流更新
 * @param {string} targetPath - 下游项目路径
 * @param {Object} options - 选项
 * @param {boolean} options.reset - 强制重置工作流（--reset/--force）
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

/**
 * ⭐ v20.0.4: 清理旧版本文件（在部署前执行）
 * @param {string} targetPath - 下游项目路径
 * @param {string} upstreamPath - 上游工作流路径
 */
async function cleanupBeforeDeploy(targetPath, upstreamPath) {
  const hooksDir = path.join(targetPath, '.claude', 'hooks');
  const commandsDir = path.join(targetPath, '.claude', 'commands');
  // ⭐ v20.0.4修复: 使用path.resolve()避免Windows中文路径Bug
  const templatesHooksDir = path.resolve(upstreamPath, 'templates/.claude/hooks');
  const templatesCommandsDir = path.resolve(upstreamPath, 'templates/.claude/commands');

  let cleanedCount = 0;

  // 1. 清理 hooks 目录中的上游文件
  if (fs.existsSync(templatesHooksDir)) {
    const upstreamHooks = fs.readdirSync(templatesHooksDir)
      .filter(f => f.endsWith('.py') || f.endsWith('.sh') || f === 'README.md');

    console.log(`🔍 扫描到 ${upstreamHooks.length} 个上游 hooks 文件\n`);

    for (const file of upstreamHooks) {
      const targetFile = path.join(hooksDir, file);
      if (fs.existsSync(targetFile)) {
        fs.removeSync(targetFile);
        console.log(`   🗑️  已删除: .claude/hooks/${file}`);
        cleanedCount++;
      }
    }
  }

  // 2. 清理 commands 目录中的核心命令
  const coreCommands = ['mc.md', 'mc-review.md', 'mc-perf.md', 'mc-docs.md', 'mc-why.md', 'mc-discover.md'];
  console.log(`\n🔍 扫描核心命令文件\n`);

  for (const cmdFile of coreCommands) {
    const targetFile = path.join(commandsDir, cmdFile);
    if (fs.existsSync(targetFile)) {
      fs.removeSync(targetFile);
      console.log(`   🗑️  已删除: .claude/commands/${cmdFile}`);
      cleanedCount++;
    }
  }

  // 3. 清理 CLAUDE.md 和 settings.json
  const otherFiles = ['CLAUDE.md', '.claude/settings.json'];
  console.log(`\n🔍 扫描核心配置文件\n`);

  for (const file of otherFiles) {
    const targetFile = path.join(targetPath, file);
    if (fs.existsSync(targetFile)) {
      fs.removeSync(targetFile);
      console.log(`   🗑️  已删除: ${file}`);
      cleanedCount++;
    }
  }

  if (cleanedCount > 0) {
    console.log(`\n✅ 共清理 ${cleanedCount} 个旧文件`);
  } else {
    console.log(`\n✅ 无旧文件需要清理`);
  }
}

// 运行
if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { main, syncWorkflow, cleanupBeforeDeploy, isDevEnvironment };
