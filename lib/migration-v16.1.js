/**
 * v16.0 → v16.1 迁移脚本
 * 新增CLAUDE.md项目扩展区支持
 */

const fs = require('fs-extra');
const path = require('path');
const { VersionChecker } = require('./version-checker');

class MigrationV161 {
  constructor(upstreamPath, downstreamPath) {
    this.upstreamPath = upstreamPath;
    this.downstreamPath = downstreamPath;
    this.versionChecker = new VersionChecker(upstreamPath, downstreamPath);
  }

  /**
   * 检测是否需要迁移
   */
  needsMigration() {
    const localVersion = this.versionChecker.getLocalVersion();
    const upstreamVersion = this.versionChecker.getUpstreamVersion();

    // v16.0 → v16.1
    return localVersion.startsWith('16.0') && upstreamVersion.startsWith('16.1');
  }

  /**
   * 执行迁移
   */
  async migrate(options = {}) {
    const autoConfirm = options.autoConfirm || false;

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🔄 v16.0 → v16.1 自动迁移');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📋 迁移内容:');
    console.log('  1. 升级 CLAUDE.md 到四段式结构');
    console.log('  2. 提取并保留用户编辑内容');
    console.log('  3. 新增"项目扩展区"支持');
    console.log('  4. 更新工作流元数据\n');

    // 询问用户确认
    if (!autoConfirm) {
      const readline = require('readline');
      const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
      });

      const answer = await new Promise(resolve => {
        rl.question('是否开始迁移？[Y/n]: ', answer => {
          rl.close();
          resolve(answer.trim().toLowerCase());
        });
      });

      if (answer === 'n' || answer === 'no') {
        console.log('\n⏸️  迁移已取消\n');
        return { success: false, cancelled: true };
      }
    }

    // 执行迁移
    console.log('\n🚀 开始执行迁移...\n');

    try {
      await this._executeMigration();

      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('✅ 迁移完成！');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

      console.log('📚 新增功能:');
      console.log('  CLAUDE.md 项目扩展区    - 添加项目特定规范');
      console.log('  三层文档优先级          - 扩展区 → 覆盖层 → 基线\n');

      console.log('💡 下一步:');
      console.log('  打开 CLAUDE.md，在"项目扩展区"添加项目规范\n');

      return { success: true };

    } catch (error) {
      console.error('\n❌ 迁移失败:', error.message);
      console.error('\n🔙 可以手动恢复: 检查备份文件\n');

      return { success: false, error: error.message };
    }
  }

  /**
   * 执行迁移逻辑
   */
  async _executeMigration() {
    // 步骤1: 更新CLAUDE.md到v16.1
    console.log('📝 升级CLAUDE.md到v16.1...');
    await this._updateClaudeMd();
    console.log('   ✅ CLAUDE.md已升级\n');

    // 步骤2: 更新manifest
    console.log('📝 更新工作流元数据...');
    const baselineHashes = this.versionChecker.computeBaselineHashes();
    this.versionChecker.writeManifest({
      version: '16.1.0',
      baselineHashes: baselineHashes,
      migratedFrom: '16.0.0',
      migratedAt: new Date().toISOString()
    });
    console.log('   ✅ 已更新 .claude/workflow-manifest.json\n');
  }

  /**
   * 更新CLAUDE.md到v16.1
   */
  async _updateClaudeMd() {
    const claudePath = path.join(this.downstreamPath, 'CLAUDE.md');

    if (!fs.existsSync(claudePath)) {
      // 如果不存在，从模板生成（罕见情况）
      await this._generateClaudeMdFromTemplate();
      return;
    }

    // 读取现有CLAUDE.md
    const content = fs.readFileSync(claudePath, 'utf-8');

    // 创建备份
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
    const backupPath = `${claudePath}.backup.${timestamp}`;
    fs.copyFileSync(claudePath, backupPath);
    console.log(`   📦 已备份到: ${path.basename(backupPath)}`);

    // 提取用户编辑的区域（v16.0可能没有这些区域，容错处理）
    const projectConfig = this._extractSection(content, '项目配置区') || this._extractDefaultProjectConfig();
    const projectExtension = this._extractSection(content, '项目扩展区') || '';  // v16.0没有扩展区

    // 生成新版工作流内容
    const newWorkflowContent = this._generateWorkflowContent();

    // 组装新版CLAUDE.md
    const newContent = this._assembleCLAUDEmd({
      projectConfig,
      workflowContent: newWorkflowContent,
      projectExtension,
      metadata: {
        version: '16.1.0',
        updatedAt: new Date().toISOString().split('T')[0]
      }
    });

    // 写入新版
    fs.writeFileSync(claudePath, newContent, 'utf-8');
  }

  /**
   * 提取HTML注释标记的区域
   */
  _extractSection(content, sectionName) {
    const startMarker = `<!-- ==================== ${sectionName} START ==================== -->`;
    const endMarker = `<!-- ==================== ${sectionName} END ==================== -->`;

    const startIdx = content.indexOf(startMarker);
    const endIdx = content.indexOf(endMarker);

    if (startIdx === -1 || endIdx === -1) {
      return null;
    }

    // 提取标记之间的内容
    const sectionContent = content.substring(startIdx + startMarker.length, endIdx).trim();

    return sectionContent;
  }

  /**
   * 提取默认项目配置（如果找不到配置区）
   */
  _extractDefaultProjectConfig() {
    // 尝试从v16.0格式中提取项目信息
    const claudePath = path.join(this.downstreamPath, 'CLAUDE.md');
    const content = fs.existsSync(claudePath) ? fs.readFileSync(claudePath, 'utf-8') : '';

    // 默认项目配置
    return `## 📌 项目信息

**项目名称**: ${path.basename(this.downstreamPath)}
**项目路径**: \`${this.downstreamPath}\`
**创建日期**: ${new Date().toISOString().split('T')[0]}
**项目状态**: 生产就绪 (Production Ready)`;
  }

  /**
   * 生成工作流内容区
   */
  _generateWorkflowContent() {
    const { ProjectAnalyzer } = require('./analyzer');
    const { DocumentGenerator } = require('./generator');

    // 分析项目
    const analyzer = new ProjectAnalyzer(this.downstreamPath);
    const report = analyzer.analyze();

    // 生成工作流内容
    const generator = new DocumentGenerator(report, this.upstreamPath);
    const replacements = generator._buildReplacements(this.downstreamPath);

    // 读取模板
    // ⭐ v20.0.4修复: 使用path.resolve()避免Windows中文路径Bug
    const templatePath = path.resolve(this.upstreamPath, 'templates/CLAUDE.md.template');
    let template = fs.readFileSync(templatePath, 'utf-8');

    // 应用替换
    for (const [key, value] of Object.entries(replacements)) {
      const placeholder = `{{${key}}}`;
      template = template.replace(new RegExp(placeholder.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g'), value);
    }

    // 提取工作流内容区（从模板中）
    const workflowContent = this._extractSection(template, '工作流内容');

    return workflowContent || '';
  }

  /**
   * 组装新版CLAUDE.md
   */
  _assembleCLAUDEmd({ projectConfig, workflowContent, projectExtension, metadata }) {
    const parts = [];

    // 头部
    parts.push(`# CLAUDE.md

> 🤖 **Claude Code AI Assistant 项目参考文档 v16.1**
>
> This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
>
> **当前版本**: v16.1 (双层文档架构 + 项目扩展区)
> **最后更新**: ${metadata.updatedAt}

---
`);

    // 项目配置区
    parts.push(`<!-- ==================== 项目配置区 START ==================== -->
<!-- 用户可编辑：基础项目信息 -->

${projectConfig}

<!-- ==================== 项目配置区 END ==================== -->
`);

    // 工作流内容区
    parts.push(`<!-- ==================== 工作流内容 START v16.1 ==================== -->
<!-- ⚠️ 警告：以下内容由工作流自动管理，升级时会精确替换此区域 -->
<!-- ⚠️ 请勿手动编辑，所有修改将在升级时丢失 -->
<!-- ⚠️ 如需添加项目特定规范，请使用下方的"项目扩展区" -->

${workflowContent}

<!-- ==================== 工作流内容 END v16.1 ==================== -->
`);

    // 项目扩展区
    const defaultExtension = `## 🎯 项目特定规范

> 💡 **使用说明**：
>
> 在此添加**非MODSDK相关**的项目特定规范，例如：
> - ✅ **适合添加**：团队协作流程、自定义架构模式、项目依赖声明、命名约定
> - ❌ **不适合添加**：MODSDK API/事件规范（应放在 \`markdown/core/开发规范.md\`）
>
> **示例**：
> \`\`\`markdown
> ### 项目依赖
> - 依赖项目：XXX
> - 项目路径：D:\\path\\to\\dependency
>
> ### 自定义架构
> - 使用State模式管理游戏状态
> - 所有数据库操作统一使用DBManager
>
> ### 团队约定
> - 提交代码前必须运行单元测试
> - 函数命名使用驼峰命名法
> \`\`\`

<!-- 在此下方添加项目特定规范 -->
${projectExtension}`;

    parts.push(`<!-- ==================== 项目扩展区 START ==================== -->
<!-- 用户可编辑：添加项目特定规范 -->
<!-- ⚠️ 本区域内容会在升级时自动保留 -->

${defaultExtension}

<!-- ==================== 项目扩展区 END ==================== -->
`);

    // 元数据区
    parts.push(`<!-- ==================== 文档元数据区 START ==================== -->
<!-- 自动生成，升级时更新 -->

**文档元数据**：
- 工作流版本：v${metadata.version}
- 上游仓库：基于Claude的MODSDK开发工作流
- 生成时间：${metadata.updatedAt}

<!-- ==================== 文档元数据区 END ==================== -->
`);

    return parts.join('\n');
  }

  /**
   * 从模板生成CLAUDE.md（首次安装）
   */
  async _generateClaudeMdFromTemplate() {
    const { ProjectAnalyzer } = require('./analyzer');
    const { DocumentGenerator } = require('./generator');

    const analyzer = new ProjectAnalyzer(this.downstreamPath);
    const report = analyzer.analyze();

    const generator = new DocumentGenerator(report, this.upstreamPath);
    const replacements = generator._buildReplacements(this.downstreamPath);
    generator._generateFromTemplate('CLAUDE.md', this.downstreamPath, 'CLAUDE.md', replacements);
  }
}

module.exports = { MigrationV161 };
