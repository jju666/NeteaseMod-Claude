/**
 * 覆盖层冲突合并工具
 * 负责检测markdown/core/中的文件与上游更新的冲突，并提供合并选项
 */

const fs = require('fs-extra');
const path = require('path');
const readline = require('readline');
const { VersionChecker } = require('./version-checker');

class OverrideMergeTool {
  constructor(upstreamPath, downstreamPath) {
    this.upstreamPath = upstreamPath;
    this.downstreamPath = downstreamPath;
    this.versionChecker = new VersionChecker(upstreamPath, downstreamPath);
  }

  /**
   * 执行冲突检测和合并
   */
  async run() {
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🔀 覆盖层冲突合并工具');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    // 1. 检测冲突
    const conflicts = await this.versionChecker.detectOverrideConflicts();

    if (conflicts.length === 0) {
      console.log('✅ 未发现冲突，所有覆盖层文件都是最新的\n');
      return;
    }

    console.log(`⚠️  发现 ${conflicts.length} 个文件的上游版本已更新:\n`);

    // 2. 逐个处理冲突
    for (const conflict of conflicts) {
      await this._handleConflict(conflict);
    }

    console.log('\n✅ 冲突处理完成\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  }

  /**
   * 处理单个冲突
   */
  async _handleConflict(conflict) {
    console.log(`\n📄 文件: ${conflict.file}`);
    console.log(`   路径: ${conflict.overridePath}`);
    console.log(`   说明: ${conflict.description}\n`);

    // 显示差异统计
    const diffStats = this._getDiffStats(conflict);
    console.log(`   差异: ${diffStats}\n`);

    // 提供选项
    console.log('   请选择操作:');
    console.log('   1) 查看详细差异 (diff)');
    console.log('   2) 使用上游版本覆盖 (接受上游更新)');
    console.log('   3) 保留当前版本 (忽略上游更新)');
    console.log('   4) 手动合并 (生成合并文件)');
    console.log('   5) 跳过此文件\n');

    const choice = await this._prompt('   选择 [1-5]: ');

    switch (choice.trim()) {
      case '1':
        await this._showDiff(conflict);
        // 重新显示选项
        await this._handleConflict(conflict);
        break;

      case '2':
        await this._useUpstream(conflict);
        break;

      case '3':
        await this._keepOverride(conflict);
        break;

      case '4':
        await this._createMergeFile(conflict);
        break;

      case '5':
        console.log('   ⏭️  跳过\n');
        break;

      default:
        console.log('   ❌ 无效选择，跳过\n');
        break;
    }
  }

  /**
   * 显示详细差异
   */
  async _showDiff(conflict) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 文件差异');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    const overrideContent = fs.readFileSync(conflict.overridePath, 'utf-8').split('\n');
    const upstreamContent = fs.readFileSync(conflict.upstreamPath, 'utf-8').split('\n');

    // 简单的逐行对比
    const maxLines = Math.max(overrideContent.length, upstreamContent.length);
    let diffCount = 0;

    for (let i = 0; i < Math.min(maxLines, 50); i++) { // 只显示前50行
      const overrideLine = overrideContent[i] || '';
      const upstreamLine = upstreamContent[i] || '';

      if (overrideLine !== upstreamLine) {
        diffCount++;
        console.log(`行 ${i + 1}:`);
        console.log(`  - [当前] ${overrideLine.substring(0, 80)}`);
        console.log(`  + [上游] ${upstreamLine.substring(0, 80)}\n`);
      }
    }

    if (maxLines > 50) {
      console.log(`... (还有 ${maxLines - 50} 行未显示)\n`);
    }

    console.log(`总共 ${diffCount} 处差异\n`);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  }

  /**
   * 使用上游版本覆盖
   */
  async _useUpstream(conflict) {
    // 备份当前覆盖层文件
    const backupPath = conflict.overridePath + '.backup-' + Date.now();
    fs.copyFileSync(conflict.overridePath, backupPath);

    // 复制上游版本
    fs.copyFileSync(conflict.upstreamPath, conflict.overridePath);

    console.log(`   ✅ 已使用上游版本覆盖`);
    console.log(`   📦 旧版本已备份: ${path.basename(backupPath)}\n`);

    // 更新manifest的baselineHash
    this._updateBaselineHash(conflict.file, conflict.newBaselineHash);
  }

  /**
   * 保留当前版本
   */
  async _keepOverride(conflict) {
    console.log(`   ✅ 保留当前版本（覆盖层）\n`);

    // 更新manifest的baselineHash（标记为已处理）
    this._updateBaselineHash(conflict.file, conflict.newBaselineHash);
  }

  /**
   * 创建合并文件
   */
  async _createMergeFile(conflict) {
    const mergePath = conflict.overridePath + '.merge';

    // 读取两个版本
    const overrideContent = fs.readFileSync(conflict.overridePath, 'utf-8');
    const upstreamContent = fs.readFileSync(conflict.upstreamPath, 'utf-8');

    // 创建合并文件（类似Git冲突标记）
    const mergeContent = `
<<<<<<< 当前版本 (markdown/core/${conflict.file})
${overrideContent}
=======
>>>>>>> 上游版本 (.claude/core-docs/${conflict.file})
${upstreamContent}
<<<<<<< END

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 合并指南
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 手动编辑此文件，合并两个版本的内容
2. 删除冲突标记 (<<<<<<< / ======= / >>>>>>>)
3. 保存为 ${conflict.file}
4. 删除此 .merge 文件

合并建议:
- 保留项目特定的定制内容
- 采纳上游的新增功能和修复
- 确保文档结构和链接正确
`.trim();

    fs.writeFileSync(mergePath, mergeContent, 'utf-8');

    console.log(`   ✅ 已生成合并文件: ${path.basename(mergePath)}`);
    console.log(`   📝 请手动编辑该文件并完成合并\n`);
  }

  /**
   * 获取差异统计
   */
  _getDiffStats(conflict) {
    try {
      const overrideContent = fs.readFileSync(conflict.overridePath, 'utf-8');
      const upstreamContent = fs.readFileSync(conflict.upstreamPath, 'utf-8');

      const overrideLines = overrideContent.split('\n').length;
      const upstreamLines = upstreamContent.split('\n').length;
      const sizeDiff = upstreamContent.length - overrideContent.length;

      return `${overrideLines}行 → ${upstreamLines}行, 大小变化: ${sizeDiff > 0 ? '+' : ''}${sizeDiff}字节`;
    } catch (err) {
      return '无法计算';
    }
  }

  /**
   * 更新manifest中的baselineHash
   */
  _updateBaselineHash(filename, newHash) {
    const manifest = this.versionChecker.readManifest();

    if (!manifest.baselineHashes) {
      manifest.baselineHashes = {};
    }

    manifest.baselineHashes[filename] = newHash;
    this.versionChecker.writeManifest(manifest);
  }

  /**
   * 交互式输入提示
   */
  _prompt(question) {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    return new Promise(resolve => {
      rl.question(question, answer => {
        rl.close();
        resolve(answer);
      });
    });
  }
}

/**
 * 命令行入口
 */
async function main() {
  const downstreamPath = process.cwd();

  // 查找全局工作流目录
  const upstreamPath = process.env.NETEASE_CLAUDE_HOME ||
                       path.join(require('os').homedir(), '.claude-modsdk-workflow');

  if (!fs.existsSync(upstreamPath)) {
    console.error('❌ 错误: 未找到全局工作流目录');
    console.error('请先运行: npm run install-global');
    process.exit(1);
  }

  const tool = new OverrideMergeTool(upstreamPath, downstreamPath);
  await tool.run();
}

// 如果直接运行此脚本
if (require.main === module) {
  main().catch(err => {
    console.error('❌ 执行失败:', err.message);
    process.exit(1);
  });
}

module.exports = { OverrideMergeTool };
