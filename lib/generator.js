/**
 * 文档生成器
 * 根据分析报告生成完整的工作流文档
 */

const path = require('path');
const {
  ensureDir,
  replacePlaceholders,
  readFile,
  writeFile,
  normalizePathForMarkdown
} = require('./utils');
const { getTemplatePath, getCurrentDate } = require('./config');

/**
 * 文档生成器
 */
class DocumentGenerator {
  constructor(analysisReport) {
    this.report = analysisReport;
    this.metadata = analysisReport.metadata;
    this.codeStructure = analysisReport.codeStructure;
  }

  /**
   * 生成所有文档到目标项目
   * @param {string} targetPath - 目标项目路径
   */
  async generateAll(targetPath) {
    console.log('[生成器] 开始生成文档...');

    // 创建基础目录结构
    this._createDirectoryStructure(targetPath);

    // Layer 1: 通用层
    await this._generateLayer1(targetPath);

    // Layer 2: 架构层（Systems文档）
    await this._generateLayer2(targetPath);

    // Layer 3: 业务层（框架）
    await this._generateLayer3(targetPath);

    // 生成文档待补充清单
    await this._generateTodoList(targetPath);

    console.log('[生成器] 文档生成完成！');
  }

  /**
   * 创建目录结构
   * @param {string} targetPath
   */
  _createDirectoryStructure(targetPath) {
    console.log('[生成器] 创建目录结构...');

    const dirs = [
      '.claude/commands',
      'markdown/ai',
      'markdown/systems',
      'tasks'
    ];

    for (const dir of dirs) {
      ensureDir(path.join(targetPath, dir));
    }
  }

  /**
   * 生成Layer 1（通用层）
   * @param {string} targetPath
   */
  async _generateLayer1(targetPath) {
    console.log('[生成器] 生成Layer 1（通用层）...');

    const replacements = this._buildReplacements(targetPath);

    // 1. CLAUDE.md
    this._generateFromTemplate('CLAUDE.md', targetPath, 'CLAUDE.md', replacements);

    // 2. /cc 命令
    this._generateFromTemplate('cc.md', targetPath, '.claude/commands/cc.md', replacements);

    // 3. README.md
    this._generateFromTemplate('README.md', targetPath, 'README.md', replacements);

    // 4. 开发规范.md
    this._generateFromTemplate('开发规范.md', targetPath, 'markdown/开发规范.md', replacements);

    // 5. 问题排查.md
    this._generateFromTemplate('问题排查.md', targetPath, 'markdown/问题排查.md', replacements);

    // 6. 快速开始.md
    this._generateFromTemplate('快速开始.md', targetPath, 'markdown/快速开始.md', replacements);

    // 7. AI辅助文档（3个文件，无需替换）
    const aiDocs = [
      '上下文管理规范.md',
      '任务类型决策表.md',
      '快速通道流程.md'
    ];

    for (const aiDoc of aiDocs) {
      const srcPath = path.join(getTemplatePath(''), 'markdown/ai', aiDoc);
      const destPath = path.join(targetPath, 'markdown/ai', aiDoc);
      const content = readFile(srcPath);
      writeFile(destPath, content);
    }

    // 8. 创建空的开发指南.md和项目状态.md
    writeFile(
      path.join(targetPath, 'markdown/开发指南.md'),
      '# 开发指南\n\n⚠️ **待补充**\n'
    );
    writeFile(
      path.join(targetPath, 'markdown/项目状态.md'),
      '# 项目状态\n\n⚠️ **待补充**\n'
    );

    // 9. 创建tasks/README.md
    writeFile(
      path.join(targetPath, 'tasks/README.md'),
      this._generateTasksReadme()
    );

    console.log('[生成器] Layer 1 完成 ✅');
  }

  /**
   * 生成Layer 2（系统文档）
   * @param {string} targetPath
   */
  async _generateLayer2(targetPath) {
    console.log('[生成器] 生成Layer 2（系统文档）...');

    const systemsDir = path.join(targetPath, 'markdown/systems');

    // Systems README
    const systemsReadme = this._generateSystemsReadme();
    writeFile(path.join(systemsDir, 'README.md'), systemsReadme);

    // 为每个System生成文档
    for (const [systemName, systemInfo] of Object.entries(this.codeStructure.systems)) {
      const docContent = this._generateSystemDoc(systemName, systemInfo, targetPath);
      writeFile(path.join(systemsDir, `${systemName}.md`), docContent);
    }

    console.log(`[生成器] 生成了 ${Object.keys(this.codeStructure.systems).length} 个系统文档 ✅`);
  }

  /**
   * 生成Layer 3（业务层框架）
   * @param {string} targetPath
   */
  async _generateLayer3(targetPath) {
    console.log('[生成器] 生成Layer 3（业务层框架）...');

    const businessType = this.metadata.businessType;

    if (businessType === 'RPG') {
      ensureDir(path.join(targetPath, 'markdown/NEWRPG'));
      writeFile(
        path.join(targetPath, 'markdown/NEWRPG/README.md'),
        '# NEWRPG 系统文档\n\n⚠️ **待补充**: AI将在开发过程中逐步完善。\n'
      );
    } else if (this.metadata.usesEcpreset) {
      ensureDir(path.join(targetPath, 'markdown/presets'));
      writeFile(
        path.join(targetPath, 'markdown/presets/README.md'),
        '# Presets 文档\n\n⚠️ **待补充**: AI将在开发过程中逐步完善。\n'
      );
    }

    console.log('[生成器] Layer 3 框架创建完成 ✅');
  }

  /**
   * 生成文档待补充清单
   * @param {string} targetPath
   */
  async _generateTodoList(targetPath) {
    const lines = [];
    lines.push('# 📝 文档待补充清单\n');
    lines.push(`> 本清单由 \`/initmc\` 自动生成于 ${getCurrentDate()}`);
    lines.push('> AI在开发过程中会逐步补充这些内容\n');
    lines.push('---\n');

    lines.push('## 🔴 Layer 2 - 架构层待补充\n');
    for (const [systemName, systemInfo] of Object.entries(this.codeStructure.systems)) {
      if (['medium', 'detailed'].includes(systemInfo.getDetailLevel())) {
        lines.push(`- [ ] \`systems/${systemName}.md\` - 补充业务逻辑和数据流`);
      }
    }
    lines.push('');

    lines.push('## 🟡 Layer 3 - 业务层待补充\n');
    lines.push('- [ ] 补充业务系统详细文档');
    lines.push('- [ ] 补充配置文档说明\n');
    lines.push('---\n');

    lines.push('## 📖 使用说明\n');
    lines.push('1. 在开发过程中，AI会自动检测文档缺失');
    lines.push('2. 在任务收尾时（步骤3.6），AI会询问是否更新文档');
    lines.push('3. 批量补充：使用 `/enhance-docs` 命令\n');
    lines.push('---\n');

    lines.push(`_最后更新: ${getCurrentDate()}_\n`);

    writeFile(path.join(targetPath, 'markdown/文档待补充清单.md'), lines.join('\n'));
  }

  /**
   * 构建占位符替换映射
   * @param {string} targetPath
   * @returns {Object}
   */
  _buildReplacements(targetPath) {
    const normalizedPath = normalizePathForMarkdown(targetPath);

    return {
      '{{PROJECT_PATH}}': normalizedPath,
      '{{PROJECT_NAME}}': this.metadata.projectName,
      '{{CURRENT_DATE}}': getCurrentDate(),
      '{{EXAMPLE_TASKS}}': this._generateExampleTasks(),
      '{{LOG_FILES}}': this._generateLogFiles(targetPath),
      '{{ARCHITECTURE_DOCS_SECTION}}': this._generateArchitectureDocs(),
      '{{BUSINESS_DOCS_SECTION}}': this._generateBusinessDocs(),
      '{{NBT_CHECK_SECTION}}': this.metadata.businessType === 'RPG' ? this._generateNBTSection() : '',
      '{{CRITICAL_RULES}}': this._generateCriticalRulesSection(),
      '{{CRITICAL_RULES_EXTRA}}': this._generateCriticalRules(),
      '{{PROJECT_DESCRIPTION}}': `${this.metadata.businessType}类型MODSDK项目`,
      '{{EXTRA_DOCS}}': this._generateExtraDocs(),
      '{{SDK_DOC_PATH}}': 'D:\\EcWork\\netease-modsdk-wiki',
      '{{CORE_PATHS}}': this._generateCorePaths(normalizedPath)
    };
  }

  /**
   * 从模板生成文件
   * @param {string} templateName
   * @param {string} targetPath
   * @param {string} relativePath
   * @param {Object} replacements
   */
  _generateFromTemplate(templateName, targetPath, relativePath, replacements) {
    const templatePath = getTemplatePath(templateName);
    const content = readFile(templatePath);
    const replaced = replacePlaceholders(content, replacements);
    writeFile(path.join(targetPath, relativePath), replaced);
  }

  /**
   * 生成示例任务
   * @returns {string}
   */
  _generateExampleTasks() {
    const businessType = this.metadata.businessType;

    const examples = {
      RPG: [
        '/cc 修复战斗系统的暴击伤害计算BUG',
        '/cc 为装备系统添加新的饰品充能功能',
        '/cc 优化玩家属性计算性能',
        '/cc 日志显示玩家死亡时出现AttributeError'
      ],
      BedWars: [
        '/cc 修复商店预设在打开UI时报错的问题',
        '/cc 为队伍系统添加队伍聊天功能',
        '/cc 优化资源点刷新逻辑',
        '/cc 日志中显示GetComponent返回None'
      ],
      default: [
        '/cc 修复System初始化错误',
        '/cc 添加新功能模块',
        '/cc 优化代码性能',
        '/cc 日志显示错误'
      ]
    };

    const tasks = examples[businessType] || examples.default;
    return tasks.join('\n');
  }

  /**
   * 生成日志文件列表
   * @param {string} targetPath
   * @returns {string}
   */
  _generateLogFiles(targetPath) {
    const possibleLogs = ['日志.log', '服务端日志.log', '客户端日志.log', 'server.log', 'client.log'];
    const logs = possibleLogs.filter(log => {
      const fs = require('fs');
      return fs.existsSync(path.join(targetPath, log));
    });

    if (logs.length === 0) {
      return `     - \`${normalizePathForMarkdown(targetPath)}/日志.log\` - 主日志文件`;
    }

    return logs.map(log => `     - \`${normalizePathForMarkdown(path.join(targetPath, log))}\``).join('\n');
  }

  /**
   * 生成架构文档部分
   * @returns {string}
   */
  _generateArchitectureDocs() {
    if (this.metadata.usesApollo) {
      return `
4. **Apollo架构文档** - 数据库与网络架构
   - 路径: \`D:/EcWork/netease-modsdk-wiki/docs/mcdocs/2-Apollo\`
   - 涉及数据存储、Redis、MySQL时查阅
`;
    }
    return '';
  }

  /**
   * 生成业务文档部分
   * @returns {string}
   */
  _generateBusinessDocs() {
    if (this.metadata.businessType === 'RPG') {
      return `
5. **NEWRPG详细技术文档** - 系统设计原则（涉及RPG模块时强制）⭐
   - 路径: \`markdown/NEWRPG/\`
   - 使用Grep智能搜索相关文档
   - 优先阅读主系统文档
`;
    } else if (this.metadata.usesEcpreset) {
      return `
5. **Presets文档** - 预设开发指南
   - 路径: \`markdown/presets/\`
   - 查阅预设开发规范和示例
`;
    }
    return `
5. **Systems文档** - 系统实现文档
   - 路径: \`markdown/systems/\`
   - 查阅对应系统的技术文档
`;
  }

  /**
   * 生成NBT检查部分
   * @returns {string}
   */
  _generateNBTSection() {
    return `
4. NBT字段兼容性检查（装备/物品操作时强制）:
   - 已对比老RPG代码: [文件路径:行号]
   - NBT字段列表: [field1, field2, field3, ...]
   - 兼容性确认: ✅ 字段名称100%一致
   (如不涉及装备/物品NBT操作，可跳过此项)
`;
  }

  /**
   * 生成CRITICAL规范章节（用于cc.md的完整规范提醒）
   * @returns {string}
   */
  _generateCriticalRulesSection() {
    const lines = [];

    lines.push('在开发过程中必须遵守以下CRITICAL规范（详见 `markdown/开发规范.md`）：\n');

    // 基础规范（所有项目通用）
    lines.push('### ⛔ 规范1: System生命周期');
    lines.push('');
    lines.push('**禁止:**');
    lines.push('- ❌ 不调用 `self.Create()` - 会导致事件注册失败');
    lines.push('');
    lines.push('**应该:**');
    lines.push('- ✅ 在 `__init__` 中手动调用 `self.Create()`');
    lines.push('- 原因: 网易引擎不会自动调用 `Create()`，必须手动触发\n');

    lines.push('### ⛔ 规范2: 模块导入规范');
    lines.push('');
    lines.push('**禁止:**');
    lines.push('- ❌ 使用相对路径导入（如 `from ..utils import xxx`）');
    lines.push('');
    lines.push('**应该:**');
    lines.push('- ✅ 使用绝对路径导入（如 `from modMain.utils import xxx`）');
    lines.push('- 原因: 网易引擎的Python环境不支持相对导入\n');

    // 添加项目特定规范
    const extraRules = this._generateCriticalRules();
    if (extraRules.trim()) {
      lines.push(extraRules);
    }

    return lines.join('\n');
  }

  /**
   * 生成额外的CRITICAL规范（根据项目类型）
   * @returns {string}
   */
  _generateCriticalRules() {
    const rules = [];

    if (this.metadata.usesApollo) {
      rules.push(`
### ⛔ 规范3: Apollo1.0架构规范

**应该:**
- ✅ 使用Apollo SDK获取数据库连接
- ✅ 遵循Apollo数据访问模式

**禁止:**
- ❌ 直接创建数据库连接
`);
    }

    if (this.metadata.usesEcpreset) {
      rules.push(`
### ⛔ 规范4: ECPreset数据存储规范

**禁止:**
- ❌ 在PresetDefinition类中存储运行时状态

**应该:**
- ✅ 使用instance.set_data/get_data存储实例数据
`);
    }

    if (this.metadata.businessType === 'RPG') {
      rules.push(`
### ⛔ 规范5: NBT兼容性

**应该:**
- ✅ 涉及装备/物品操作时，必须对比老RPG代码
- ✅ 确保NBT字段名称100%一致
`);
    }

    return rules.join('\n');
  }

  /**
   * 生成额外文档链接
   * @returns {string}
   */
  _generateExtraDocs() {
    const docs = ['- **[开发指南.md](./markdown/开发指南.md)** - 待补充'];

    if (this.metadata.businessType === 'RPG') {
      docs.push('- **[NEWRPG/](./markdown/NEWRPG/)** - RPG业务文档');
    }

    if (this.metadata.usesEcpreset) {
      docs.push('- **[presets/](./markdown/presets/)** - Presets文档');
    }

    return '\n' + docs.join('\n');
  }

  /**
   * 生成核心路径列表
   * @param {string} normalizedPath
   * @returns {string}
   */
  _generateCorePaths(normalizedPath) {
    const paths = [`- **项目根目录**: \`${normalizedPath}\``];

    if (this.metadata.businessType === 'RPG') {
      paths.push('- **老RPG项目**: `D:/mg`');
    }

    return paths.join('\n');
  }

  /**
   * 生成Systems README
   * @returns {string}
   */
  _generateSystemsReadme() {
    return `# Systems 文档索引

本目录包含所有System的技术文档。

## 📋 Systems列表

${Object.keys(this.codeStructure.systems).map(name => `- [${name}](./${name}.md)`).join('\n')}

---

_自动生成于 ${getCurrentDate()}_
`;
  }

  /**
   * 创建System元数据（YAML Front Matter）
   * @param {Object} systemInfo
   * @returns {string}
   */
  _createSystemMetadata(systemInfo) {
    const lines = [];
    lines.push('---');
    lines.push(`type: ${systemInfo.type}`);
    lines.push(`complexity: ${systemInfo.complexityScore}`);
    lines.push(`detail_level: ${systemInfo.getDetailLevel()}`);
    lines.push(`lines_of_code: ${systemInfo.linesOfCode}`);
    lines.push('---');
    return lines.join('\n');
  }

  /**
   * 生成单个System文档
   * @param {string} systemName
   * @param {Object} systemInfo
   * @param {string} targetPath
   * @returns {string}
   */
  _generateSystemDoc(systemName, systemInfo, targetPath) {
    const relativePath = path.relative(targetPath, systemInfo.filePath).replace(/\\/g, '/');

    const lines = [];
    lines.push(`# ${systemName}\n`);
    // Add YAML Front Matter
    const frontMatter = this._createSystemMetadata(systemInfo);
    lines.push(frontMatter);
    lines.push('\n');

    lines.push(`> **类型**: ${systemInfo.type}`);
    lines.push(`> **文件路径**: \`${relativePath}\``);
    lines.push(`> **代码行数**: ${systemInfo.linesOfCode}`);
    lines.push(`> **复杂度**: ${systemInfo.complexityScore}/10`);
    lines.push(`> **推荐详细度**: ${systemInfo.getDetailLevel()}\n`);
    lines.push('---\n');

    lines.push('## 📋 概述\n');
    lines.push(`${systemName} 是项目中的 ${systemInfo.type}，主要负责...\n`);
    lines.push('⚠️ **待补充**: 请在后续开发中补充该系统的详细业务逻辑。\n');
    lines.push('---\n');

    lines.push('## 🏗️ 架构设计\n');
    lines.push('### 类结构\n');
    lines.push('```python');
    lines.push(`class ${systemName}(${systemInfo.type}):`);
    lines.push('    # 主要方法');
    const methods = (systemInfo.content.match(/def\s+\w+\s*\([^)]*\)/g) || []).slice(0, 15);
    methods.forEach(method => lines.push(`    ${method}`));
    lines.push('```\n');
    lines.push('---\n');

    lines.push('## 🔧 主要方法\n');
    const methodNames = (systemInfo.content.match(/def\s+(\w+)\s*\(/g) || [])
      .map(m => m.match(/def\s+(\w+)/)[1])
      .slice(0, 20);
    methodNames.forEach(name => lines.push(`- \`${name}()\` - 待补充说明`));
    lines.push('\n⚠️ **待补充**: 请在后续开发中补充主要方法的详细说明和示例。\n');
    lines.push('---\n');

    lines.push('## 📊 数据流\n');
    lines.push('⚠️ **待补充**: 请在理解完整业务逻辑后补充数据流图。\n');
    lines.push('---\n');

    lines.push('## ❓ 常见问题\n');
    lines.push('⚠️ **待补充**: 在开发过程中遇到问题时补充到此处。\n');
    lines.push('---\n');

    lines.push('## 📚 相关文档\n');
    lines.push('- [开发规范](../开发规范.md)');
    lines.push('- [问题排查](../问题排查.md)\n');
    lines.push('---\n');

    lines.push(`_最后更新: ${getCurrentDate()} | 自动生成_\n`);

    return lines.join('\n');
  }

  /**
   * 生成tasks README
   * @returns {string}
   */
  _generateTasksReadme() {
    return `# Tasks 任务目录

本目录用于存储Claude Code执行任务时的实施日志和上下文。

## 📋 使用说明

当执行复杂任务时，AI会自动创建任务目录（如 \`task-001-feature-name/\`），包含：
- \`README.md\` - 任务总览和进度
- \`implementation.md\` - 实施日志
- \`context.md\` - 上下文信息

## 📂 任务列表

_任务将在创建时自动列出_

---

_创建于 ${getCurrentDate()}_
`;
  }
}

module.exports = { DocumentGenerator };
