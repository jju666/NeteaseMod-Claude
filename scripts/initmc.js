#!/usr/bin/env node

/**
 * MODSDK 工作流部署脚本
 *
 * 功能：在 MODSDK 项目目录中部署 Claude Code 工作流
 *
 * 使用方式：
 *   1. 在 MODSDK 项目根目录打开 cmd
 *   2. 输入：initmc
 *   3. 等待部署完成
 *
 * 作者：Claude Code Workflow
 * 版本：2.0.0
 */

const fs = require('fs-extra');
const path = require('path');
const os = require('os');

// ANSI 颜色代码
const colors = {
  reset: '\x1b[0m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m'
};

function log(message, color = 'reset') {
  console.log(`${colors[color]}${message}${colors.reset}`);
}

function error(message) {
  log(`❌ 错误: ${message}`, 'red');
}

function success(message) {
  log(`✅ ${message}`, 'green');
}

function info(message) {
  log(`ℹ️  ${message}`, 'cyan');
}

function warning(message) {
  log(`⚠️  ${message}`, 'yellow');
}

/**
 * 检测全局工作流目录
 */
function detectGlobalWorkflowDir() {
  // 方法1: 默认位置
  const defaultDir = path.join(os.homedir(), '.claude-modsdk-workflow');
  if (fs.existsSync(path.join(defaultDir, 'CLAUDE.md'))) {
    return defaultDir;
  }

  // 方法2: 环境变量
  if (process.env.CLAUDE_WORKFLOW_ROOT) {
    const envDir = process.env.CLAUDE_WORKFLOW_ROOT;
    if (fs.existsSync(path.join(envDir, 'CLAUDE.md'))) {
      return envDir;
    }
  }

  return null;
}

/**
 * 检测manifest.json是否为behavior pack
 */
function isBehaviorPack(manifestPath) {
  try {
    const content = fs.readFileSync(manifestPath, 'utf-8');
    const manifest = JSON.parse(content);

    // 检查modules中是否包含data类型（behavior pack特征）
    if (manifest.modules && Array.isArray(manifest.modules)) {
      return manifest.modules.some(module => module.type === 'data');
    }
    return false;
  } catch (err) {
    return false;
  }
}

/**
 * 检测单个目录的MODSDK特征
 * @returns {Object|null} { feature: string, path: string } 或 null
 */
function detectModSDKFeatures(dir) {
  // 1. 排除工作流项目本身（更严格的检测）
  const hasCLAUDE = fs.existsSync(path.join(dir, 'CLAUDE.md'));
  const hasInitmc = fs.existsSync(path.join(dir, '.claude', 'commands', 'initmc.md'));
  const hasPackageJson = fs.existsSync(path.join(dir, 'package.json'));
  const hasBinDir = fs.existsSync(path.join(dir, 'bin', 'initmc.js'));
  const hasScriptsDir = fs.existsSync(path.join(dir, 'scripts', 'initmc.js'));

  // 只有同时满足以下条件才是工作流项目：
  // - 有 CLAUDE.md 和 .claude/commands/initmc.md
  // - 有 package.json（工作流项目特征）
  // - 有 bin/initmc.js 或 scripts/initmc.js（工作流项目核心文件）
  if (hasCLAUDE && hasInitmc && hasPackageJson && (hasBinDir || hasScriptsDir)) {
    return null;
  }

  // 2. 检测modMain.py（最高优先级）
  const modMainPath = path.join(dir, 'modMain.py');
  if (fs.existsSync(modMainPath)) {
    return { feature: 'modMain.py', path: modMainPath };
  }

  // 3. 检测behavior pack的manifest.json
  const manifestPath = path.join(dir, 'manifest.json');
  if (fs.existsSync(manifestPath) && isBehaviorPack(manifestPath)) {
    return { feature: 'manifest.json (behavior pack)', path: manifestPath };
  }

  // 4. 检测网易地图特征
  const worldBPPath = path.join(dir, 'world_behavior_packs.json');
  if (fs.existsSync(worldBPPath)) {
    return { feature: 'world_behavior_packs.json', path: worldBPPath };
  }

  const studioPath = path.join(dir, 'studio.json');
  if (fs.existsSync(studioPath)) {
    return { feature: 'studio.json', path: studioPath };
  }

  return null;
}

/**
 * 递归搜索所有符合条件的MODSDK项目
 */
function findModSDKProjects(startDir, maxDepth = 10, currentDepth = 0) {
  const results = [];
  const excludeDirs = ['node_modules', '.git', '__pycache__', '.venv', 'venv',
                       'dist', 'build', '.cache', '.temp', 'temp'];

  if (currentDepth > maxDepth) {
    return results;
  }

  try {
    const entries = fs.readdirSync(startDir, { withFileTypes: true });

    for (const entry of entries) {
      if (!entry.isDirectory()) continue;
      if (excludeDirs.includes(entry.name)) continue;

      const fullPath = path.join(startDir, entry.name);

      // 检测当前目录特征
      const features = detectModSDKFeatures(fullPath);
      if (features) {
        results.push({ dir: fullPath, ...features });
      }

      // 递归搜索子目录
      const subResults = findModSDKProjects(fullPath, maxDepth, currentDepth + 1);
      results.push(...subResults);
    }
  } catch (err) {
    // 忽略无权限访问的目录
  }

  return results;
}

/**
 * 推断项目根目录
 */
function inferProjectRoot(featurePath, feature) {
  let dir = path.dirname(featurePath);

  // 1. 如果是modMain.py，向上查找最近的manifest.json
  if (feature === 'modMain.py') {
    let current = dir;
    for (let i = 0; i < 5; i++) {
      const manifestPath = path.join(current, 'manifest.json');
      if (fs.existsSync(manifestPath) && isBehaviorPack(manifestPath)) {
        // 继续向上查找behavior_packs目录
        let parent = path.dirname(current);
        if (path.basename(parent) === 'behavior_packs' ||
            path.basename(parent) === 'development_behavior_packs') {
          return path.dirname(parent); // 返回项目根目录
        }
        return current; // 返回behavior pack目录
      }
      const parent = path.dirname(current);
      if (parent === current) break;
      current = parent;
    }
    return dir; // 找不到manifest.json，返回modMain.py所在目录
  }

  // 2. 如果是manifest.json，向上查找behavior_packs父目录
  if (feature.includes('manifest.json')) {
    const parent = path.dirname(dir);
    if (path.basename(parent) === 'behavior_packs' ||
        path.basename(parent) === 'development_behavior_packs') {
      return path.dirname(parent);
    }
    return dir;
  }

  // 3. 如果是网易地图特征文件，返回其所在目录
  return dir;
}

/**
 * 检测当前项目类型（新版本）
 * @returns {Object} { type: 'modsdk'|'workflow'|'unknown', projectDir: string, feature?: string }
 */
function detectProjectType(projectDir) {
  // 1. 检查是否为工作流项目（使用严格检测）
  const hasCLAUDE = fs.existsSync(path.join(projectDir, 'CLAUDE.md'));
  const hasInitmc = fs.existsSync(path.join(projectDir, '.claude', 'commands', 'initmc.md'));
  const hasPackageJson = fs.existsSync(path.join(projectDir, 'package.json'));
  const hasBinDir = fs.existsSync(path.join(projectDir, 'bin', 'initmc.js'));
  const hasScriptsDir = fs.existsSync(path.join(projectDir, 'scripts', 'initmc.js'));

  // 只有同时满足所有条件才是工作流项目
  if (hasCLAUDE && hasInitmc && hasPackageJson && (hasBinDir || hasScriptsDir)) {
    return { type: 'workflow', projectDir };
  }

  // 2. 检测当前目录特征
  const currentFeatures = detectModSDKFeatures(projectDir);
  if (currentFeatures) {
    const root = inferProjectRoot(currentFeatures.path, currentFeatures.feature);
    return {
      type: 'modsdk',
      projectDir: root,
      feature: currentFeatures.feature,
      featurePath: currentFeatures.path
    };
  }

  // 3. 递归搜索子目录
  info('当前目录未检测到MODSDK特征，开始搜索子目录...');
  const candidates = findModSDKProjects(projectDir);

  if (candidates.length === 0) {
    return { type: 'unknown', projectDir };
  }

  // 4. 处理搜索结果
  if (candidates.length === 1) {
    const root = inferProjectRoot(candidates[0].path, candidates[0].feature);
    success(`找到项目: ${path.relative(projectDir, root)}`);
    info(`检测依据: ${candidates[0].feature}`);
    return {
      type: 'modsdk',
      projectDir: root,
      feature: candidates[0].feature,
      featurePath: candidates[0].path
    };
  }

  // 5. 多个候选项目，需要推断最佳根目录
  const roots = new Map();
  candidates.forEach(candidate => {
    const root = inferProjectRoot(candidate.path, candidate.feature);
    if (!roots.has(root)) {
      roots.set(root, []);
    }
    roots.get(root).push(candidate);
  });

  if (roots.size === 1) {
    const root = Array.from(roots.keys())[0];
    const features = roots.get(root);
    success(`找到项目: ${path.relative(projectDir, root)}`);
    info(`检测依据: ${features.map(f => f.feature).join(', ')}`);
    return {
      type: 'modsdk',
      projectDir: root,
      feature: features[0].feature,
      featurePath: features[0].path
    };
  }

  // 6. 多个不同的项目根目录
  warning(`找到 ${roots.size} 个候选项目:`);
  Array.from(roots.keys()).forEach((root, idx) => {
    const features = roots.get(root);
    console.log(`  ${idx + 1}. ${path.relative(projectDir, root)}`);
    console.log(`     特征: ${features.map(f => f.feature).join(', ')}`);
  });
  console.log('');
  error('请在具体的项目目录中执行 initmc');
  return { type: 'multiple', projectDir, candidates: Array.from(roots.keys()) };
}

/**
 * 复制文件并验证（带备份保护）
 */
function copyFileWithValidation(src, dest, minSize = 1000, enableBackup = true) {
  const fileName = path.basename(dest);

  try {
    // 确保目标目录存在
    fs.ensureDirSync(path.dirname(dest));

    // 如果目标文件已存在，且启用了备份保护
    if (enableBackup && fs.existsSync(dest)) {
      // 只备份用户可能修改的文件（命令文件）
      const isCommandFile = dest.includes('.claude/commands/');
      if (isCommandFile) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
        const backupPath = `${dest}.backup.${timestamp}`;
        fs.copyFileSync(dest, backupPath);
        log(`  📦 备份 ${fileName}: ${path.basename(backupPath)}`, 'yellow');
      }
    }

    // 复制文件
    fs.copyFileSync(src, dest);

    // 验证文件大小
    const stat = fs.statSync(dest);
    if (stat.size < minSize) {
      throw new Error(`文件过小 (${stat.size} bytes)`);
    }

    log(`  ✅ ${fileName} - ${(stat.size / 1024).toFixed(1)} KB`, 'green');
    return true;
  } catch (err) {
    error(`  复制 ${fileName} 失败: ${err.message}`);
    return false;
  }
}

/**
 * 生成定制化的 cc.md
 */
function generateCustomizedCC(globalDir, projectDir) {
  const templatePath = path.join(globalDir, '.claude', 'commands', 'cc.md');

  if (!fs.existsSync(templatePath)) {
    error('找不到 cc.md 模板文件');
    return false;
  }

  try {
    let content = fs.readFileSync(templatePath, 'utf-8');

    // 替换项目路径占位符
    // 注意: Windows 路径需要转换为正斜杠
    const normalizedPath = projectDir.replace(/\\/g, '/');
    content = content.replace(/D:\/EcWork\/NetEaseMapECBedWars_备份/g, normalizedPath);

    // 写入目标文件
    const destPath = path.join(projectDir, '.claude', 'commands', 'cc.md');
    fs.ensureDirSync(path.dirname(destPath));
    fs.writeFileSync(destPath, content, 'utf-8');

    const stat = fs.statSync(destPath);
    log(`  ✅ cc.md - ${(stat.size / 1024).toFixed(1)} KB (定制化)`, 'green');
    return true;
  } catch (err) {
    error(`生成 cc.md 失败: ${err.message}`);
    return false;
  }
}

/**
 * 从工作流模板中提取纯工作流内容
 */
function extractWorkflowContent(globalDir) {
  const templatePath = path.join(globalDir, '.claude', 'workflow.template.md');

  if (fs.existsSync(templatePath)) {
    // 优先使用 workflow.template.md
    return fs.readFileSync(templatePath, 'utf-8');
  }

  // 降级：从 CLAUDE.md 中提取（向后兼容）
  const claudePath = path.join(globalDir, 'CLAUDE.md');
  if (!fs.existsSync(claudePath)) {
    throw new Error('找不到工作流模板文件');
  }

  let content = fs.readFileSync(claudePath, 'utf-8');

  // 移除文件头和元数据，只保留从"AI助手身份定位"开始的内容
  const match = content.match(/## 🎯 AI助手身份定位[\s\S]*/);
  if (match) {
    content = match[0];
    // 移除版本信息章节
    content = content.replace(/## 📝 版本信息[\s\S]*$/, '');
    // 移除尾部"记住"章节后的空行
    content = content.replace(/\n+$/, '');
  }

  return content.trim();
}

/**
 * 生成全新的内联式 CLAUDE.md
 */
function generateNewCLAUDE({ projectRoot, currentDate, workflowContent, version }) {
  return `# CLAUDE.md

> 🤖 **基于 MODSDK 工作流 v${version}**
>
> 本文件由工作流自动生成和管理，请勿删除标记行。

---

<!-- ==================== 用户配置区 START ==================== -->
<!-- 此区域可自由编辑，升级时会保留 -->

## 📌 项目配置

- **项目路径**: ${projectRoot}
- **项目类型**: MODSDK 行为包
- **开发阶段**: 开发中
- **最后更新**: ${currentDate}

---
<!-- ==================== 用户配置区 END ==================== -->

<!-- ==================== 工作流内容 START v${version} ==================== -->
<!-- ⚠️ 警告：以下内容由工作流管理，请勿手动修改！升级时会自动替换。 -->
<!-- 如需自定义规范，请在"项目扩展区"添加 -->

${workflowContent}

<!-- ==================== 工作流内容 END v${version} ==================== -->

<!-- ==================== 项目扩展区 START ==================== -->
<!-- 此区域可自由编辑，升级时会保留 -->

## 🎯 项目特定规范

<!-- 在此添加项目特定的开发规范、约定、注意事项等 -->

---

## 🔧 扩展配置

<!-- 可选：覆盖工作流默认行为 -->

---
<!-- ==================== 项目扩展区 END ==================== -->
`;
}

/**
 * 升级内联式 CLAUDE.md（精确替换工作流区域）
 */
function upgradeInlineCLAUDE({ existingContent, newWorkflowContent, newVersion, currentDate }) {
  // 正则匹配工作流区域（支持任意版本号）
  const workflowRegex = /<!-- ==================== 工作流内容 START v[\d.]+ ====================.*?-->[\s\S]*?<!-- ==================== 工作流内容 END v[\d.]+ ====================.*?-->/;

  const newWorkflowSection = `<!-- ==================== 工作流内容 START v${newVersion} ==================== -->
<!-- ⚠️ 警告：以下内容由工作流管理，请勿手动修改！升级时会自动替换。 -->
<!-- 如需自定义规范，请在"项目扩展区"添加 -->

${newWorkflowContent}

<!-- ==================== 工作流内容 END v${newVersion} ==================== -->`;

  // 替换工作流区域，保留用户配置区和扩展区
  let updated = existingContent.replace(workflowRegex, newWorkflowSection);

  // 更新日期（如果用户配置区包含"最后更新"字段）
  updated = updated.replace(
    /(- \*\*最后更新\*\*: ).+/,
    `$1${currentDate}`
  );

  // 更新顶部版本标记
  updated = updated.replace(
    /(> 🤖 \*\*基于 MODSDK 工作流 v)[\d.]+(\*\*)/,
    `$1${newVersion}$2`
  );

  return updated;
}

/**
 * 将旧版 CLAUDE.md 迁移为内联式（智能提取用户内容）
 */
function migrateToInline({ oldContent, workflowContent, projectRoot, currentDate, version }) {
  // 提取项目路径（如果存在）
  const pathMatch = oldContent.match(/- \*\*项目根目录\*\*:\s*`(.+?)`/);
  const extractedPath = pathMatch ? pathMatch[1] : projectRoot;

  // 生成新内容（暂时不尝试智能提取用户内容，因为旧版结构复杂）
  const migratedContent = generateNewCLAUDE({
    projectRoot: extractedPath,
    currentDate: currentDate,
    workflowContent: workflowContent,
    version: version
  });

  // 在扩展区添加迁移提示
  return migratedContent.replace(
    '<!-- 在此添加项目特定的开发规范、约定、注意事项等 -->',
    `<!-- 在此添加项目特定的开发规范、约定、注意事项等 -->

<!-- ⚠️ 迁移提示：-->
<!-- 您的旧版 CLAUDE.md 已自动备份为 CLAUDE.md.backup.${currentDate} -->
<!-- 如旧版中有自定义内容，请从备份中提取并粘贴到此处 -->
<!-- 详见迁移指南：markdown/迁移指南-v15.0.md -->`
  );
}

/**
 * 更新版本追踪文件
 */
function updateVersionTracking(projectDir, version, isNewInstall, oldVersion = null) {
  const versionFilePath = path.join(projectDir, '.claude', 'workflow-version.json');
  const now = new Date().toISOString();
  const today = now.split('T')[0];

  let versionData;

  if (isNewInstall || !fs.existsSync(versionFilePath)) {
    // 新安装
    versionData = {
      version: version,
      installedAt: now,
      lastUpdatedAt: now,
      changes: [
        {
          version: version,
          date: today,
          description: '初始安装内联式架构'
        }
      ]
    };
  } else {
    // 升级
    versionData = JSON.parse(fs.readFileSync(versionFilePath, 'utf-8'));
    const previousVersion = oldVersion || versionData.version;

    versionData.version = version;
    versionData.lastUpdatedAt = now;
    versionData.changes.unshift({
      version: version,
      date: today,
      description: `从 v${previousVersion} 升级`,
      previousVersion: previousVersion
    });

    // 只保留最近10次变更记录
    if (versionData.changes.length > 10) {
      versionData.changes = versionData.changes.slice(0, 10);
    }
  }

  fs.ensureDirSync(path.dirname(versionFilePath));
  fs.writeFileSync(versionFilePath, JSON.stringify(versionData, null, 2), 'utf-8');

  log(`  ✅ 版本追踪: v${version}`, 'green');
}

/**
 * 生成定制化的 CLAUDE.md（重构版 - 内联式架构）
 */
function generateCustomizedCLAUDE(globalDir, projectDir) {
  const destPath = path.join(projectDir, 'CLAUDE.md');
  const currentDate = new Date().toISOString().split('T')[0];
  const normalizedPath = projectDir.replace(/\\/g, '/');
  const version = '15.0'; // 从 package.json 读取的版本号

  let hasBackup = false;
  let isUpgrade = false;
  let needsMigration = false;

  // 提取工作流内容
  let workflowContent;
  try {
    workflowContent = extractWorkflowContent(globalDir);
  } catch (err) {
    error(`提取工作流内容失败: ${err.message}`);
    return { success: false, hasBackup: false, isUpgrade: false };
  }

  // 替换工作流内容中的占位符
  workflowContent = workflowContent.replace(/\{\{PROJECT_ROOT\}\}/g, normalizedPath);

  // 场景1: 文件不存在 → 全新安装
  if (!fs.existsSync(destPath)) {
    const newContent = generateNewCLAUDE({
      projectRoot: normalizedPath,
      currentDate: currentDate,
      workflowContent: workflowContent,
      version: version
    });

    fs.writeFileSync(destPath, newContent, 'utf-8');
    log(`  ✅ CLAUDE.md - ${(fs.statSync(destPath).size / 1024).toFixed(1)} KB (全新创建)`, 'green');

    // 创建版本追踪文件
    updateVersionTracking(projectDir, version, true);

    return { success: true, hasBackup: false, isUpgrade: false, needsMigration: false };
  }

  // 场景2: 文件已存在 → 检测是否为内联式
  const existingContent = fs.readFileSync(destPath, 'utf-8');
  const hasMarkers = existingContent.includes('<!-- ==================== 工作流内容 START');

  if (hasMarkers) {
    // 场景2a: 已经是内联式 → 升级模式（精确替换）
    isUpgrade = true;

    // 提取旧版本号
    const versionMatch = existingContent.match(/<!-- ==================== 工作流内容 START v([\d.]+) ====================/);
    const oldVersion = versionMatch ? versionMatch[1] : '14.x';

    const updatedContent = upgradeInlineCLAUDE({
      existingContent: existingContent,
      newWorkflowContent: workflowContent,
      newVersion: version,
      currentDate: currentDate
    });

    fs.writeFileSync(destPath, updatedContent, 'utf-8');
    log(`  ✅ CLAUDE.md - 升级 v${oldVersion} → v${version}`, 'green');

    // 更新版本追踪文件
    updateVersionTracking(projectDir, version, false, oldVersion);

    return { success: true, hasBackup: false, isUpgrade: true, needsMigration: false };
  }

  // 场景2b: 旧版格式 → 迁移模式（保留用户内容）
  needsMigration = true;

  const timestamp = currentDate;
  const backupPath = path.join(projectDir, `CLAUDE.md.backup.${timestamp}`);
  fs.copyFileSync(destPath, backupPath);
  log(`  📦 备份旧版: ${path.basename(backupPath)}`, 'yellow');
  hasBackup = true;

  const migratedContent = migrateToInline({
    oldContent: existingContent,
    workflowContent: workflowContent,
    projectRoot: normalizedPath,
    currentDate: currentDate,
    version: version
  });

  fs.writeFileSync(destPath, migratedContent, 'utf-8');
  log(`  ⚠️  CLAUDE.md - 迁移到 v${version} (请检查备份)`, 'yellow');

  // 创建版本追踪文件（标记为迁移）
  updateVersionTracking(projectDir, version, false, '14.x');

  return { success: true, hasBackup: true, isUpgrade: false, needsMigration: true };
}

/**
 * 主部署函数
 */
async function deployWorkflow() {
  console.log('');
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan');
  log('  MODSDK 工作流部署工具 v2.0', 'cyan');
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan');
  console.log('');

  // 1. 检测当前目录
  const currentDir = process.cwd();
  info(`当前目录: ${currentDir}`);
  console.log('');

  const detection = detectProjectType(currentDir);

  if (detection.type === 'workflow') {
    error('检测到工作流项目本身');
    console.log('');
    console.log('initmc 命令仅用于在 MODSDK 项目中部署工作流。');
    console.log('当前目录是工作流项目本身，无需部署。');
    console.log('');
    console.log('使用说明:');
    console.log('  1. 在需要部署工作流的 MODSDK 项目根目录打开 cmd');
    console.log('  2. 输入: initmc');
    console.log('  3. 等待部署完成');
    console.log('');
    process.exit(1);
  }

  if (detection.type === 'unknown') {
    error('未找到 MODSDK 项目');
    console.log('');
    console.log('支持的项目类型:');
    console.log('  • 包含 modMain.py 的 MODSDK 项目');
    console.log('  • 包含 behavior pack (manifest.json) 的基岩版项目');
    console.log('  • 包含 world_behavior_packs.json 的网易地图项目');
    console.log('');
    console.log('请在项目目录或其父目录中执行 initmc');
    console.log('');
    process.exit(1);
  }

  if (detection.type === 'multiple') {
    error('找到多个候选项目，请在具体项目目录中执行');
    process.exit(1);
  }

  // 使用检测到的项目根目录
  const projectDir = detection.projectDir;

  success('检测到 MODSDK 项目');
  if (projectDir !== currentDir) {
    info(`项目根目录: ${path.relative(currentDir, projectDir)}`);
  }
  if (detection.feature) {
    info(`检测依据: ${detection.feature}`);
  }
  console.log('');

  // 2. 检测全局工作流目录
  log('🔍 检测全局工作流目录...', 'blue');
  const globalDir = detectGlobalWorkflowDir();

  if (!globalDir) {
    error('找不到全局工作流目录');
    console.log('');
    console.log('可能原因:');
    console.log('  1. 未执行全局安装（npm run install-global）');
    console.log('  2. 环境变量 CLAUDE_WORKFLOW_ROOT 未设置');
    console.log('');
    console.log('解决方案:');
    console.log('  cd <工作流项目目录>');
    console.log('  npm run install-global');
    console.log('');
    process.exit(1);
  }

  success(`找到全局工作流目录: ${globalDir}`);
  console.log('');

  // 3. 复制命令文件
  log('📋 复制命令文件...', 'blue');

  let allSuccess = true;

  allSuccess &= copyFileWithValidation(
    path.join(globalDir, '.claude', 'commands', 'discover.md'),
    path.join(projectDir, '.claude', 'commands', 'discover.md'),
    5000
  );

  allSuccess &= copyFileWithValidation(
    path.join(globalDir, '.claude', 'commands', 'enhance-docs.md'),
    path.join(projectDir, '.claude', 'commands', 'enhance-docs.md'),
    5000
  );

  allSuccess &= copyFileWithValidation(
    path.join(globalDir, '.claude', 'commands', 'validate-docs.md'),
    path.join(projectDir, '.claude', 'commands', 'validate-docs.md'),
    6000
  );

  // 生成定制化 cc.md
  allSuccess &= generateCustomizedCC(globalDir, projectDir);

  console.log('');

  if (!allSuccess) {
    error('命令文件复制失败');
    process.exit(1);
  }

  // 4. 复制通用文档
  log('📚 复制通用文档...', 'blue');

  const docsToCopy = [
    { src: 'markdown/开发规范.md', minSize: 10000 },
    { src: 'markdown/问题排查.md', minSize: 5000 },
    { src: 'markdown/快速开始.md', minSize: 3000 },
    { src: 'markdown/开发指南.md', minSize: 10000 },
    { src: 'markdown/API速查.md', minSize: 3000 },
    { src: 'markdown/MODSDK核心概念.md', minSize: 3000 }
  ];

  docsToCopy.forEach(doc => {
    allSuccess &= copyFileWithValidation(
      path.join(globalDir, doc.src),
      path.join(projectDir, doc.src),
      doc.minSize
    );
  });

  console.log('');

  if (!allSuccess) {
    error('通用文档复制失败');
    process.exit(1);
  }

  // 5. 复制 AI 辅助文档
  log('🤖 复制 AI 辅助文档...', 'blue');

  const aiDocsToCopy = [
    { src: 'markdown/ai/任务类型决策表.md', minSize: 2000 },
    { src: 'markdown/ai/快速通道流程.md', minSize: 2000 },
    { src: 'markdown/ai/上下文管理规范.md', minSize: 2000 }
  ];

  aiDocsToCopy.forEach(doc => {
    allSuccess &= copyFileWithValidation(
      path.join(globalDir, doc.src),
      path.join(projectDir, doc.src),
      doc.minSize
    );
  });

  console.log('');

  if (!allSuccess) {
    error('AI 辅助文档复制失败');
    process.exit(1);
  }

  // 5.5. 复制 lib/ 核心工具库（新增！）
  log('🔧 复制核心工具库...', 'blue');

  const libFiles = [
    { src: 'lib/adaptive-doc-discovery.js', minSize: 3000 },
    { src: 'lib/utils.js', minSize: 500 },
    { src: 'lib/config.js', minSize: 500 },
    { src: 'lib/metadata-schema.js', minSize: 1000 },
    { src: 'lib/indexer.js', minSize: 2000 },
    { src: 'lib/search-engine.js', minSize: 2000 }
  ];

  libFiles.forEach(file => {
    const srcPath = path.join(globalDir, file.src);
    const destPath = path.join(projectDir, file.src);

    // 检查源文件是否存在（某些文件可能可选）
    if (fs.existsSync(srcPath)) {
      allSuccess &= copyFileWithValidation(srcPath, destPath, file.minSize);
    } else {
      warning(`  跳过 ${file.src} (源文件不存在)`);
    }
  });

  console.log('');

  if (!allSuccess) {
    error('核心工具库复制失败');
    process.exit(1);
  }

  // 6. 生成 CLAUDE.md
  log('⚙️  生成定制化配置...', 'blue');
  const claudeResult = generateCustomizedCLAUDE(globalDir, projectDir);
  console.log('');

  if (!claudeResult.success) {
    error('配置生成失败');
    process.exit(1);
  }

  // 7. 创建必要的目录结构
  log('📁 创建目录结构...', 'blue');

  try {
    fs.ensureDirSync(path.join(projectDir, 'tasks'));
    log('  ✅ tasks/', 'green');

    fs.ensureDirSync(path.join(projectDir, 'markdown', 'systems'));
    log('  ✅ markdown/systems/', 'green');

    console.log('');
  } catch (err) {
    error(`创建目录失败: ${err.message}`);
    process.exit(1);
  }

  // 8. 部署官方文档（Git Submodule）
  log('📚 部署官方文档...', 'blue');

  const globalDocsPath = path.join(globalDir, 'docs');
  const projectDocsPath = path.join(projectDir, '.claude', 'docs');

  if (!fs.existsSync(globalDocsPath)) {
    console.log('');
    warning('官方文档未下载，将使用在线查询（WebFetch）');
    info('如需本地文档加速查询，请在工作流目录执行：');
    console.log(`  cd ${globalDir}`);
    console.log('  git submodule update --init --recursive');
    console.log('');
  } else {
    // 检查文档子模块是否完整
    const modsdkWikiPath = path.join(globalDocsPath, 'modsdk-wiki');
    const bedrockWikiPath = path.join(globalDocsPath, 'bedrock-wiki');
    const hasModsdkWiki = fs.existsSync(modsdkWikiPath) && fs.readdirSync(modsdkWikiPath).length > 1;
    const hasBedrockWiki = fs.existsSync(bedrockWikiPath) && fs.readdirSync(bedrockWikiPath).length > 1;

    if (!hasModsdkWiki && !hasBedrockWiki) {
      console.log('');
      warning('官方文档子模块为空，跳过部署');
      info('请执行 git submodule update --init --recursive');
      console.log('');
    } else {
      // 创建软链接（Windows使用junction）
      try {
        // 删除旧的软链接（如果存在）
        if (fs.existsSync(projectDocsPath)) {
          fs.removeSync(projectDocsPath);
        }

        // 创建软链接
        fs.symlinkSync(globalDocsPath, projectDocsPath, 'junction');

        console.log('');
        success('已部署官方文档到 .claude/docs/（软链接）');
        console.log('📁 包含文档：');
        if (hasModsdkWiki) {
          console.log('  - MODSDK Wiki (modsdk-wiki/)');
        }
        if (hasBedrockWiki) {
          console.log('  - Bedrock Wiki (bedrock-wiki/)');
        }
        info('⚡ /cc 指令将优先查询本地文档（速度提升10x）');
        console.log('');
      } catch (err) {
        if (err.code === 'EEXIST') {
          console.log('');
          success('官方文档已存在');
          console.log('');
        } else {
          console.log('');
          warning(`软链接创建失败: ${err.message}`);
          info('将使用在线查询（WebFetch）');
          console.log('');
        }
      }
    }
  }

  // 9. 最终验证
  log('🔍 验证部署结果...', 'blue');

  const filesToVerify = [
    { path: '.claude/commands/cc.md', minSize: 10000 },
    { path: '.claude/commands/discover.md', minSize: 5000 },
    { path: '.claude/commands/enhance-docs.md', minSize: 5000 },
    { path: '.claude/commands/validate-docs.md', minSize: 6000 },
    { path: 'CLAUDE.md', minSize: 10000 },
    { path: 'markdown/开发规范.md', minSize: 10000 },
    { path: 'markdown/问题排查.md', minSize: 5000 },
    { path: 'lib/adaptive-doc-discovery.js', minSize: 3000 }
  ];

  let allValid = true;

  filesToVerify.forEach(file => {
    const filePath = path.join(projectDir, file.path);

    if (!fs.existsSync(filePath)) {
      error(`  ${file.path} - 文件不存在`);
      allValid = false;
      return;
    }

    const stat = fs.statSync(filePath);

    if (stat.size < file.minSize) {
      error(`  ${file.path} - 文件过小 (${stat.size} bytes)`);
      allValid = false;
    } else {
      log(`  ✅ ${file.path} - ${(stat.size / 1024).toFixed(1)} KB`, 'green');
    }
  });

  console.log('');

  if (!allValid) {
    error('部署验证失败');
    console.log('');
    console.log('可能原因:');
    console.log('  1. 全局工作流目录文件损坏');
    console.log('  2. 磁盘空间不足');
    console.log('  3. 文件权限问题');
    console.log('');
    process.exit(1);
  }

  // 9. 输出完成报告
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
  log('  ✅ 核心工作流部署完成！', 'green');
  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'green');
  console.log('');

  console.log('📊 部署内容:');
  console.log('  ✅ 命令文件: 4 个 (/cc, /discover, /validate-docs, /enhance-docs)');
  console.log('  ✅ 通用文档: 6 个 (开发规范.md, 问题排查.md等)');
  console.log('  ✅ AI 文档: 3 个');
  console.log('  ✅ 核心工具: 6 个 (lib/目录)');
  console.log('  ✅ 配置文件: 1 个 (CLAUDE.md)');
  console.log('');
  console.log('💡 备份保护:');
  console.log('  - 已自动备份现有的 CLAUDE.md 和命令文件（如有）');
  console.log('  - 备份文件格式: 文件名.backup.YYYY-MM-DD');
  console.log('  - 通用文档不备份（可随时覆盖）');
  console.log('');

  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan');
  console.log('');
  log('🎯 下一步（重要！）⭐', 'yellow');
  console.log('');
  console.log('请在 Claude Code 中按顺序执行以下命令：');
  console.log('');
  log('步骤1: /discover', 'cyan');
  console.log('  功能: 自适应发现项目结构（5-10秒，零Token）');
  console.log('  - 识别MODSDK官方概念（System、Component）');
  console.log('  - 发现项目自定义模式（State、Preset、Manager等）');
  console.log('  - 生成 .claude/discovered-patterns.json 映射文件');
  console.log('');
  log('步骤2: /validate-docs', 'cyan');
  console.log('  功能: 文档审计与规范化（依赖步骤1的结果）');
  console.log('  - 读取自适应发现结果');
  console.log('  - AI智能推断规范化的中文文档名');
  console.log('  - 检查文档覆盖率');
  console.log('  - 生成文档待补充清单');
  console.log('');

  log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'cyan');
  console.log('');
  console.log('📚 完整工作流（四段式）:');
  console.log('  1. /discover - 自适应发现项目结构（零配置）');
  console.log('  2. /validate-docs - 发现组件并规范化文档结构');
  console.log('  3. /enhance-docs - 批量生成高质量文档内容');
  console.log('  4. /cc "任务描述" - 开发时自动维护文档');
  console.log('');

  // 根据不同场景输出不同提示
  if (claudeResult.needsMigration) {
    // 场景：旧版迁移
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'yellow');
    console.log('');
    log('⚠️  检测到旧版格式，已自动迁移', 'yellow');
    console.log('');
    console.log('您的旧版 CLAUDE.md 已备份，迁移到新版内联式架构。');
    console.log('');
    console.log('📋 如何处理旧版自定义内容：');
    console.log('  1. 查看备份文件：CLAUDE.md.backup.YYYY-MM-DD');
    console.log('  2. 如有自定义内容，复制到新版"项目扩展区"');
    console.log('  3. 详见迁移指南：markdown/迁移指南-v15.0.md');
    console.log('');
    console.log('✨ 新版优势：');
    console.log('  - 零风险升级：用户内容自动保留');
    console.log('  - 精确替换：工作流更新不影响自定义内容');
    console.log('  - 版本追踪：.claude/workflow-version.json');
    console.log('');
    log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', 'yellow');
    console.log('');
  } else if (claudeResult.isUpgrade) {
    // 场景：内联式升级
    info('✅ 升级完成！您的自定义内容已自动保留。');
    console.log('');
  }

  log('🎉 开始体验文档驱动的开发工作流吧！', 'green');
  console.log('');
}

// 执行部署
deployWorkflow().catch(err => {
  console.log('');
  error(`部署过程出现异常: ${err.message}`);
  console.error(err.stack);
  console.log('');
  process.exit(1);
});
