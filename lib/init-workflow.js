#!/usr/bin/env node
/**
 * 工作流初始化入口
 * 被 /initmc 命令调用
 */

const { ProjectAnalyzer } = require('./analyzer');
const { DocumentGenerator } = require('./generator');

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

    // 步骤3: 输出完成报告
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 工作流部署完成！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    const systemsCount = Object.keys(report.codeStructure.systems).length;

    console.log('📊 生成统计:');
    console.log('- Layer 1（通用层）: 13个文件 ✅');
    console.log('  - CLAUDE.md');
    console.log('  - .claude/commands/cc.md ⭐');
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
