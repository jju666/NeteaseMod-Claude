/**
 * 版本检测器
 * 负责检测工作流版本、比较更新、计算文件哈希
 */

const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');

class VersionChecker {
  constructor(upstreamPath, downstreamPath) {
    this.upstreamPath = upstreamPath;
    this.downstreamPath = downstreamPath;
    this.manifestPath = path.join(downstreamPath, '.claude', 'workflow-manifest.json');
  }

  /**
   * 检查是否需要更新
   * @returns {Object} {needsUpdate, local, upstream, changelog}
   */
  checkVersion() {
    const localVersion = this.getLocalVersion();
    const upstreamVersion = this.getUpstreamVersion();

    const needsUpdate = this._compareVersions(localVersion, upstreamVersion) < 0;

    return {
      needsUpdate,
      local: localVersion,
      upstream: upstreamVersion,
      changelog: needsUpdate ? this._getChangelog(localVersion, upstreamVersion) : null
    };
  }

  /**
   * 获取本地工作流版本
   * 优先读取workflow-version.json（v15.x），降级到workflow-manifest.json（v16.0+）
   */
  getLocalVersion() {
    try {
      // 1. 优先检查workflow-version.json（v15.x的版本文件）
      const versionPath = path.join(this.downstreamPath, '.claude', 'workflow-version.json');
      if (fs.existsSync(versionPath)) {
        const versionFile = JSON.parse(fs.readFileSync(versionPath, 'utf-8'));
        const version = versionFile.version || '15.0.0';

        // v15.x使用的版本格式是"15.0"，需要标准化为"15.0.0"
        if (version && !version.includes('.', version.indexOf('.') + 1)) {
          return version + '.0';
        }
        return version;
      }

      // 2. 降级检查workflow-manifest.json（v16.0+的版本文件）
      if (!fs.existsSync(this.manifestPath)) {
        // 完全没有版本文件，认为是全新项目
        return '0.0.0';
      }

      const manifest = JSON.parse(fs.readFileSync(this.manifestPath, 'utf-8'));
      return manifest.version || '15.1.0';
    } catch (err) {
      return '15.1.0';
    }
  }

  /**
   * 获取上游工作流版本
   */
  getUpstreamVersion() {
    try {
      const packagePath = path.join(this.upstreamPath, 'package.json');
      const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf-8'));
      return pkg.version || '16.0.0';
    } catch (err) {
      return '16.0.0';
    }
  }

  /**
   * 比较版本号
   * @returns {number} -1: v1<v2, 0: v1==v2, 1: v1>v2
   */
  _compareVersions(v1, v2) {
    const parts1 = v1.split('.').map(Number);
    const parts2 = v2.split('.').map(Number);

    for (let i = 0; i < Math.max(parts1.length, parts2.length); i++) {
      const p1 = parts1[i] || 0;
      const p2 = parts2[i] || 0;

      if (p1 < p2) return -1;
      if (p1 > p2) return 1;
    }

    return 0;
  }

  /**
   * 获取更新日志（简化版）
   */
  _getChangelog(fromVersion, toVersion) {
    const changelogs = {
      '16.0.0': `
📋 v16.0.0 更新内容:

✨ **核心特性**:
- 双层文档架构: 上游基线 + 项目覆盖层
- 自动同步: initmc --sync 一键更新
- 智能清理: 自动检测并清理废弃文件
- 覆盖层支持: markdown/core/ 实现项目定制

🔧 **架构变更**:
- 上游文档移至 .claude/core-docs/ (软连接)
- 支持非MODSDK项目定制化
- 完全职责隔离 (多项目互不影响)

📚 **文档改进**:
- 新增 markdown/README.md 导航文档
- AI智能文档路由 (覆盖层优先)
- 自动迁移v15.x项目

⚠️ **破坏性变更**:
- markdown/ 目录结构调整
- 需要执行迁移脚本 (自动)
      `.trim()
    };

    return changelogs[toVersion] || '详见更新日志';
  }

  /**
   * 读取manifest
   */
  readManifest() {
    try {
      if (!fs.existsSync(this.manifestPath)) {
        return this._createDefaultManifest();
      }

      return JSON.parse(fs.readFileSync(this.manifestPath, 'utf-8'));
    } catch (err) {
      return this._createDefaultManifest();
    }
  }

  /**
   * 写入manifest
   */
  writeManifest(data) {
    const manifest = {
      ...this.readManifest(),
      ...data,
      updatedAt: new Date().toISOString()
    };

    fs.ensureDirSync(path.dirname(this.manifestPath));
    fs.writeFileSync(this.manifestPath, JSON.stringify(manifest, null, 2), 'utf-8');

    return manifest;
  }

  /**
   * 创建默认manifest
   */
  _createDefaultManifest() {
    return {
      version: '15.1.0',
      createdAt: new Date().toISOString(),
      baselineHashes: {},
      obsoleteFiles: []
    };
  }

  /**
   * 计算上游基线文件的哈希值
   * @returns {Object} {filename: hash}
   */
  computeBaselineHashes() {
    const coreFiles = [
      '开发规范.md',
      '问题排查.md',
      '快速开始.md',
      'MODSDK核心概念.md',
      'API速查.md',
      '官方文档查询指南.md',
      '迁移指南-v15.0.md'
    ];

    const hashes = {};

    for (const file of coreFiles) {
      const filePath = path.join(this.upstreamPath, 'markdown', file);

      if (fs.existsSync(filePath)) {
        hashes[file] = this.getFileHash(filePath);
      }
    }

    return hashes;
  }

  /**
   * 计算文件SHA256哈希
   */
  getFileHash(filePath) {
    try {
      const content = fs.readFileSync(filePath);
      return crypto.createHash('sha256').update(content).digest('hex');
    } catch (err) {
      return null;
    }
  }

  /**
   * 检测文件是否被用户定制过
   * @param {string} filePath - 文件绝对路径
   * @param {string} baselineHash - 基线哈希（从manifest读取）
   * @returns {boolean} true=已定制, false=未定制
   */
  isFileCustomized(filePath, baselineHash) {
    if (!fs.existsSync(filePath)) {
      return false;
    }

    const currentHash = this.getFileHash(filePath);
    return currentHash !== baselineHash;
  }

  /**
   * 检测废弃文件
   * @param {string} fromVersion - 起始版本
   * @param {string} toVersion - 目标版本
   * @returns {Array<string>} 废弃文件路径列表
   */
  detectObsoleteFiles(fromVersion, toVersion) {
    const obsolete = [];

    // v16.0: markdown/下的核心文档应移至.claude/core-docs/引用
    if (this._compareVersions(fromVersion, '16.0.0') < 0 &&
        this._compareVersions(toVersion, '16.0.0') >= 0) {

      const v16CoreFiles = [
        'markdown/开发规范.md',
        'markdown/问题排查.md',
        'markdown/快速开始.md',
        'markdown/MODSDK核心概念.md',
        'markdown/API速查.md',
        'markdown/官方文档查询指南.md',
        'markdown/迁移指南-v15.0.md',
        'markdown/ai' // 目录
      ];

      obsolete.push(...v16CoreFiles);
    }

    return obsolete;
  }

  /**
   * 检测覆盖层文件的上游更新
   * @returns {Array<Object>} 冲突列表
   */
  async detectOverrideConflicts() {
    const conflicts = [];
    const overrideDir = path.join(this.downstreamPath, 'markdown', 'core');

    if (!fs.existsSync(overrideDir)) {
      return conflicts;
    }

    const manifest = this.readManifest();
    const baselineHashes = manifest.baselineHashes || {};
    const currentBaselineHashes = this.computeBaselineHashes();

    // 遍历覆盖层文件
    const overrideFiles = fs.readdirSync(overrideDir).filter(f => f.endsWith('.md'));

    for (const file of overrideFiles) {
      const oldBaselineHash = baselineHashes[file];
      const newBaselineHash = currentBaselineHashes[file];

      // 如果上游文件有变化
      if (oldBaselineHash && newBaselineHash && oldBaselineHash !== newBaselineHash) {
        const overridePath = path.join(overrideDir, file);
        const upstreamPath = path.join(this.upstreamPath, 'markdown', file);

        conflicts.push({
          file,
          overridePath,
          upstreamPath,
          oldBaselineHash,
          newBaselineHash,
          description: '上游文档有更新，建议审查并合并'
        });
      }
    }

    return conflicts;
  }

  /**
   * 打印版本检测报告
   */
  printVersionReport() {
    const check = this.checkVersion();

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 工作流版本检测');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log(`本地版本: v${check.local}`);
    console.log(`上游版本: v${check.upstream}\n`);

    if (check.needsUpdate) {
      console.log('⚠️  检测到新版本！\n');
      console.log(check.changelog);
      console.log('\n💡 执行 `initmc --sync` 更新到最新版本\n');
    } else {
      console.log('✅ 已是最新版本\n');
    }

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    return check;
  }
}

module.exports = { VersionChecker };
