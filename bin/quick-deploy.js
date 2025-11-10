#!/usr/bin/env node
/**
 * 快速部署脚本
 * 在目标MODSDK项目中创建 /initmc 命令
 */

const fs = require('fs');
const path = require('path');
const os = require('os');

const WORKFLOW_HOME = path.join(os.homedir(), '.claude-modsdk-workflow');
const CURRENT_DIR = process.cwd();
const IS_WINDOWS = process.platform === 'win32';

/**
 * 检测项目提示（不强制）
 * @returns {Array<string>} 检测到的项目特征
 */
function detectProjectHints() {
  const hints = [];

  // 查找 modMain.py（向上3层）
  if (findFileShallow(CURRENT_DIR, 'modMain.py', 3)) {
    hints.push('modMain.py');
  }

  // 检查 behavior_packs/（网易地图）
  if (fs.existsSync(path.join(CURRENT_DIR, 'behavior_packs'))) {
    hints.push('behavior_packs/');
  }

  // 检查 deploy.json（Apollo）
  if (fs.existsSync(path.join(CURRENT_DIR, 'deploy.json'))) {
    hints.push('deploy.json');
  }

  // 检查 .mcs/（网易开发工具）
  if (fs.existsSync(path.join(CURRENT_DIR, '.mcs'))) {
    hints.push('.mcs/');
  }

  // 检查是否有 .py 文件
  try {
    const files = fs.readdirSync(CURRENT_DIR);
    const hasPythonFiles = files.some(f => f.endsWith('.py'));
    if (hasPythonFiles) {
      hints.push('Python文件');
    }
  } catch (err) {
    // 忽略读取错误
  }

  return hints;
}

/**
 * 浅层查找文件（向上查找N层）
 * @param {string} dir - 起始目录
 * @param {string} filename - 文件名
 * @param {number} maxDepth - 最大深度
 * @returns {boolean}
 */
function findFileShallow(dir, filename, maxDepth = 3) {
  for (let i = 0; i < maxDepth; i++) {
    if (fs.existsSync(path.join(dir, filename))) {
      return true;
    }
    const parentDir = path.dirname(dir);
    if (parentDir === dir) break; // 到达根目录
    dir = parentDir;
  }
  return false;
}

/**
 * 创建目录（如果不存在）
 */
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * 复制单个命令文件
 * @param {string} commandName - 命令名称（不含.md扩展名）
 * @returns {boolean} 是否成功
 */
function copyCommandFile(commandName) {
  const srcPath = path.join(WORKFLOW_HOME, '.claude', 'commands', `${commandName}.md`);
  const destPath = path.join(CURRENT_DIR, '.claude', 'commands', `${commandName}.md`);

  if (!fs.existsSync(srcPath)) {
    console.error(`❌ 错误: 缺少 ${commandName}.md`);
    return false;
  }

  // Windows: 复制文件（避免符号链接权限问题）
  if (IS_WINDOWS) {
    fs.copyFileSync(srcPath, destPath);
  } else {
    // Unix: 创建符号链接
    if (fs.existsSync(destPath)) {
      fs.unlinkSync(destPath);
    }
    fs.symlinkSync(srcPath, destPath);
  }

  console.log(`✅ 已复制 ${commandName}.md`);
  return true;
}

/**
 * 部署所有命令文件
 * @returns {number} 成功部署的命令数量
 */
function deployCommands() {
  const commandsDir = path.join(CURRENT_DIR, '.claude', 'commands');
  ensureDir(commandsDir);

  // 检查全局工作流是否安装
  const globalCommandsDir = path.join(WORKFLOW_HOME, '.claude', 'commands');
  if (!fs.existsSync(globalCommandsDir)) {
    console.error('❌ 错误: 全局工作流未安装');
    console.error('   请先运行: npm run install-global');
    process.exit(1);
  }

  const commands = ['initmc', 'cc', 'enhance-docs', 'validate-docs'];
  let successCount = 0;

  for (const cmd of commands) {
    if (copyCommandFile(cmd)) {
      successCount++;
    }
  }

  return successCount;
}

/**
 * 创建轻量级 CLAUDE.md（如果不存在）
 */
function createLightweightCLAUDE() {
  const claudePath = path.join(CURRENT_DIR, 'CLAUDE.md');

  if (fs.existsSync(claudePath)) {
    console.log('ℹ️  CLAUDE.md 已存在，跳过创建');
    return;
  }

  const today = new Date().toISOString().split('T')[0];

  const content = `# CLAUDE.md

> 🤖 **MODSDK AI辅助工作流 - 轻量级配置**
>
> 已就绪！使用 \`/cc\` 命令开始开发。

---

## 🚀 快速开始

### 核心命令

\`\`\`bash
# 最常用：快速任务执行器
/cc "创建一个玩家加入事件监听System"
/cc "修复System初始化错误"
/cc "搜索 双端通信实现"

# 文档管理
/enhance-docs       # 批量补充文档
/validate-docs      # 验证文档完整性

# 可选：生成完整文档
/initmc            # 生成完整的markdown/文档库和项目分析
\`\`\`

---

## 📚 工作流程

使用 \`/cc\` 命令时，AI会自动：
1. **理解任务** - 分析任务类型和复杂度
2. **查阅文档** - 搜索相关开发规范和已知问题
3. **执行收尾** - 实施方案并更新文档

---

## ⚠️ CRITICAL规范（必读）

### 1. 双端隔离原则
- ❌ 禁止在服务端GetSystem获取客户端系统
- ✅ 使用 NotifyToClient/NotifyToServer 跨端通信

### 2. System生命周期
- ❌ 禁止在 __init__ 中调用 GetComponent/GetEntity
- ✅ 在 __init__ 中手动调用 self.Create()
- ✅ 在 Create() 中初始化组件和事件

### 3. EventData序列化
- ❌ 禁止使用 tuple 类型
- ✅ 使用 list、dict、基础类型

---

## 📖 更多信息

运行 \`/initmc\` 生成完整文档：
- 开发规范（防止90%错误）
- 问题排查（已知问题解决）
- 系统文档（每个System的详细文档）
- AI辅助文档（工作流详解）

---

_轻量级配置 | 创建于: ${today} | 运行 /initmc 获取完整文档_
`;

  fs.writeFileSync(claudePath, content, 'utf8');
  console.log('✅ 已创建轻量级 CLAUDE.md');
}

/**
 * 创建 markdown/ 目录和占位符文件
 */
function createMarkdownStub() {
  const mdDir = path.join(CURRENT_DIR, 'markdown');

  if (fs.existsSync(mdDir)) {
    console.log('ℹ️  markdown/ 目录已存在，跳过创建');
    return;
  }

  fs.mkdirSync(mdDir, { recursive: true });

  // 创建文档待补充清单.md占位符
  const checklistContent = `# 文档待补充清单

> 运行 \`/initmc\` 生成完整的文档结构和待补充清单。

## 当前状态

⏳ 等待运行 \`/initmc\` 分析项目...

## 功能说明

\`/initmc\` 会：
1. 扫描项目中的所有Systems
2. 分析代码结构和复杂度
3. 生成系统文档（markdown/systems/）
4. 创建详细的文档待补充清单

## 快速开始

\`\`\`bash
# 在Claude Code中运行
/initmc

# 生成后可以使用
/enhance-docs      # 批量补充文档
/validate-docs     # 验证文档完整性
\`\`\`

---

_占位符文件 | 运行 /initmc 生成完整清单_
`;

  fs.writeFileSync(
    path.join(mdDir, '文档待补充清单.md'),
    checklistContent,
    'utf8'
  );

  console.log('✅ 已创建 markdown/ 目录占位符');
}

/**
 * 主函数
 */
function main() {
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('📦 MODSDK工作流 - 快速部署');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  // 检测项目特征（提示但不阻止）
  const projectHints = detectProjectHints();

  console.log(`📂 当前目录: ${path.basename(CURRENT_DIR)}`);

  if (projectHints.length > 0) {
    console.log(`✅ 检测到: ${projectHints.join(', ')}`);
    console.log('');
  } else {
    console.log('ℹ️  提示: 未检测到常见MODSDK特征');
    console.log('   (modMain.py, behavior_packs/, deploy.json 等)');
    console.log('   如果这是MODSDK项目，可以继续部署');
    console.log('');
  }

  // 检查全局安装
  if (!fs.existsSync(WORKFLOW_HOME)) {
    console.error('❌ 错误: 全局工作流未安装');
    console.error('   请先运行全局安装:');
    console.error('   cd <工作流生成器目录>');
    console.error('   npm run install-global');
    process.exit(1);
  }

  console.log(`✅ 全局工作流已安装: ${WORKFLOW_HOME}\n`);

  // 1. 部署命令文件
  console.log('📍 步骤1：部署命令文件...\n');
  const count = deployCommands();

  // 2. 创建轻量级 CLAUDE.md
  console.log('\n📍 步骤2：创建基础配置...\n');
  createLightweightCLAUDE();

  // 3. 创建 markdown/ 占位符
  console.log('\n📍 步骤3：创建文档占位符...\n');
  createMarkdownStub();

  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  console.log('✅ 部署完成！');
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

  console.log('📊 部署统计:');
  console.log(`   命令文件: ${count}/4 个`);
  console.log('   配置文件: CLAUDE.md ✅');
  console.log('   文档目录: markdown/ ✅\n');

  console.log('🎯 可用命令（重启Claude Code后生效）:');
  console.log('   /cc <任务描述>   - 快速任务执行器 ⭐');
  console.log('   /enhance-docs     - 批量补充文档');
  console.log('   /validate-docs    - 验证文档完整性');
  console.log('   /initmc           - 生成完整文档（可选）\n');

  console.log('📝 使用说明:');
  console.log('   1. 重启Claude Code');
  console.log('   2. 直接使用 /cc 开始开发（推荐）');
  console.log('   3. 或运行 /initmc 生成完整文档（可选）\n');

  console.log('💡 提示:');
  console.log('   - /cc 命令已包含核心开发规范，可直接使用');
  console.log('   - /initmc 会生成详细的系统文档和分析报告');
  console.log('   - 首次运行 /initmc 需要3-15分钟');
}

// 运行
main();
