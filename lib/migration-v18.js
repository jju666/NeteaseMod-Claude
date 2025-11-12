#!/usr/bin/env node
/**
 * v17.x → v18.0 迁移脚本
 * 核心变更：CLAUDE.md不再由工作流管理，完全由用户维护
 *
 * @module migration-v18
 * @version 18.0.0
 * @date 2025-11-12
 */

const path = require('path');
const fs = require('fs-extra');
const readline = require('readline');
const { readFile, writeFile } = require('./utils');

class MigrationV18 {
  constructor(upstreamPath, downstreamPath) {
    this.upstreamPath = upstreamPath;
    this.downstreamPath = downstreamPath;
    this.claudePath = path.join(downstreamPath, 'CLAUDE.md');
  }

  /**
   * 检查是否需要迁移
   * @returns {boolean}
   */
  needsMigration() {
    // 检查是否存在旧版CLAUDE.md（由工作流管理的版本）
    if (!fs.existsSync(this.claudePath)) {
      return false; // 全新项目，跳过迁移
    }

    const content = readFile(this.claudePath);

    // 检查是否包含旧版标记（工作流管理的区域）
    const hasWorkflowManagedSection = /<!-- ={20} 工作流内容 START/.test(content);

    return hasWorkflowManagedSection;
  }

  /**
   * 执行迁移
   * @param {Object} options - 迁移选项
   * @param {boolean} options.autoConfirm - 是否自动确认（默认保留现有文件）
   * @returns {Promise<Object>} 迁移结果
   */
  async migrate(options = {}) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🔄 NeteaseMod-Claude v18.0 迁移向导');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📋 核心变更说明：');
    console.log('  - CLAUDE.md不再由工作流管理，完全由用户维护');
    console.log('  - initmc不再生成/覆盖CLAUDE.md');
    console.log('  - MODSDK开发工作流通过 /mc 系列命令隐式适配\n');

    console.log('🔍 检测到v17.x版本的CLAUDE.md');
    console.log('');

    // 提示用户选择迁移方式
    if (!options.autoConfirm) {
      console.log('请选择迁移方式：');
      console.log('  [1] 保留现有CLAUDE.md（推荐）');
      console.log('  [2] 简化为最小化模板（旧版备份为CLAUDE.md.v17.backup）');
      console.log('  [3] 取消迁移（稍后手动处理）');
      console.log('');

      const choice = await this._askUser('请输入选项 [1/2/3]：');

      if (choice === '3') {
        console.log('\n⚠️  迁移已取消');
        console.log('💡 提示：您可以稍后手动运行 initmc 重新触发迁移\n');
        return { success: false, action: 'cancelled' };
      }

      if (choice === '2') {
        return await this._simplifyToMinimal();
      }

      // 默认选项1：保留现有CLAUDE.md
      return await this._preserveExisting();

    } else {
      // 自动确认模式（默认保留）
      return await this._preserveExisting();
    }
  }

  /**
   * 保留现有CLAUDE.md
   * @returns {Promise<Object>}
   */
  async _preserveExisting() {
    console.log('\n🔄 迁移方式：保留现有CLAUDE.md\n');

    const content = readFile(this.claudePath);

    // 移除旧版的工作流管理标记（清理HTML注释）
    const cleanedContent = this._removeWorkflowMarkers(content);

    // 写回文件
    writeFile(this.claudePath, cleanedContent);

    console.log('✅ 迁移完成：CLAUDE.md已保留');
    console.log('💡 提示：');
    console.log('  - CLAUDE.md现在完全由您管理，initmc不再干预');
    console.log('  - 旧版的"工作流内容区"标记已清理');
    console.log('  - 您可以自由编辑CLAUDE.md，无需担心升级时丢失内容\n');

    return { success: true, action: 'preserved' };
  }

  /**
   * 简化为最小化模板
   * @returns {Promise<Object>}
   */
  async _simplifyToMinimal() {
    console.log('\n🔄 迁移方式：简化为最小化模板\n');

    // 1. 备份旧版
    const backupPath = `${this.claudePath}.v17.backup`;
    fs.copySync(this.claudePath, backupPath);
    console.log(`📦 已备份旧版：${backupPath}`);

    // 2. 生成最小化模板
    const minimalCLAUDE = this._generateMinimalCLAUDE();
    writeFile(this.claudePath, minimalCLAUDE);

    console.log('✅ 迁移完成：CLAUDE.md已简化');
    console.log('💡 提示：');
    console.log('  - 旧版备份：CLAUDE.md.v17.backup');
    console.log('  - 新版CLAUDE.md是最小化模板（~30行）');
    console.log('  - 您可以参考旧版备份，手动添加需要的内容\n');

    return { success: true, action: 'simplified' };
  }

  /**
   * 移除工作流管理标记
   * @param {string} content - 文件内容
   * @returns {string} 清理后的内容
   */
  _removeWorkflowMarkers(content) {
    // 移除所有 HTML 注释标记
    let cleaned = content;

    // 移除工作流管理区域标记
    cleaned = cleaned.replace(/<!-- ={20} 工作流内容 START[^>]*-->/gm, '');
    cleaned = cleaned.replace(/<!-- ={20} 工作流内容 END[^>]*-->/gm, '');

    // 移除项目配置区标记
    cleaned = cleaned.replace(/<!-- ={20} 项目配置区 START[^>]*-->/gm, '');
    cleaned = cleaned.replace(/<!-- ={20} 项目配置区 END[^>]*-->/gm, '');

    // 移除项目扩展区标记
    cleaned = cleaned.replace(/<!-- ={20} 项目扩展区 START[^>]*-->/gm, '');
    cleaned = cleaned.replace(/<!-- ={20} 项目扩展区 END[^>]*-->/gm, '');

    // 移除文档元数据区标记
    cleaned = cleaned.replace(/<!-- ={20} 文档元数据区 START[^>]*-->/gm, '');
    cleaned = cleaned.replace(/<!-- ={20} 文档元数据区 END[^>]*-->/gm, '');

    // 移除用户编辑提示注释
    cleaned = cleaned.replace(/<!--\s*用户可编辑[：:：][^>]*-->\s*/gm, '');
    cleaned = cleaned.replace(/<!--\s*⚠️\s*[^>]*-->\s*/gm, '');
    cleaned = cleaned.replace(/<!--\s*自动生成[^>]*-->\s*/gm, '');

    // 清理多余空行（最多保留两个换行）
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n');

    return cleaned.trim() + '\n';
  }

  /**
   * 生成最小化CLAUDE.md模板
   * @returns {string}
   */
  _generateMinimalCLAUDE() {
    const projectName = path.basename(this.downstreamPath);
    const currentDate = new Date().toISOString().split('T')[0];

    return `# ${projectName}

> **项目路径**: \`${this.downstreamPath}\`
> **创建日期**: ${currentDate}

---

## 📌 项目说明

（请在此添加项目说明）

---

## 🎯 项目规范

（请在此添加项目特定的开发规范）

---

## 📚 文档索引

- [Systems文档](./markdown/systems/)
- [项目文档](./markdown/)
- [MODSDK官方文档](./.claude/docs/)

---

> 💡 **提示**：本文档完全由项目维护者管理。
>
> MODSDK开发工作流通过 \`/mc\` 系列命令提供，详见 [.claude/commands/](./.claude/commands/)。
`;
  }

  /**
   * 询问用户输入
   * @param {string} question - 问题
   * @returns {Promise<string>}
   */
  _askUser(question) {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise(resolve => {
      rl.question(question, answer => {
        rl.close();
        resolve(answer.trim());
      });
    });
  }
}

module.exports = { MigrationV18 };
