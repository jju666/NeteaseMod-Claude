/**
 * 文档生成器
 * 根据分析报告生成完整的工作流文档
 * v2.0: 集成自适应文档维护机制
 */

const path = require('path');
const {
  ensureDir,
  replacePlaceholders,
  readFile,
  writeFile,
  normalizePathForMarkdown
} = require('./utils');
const { getTemplatePath, getCurrentDate, VERSION } = require('./config');
const { DocMappingInference } = require('./doc-mapping-inference');
const { IntelligentDocMaintenance } = require('./intelligent-doc-maintenance');
const { SymlinkManager } = require('./symlink-manager');
const { VersionChecker } = require('./version-checker');

/**
 * 文档生成器
 */
class DocumentGenerator {
  constructor(analysisReport, upstreamPath) {
    this.report = analysisReport;
    this.metadata = analysisReport.metadata;
    this.codeStructure = analysisReport.codeStructure;
    this.upstreamPath = upstreamPath;
  }

  /**
   * 生成所有文档到目标项目
   * @param {string} targetPath - 目标项目路径
   * @param {Object} options - 生成选项
   * @param {boolean} options.minimalMode - 最小化模式：只生成Layer 1核心工作流文档
   */
  async generateAll(targetPath, options = {}) {
    const minimalMode = options.minimalMode || false;

    if (minimalMode) {
      console.log('[生成器] 🚀 最小化模式：只部署核心工作流文档...');
    } else {
      console.log('[生成器] 开始生成文档...');
    }

    // 创建基础目录结构
    this._createDirectoryStructure(targetPath);

    // Layer 1: 通用层（核心工作流）
    await this._generateLayer1(targetPath);

    if (minimalMode) {
      // 部署官方文档（如果存在）
      await this._deployOfficialDocs(targetPath);

      // 最小化模式：跳过业务文档生成
      console.log('[生成器] ✅ 核心工作流部署完成！');
      console.log('[生成器] 💡 使用 /validate-docs 命令发现并规范化项目组件文档');
      return;
    }

    // Layer 2: 架构层（Systems文档 + 自适应组件文档）⭐ 扩展
    await this._generateLayer2(targetPath);

    // ⭐ Layer 2 扩展：自适应组件文档维护
    await this._generateAdaptiveDocs(targetPath);

    // Layer 3: 业务层（框架）
    await this._generateLayer3(targetPath);

    // 生成文档待补充清单
    await this._generateTodoList(targetPath);

    console.log('[生成器] 文档生成完成！');
  }

  /**
   * ⭐ 生成自适应组件文档（新增）
   */
  async _generateAdaptiveDocs(targetPath) {
    console.log('\n[生成器] ========== 自适应文档维护 ==========');

    // 检查是否有发现的组件
    const discoveredComponents = this.codeStructure.discoveredComponents;
    if (!discoveredComponents) {
      console.log('[生成器] 未发现需要自适应维护的组件');
      return;
    }

    // 1. 推断文档映射关系
    const inference = new DocMappingInference(targetPath);
    const mappings = inference.inferMappings(discoveredComponents);

    // 2. 智能维护文档
    const maintenance = new IntelligentDocMaintenance(targetPath);
    await maintenance.maintainAllDocs(mappings);

    console.log('[生成器] ========== 自适应维护完成 ==========\n');
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
   * 生成Layer 1（通用层）- v16.0双层架构
   * @param {string} targetPath
   */
  async _generateLayer1(targetPath) {
    console.log('[生成器] 生成Layer 1（通用层 - v16.0双层架构）...');

    const replacements = this._buildReplacements(targetPath);

    // 1. CLAUDE.md（下游副本，后续升级时会被替换）
    this._generateFromTemplate('CLAUDE.md', targetPath, 'CLAUDE.md', replacements);

    // 2. Claude命令文件
    this._generateFromTemplate('cc.md', targetPath, '.claude/commands/cc.md', replacements);
    this._generateFromTemplate('enhance-docs.md', targetPath, '.claude/commands/enhance-docs.md', replacements);
    this._generateFromTemplate('validate-docs.md', targetPath, '.claude/commands/validate-docs.md', replacements);

    // 3. README.md
    this._generateFromTemplate('README.md', targetPath, 'README.md', replacements);

    // 4. ⭐ 创建.claude/core-docs/软连接（上游基线层）
    console.log('[生成器] 创建上游文档引用（.claude/core-docs/）...');
    const symlinkManager = new SymlinkManager(this.upstreamPath, targetPath);
    await symlinkManager.createAllSymlinks();
    console.log('[生成器] ✅ 上游文档引用创建完成');

    // 5. ⭐ 生成markdown/README.md（导航文档）
    console.log('[生成器] 生成文档导航（markdown/README.md）...');
    this._generateFromTemplate(
      'markdown/README.md',
      targetPath,
      'markdown/README.md',
      replacements
    );
    console.log('[生成器] ✅ 文档导航生成完成');

    // 6. 创建markdown/core/目录（项目覆盖层）
    ensureDir(path.join(targetPath, 'markdown/core'));

    // 7. 创建tasks/README.md
    writeFile(
      path.join(targetPath, 'tasks/README.md'),
      this._generateTasksReadme()
    );

    // 8. ⭐ 生成.claude/workflow-manifest.json（版本追踪）
    console.log('[生成器] 生成工作流元数据（workflow-manifest.json）...');
    const versionChecker = new VersionChecker(this.upstreamPath, targetPath);
    const baselineHashes = versionChecker.computeBaselineHashes();
    versionChecker.writeManifest({
      version: VERSION,
      baselineHashes: baselineHashes,
      installedAt: new Date().toISOString()
    });
    console.log('[生成器] ✅ 工作流元数据生成完成');

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

    // ⭐ 实例化智能文档维护器（用于AI命名）
    const maintenance = new IntelligentDocMaintenance(targetPath);

    let generatedCount = 0;
    let skippedCount = 0;

    // 为每个System生成文档（带智能检测）
    for (const [systemName, systemInfo] of Object.entries(this.codeStructure.systems)) {
      const existingDoc = this._detectExistingSystemDoc(systemName, systemsDir);

      if (existingDoc) {
        console.log(`[生成器] 检测到现有文档: ${existingDoc.fileName} (质量评分: ${existingDoc.quality}/5)`);

        if (existingDoc.quality >= 3) {
          // 高质量文档，跳过生成
          console.log(`[生成器] ✓ 保留高质量文档: ${existingDoc.fileName}`);
          skippedCount++;
          continue;
        } else {
          // 低质量文档，提示用户
          console.log(`[生成器] ⚠️  发现低质量文档: ${existingDoc.fileName}，将覆盖生成新文档`);
        }
      }

      const docContent = this._generateSystemDoc(systemName, systemInfo, targetPath);

      // ⭐ 使用AI智能命名（而非硬编码英文类名）
      const systemFilePath = systemInfo.filePath;
      const chineseFileName = maintenance._inferChineseNameByAI(
        systemFilePath,
        systemName,
        { type: 'system', subtype: 'system' }
      );

      writeFile(path.join(systemsDir, chineseFileName), docContent);
      generatedCount++;
    }

    console.log(`[生成器] 生成了 ${generatedCount} 个系统文档，跳过 ${skippedCount} 个现有文档 ✅`);
  }

  /**
   * 检测现有的System文档（智能匹配）
   * @param {string} systemName - 系统类名（如 ShopServerSystem）
   * @param {string} systemsDir - systems目录路径
   * @returns {Object|null} - { fileName, filePath, quality } 或 null
   */
  _detectExistingSystemDoc(systemName, systemsDir) {
    const fs = require('fs');

    // 检查目录是否存在
    if (!fs.existsSync(systemsDir)) {
      return null;
    }

    // 获取所有markdown文件
    const files = fs.readdirSync(systemsDir).filter(f => f.endsWith('.md') && f !== 'README.md');

    // 收集所有匹配的文档
    const candidates = [];

    // 扫描所有文件
    for (const fileName of files) {
      const filePath = path.join(systemsDir, fileName);
      const content = readFile(filePath);

      // 级别1: 精确文件名匹配
      const isExactMatch = fileName === `${systemName}.md`;

      // 级别2: 内容智能匹配
      const isContentMatch = this._isSystemDocMatch(systemName, content);

      if (isExactMatch || isContentMatch) {
        const quality = this._assessDocQuality(content);
        candidates.push({
          fileName,
          filePath,
          quality,
          isExactMatch,
          matchType: isExactMatch ? 'exact' : 'content'
        });
      }
    }

    // 如果没有找到任何候选文档
    if (candidates.length === 0) {
      return null;
    }

    // 如果只有一个候选，直接返回
    if (candidates.length === 1) {
      return candidates[0];
    }

    // 多个候选时，选择质量最高的
    // 优先级: 质量评分 > 内容匹配 > 精确匹配
    candidates.sort((a, b) => {
      // 首先按质量排序（降序）
      if (b.quality !== a.quality) {
        return b.quality - a.quality;
      }
      // 质量相同时，内容匹配优先于精确文件名匹配
      // （因为内容匹配可能是更详细的中文文档）
      if (a.matchType !== b.matchType) {
        return a.matchType === 'content' ? -1 : 1;
      }
      return 0;
    });

    return candidates[0];
  }

  /**
   * 判断文档内容是否匹配系统名
   * @param {string} systemName - 系统类名（如 ShopServerSystem）
   * @param {string} content - 文档内容
   * @returns {boolean}
   */
  _isSystemDocMatch(systemName, content) {
    // 策略1: 标题中包含系统名
    const titlePattern = new RegExp(`^#\\s+.*${systemName}`, 'm');
    if (titlePattern.test(content)) {
      return true;
    }

    // 策略2: Front Matter中声明了系统名
    const frontMatterPattern = /^---\n[\s\S]*?^---/m;
    const frontMatterMatch = content.match(frontMatterPattern);
    if (frontMatterMatch && frontMatterMatch[0].includes(systemName)) {
      return true;
    }

    // 策略3: 类定义中明确引用了系统名
    const classPattern = new RegExp(`class\\s+${systemName}`, 'm');
    if (classPattern.test(content)) {
      return true;
    }

    // 策略4: 中文文档常见模式 - 检查是否有类似"商店系统"匹配"ShopServerSystem"
    // 提取系统名中的关键词（去掉System后缀）
    const coreSystemName = systemName.replace(/(Server|Client)?System$/i, '');
    if (coreSystemName !== systemName) {
      // 检查标题中是否包含关键词
      const coreTitlePattern = new RegExp(`^#\\s+.*${coreSystemName}`, 'mi');
      if (coreTitlePattern.test(content)) {
        return true;
      }

      // 检查是否在代码块中引用了完整系统名
      const codeBlockPattern = new RegExp(`\`${systemName}\``, 'm');
      if (codeBlockPattern.test(content)) {
        return true;
      }
    }

    return false;
  }

  /**
   * 评估文档质量（0-5分）
   * @param {string} content - 文档内容
   * @returns {number} 质量评分
   */
  _assessDocQuality(content) {
    let score = 0;

    // 因素1: 有代码块示例 (+1)
    if (/```/.test(content)) {
      score += 1;
    }

    // 因素2: 有图表（mermaid/flowchart）(+1)
    if (/mermaid|graph|flowchart|```diagram/.test(content)) {
      score += 1;
    }

    // 因素3: 有示例说明 (+1)
    if (/示例|Example|案例|使用方法|Usage/.test(content)) {
      score += 1;
    }

    // 因素4: 内容丰富（>500字符）(+1)
    if (content.length > 500) {
      score += 1;
    }

    // 因素5: 不是"待补充"模板 (+1)
    if (!/⚠️\s*\*\*待补充\*\*/.test(content)) {
      score += 1;
    }

    return score;
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
      '{{PROJECT_STATUS}}': '生产就绪 (Production Ready)', // 默认项目状态
      '{{VERSION}}': VERSION, // 工作流版本号
      '{{EXAMPLE_TASKS}}': this._generateExampleTasks(),
      '{{LOG_FILES}}': this._generateLogFiles(targetPath),
      '{{ARCHITECTURE_DOCS_SECTION}}': this._generateArchitectureDocs(),
      '{{BUSINESS_DOCS_SECTION}}': this._generateBusinessDocs(),
      '{{PRESETS_DOCS_SECTION}}': this._generatePresetsDocs(), // 新增
      '{{NBT_CHECK_SECTION}}': this.metadata.businessType === 'RPG' ? this._generateNBTSection() : '',
      '{{CRITICAL_RULES}}': this._generateCriticalRulesSection(),
      '{{CRITICAL_RULES_EXTRA}}': this._generateCriticalRules(),
      '{{PROJECT_DESCRIPTION}}': `${this.metadata.businessType}类型MODSDK项目`,
      '{{EXTRA_DOCS}}': this._generateExtraDocs(),
      '{{QUICK_INDEX_EXTRA}}': '', // 快速索引扩展（预留）
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

    // ⭐ v16.1+: CLAUDE.md 特殊处理 - 保护用户编辑区域
    if (templateName === 'CLAUDE.md') {
      const targetFilePath = path.join(targetPath, relativePath);
      const fs = require('fs');

      // 如果目标文件已存在，智能合并
      if (fs.existsSync(targetFilePath)) {
        const existingContent = readFile(targetFilePath);
        const mergedContent = this._mergeCLAUDEmd(replaced, existingContent);
        writeFile(targetFilePath, mergedContent);
        return;
      }
    }

    // 其他文件：直接覆盖
    writeFile(path.join(targetPath, relativePath), replaced);
  }

  /**
   * 智能合并 CLAUDE.md（保护用户编辑区域）
   * @param {string} newTemplate - 新模板内容（已替换占位符）
   * @param {string} existingContent - 现有文件内容
   * @returns {string} 合并后的内容
   */
  _mergeCLAUDEmd(newTemplate, existingContent) {
    // 提取现有文件中的用户编辑区域
    const projectConfig = this._extractSection(existingContent, '项目配置区') ||
                          this._extractSection(newTemplate, '项目配置区');
    const projectExtension = this._extractSection(existingContent, '项目扩展区') || '';

    // 提取新模板中的工作流内容
    const workflowContent = this._extractSection(newTemplate, '工作流内容');

    // 组装新版 CLAUDE.md
    return this._assembleCLAUDEmd({
      projectConfig,
      workflowContent,
      projectExtension,
      metadata: {
        version: VERSION,
        updatedAt: getCurrentDate()
      }
    });
  }

  /**
   * 提取 HTML 注释标记的区域
   * @param {string} content - 文档内容
   * @param {string} sectionName - 区域名称（如 "项目配置区"）
   * @returns {string|null} 区域内容，如果未找到返回 null
   */
  _extractSection(content, sectionName) {
    // 支持两种格式：带版本号和不带版本号
    // 例如：<!-- ==================== 工作流内容 START v16.1 ==================== -->
    //       <!-- ==================== 工作流内容 END v16.1 ==================== -->
    //      或 <!-- ==================== 项目配置区 START ==================== -->
    //       <!-- ==================== 项目配置区 END ==================== -->
    const startPattern = new RegExp(`<!-- ={20} ${sectionName} START(?:\\s+v[\\d.]+)? ={20} -->`, 'm');
    const endPattern = new RegExp(`<!-- ={20} ${sectionName} END(?:\\s+v[\\d.]+)? ={20} -->`, 'm');

    const startMatch = content.match(startPattern);
    const endMatch = content.match(endPattern);

    if (!startMatch || !endMatch) {
      return null;
    }

    const startIdx = startMatch.index + startMatch[0].length;
    const endIdx = endMatch.index;

    // 提取标记之间的内容（不包含标记本身）
    const sectionContent = content.substring(startIdx, endIdx).trim();

    return sectionContent;
  }

  /**
   * 组装新版 CLAUDE.md（四段式结构）
   * @param {Object} params
   * @param {string} params.projectConfig - 项目配置区内容
   * @param {string} params.workflowContent - 工作流内容区
   * @param {string} params.projectExtension - 项目扩展区内容
   * @param {Object} params.metadata - 元数据
   * @returns {string} 完整的 CLAUDE.md 内容
   */
  _assembleCLAUDEmd({ projectConfig, workflowContent, projectExtension, metadata }) {
    const parts = [];

    // 头部
    parts.push(`# CLAUDE.md

> 🤖 **Claude Code AI Assistant 项目参考文档 v16.1**
>
> This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.
>
> **当前版本**: v16.1 (双层文档架构 + 项目扩展区)
> **最后更新**: ${metadata.updatedAt}

---
`);

    // 项目配置区
    parts.push(`<!-- ==================== 项目配置区 START ==================== -->
<!-- 用户可编辑：基础项目信息 -->

${projectConfig}

<!-- ==================== 项目配置区 END ==================== -->
`);

    // 工作流内容区
    parts.push(`<!-- ==================== 工作流内容 START v16.1 ==================== -->
<!-- ⚠️ 警告：以下内容由工作流自动管理，升级时会精确替换此区域 -->
<!-- ⚠️ 请勿手动编辑，所有修改将在升级时丢失 -->
<!-- ⚠️ 如需添加项目特定规范，请使用下方的"项目扩展区" -->

${workflowContent}

<!-- ==================== 工作流内容 END v16.1 ==================== -->
`);

    // 项目扩展区
    // 如果从旧文件提取到了内容，直接使用；否则使用默认模板
    let extensionContent;

    if (projectExtension && projectExtension.trim().length > 0) {
      // 已有内容，直接使用（避免重复添加默认模板）
      extensionContent = projectExtension;
    } else {
      // 首次生成，使用默认模板
      extensionContent = `## 🎯 项目特定规范

> 💡 **使用说明**：
>
> 在此添加**非MODSDK相关**的项目特定规范，例如：
> - ✅ **适合添加**：团队协作流程、自定义架构模式、项目依赖声明、命名约定
> - ❌ **不适合添加**：MODSDK API/事件规范（应放在 \`markdown/core/开发规范.md\`）
>
> **示例**：
> \`\`\`markdown
> ### 项目依赖
> - 依赖项目：XXX
> - 项目路径：D:\\path\\to\\dependency
>
> ### 自定义架构
> - 使用State模式管理游戏状态
> - 所有数据库操作统一使用DBManager
>
> ### 团队约定
> - 提交代码前必须运行单元测试
> - 函数命名使用驼峰命名法
> \`\`\`

<!-- 在此下方添加项目特定规范 -->`;
    }

    parts.push(`<!-- ==================== 项目扩展区 START ==================== -->
<!-- 用户可编辑：添加项目特定规范 -->
<!-- ⚠️ 本区域内容会在升级时自动保留 -->

${extensionContent}

<!-- ==================== 项目扩展区 END ==================== -->
`);

    // 元数据区
    parts.push(`<!-- ==================== 文档元数据区 START ==================== -->
<!-- 自动生成，升级时更新 -->

**文档元数据**：
- 工作流版本：v${metadata.version}
- 上游仓库：基于Claude的MODSDK开发工作流
- 生成时间：${metadata.updatedAt}

<!-- ==================== 文档元数据区 END ==================== -->
`);

    return parts.join('\n');
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
   * 生成 Presets 文档部分（用于模板中的 {{PRESETS_DOCS_SECTION}}）
   * @returns {string}
   */
  _generatePresetsDocs() {
    // 目前返回空字符串，预留扩展
    return '';
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

  /**
   * 部署官方文档到目标项目（Git Submodule）
   * @param {string} targetPath - 目标项目路径
   */
  async _deployOfficialDocs(targetPath) {
    const fs = require('fs-extra');
    const path = require('path');

    console.log('\n[生成器] ========== 部署官方文档 ==========');

    // 检测全局工作流路径
    const workflowHome = process.env.NETEASE_CLAUDE_HOME;
    if (!workflowHome) {
      console.log('[生成器] ⚠️  未设置 NETEASE_CLAUDE_HOME 环境变量，跳过文档部署');
      console.log('[生成器] 💡 将使用在线查询（WebFetch）获取官方文档');
      return;
    }

    const globalDocsPath = path.join(workflowHome, 'docs');
    const projectDocsPath = path.join(targetPath, '.claude', 'docs');

    // 检测全局文档是否存在
    if (!fs.existsSync(globalDocsPath)) {
      console.log('[生成器] 💡 官方文档未下载，将使用在线查询（WebFetch）');
      console.log('[生成器] 📝 如需本地文档加速查询，请在工作流目录执行：');
      console.log('[生成器]    cd ' + workflowHome);
      console.log('[生成器]    git submodule update --init --recursive\n');
      return;
    }

    // 检查文档子模块是否完整
    const modsdkWikiPath = path.join(globalDocsPath, 'modsdk-wiki');
    const bedrockWikiPath = path.join(globalDocsPath, 'bedrock-wiki');
    const hasModsdkWiki = fs.existsSync(modsdkWikiPath);
    const hasBedrockWiki = fs.existsSync(bedrockWikiPath);

    if (!hasModsdkWiki && !hasBedrockWiki) {
      console.log('[生成器] ⚠️  官方文档子模块为空，跳过部署');
      console.log('[生成器] 💡 请执行 git submodule update --init --recursive\n');
      return;
    }

    // 创建软链接（Windows使用junction）
    try {
      // 删除旧的软链接（如果存在）
      if (fs.existsSync(projectDocsPath)) {
        fs.removeSync(projectDocsPath);
      }

      // 创建软链接
      fs.symlinkSync(globalDocsPath, projectDocsPath, 'junction');

      console.log('[生成器] ✅ 已部署官方文档到 .claude/docs/（软链接）');
      console.log('[生成器] 📁 包含文档：');
      if (hasModsdkWiki) {
        console.log('[生成器]    - MODSDK Wiki (modsdk-wiki/)');
      }
      if (hasBedrockWiki) {
        console.log('[生成器]    - Bedrock Wiki (bedrock-wiki/)');
      }
      console.log('[生成器] ⚡ /cc 指令将优先查询本地文档（速度提升10x）\n');

    } catch (err) {
      if (err.code === 'EEXIST') {
        console.log('[生成器] ✅ 官方文档已存在');
      } else {
        console.warn('[生成器] ⚠️  软链接创建失败:', err.message);
        console.warn('[生成器] 💡 将使用在线查询（WebFetch）\n');
      }
    }

    console.log('[生成器] ========== 文档部署完成 ==========\n');
  }
}

module.exports = { DocumentGenerator };
