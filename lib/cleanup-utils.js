/**
 * 清理工具模块 (v20.2.12)
 * 负责清理遗留文件和缓存
 */

const fs = require('fs-extra');
const path = require('path');
const os = require('os');

/**
 * 清理遗留的全局命令文件
 * 这些文件由旧版 install-global.js 创建,需要清理
 */
function cleanupLegacyGlobalCommands() {
  const legacyFiles = [
    path.join(os.homedir(), 'initmc.cmd'),
    path.join(os.homedir(), 'modsdk-deploy.cmd'),
    path.join(os.homedir(), 'uninstallmc.cmd')
  ];

  let cleaned = false;
  const cleanedFiles = [];

  for (const file of legacyFiles) {
    if (fs.existsSync(file)) {
      try {
        fs.unlinkSync(file);
        cleanedFiles.push(path.basename(file));
        cleaned = true;
      } catch (err) {
        console.warn(`⚠️  无法删除: ${file} (${err.message})`);
      }
    }
  }

  if (cleaned) {
    console.log('🗑️  清理遗留的全局命令文件:');
    cleanedFiles.forEach(file => console.log(`   ✅ ${file}`));
    console.log('');
  }

  return cleaned;
}

/**
 * 清除所有工作流缓存
 * 用于完全重置部署状态
 *
 * @param {string} targetPath - 目标项目路径
 */
function cleanupAllCaches(targetPath) {
  const cacheFiles = [
    path.join(targetPath, '.claude', 'workflow-manifest.json'),
    path.join(targetPath, '.claude', 'workflow-version.json')
  ];

  let cleaned = false;

  for (const file of cacheFiles) {
    if (fs.existsSync(file)) {
      try {
        fs.unlinkSync(file);
        console.log(`🗑️  已清除缓存: ${path.basename(file)}`);
        cleaned = true;
      } catch (err) {
        console.warn(`⚠️  无法清除缓存: ${file} (${err.message})`);
      }
    }
  }

  if (cleaned) {
    console.log('');
  }

  return cleaned;
}

/**
 * 清理遗留的全局部署目录
 * ~/.claude-modsdk-workflow (已废弃)
 */
function cleanupLegacyGlobalDir() {
  const legacyDir = path.join(os.homedir(), '.claude-modsdk-workflow');

  if (fs.existsSync(legacyDir)) {
    console.log('🗑️  检测到旧版全局部署目录:');
    console.log(`   ${legacyDir}\n`);
    console.log('   建议手动删除以释放空间:');
    console.log(`   rm -rf "${legacyDir}"\n`);
    return true;
  }

  return false;
}

module.exports = {
  cleanupLegacyGlobalCommands,
  cleanupAllCaches,
  cleanupLegacyGlobalDir
};
