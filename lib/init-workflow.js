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

    // 步骤2: 生成文档（只部署Layer 1核心工作流）
    console.log('\n📍 步骤2：部署核心工作流文档...\n');
    const generator = new DocumentGenerator(report);
    await generator.generateAll(targetPath, { minimalMode: true });

    // 步骤3: 输出完成报告
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 核心工作流部署完成！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📊 部署内容:');
    console.log('- ✅ CLAUDE.md - AI工作流程总览');
    console.log('- ✅ .claude/commands/ - 3个核心命令');
    console.log('  - /cc - 任务执行器');
    console.log('  - /validate-docs - 文档审计与规范化');
    console.log('  - /enhance-docs - 文档批量生成');
    console.log('- ✅ markdown/ - 核心开发文档');
    console.log('  - 开发规范.md、问题排查.md、快速开始.md等');
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
    console.log('  3. /cc "任务描述" - 开发时自动维护文档\n');

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

// 运行
if (require.main === module) {
  main().catch(err => {
    console.error('Fatal error:', err);
    process.exit(1);
  });
}

module.exports = { main };
