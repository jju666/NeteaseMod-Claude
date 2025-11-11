/**
 * 软连接管理器
 * 负责创建和管理上游文档到下游项目的软连接
 * 支持跨平台，Windows下优雅降级为只读副本
 */

const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');

class SymlinkManager {
  constructor(upstreamPath, downstreamPath) {
    this.upstreamPath = upstreamPath;
    this.downstreamPath = downstreamPath;
    this.coreDocsPath = path.join(downstreamPath, '.claude', 'core-docs');
    this.markdownPath = path.join(downstreamPath, 'markdown');
  }

  /**
   * 创建所有核心文档的软连接
   * @returns {Object} 创建结果统计
   */
  async createAllSymlinks() {
    console.log('📂 创建上游文档引用...\n');

    // 确保目标目录存在
    fs.ensureDirSync(this.coreDocsPath);

    const coreFiles = this._getCoreFiles();
    const results = {
      symlinks: [],
      readonlyCopies: [],
      failed: []
    };

    for (const file of coreFiles) {
      const result = await this.createSymlink(file);

      if (result.type === 'symlink') {
        results.symlinks.push(file);
      } else if (result.type === 'readonly-copy') {
        results.readonlyCopies.push(file);
      } else {
        results.failed.push({ file, error: result.error });
      }
    }

    this._printResults(results);
    return results;
  }

  /**
   * 创建单个文件的软连接
   * @param {string} relativePath - 相对于markdown/的路径
   * @returns {Object} {type: 'symlink'|'readonly-copy'|'failed', error?: string}
   */
  async createSymlink(relativePath) {
    const targetPath = path.join(this.upstreamPath, 'markdown', relativePath);
    const linkPath = path.join(this.coreDocsPath, relativePath);

    // 确保父目录存在
    fs.ensureDirSync(path.dirname(linkPath));

    // 如果已存在，先删除
    if (fs.existsSync(linkPath)) {
      fs.removeSync(linkPath);
    }

    try {
      // 尝试创建软连接
      return await this._tryCreateSymlink(targetPath, linkPath, relativePath);
    } catch (error) {
      return { type: 'failed', error: error.message };
    }
  }

  /**
   * 尝试创建软连接（带降级策略）
   */
  async _tryCreateSymlink(targetPath, linkPath, relativePath) {
    const isDirectory = fs.statSync(targetPath).isDirectory();

    try {
      if (process.platform === 'win32') {
        // Windows: 使用Junction（不需要管理员权限）
        const type = isDirectory ? 'junction' : 'file';
        fs.symlinkSync(targetPath, linkPath, type);
      } else {
        // Linux/Mac: 标准符号链接
        fs.symlinkSync(targetPath, linkPath);
      }

      console.log(`   ✅ 软连接: ${relativePath} → 上游`);
      return { type: 'symlink' };

    } catch (err) {
      // 降级：创建只读副本
      return await this._createReadonlyCopy(targetPath, linkPath, relativePath, isDirectory);
    }
  }

  /**
   * 创建只读副本（软连接失败时的降级方案）
   */
  async _createReadonlyCopy(targetPath, linkPath, relativePath, isDirectory) {
    try {
      console.log(`   ⚠️  无法创建软连接，降级为只读副本: ${relativePath}`);

      if (isDirectory) {
        // 复制目录
        fs.copySync(targetPath, linkPath);

        // 为目录中的每个.md文件添加标记
        const mdFiles = this._findMarkdownFiles(linkPath);
        for (const mdFile of mdFiles) {
          this._addReadonlyHeader(mdFile);
        }
      } else {
        // 复制文件
        fs.copySync(targetPath, linkPath);

        // 添加只读标记
        if (relativePath.endsWith('.md')) {
          this._addReadonlyHeader(linkPath);
        }
      }

      // 设置只读权限（尽力而为）
      try {
        this._setReadonly(linkPath, isDirectory);
      } catch {}

      return { type: 'readonly-copy' };

    } catch (copyErr) {
      return { type: 'failed', error: copyErr.message };
    }
  }

  /**
   * 为Markdown文件添加只读标记
   */
  _addReadonlyHeader(filePath) {
    try {
      const content = fs.readFileSync(filePath, 'utf-8');

      // 检查是否已有标记
      if (content.includes('⚠️ **只读文档**')) {
        return;
      }

      const header = `<!--
⚠️ **只读文档**

此文档来自上游工作流，请勿直接编辑。

如需定制：
1. 复制到 markdown/core/${path.basename(filePath)}
2. 编辑项目副本
3. AI会自动优先读取项目定制版本

执行 \`initmc --sync\` 可更新此文档。
-->

`;

      fs.writeFileSync(filePath, header + content, 'utf-8');
    } catch (err) {
      console.warn(`     警告: 无法添加只读标记到 ${filePath}`);
    }
  }

  /**
   * 设置只读权限
   */
  _setReadonly(targetPath, isDirectory) {
    if (isDirectory) {
      // 递归设置目录中所有文件为只读
      const files = this._findAllFiles(targetPath);
      for (const file of files) {
        fs.chmodSync(file, 0o444);
      }
    } else {
      fs.chmodSync(targetPath, 0o444);
    }
  }

  /**
   * 动态获取核心文档列表(扫描markdown/目录)
   * v16.4+: 自动发现文档,零维护
   */
  _getCoreFiles() {
    const glob = require('glob');
    const coreFiles = [];

    const markdownRoot = path.join(this.upstreamPath, 'markdown');

    // 定义需要部署的目录和文件模式
    const includePatterns = [
      '核心工作流文档/**/*.md',
      '概念参考/**/*.md',
      '深度指南/**/*.md',
      'ai/**/*.md',
      'ai',  // 包含ai目录本身
      '可选工具说明.md'
    ];

    // 排除模式(下游项目文档)
    const excludePatterns = [
      '**/索引.md',
      '**/项目状态.md',
      '**/文档待补充清单.md',
      'systems/**',  // 模板目录不部署
      'core/**',     // 项目覆盖层不部署
      'README.md'    // 根README不部署(下游有自己的)
    ];

    // 扫描匹配的文件
    for (const pattern of includePatterns) {
      const files = glob.sync(pattern, {
        cwd: markdownRoot,
        nodir: pattern === 'ai' ? false : true,  // ai目录需要创建软连接
        dot: false
      });

      // 过滤排除模式
      const filtered = files.filter(file => {
        return !excludePatterns.some(exclude => {
          // 简单的glob匹配
          const excludeRegex = new RegExp(exclude.replace(/\*\*/g, '.*').replace(/\*/g, '[^/]*'));
          return excludeRegex.test(file);
        });
      });

      coreFiles.push(...filtered);
    }

    // 去重并返回
    return [...new Set(coreFiles)];
  }

  /**
   * 递归查找所有Markdown文件
   */
  _findMarkdownFiles(dir) {
    const mdFiles = [];

    const traverse = (currentDir) => {
      const entries = fs.readdirSync(currentDir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentDir, entry.name);

        if (entry.isDirectory()) {
          traverse(fullPath);
        } else if (entry.name.endsWith('.md')) {
          mdFiles.push(fullPath);
        }
      }
    };

    traverse(dir);
    return mdFiles;
  }

  /**
   * 递归查找所有文件
   */
  _findAllFiles(dir) {
    const files = [];

    const traverse = (currentDir) => {
      const entries = fs.readdirSync(currentDir, { withFileTypes: true });

      for (const entry of entries) {
        const fullPath = path.join(currentDir, entry.name);

        if (entry.isDirectory()) {
          traverse(fullPath);
        } else {
          files.push(fullPath);
        }
      }
    };

    traverse(dir);
    return files;
  }

  /**
   * 打印创建结果
   */
  _printResults(results) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 上游文档引用创建完成');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    if (results.symlinks.length > 0) {
      console.log(`✅ 软连接 (${results.symlinks.length}个):`);
      results.symlinks.forEach(f => console.log(`   - ${f}`));
      console.log('');
    }

    if (results.readonlyCopies.length > 0) {
      console.log(`📋 只读副本 (${results.readonlyCopies.length}个):`);
      results.readonlyCopies.forEach(f => console.log(`   - ${f}`));
      console.log('');
      console.log('💡 提示: 检测到无法创建软连接（可能缺少权限），已降级为只读副本');
      console.log('   功能完全正常，但更新时需要重新复制文件\n');
    }

    if (results.failed.length > 0) {
      console.log(`❌ 失败 (${results.failed.length}个):`);
      results.failed.forEach(item => {
        console.log(`   - ${item.file}: ${item.error}`);
      });
      console.log('');
    }

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  }

  /**
   * 更新已有的软连接（同步时使用）
   */
  async updateSymlinks() {
    console.log('🔄 更新上游文档引用...\n');

    // 检查.claude/core-docs/是否存在
    if (!fs.existsSync(this.coreDocsPath)) {
      console.log('   ℹ️  首次同步，创建新的引用...\n');
      return await this.createAllSymlinks();
    }

    const coreFiles = this._getCoreFiles();
    const results = {
      updated: [],
      unchanged: [],
      failed: []
    };

    for (const file of coreFiles) {
      const linkPath = path.join(this.coreDocsPath, file);
      const targetPath = path.join(this.upstreamPath, 'markdown', file);

      try {
        // 检查是否是软连接
        const stats = fs.lstatSync(linkPath);

        if (stats.isSymbolicLink()) {
          // 检查软连接是否指向正确的目标
          const currentTarget = fs.readlinkSync(linkPath);
          const expectedTarget = path.relative(path.dirname(linkPath), targetPath);

          if (currentTarget !== expectedTarget) {
            // 重新创建软连接
            fs.removeSync(linkPath);
            await this.createSymlink(file);
            results.updated.push(file);
          } else {
            results.unchanged.push(file);
          }
        } else {
          // 是只读副本，重新复制
          fs.removeSync(linkPath);
          const result = await this.createSymlink(file);

          if (result.type !== 'failed') {
            results.updated.push(file);
          } else {
            results.failed.push({ file, error: result.error });
          }
        }
      } catch (err) {
        // 文件不存在或其他错误，重新创建
        const result = await this.createSymlink(file);

        if (result.type !== 'failed') {
          results.updated.push(file);
        } else {
          results.failed.push({ file, error: result.error });
        }
      }
    }

    this._printUpdateResults(results);
    return results;
  }

  /**
   * 打印更新结果
   */
  _printUpdateResults(results) {
    if (results.updated.length > 0) {
      console.log(`   ✅ 已更新 ${results.updated.length} 个文档引用`);
    }

    if (results.unchanged.length > 0) {
      console.log(`   ℹ️  ${results.unchanged.length} 个引用无需更新`);
    }

    if (results.failed.length > 0) {
      console.log(`   ❌ ${results.failed.length} 个引用更新失败`);
      results.failed.forEach(item => {
        console.log(`      - ${item.file}: ${item.error}`);
      });
    }

    console.log('');
  }

  /**
   * 在markdown/目录创建指向.claude/core-docs/的软连接
   * 用于解决/cc命令引用markdown/开发规范.md的路径问题
   * @returns {Object} 创建结果统计
   */
  async createMarkdownSymlinks() {
    console.log('📂 在markdown/目录创建核心文档引用...\n');

    // 确保markdown目录存在
    fs.ensureDirSync(this.markdownPath);

    const coreFiles = this._getCoreFiles();
    const results = {
      symlinks: [],
      readonlyCopies: [],
      skipped: [],
      failed: []
    };

    for (const file of coreFiles) {
      const result = await this._createMarkdownSymlink(file);

      if (result.type === 'symlink') {
        results.symlinks.push(file);
      } else if (result.type === 'readonly-copy') {
        results.readonlyCopies.push(file);
      } else if (result.type === 'skipped') {
        results.skipped.push(file);
      } else {
        results.failed.push({ file, error: result.error });
      }
    }

    this._printMarkdownResults(results);
    return results;
  }

  /**
   * 创建单个文件从markdown/到.claude/core-docs/的软连接
   */
  async _createMarkdownSymlink(relativePath) {
    const sourcePath = path.join(this.coreDocsPath, relativePath);
    const targetPath = path.join(this.markdownPath, relativePath);

    // 检查源文件是否存在
    if (!fs.existsSync(sourcePath)) {
      console.log(`   ⚠️  跳过: ${relativePath}（源文件不存在）`);
      return { type: 'skipped' };
    }

    // 如果目标已存在且不是软连接，跳过（保护用户文件）
    if (fs.existsSync(targetPath)) {
      const stats = fs.lstatSync(targetPath);
      if (!stats.isSymbolicLink()) {
        console.log(`   ℹ️  跳过: ${relativePath}（已存在用户文件）`);
        return { type: 'skipped' };
      }
      // 如果是软连接，删除并重新创建
      fs.removeSync(targetPath);
    }

    // 确保父目录存在
    fs.ensureDirSync(path.dirname(targetPath));

    try {
      const isDirectory = fs.statSync(sourcePath).isDirectory();

      if (process.platform === 'win32') {
        // Windows: 使用相对路径创建软连接
        const relativeSource = path.relative(path.dirname(targetPath), sourcePath);
        const type = isDirectory ? 'junction' : 'file';
        fs.symlinkSync(relativeSource, targetPath, type);
      } else {
        // Linux/Mac: 使用相对路径创建软连接
        const relativeSource = path.relative(path.dirname(targetPath), sourcePath);
        fs.symlinkSync(relativeSource, targetPath);
      }

      console.log(`   ✅ markdown/${relativePath} → .claude/core-docs/${relativePath}`);
      return { type: 'symlink' };

    } catch (err) {
      console.log(`   ⚠️  软连接失败，降级为只读副本: ${relativePath}`);

      try {
        const isDirectory = fs.statSync(sourcePath).isDirectory();
        fs.copySync(sourcePath, targetPath);

        // 添加只读标记
        if (!isDirectory && relativePath.endsWith('.md')) {
          this._addReadonlyHeader(targetPath);
        }

        return { type: 'readonly-copy' };
      } catch (copyErr) {
        return { type: 'failed', error: copyErr.message };
      }
    }
  }

  /**
   * 打印markdown软连接创建结果
   */
  _printMarkdownResults(results) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 markdown/核心文档引用创建完成');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    if (results.symlinks.length > 0) {
      console.log(`✅ 软连接 (${results.symlinks.length}个):`);
      results.symlinks.forEach(f => console.log(`   - ${f}`));
      console.log('');
    }

    if (results.readonlyCopies.length > 0) {
      console.log(`📋 只读副本 (${results.readonlyCopies.length}个):`);
      results.readonlyCopies.forEach(f => console.log(`   - ${f}`));
      console.log('');
    }

    if (results.skipped.length > 0) {
      console.log(`ℹ️  跳过 (${results.skipped.length}个):`);
      results.skipped.forEach(f => console.log(`   - ${f}`));
      console.log('');
    }

    if (results.failed.length > 0) {
      console.log(`❌ 失败 (${results.failed.length}个):`);
      results.failed.forEach(item => {
        console.log(`   - ${item.file}: ${item.error}`);
      });
      console.log('');
    }

    console.log('💡 /cc命令现在可以通过 markdown/开发规范.md 访问核心文档\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  }
}

module.exports = { SymlinkManager };
