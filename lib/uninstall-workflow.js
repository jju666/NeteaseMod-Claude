#!/usr/bin/env node
/**
 * 工作流卸载工具
 * 从下游项目中移除由 initmc 部署的所有工作流文件
 *
 * v16.0
 */

const fs = require('fs');
const path = require('path');

/**
 * 工作流卸载器
 */
class WorkflowUninstaller {
  constructor(projectPath) {
    this.projectPath = projectPath;
    this.versionFilePath = path.join(projectPath, '.claude', 'workflow-version.json');
    this.timestamp = new Date().toISOString().split('T')[0];
    this.backupPath = path.join(projectPath, `.backup-uninstall-${this.timestamp}`);

    // 定义工作流文件清单（需要删除的文件）
    this.workflowFiles = [
      // 命令文件
      '.claude/commands/cc.md',
      '.claude/commands/discover.md',
      '.claude/commands/validate-docs.md',
      '.claude/commands/enhance-docs.md',
      '.claude/commands/review-design.md',

      // 核心文档（v16.0: 软连接或副本）
      '.claude/core-docs',

      // 版本追踪
      '.claude/workflow-version.json',

      // 通用文档（markdown/）
      'markdown/开发规范.md',
      'markdown/问题排查.md',
      'markdown/快速开始.md',
      'markdown/开发指南.md',
      'markdown/API速查.md',
      'markdown/MODSDK核心概念.md',
      'markdown/可选工具说明.md',
      'markdown/迁移指南-v15.0.md',
      'markdown/迁移指南-v16.0.md',

      // AI辅助文档
      'markdown/ai/任务类型决策表.md',
      'markdown/ai/快速通道流程.md',
      'markdown/ai/上下文管理规范.md',
      'markdown/ai/任务模式策略表.md',
      'markdown/ai/方案自检清单.md',

      // 工具库
      'lib/adaptive-doc-discovery.js',
      'lib/utils.js',
      'lib/config.js',
      'lib/metadata-schema.js',
      'lib/indexer.js',
      'lib/search-engine.js',
      'lib/project-discovery.js',
      'lib/doc-mapping-inference.js',
      'lib/analyzer.js',
      'lib/intelligent-doc-maintenance.js',
      'lib/symlink-manager.js',
      'lib/merge-override-conflicts.js',
      'lib/obsolete-file-detector.js',
      'lib/init-workflow.js',
      'lib/migration-v16.js',
      'lib/generator.js',
      'lib/version-checker.js',
      'lib/uninstall-workflow.js'  // 自己也删除
    ];

    // 需要保留的用户文件（不会删除）
    this.userFiles = [
      'tasks/',
      'markdown/systems/',
      'markdown/states/',
      'markdown/presets/',
      'markdown/managers/',
      'markdown/README.md',  // v16.0: 用户可能已定制
      '.claude/discovered-patterns.json'
    ];

    // 需要询问用户的文件
    this.optionalFiles = [
      'CLAUDE.md'
    ];
  }

  /**
   * 检查是否已部署工作流
   */
  isWorkflowInstalled() {
    return fs.existsSync(this.versionFilePath);
  }

  /**
   * 获取已安装的工作流版本
   */
  getInstalledVersion() {
    if (!this.isWorkflowInstalled()) {
      return null;
    }

    try {
      const versionData = JSON.parse(fs.readFileSync(this.versionFilePath, 'utf-8'));
      return versionData.version;
    } catch (err) {
      return 'unknown';
    }
  }

  /**
   * 扫描实际存在的工作流文件
   */
  scanWorkflowFiles() {
    const existingFiles = [];

    for (const file of this.workflowFiles) {
      const fullPath = path.join(this.projectPath, file);
      if (fs.existsSync(fullPath)) {
        const stat = fs.statSync(fullPath);
        existingFiles.push({
          relativePath: file,
          fullPath: fullPath,
          isDirectory: stat.isDirectory(),
          size: stat.isDirectory() ? this.getDirectorySize(fullPath) : stat.size
        });
      }
    }

    return existingFiles;
  }

  /**
   * 递归计算目录大小
   */
  getDirectorySize(dirPath) {
    let totalSize = 0;

    try {
      const entries = fs.readdirSync(dirPath, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(dirPath, entry.name);

        if (entry.isDirectory()) {
          totalSize += this.getDirectorySize(fullPath);
        } else {
          const stat = fs.statSync(fullPath);
          totalSize += stat.size;
        }
      }
    } catch (err) {
      // 忽略无权限目录
    }

    return totalSize;
  }

  /**
   * 创建备份
   */
  createBackup(filesToBackup) {
    if (!fs.existsSync(this.backupPath)) {
      fs.mkdirSync(this.backupPath, { recursive: true });
    }

    for (const file of filesToBackup) {
      const srcPath = file.fullPath;
      const destPath = path.join(this.backupPath, file.relativePath);

      try {
        // 确保目标目录存在
        const destDir = path.dirname(destPath);
        if (!fs.existsSync(destDir)) {
          fs.mkdirSync(destDir, { recursive: true });
        }

        if (file.isDirectory) {
          // 递归复制目录
          this.copyDirectoryRecursive(srcPath, destPath);
        } else {
          // 复制文件
          fs.copyFileSync(srcPath, destPath);
        }
      } catch (err) {
        console.error(`  ⚠️  备份失败: ${file.relativePath} - ${err.message}`);
      }
    }
  }

  /**
   * 递归复制目录
   */
  copyDirectoryRecursive(src, dest) {
    if (!fs.existsSync(dest)) {
      fs.mkdirSync(dest, { recursive: true });
    }

    const entries = fs.readdirSync(src, { withFileTypes: true });

    for (const entry of entries) {
      const srcPath = path.join(src, entry.name);
      const destPath = path.join(dest, entry.name);

      if (entry.isDirectory()) {
        this.copyDirectoryRecursive(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }

  /**
   * 删除文件
   */
  removeFiles(filesToRemove) {
    const removedFiles = [];
    const failedFiles = [];

    for (const file of filesToRemove) {
      try {
        if (file.isDirectory) {
          fs.rmSync(file.fullPath, { recursive: true, force: true });
        } else {
          fs.unlinkSync(file.fullPath);
        }
        removedFiles.push(file);
      } catch (err) {
        failedFiles.push({ file, error: err.message });
      }
    }

    return { removedFiles, failedFiles };
  }

  /**
   * 清理空目录
   */
  cleanEmptyDirectories() {
    const dirsToCheck = [
      path.join(this.projectPath, '.claude', 'commands'),
      path.join(this.projectPath, '.claude'),
      path.join(this.projectPath, 'markdown', 'ai'),
      path.join(this.projectPath, 'markdown'),
      path.join(this.projectPath, 'lib')
    ];

    for (const dir of dirsToCheck) {
      try {
        if (fs.existsSync(dir) && fs.readdirSync(dir).length === 0) {
          fs.rmdirSync(dir);
          console.log(`  🗑️  已删除空目录: ${path.relative(this.projectPath, dir)}`);
        }
      } catch (err) {
        // 忽略删除失败的目录
      }
    }
  }

  /**
   * 格式化文件大小
   */
  formatSize(bytes) {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  /**
   * 生成卸载报告
   */
  generateReport(existingFiles, removedFiles, failedFiles) {
    const totalSize = existingFiles.reduce((sum, f) => sum + f.size, 0);
    const removedSize = removedFiles.reduce((sum, f) => sum + f.size, 0);

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 卸载报告');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log(`📦 已删除文件: ${removedFiles.length} 个`);
    console.log(`💾 释放空间: ${this.formatSize(removedSize)}\n`);

    if (failedFiles.length > 0) {
      console.log(`⚠️  删除失败: ${failedFiles.length} 个`);
      failedFiles.forEach(({ file, error }) => {
        console.log(`   - ${file.relativePath}: ${error}`);
      });
      console.log('');
    }

    console.log(`📁 备份位置: ${path.basename(this.backupPath)}`);
    console.log(`   ${this.backupPath}\n`);

    console.log('✅ 保留的用户文件:');
    this.userFiles.forEach(file => {
      const fullPath = path.join(this.projectPath, file);
      if (fs.existsSync(fullPath)) {
        console.log(`   - ${file}`);
      }
    });
    console.log('');
  }

  /**
   * 执行卸载（主函数）
   */
  async uninstall(options = {}) {
    const { dryRun = false, removeCLAUDE = false } = options;

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🗑️  MODSDK 工作流卸载工具 v16.0');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // 检查是否已部署
    if (!this.isWorkflowInstalled()) {
      console.log('⚠️  未检测到已部署的工作流');
      console.log('   项目路径: ' + this.projectPath);
      console.log('\n提示: 如果您确认已部署工作流，请检查 .claude/workflow-version.json 是否存在\n');
      return { success: false, reason: 'not_installed' };
    }

    const version = this.getInstalledVersion();
    console.log(`📦 检测到工作流版本: v${version}`);
    console.log(`📍 项目路径: ${this.projectPath}\n`);

    // 扫描文件
    console.log('🔍 扫描工作流文件...\n');
    let existingFiles = this.scanWorkflowFiles();

    // 处理 CLAUDE.md
    if (removeCLAUDE) {
      const claudePath = path.join(this.projectPath, 'CLAUDE.md');
      if (fs.existsSync(claudePath)) {
        const stat = fs.statSync(claudePath);
        existingFiles.push({
          relativePath: 'CLAUDE.md',
          fullPath: claudePath,
          isDirectory: false,
          size: stat.size
        });
      }
    }

    if (existingFiles.length === 0) {
      console.log('✅ 未找到需要删除的工作流文件\n');
      return { success: true, reason: 'no_files' };
    }

    // 输出文件清单
    console.log(`📋 将要删除的文件 (${existingFiles.length} 个):\n`);

    const filesByCategory = {
      commands: [],
      docs: [],
      lib: [],
      config: [],
      other: []
    };

    existingFiles.forEach(file => {
      if (file.relativePath.startsWith('.claude/commands/')) {
        filesByCategory.commands.push(file);
      } else if (file.relativePath.startsWith('markdown/')) {
        filesByCategory.docs.push(file);
      } else if (file.relativePath.startsWith('lib/')) {
        filesByCategory.lib.push(file);
      } else if (file.relativePath.includes('version.json') || file.relativePath === 'CLAUDE.md') {
        filesByCategory.config.push(file);
      } else {
        filesByCategory.other.push(file);
      }
    });

    if (filesByCategory.commands.length > 0) {
      console.log('  📋 命令文件:');
      filesByCategory.commands.forEach(f => {
        console.log(`     - ${f.relativePath} (${this.formatSize(f.size)})`);
      });
    }

    if (filesByCategory.docs.length > 0) {
      console.log('  📚 文档文件:');
      filesByCategory.docs.forEach(f => {
        console.log(`     - ${f.relativePath} (${this.formatSize(f.size)})`);
      });
    }

    if (filesByCategory.lib.length > 0) {
      console.log('  🔧 工具库:');
      filesByCategory.lib.forEach(f => {
        console.log(`     - ${f.relativePath} (${this.formatSize(f.size)})`);
      });
    }

    if (filesByCategory.config.length > 0) {
      console.log('  ⚙️  配置文件:');
      filesByCategory.config.forEach(f => {
        console.log(`     - ${f.relativePath} (${this.formatSize(f.size)})`);
      });
    }

    if (filesByCategory.other.length > 0) {
      console.log('  🗂️  其他:');
      filesByCategory.other.forEach(f => {
        console.log(`     - ${f.relativePath} (${this.formatSize(f.size)})`);
      });
    }

    const totalSize = existingFiles.reduce((sum, f) => sum + f.size, 0);
    console.log(`\n  💾 总大小: ${this.formatSize(totalSize)}\n`);

    // Dry-run 模式
    if (dryRun) {
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
      console.log('ℹ️  预览模式（--dry-run）');
      console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
      console.log('以上文件将在正式卸载时被删除。');
      console.log('如需执行卸载，请移除 --dry-run 参数。\n');
      return { success: true, reason: 'dry_run' };
    }

    // 创建备份
    console.log('📦 创建备份...\n');
    this.createBackup(existingFiles);
    console.log(`  ✅ 已备份到: ${path.basename(this.backupPath)}\n`);

    // 删除文件
    console.log('🗑️  删除文件...\n');
    const { removedFiles, failedFiles } = this.removeFiles(existingFiles);

    // 清理空目录
    console.log('\n🧹 清理空目录...\n');
    this.cleanEmptyDirectories();

    // 生成报告
    this.generateReport(existingFiles, removedFiles, failedFiles);

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('✅ 卸载完成！');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('💡 提示:');
    console.log('   - 如需恢复，请从备份目录复制文件');
    console.log('   - 如需重新部署，请运行: initmc\n');

    return {
      success: true,
      removedCount: removedFiles.length,
      failedCount: failedFiles.length,
      backupPath: this.backupPath
    };
  }
}

/**
 * 主函数（用于直接调用）
 */
async function main() {
  const args = process.argv.slice(2);
  const projectPath = args.find(arg => !arg.startsWith('--')) || process.cwd();
  const dryRun = args.includes('--dry-run');
  const removeCLAUDE = args.includes('--remove-claude-md');

  const uninstaller = new WorkflowUninstaller(projectPath);
  await uninstaller.uninstall({ dryRun, removeCLAUDE });
}

// 导出
module.exports = { WorkflowUninstaller, main };

// 如果直接运行
if (require.main === module) {
  main().catch(err => {
    console.error('\n❌ 卸载失败:', err.message);
    if (err.stack) {
      console.error('\n详细错误信息:');
      console.error(err.stack);
    }
    process.exit(1);
  });
}
