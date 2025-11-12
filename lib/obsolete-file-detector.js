/**
 * 废弃文件检测器（扩展版）
 * 负责检测各版本之间的废弃文件，支持自定义规则
 */

const fs = require('fs-extra');
const path = require('path');

/**
 * 废弃文件检测规则配置
 * 每个规则包含：
 * - fromVersion: 起始版本
 * - toVersion: 目标版本
 * - files: 废弃文件列表
 * - reason: 废弃原因
 * - action: 处理动作 (delete, backup, migrate, warn)
 */
const OBSOLETE_RULES = [
  // v16.0: 双层文档架构迁移
  {
    fromVersion: '15.0.0',
    toVersion: '16.0.0',
    files: [
      'markdown/开发规范.md',
      'markdown/问题排查.md',
      'markdown/快速开始.md',
      'markdown/MODSDK核心概念.md',
      'markdown/API速查.md',
      'markdown/官方文档查询指南.md',
      'markdown/迁移指南-v15.0.md',
      'markdown/AI策略文档'
    ],
    reason: '双层文档架构：核心文档移至.claude/core-docs/引用',
    action: 'migrate', // 迁移到覆盖层或删除
    migrateTo: 'markdown/core'
  },

  // v16.0: 废弃旧命令脚本
  {
    fromVersion: '15.0.0',
    toVersion: '16.0.0',
    files: [
      'scripts/initmc.js'
    ],
    reason: '架构重构：改用lib/init-workflow.js',
    action: 'warn' // 只警告，不自动删除（可能在开发中使用）
  },

  // v16.0: 废弃旧配置文件
  {
    fromVersion: '15.0.0',
    toVersion: '16.0.0',
    files: [
      '.claude/workflow-config.json'
    ],
    reason: '配置合并到.claude/workflow-manifest.json',
    action: 'backup'
  },

  // 示例：未来版本的规则（v17.0）
  {
    fromVersion: '16.0.0',
    toVersion: '17.0.0',
    files: [
      'markdown/迁移指南-v15.0.md'
    ],
    reason: 'v15.0已过时，移除旧版本迁移指南',
    action: 'delete'
  },

  // v18.0: AI策略文档目录改名（ai → AI策略文档）
  {
    fromVersion: '17.0.0',
    toVersion: '18.0.0',
    files: [
      '.claude/core-docs/ai'
    ],
    reason: 'AI策略文档目录改名：ai → AI策略文档',
    action: 'delete'
  }
];

class ObsoleteFileDetector {
  constructor(downstreamPath) {
    this.downstreamPath = downstreamPath;
    this.backupDir = path.join(downstreamPath, '.backup-obsolete');
  }

  /**
   * 检测废弃文件
   * @param {string} fromVersion - 起始版本
   * @param {string} toVersion - 目标版本
   * @returns {Array<Object>} 废弃文件列表
   */
  detect(fromVersion, toVersion) {
    const obsolete = [];

    for (const rule of OBSOLETE_RULES) {
      // 检查版本范围是否匹配
      if (this._isVersionInRange(fromVersion, toVersion, rule)) {
        for (const file of rule.files) {
          const filePath = path.join(this.downstreamPath, file);

          // 检查文件是否存在
          if (fs.existsSync(filePath)) {
            obsolete.push({
              file,
              filePath,
              reason: rule.reason,
              action: rule.action,
              migrateTo: rule.migrateTo,
              fromVersion: rule.fromVersion,
              toVersion: rule.toVersion
            });
          }
        }
      }
    }

    return obsolete;
  }

  /**
   * 执行废弃文件处理
   * @param {Array<Object>} obsoleteFiles - 废弃文件列表
   * @param {Object} options - 选项 {autoConfirm, dryRun}
   * @returns {Object} 处理结果统计
   */
  async process(obsoleteFiles, options = {}) {
    const { autoConfirm = false, dryRun = false } = options;

    const stats = {
      deleted: [],
      backed: [],
      migrated: [],
      warned: [],
      skipped: []
    };

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🗑️  废弃文件处理');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    if (dryRun) {
      console.log('⚠️  [模拟运行] 不会实际修改文件\n');
    }

    for (const item of obsoleteFiles) {
      console.log(`📄 ${item.file}`);
      console.log(`   原因: ${item.reason}`);
      console.log(`   动作: ${this._getActionDescription(item.action)}\n`);

      let confirmed = autoConfirm;

      if (!autoConfirm && !dryRun) {
        const readline = require('readline');
        const rl = readline.createInterface({
          input: process.stdin,
          output: process.stdout
        });

        confirmed = await new Promise(resolve => {
          rl.question(`   确认处理? [Y/n]: `, answer => {
            rl.close();
            resolve(answer.toLowerCase() !== 'n');
          });
        });
      }

      if (!confirmed) {
        stats.skipped.push(item.file);
        console.log('   ⏭️  跳过\n');
        continue;
      }

      if (dryRun) {
        console.log(`   [模拟] 将执行 ${item.action}\n`);
        continue;
      }

      // 执行处理动作
      try {
        switch (item.action) {
          case 'delete':
            await this._deleteFile(item);
            stats.deleted.push(item.file);
            break;

          case 'backup':
            await this._backupFile(item);
            stats.backed.push(item.file);
            break;

          case 'migrate':
            await this._migrateFile(item);
            stats.migrated.push(item.file);
            break;

          case 'warn':
            this._warnFile(item);
            stats.warned.push(item.file);
            break;

          default:
            console.log(`   ❌ 未知动作: ${item.action}\n`);
            stats.skipped.push(item.file);
        }
      } catch (err) {
        console.log(`   ❌ 处理失败: ${err.message}\n`);
        stats.skipped.push(item.file);
      }
    }

    // 打印统计
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 处理结果');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    if (stats.deleted.length > 0) {
      console.log(`✅ 已删除: ${stats.deleted.length} 个文件`);
    }
    if (stats.backed.length > 0) {
      console.log(`📦 已备份: ${stats.backed.length} 个文件`);
    }
    if (stats.migrated.length > 0) {
      console.log(`🔄 已迁移: ${stats.migrated.length} 个文件`);
    }
    if (stats.warned.length > 0) {
      console.log(`⚠️  已警告: ${stats.warned.length} 个文件`);
    }
    if (stats.skipped.length > 0) {
      console.log(`⏭️  已跳过: ${stats.skipped.length} 个文件`);
    }

    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    return stats;
  }

  /**
   * 删除文件
   */
  async _deleteFile(item) {
    fs.removeSync(item.filePath);
    console.log(`   ✅ 已删除\n`);
  }

  /**
   * 备份文件
   */
  async _backupFile(item) {
    fs.ensureDirSync(this.backupDir);

    const backupPath = path.join(this.backupDir, item.file);
    fs.ensureDirSync(path.dirname(backupPath));
    fs.moveSync(item.filePath, backupPath, { overwrite: true });

    console.log(`   ✅ 已备份到: ${path.relative(this.downstreamPath, backupPath)}\n`);
  }

  /**
   * 迁移文件
   */
  async _migrateFile(item) {
    if (!item.migrateTo) {
      throw new Error('未指定迁移目标');
    }

    const targetPath = path.join(this.downstreamPath, item.migrateTo, path.basename(item.file));
    fs.ensureDirSync(path.dirname(targetPath));
    fs.moveSync(item.filePath, targetPath, { overwrite: true });

    console.log(`   ✅ 已迁移到: ${path.relative(this.downstreamPath, targetPath)}\n`);
  }

  /**
   * 警告文件
   */
  _warnFile(item) {
    console.log(`   ⚠️  警告: 建议手动检查此文件\n`);
  }

  /**
   * 获取动作描述
   */
  _getActionDescription(action) {
    const descriptions = {
      delete: '删除',
      backup: '备份后删除',
      migrate: '迁移到新位置',
      warn: '仅警告'
    };

    return descriptions[action] || action;
  }

  /**
   * 检查版本是否在规则范围内
   *
   * 规则应用逻辑：
   * - 如果用户从 fromVersion 升级到 toVersion
   * - 且升级路径经过了规则定义的版本区间
   * - 则应用此规则
   *
   * 例如：
   * - 规则：17.0.0 → 18.0.0
   * - 用户：17.3.0 → 18.0.0 ✅ 应用（17.3.0 在 17.0.0-18.0.0 区间内，且升级到18.0.0）
   * - 用户：16.0.0 → 18.0.0 ✅ 应用（跨越了17.0.0-18.0.0区间）
   * - 用户：17.5.0 → 17.8.0 ❌ 不应用（未到达18.0.0）
   */
  _isVersionInRange(fromVersion, toVersion, rule) {
    const from = this._parseVersion(fromVersion);
    const to = this._parseVersion(toVersion);
    const ruleFrom = this._parseVersion(rule.fromVersion);
    const ruleTo = this._parseVersion(rule.toVersion);

    // 检查升级路径是否经过此规则区间
    // 条件1: 起始版本 < 规则目标版本（确保还未应用此规则）
    // 条件2: 目标版本 >= 规则目标版本（确保升级到达或超过规则目标版本）
    return from < ruleTo && to >= ruleTo;
  }

  /**
   * 解析版本号为数字
   */
  _parseVersion(version) {
    const parts = version.split('.').map(Number);
    return parts[0] * 10000 + (parts[1] || 0) * 100 + (parts[2] || 0);
  }

  /**
   * 添加自定义规则
   */
  static addRule(rule) {
    OBSOLETE_RULES.push(rule);
  }

  /**
   * 获取所有规则
   */
  static getRules() {
    return OBSOLETE_RULES;
  }

  /**
   * 清除规则
   */
  static clearRules() {
    OBSOLETE_RULES.length = 0;
  }
}

module.exports = { ObsoleteFileDetector, OBSOLETE_RULES };
