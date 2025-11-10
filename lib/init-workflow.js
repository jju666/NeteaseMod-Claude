#!/usr/bin/env node
/**
 * 工作流初始化入口
 * 被 /initmc 命令调用
 */

const { ProjectAnalyzer } = require('./analyzer');
const { DocumentGenerator } = require('./generator');
const { IntelligentDocMaintenance } = require('./intelligent-doc-maintenance');
const fs = require('fs');
const path = require('path');

/**
 * 步骤2.5：智能文档重命名
 * 将所有混乱的文档名重命名为清晰的中文名称
 */
async function performIntelligentRenaming(targetPath) {
  console.log('\n📍 步骤2.5：智能文档重命名...\n');

  const maintenance = new IntelligentDocMaintenance(targetPath);
  const markdownDir = path.join(targetPath, 'markdown');

  // 扫描需要重命名的目录
  const dirsToScan = ['systems', 'states', 'presets', 'config'];
  const renamePlan = [];

  for (const dirName of dirsToScan) {
    const dirPath = path.join(markdownDir, dirName);

    if (!fs.existsSync(dirPath)) {
      continue;
    }

    const files = fs.readdirSync(dirPath)
      .filter(f => f.endsWith('.md') && f !== 'README.md');

    for (const fileName of files) {
      const oldPath = path.join(dirPath, fileName);
      const componentName = path.basename(fileName, '.md');

      // 推断中文名
      const mapping = { type: dirName.slice(0, -1), subtype: dirName.slice(0, -1) };  // systems -> system
      const chineseFileName = maintenance._inferChineseNameByAI(oldPath, componentName, mapping);
      const newPath = path.join(dirPath, chineseFileName);

      // 如果新文件名与旧文件名不同，添加到重命名计划
      if (chineseFileName !== fileName) {
        renamePlan.push({
          dir: dirName,
          oldName: fileName,
          newName: chineseFileName,
          oldPath: oldPath,
          newPath: newPath
        });
      }
    }
  }

  if (renamePlan.length === 0) {
    console.log('✅ 所有文档已使用规范的中文命名，无需重命名\n');
    return;
  }

  console.log(`📋 发现 ${renamePlan.length} 个文档需要重命名:\n`);

  // 按目录分组显示
  const groupedPlan = {};
  for (const item of renamePlan) {
    if (!groupedPlan[item.dir]) {
      groupedPlan[item.dir] = [];
    }
    groupedPlan[item.dir].push(item);
  }

  for (const [dirName, items] of Object.entries(groupedPlan)) {
    console.log(`【${dirName}】`);
    items.forEach((item, index) => {
      console.log(`  ${index + 1}. ${item.oldName}`);
      console.log(`     → ${item.newName}`);
    });
    console.log('');
  }

  // 执行重命名
  console.log('✨ 执行重命名...\n');

  let successCount = 0;
  let failCount = 0;

  for (const item of renamePlan) {
    try {
      // 检查目标文件是否已存在
      if (fs.existsSync(item.newPath)) {
        console.log(`  ⚠️  跳过: ${item.oldName} (目标文件已存在)`);
        failCount++;
        continue;
      }

      fs.renameSync(item.oldPath, item.newPath);
      console.log(`  ✅ ${item.oldName} → ${item.newName}`);
      successCount++;
    } catch (error) {
      console.log(`  ❌ 失败: ${item.oldName} (${error.message})`);
      failCount++;
    }
  }

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('📊 重命名完成');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  console.log(`✅ 成功: ${successCount} 个`);
  if (failCount > 0) {
    console.log(`❌ 失败/跳过: ${failCount} 个`);
  }
  console.log('');
}

/**
 * 主函数
 */
async function main() {
  // 从命令行参数获取目标路径，如果没有则使用当前目录
  const targetPath = process.argv[2] || process.cwd();

  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('📊 开始初始化MODSDK工作流');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  try {
    // 步骤1: 分析项目
    console.log('📍 步骤1：分析项目结构...\n');
    const analyzer = new ProjectAnalyzer(targetPath);
    const report = analyzer.analyze();

    // 输出分析报告
    console.log('\n' + report.toMarkdown());

    // 步骤2: 生成文档
    console.log('\n📍 步骤2：生成工作流文档...\n');
    const generator = new DocumentGenerator(report);
    await generator.generateAll(targetPath);

    // 步骤2.5: 智能文档重命名
    await performIntelligentRenaming(targetPath);

    // 步骤3: 输出完成报告
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 工作流部署完成！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    const systemsCount = Object.keys(report.codeStructure.systems).length;

    console.log('📊 生成统计:');
    console.log('- Layer 1（通用层）: 15个文件 ✅');
    console.log('  - CLAUDE.md');
    console.log('  - .claude/commands/cc.md ⭐');
    console.log('  - .claude/commands/enhance-docs.md');
    console.log('  - .claude/commands/validate-docs.md');
    console.log('  - markdown/开发规范.md');
    console.log('  - markdown/问题排查.md');
    console.log('  - markdown/ai/（3个AI文档）');
    console.log('  - 等...\n');

    console.log(`- Layer 2（架构层）: ${systemsCount}个文件 ✅`);
    console.log(`  - markdown/systems/ (${systemsCount}个系统文档)\n`);

    console.log('- Layer 3（业务层）: 框架已创建 ✅');
    console.log('  - markdown/文档待补充清单.md\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📝 后续步骤:');
    console.log('1. ✅ 查阅 CLAUDE.md 了解AI工作流程');
    console.log('2. ✅ 使用 /cc "任务描述" 快速创建/继续任务');
    console.log('3. ✅ 查阅 markdown/文档待补充清单.md 了解待补充内容');
    console.log('4. ✅ AI会在开发过程中自动完善文档\n');

    console.log('🎯 可用命令:');
    console.log('- /cc "任务描述" - 快速任务执行器 ⭐');
    console.log('- /enhance-docs - 批量补充文档');
    console.log('- /validate-docs - 验证文档完整性\n');

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🎉 工作流已就绪，开始高效开发吧！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  } catch (error) {
    console.error('\n❌ 错误:', error.message);
    console.error('\n请确保：');
    console.error('1. 当前目录是MODSDK项目（包含 modMain.py）');
    console.error('2. 已完成全局安装（运行过 npm run install-global）\n');
    process.exit(1);
  }
}

// 运行
if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { main };
