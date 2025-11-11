/**
 * v15.x → v16.0 迁移脚本
 * 自动检测旧版本项目并迁移到双层文档架构
 */

const fs = require('fs-extra');
const path = require('path');
const { VersionChecker } = require('./version-checker');
const { SymlinkManager } = require('./symlink-manager');

class MigrationV16 {
  constructor(upstreamPath, downstreamPath) {
    this.upstreamPath = upstreamPath;
    this.downstreamPath = downstreamPath;
    this.versionChecker = new VersionChecker(upstreamPath, downstreamPath);
    this.symlinkManager = new SymlinkManager(upstreamPath, downstreamPath);
  }

  /**
   * 检测是否需要迁移
   */
  needsMigration() {
    const localVersion = this.versionChecker.getLocalVersion();
    const upstreamVersion = this.versionChecker.getUpstreamVersion();

    // v15.x → v16.0
    return localVersion.startsWith('15.') && upstreamVersion.startsWith('16.');
  }

  /**
   * 执行迁移
   */
  async migrate(options = {}) {
    const autoConfirm = options.autoConfirm || false;

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🔄 v15.x → v16.0 自动迁移');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📋 迁移内容:');
    console.log('  1. 分析 markdown/ 目录中的核心文档');
    console.log('  2. 检测哪些文件被用户定制过');
    console.log('  3. 未定制文件 → 删除（改为引用上游）');
    console.log('  4. 已定制文件 → 迁移到 markdown/core/');
    console.log('  5. 创建 .claude/core-docs/ 软连接');
    console.log('  6. 生成 markdown/README.md 导航文档\n');

    // 步骤1: 分析文件
    const analysis = await this._analyzeFiles();

    // 步骤2: 显示分析结果
    this._printAnalysis(analysis);

    // 步骤3: 询问用户确认
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

    // 步骤4: 执行迁移
    console.log('\n🚀 开始执行迁移...\n');

    try {
      await this._executeMigration(analysis);

      console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('✅ 迁移完成！');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

      console.log('📚 新的文档结构:');
      console.log('  .claude/core-docs/    - 上游文档引用（只读）');
      console.log('  markdown/core/        - 项目定制文档');
      console.log('  markdown/systems/     - 项目System文档');
      console.log('  markdown/README.md    - 文档导航\n');

      console.log('💡 下一步:');
      console.log('  查看 markdown/README.md 了解新的文档组织\n');

      return { success: true, analysis };

    } catch (error) {
      console.error('\n❌ 迁移失败:', error.message);
      console.error('\n🔙 可以手动恢复: 检查 .backup-v15/ 目录\n');

      return { success: false, error: error.message };
    }
  }

  /**
   * 分析文件状态
   */
  async _analyzeFiles() {
    const markdownPath = path.join(this.downstreamPath, 'markdown');

    const coreFiles = [
      '开发规范.md',
      '问题排查.md',
      '快速开始.md',
      'MODSDK核心概念.md',
      'API速查.md',
      '官方文档查询指南.md',
      '迁移指南-v15.0.md'
    ];

    const coreDirectories = ['ai'];

    const pristineFiles = [];
    const customizedFiles = [];
    const missingFiles = [];

    // 计算上游基线哈希
    const baselineHashes = this.versionChecker.computeBaselineHashes();

    // 检查文件
    for (const file of coreFiles) {
      const filePath = path.join(markdownPath, file);

      if (!fs.existsSync(filePath)) {
        missingFiles.push(file);
        continue;
      }

      const baselineHash = baselineHashes[file];
      const isCustomized = this.versionChecker.isFileCustomized(filePath, baselineHash);

      if (isCustomized) {
        customizedFiles.push(file);
      } else {
        pristineFiles.push(file);
      }
    }

    // 检查目录（简化：假设ai/目录未被定制）
    for (const dir of coreDirectories) {
      const dirPath = path.join(markdownPath, dir);

      if (fs.existsSync(dirPath)) {
        pristineFiles.push(dir);
      } else {
        missingFiles.push(dir);
      }
    }

    return {
      pristineFiles,
      customizedFiles,
      missingFiles,
      baselineHashes
    };
  }

  /**
   * 打印分析结果
   */
  _printAnalysis(analysis) {
    console.log('📊 文件分析结果:\n');

    if (analysis.pristineFiles.length > 0) {
      console.log(`✅ 未定制文件/目录 (${analysis.pristineFiles.length}个):`);
      analysis.pristineFiles.forEach(f => console.log(`   - ${f}`));
      console.log('   → 将被删除，改为引用上游\n');
    }

    if (analysis.customizedFiles.length > 0) {
      console.log(`📝 已定制文件 (${analysis.customizedFiles.length}个):`);
      analysis.customizedFiles.forEach(f => console.log(`   - ${f}`));
      console.log('   → 将迁移到 markdown/core/\n');
    }

    if (analysis.missingFiles.length > 0) {
      console.log(`ℹ️  缺失文件 (${analysis.missingFiles.length}个):`);
      analysis.missingFiles.forEach(f => console.log(`   - ${f}`));
      console.log('   → 将通过上游引用提供\n');
    }
  }

  /**
   * 执行迁移
   */
  async _executeMigration(analysis) {
    const markdownPath = path.join(this.downstreamPath, 'markdown');

    // 步骤1: 备份
    console.log('📦 备份当前markdown/目录...');
    const backupPath = path.join(this.downstreamPath, '.backup-v15');
    fs.ensureDirSync(backupPath);
    fs.copySync(markdownPath, path.join(backupPath, 'markdown'));
    console.log('   ✅ 已备份到 .backup-v15/\n');

    // 步骤2: 创建markdown/core/目录
    const coreDir = path.join(markdownPath, 'core');
    fs.ensureDirSync(coreDir);

    // 步骤3: 迁移定制文件
    if (analysis.customizedFiles.length > 0) {
      console.log('📝 迁移定制文档...');

      for (const file of analysis.customizedFiles) {
        const src = path.join(markdownPath, file);
        const dest = path.join(coreDir, file);

        // 移动文件
        fs.moveSync(src, dest);

        // 添加项目定制标记
        this._addProjectCustomizationHeader(dest);

        console.log(`   ✅ 迁移: ${file} → markdown/core/`);
      }

      console.log('');
    }

    // 步骤4: 删除未定制文件
    if (analysis.pristineFiles.length > 0) {
      console.log('🧹 清理未定制文档...');

      for (const file of analysis.pristineFiles) {
        const filePath = path.join(markdownPath, file);

        // 删除
        fs.removeSync(filePath);

        console.log(`   ✅ 清理: ${file}`);
      }

      console.log('');
    }

    // 步骤5: 创建.claude/core-docs/软连接
    console.log('📂 创建上游文档引用...');
    await this.symlinkManager.createAllSymlinks();

    // 步骤6: 生成markdown/README.md
    console.log('📄 生成导航文档...');
    this._generateReadme();
    console.log('   ✅ 已生成 markdown/README.md\n');

    // 步骤7: 更新manifest
    console.log('📝 更新工作流元数据...');
    this.versionChecker.writeManifest({
      version: this.versionChecker.getUpstreamVersion(),
      baselineHashes: analysis.baselineHashes,
      migratedFrom: this.versionChecker.getLocalVersion(),
      migratedAt: new Date().toISOString()
    });
    console.log('   ✅ 已更新 .claude/workflow-manifest.json\n');

    // 步骤8: 更新CLAUDE.md到v16.0（新增）
    console.log('📝 更新CLAUDE.md到v16.0...');
    await this._updateClaudeMd();
    console.log('   ✅ 已更新 CLAUDE.md\n');

    // 步骤9: 更新.claude/commands/命令文件到v16.0（新增）
    console.log('📝 更新Claude命令文件到v16.0...');
    await this._updateCommands();
    console.log('   ✅ 已更新命令文件\n');
  }

  /**
   * 更新CLAUDE.md到v16.0
   */
  async _updateClaudeMd() {
    const { ProjectAnalyzer } = require('./analyzer');
    const { DocumentGenerator } = require('./generator');

    // 分析项目
    const analyzer = new ProjectAnalyzer(this.downstreamPath);
    const report = analyzer.analyze();

    // 生成CLAUDE.md
    const generator = new DocumentGenerator(report, this.upstreamPath);
    const replacements = generator._buildReplacements(this.downstreamPath);
    generator._generateFromTemplate('CLAUDE.md', this.downstreamPath, 'CLAUDE.md', replacements);
  }

  /**
   * 更新.claude/commands/命令文件到v16.0
   */
  async _updateCommands() {
    const { ProjectAnalyzer } = require('./analyzer');
    const { DocumentGenerator } = require('./generator');

    // 分析项目
    const analyzer = new ProjectAnalyzer(this.downstreamPath);
    const report = analyzer.analyze();

    // 生成命令文件
    const generator = new DocumentGenerator(report, this.upstreamPath);
    const replacements = generator._buildReplacements(this.downstreamPath);

    // 更新3个命令文件（cc.md, validate-docs.md, enhance-docs.md）
    const commands = ['cc.md', 'validate-docs.md', 'enhance-docs.md'];
    for (const cmd of commands) {
      generator._generateFromTemplate(
        cmd,
        this.downstreamPath,
        `.claude/commands/${cmd}`,
        replacements
      );
    }
  }

  /**
   * 添加项目定制标记
   */
  _addProjectCustomizationHeader(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');

      // 检查是否已有标记
      if (content.includes('📝 **项目定制文档**')) {
        return;
      }

      const upstreamVersion = this.versionChecker.getUpstreamVersion();

      const header = `> 📝 **项目定制文档**
>
> 本文档基于上游工作流 v${upstreamVersion}，已针对本项目定制。
>
> - 执行 \`initmc --sync\` 可查看上游更新
> - 上游文档位于: \`.claude/core-docs/${path.basename(filePath)}\`

---

`;

      fs.writeFileSync(filePath, header + content, 'utf-8');
    } catch (err) {
      console.warn(`     警告: 无法添加定制标记到 ${filePath}`);
    }
  }

  /**
   * 生成markdown/README.md
   */
  _generateReadme() {
    const readmePath = path.join(this.downstreamPath, 'markdown', 'README.md');

    const content = `# 项目文档导航

> 📚 本项目使用"基于Claude的MODSDK开发工作流 v16.0"

---

## 📂 文档组织结构

### 核心工作流文档（上游提供）

存储位置：\`.claude/core-docs/\`（隐藏目录）

这些文档由工作流上游维护，默认只读：
- [开发规范.md](.claude/core-docs/开发规范.md) - CRITICAL规范和最佳实践
- [问题排查.md](.claude/core-docs/问题排查.md) - 常见问题解决方案
- [快速开始.md](.claude/core-docs/快速开始.md) - 5分钟快速上手
- [MODSDK核心概念.md](.claude/core-docs/MODSDK核心概念.md) - System/Component/Event概念速查
- [API速查.md](.claude/core-docs/API速查.md) - 常用API代码片段
- [官方文档查询指南.md](.claude/core-docs/官方文档查询指南.md) - 官方文档使用指南
- [ai/](.claude/core-docs/ai/) - AI辅助工作流文档

**💡 如何定制核心文档？**

如果需要针对本项目定制（如添加非MODSDK规范）：
1. 将文档复制到 \`markdown/core/\`
2. 编辑 \`markdown/core/[文档名].md\`
3. AI会自动优先读取项目定制版本

---

### 项目特定文档（本地维护）

#### 系统文档
- [systems/](./systems/) - 本项目的System实现文档（AI自动生成）

#### 文档跟踪
- [文档待补充清单.md](./文档待补充清单.md) - 待完善的文档清单

#### 项目定制（可选）
- [core/](./core/) - 覆盖上游核心文档的项目定制版本

---

## 🔄 工作流更新

当工作流上游发布新版本时：

\`\`\`bash
# 检查更新
initmc --sync

# 自动同步上游文档
# 智能检测冲突
# 清理废弃文件
\`\`\`

---

## 📖 常用操作

### 查阅文档
Claude会自动按优先级查找：
1. \`markdown/core/\` (项目定制版)
2. \`.claude/core-docs/\` (上游基线)
3. \`markdown/systems/\` (项目System文档)

### 定制核心文档
\`\`\`bash
# 示例：定制开发规范
cp .claude/core-docs/开发规范.md markdown/core/开发规范.md

# 然后编辑
code markdown/core/开发规范.md
\`\`\`

### 查看上游更新
\`\`\`bash
# 对比上游与项目定制版
diff .claude/core-docs/开发规范.md markdown/core/开发规范.md
\`\`\`

---

_文档版本: v16.0 | 更新时间: ${new Date().toISOString().split('T')[0]}_
`;

    fs.writeFileSync(readmePath, content, 'utf-8');
  }
}

module.exports = { MigrationV16 };
