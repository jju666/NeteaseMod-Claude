/**
 * 项目分析器
 * 从 workflow-generator/analyzer.py 翻译而来
 * v2.0: 集成自适应项目结构发现
 */

const fs = require('fs');
const path = require('path');
const { walkDir, findFile, readFile } = require('./utils');
const {
  SCALE_THRESHOLDS,
  COMPLEXITY_THRESHOLDS,
  PROJECT_TYPE_KEYWORDS,
  getCurrentDate
} = require('./config');
const { ProjectDiscovery } = require('./project-discovery');

/**
 * 项目分析器
 */
class ProjectAnalyzer {
  constructor(projectPath) {
    this.projectPath = projectPath;
    this.metadata = new ProjectMetadata();
    this.codeStructure = new CodeStructure();
    this.docCoverage = new DocumentationCoverage();
  }

  /**
   * 执行完整分析
   * @returns {AnalysisReport}
   */
  analyze() {
    console.log('[分析器] 开始分析项目...');
    console.log(`[分析器] 项目路径: ${this.projectPath}`);

    // 步骤1: 检测项目类型
    this._detectProjectType();

    // 步骤2: 扫描代码结构（传统方式，保留向后兼容）
    this._scanCodeStructure();

    // ⭐ 步骤2.5: 自适应项目结构发现（新增）
    this._discoverProjectStructure();

    // 步骤3: 检查现有文档
    this._checkDocumentation();

    // 步骤4: 计算项目规模
    this._calculateProjectScale();

    console.log('[分析器] 分析完成');
    return this.generateReport();
  }

  /**
   * ⭐ 自适应项目结构发现（新增）
   */
  _discoverProjectStructure() {
    console.log('[分析器] 执行自适应结构发现...');

    const discovery = new ProjectDiscovery(this.projectPath);
    this.discoveredStructure = discovery.discover();

    // 合并发现的组件到 codeStructure
    this._mergeDiscoveredComponents();
  }

  /**
   * 合并发现的组件
   */
  _mergeDiscoveredComponents() {
    // SDK组件已经通过传统方式扫描，这里主要处理自定义组件
    const customCount = Object.keys(this.discoveredStructure.customComponents).length;
    const configCount = Object.keys(this.discoveredStructure.configFiles).length;

    console.log(`[分析器] 发现 ${customCount} 个自定义组件目录`);
    console.log(`[分析器] 发现 ${configCount} 个配置文件目录`);

    // 将发现的组件信息存储到 codeStructure
    // 注意：保持向后兼容，不破坏现有的 systems/presets 结构
    if (!this.codeStructure.discoveredComponents) {
      this.codeStructure.discoveredComponents = this.discoveredStructure;
    }
  }

  /**
   * 检测项目类型
   */
  _detectProjectType() {
    console.log('[分析器] 检测项目类型...');

    // 尝试多种检测方式
    const detectionResult = this._tryMultipleDetections();

    // 信任用户判断
    this.metadata.isModsdk = true;
    this.metadata.projectName = path.basename(this.projectPath);

    // 使用检测结果
    if (detectionResult.modMainPath) {
      this.metadata.modMainPath = detectionResult.modMainPath;
      console.log(`[分析器] 检测到modMain.py: ${detectionResult.modMainPath}`);
    } else {
      console.log('[分析器] 未找到modMain.py，使用通用分析模式');
      if (detectionResult.hints.length > 0) {
        console.log(`[分析器] 检测提示: ${detectionResult.hints.join(', ')}`);
      }
    }

    console.log(`[分析器] 项目: ${this.metadata.projectName}`);

    // 检测架构特征
    this.metadata.usesApollo = this._detectApollo(detectionResult);
    this.metadata.usesEcpreset = this._detectEcpreset();

    // 推断业务类型
    this.metadata.businessType = this._inferBusinessType();

    console.log(`[分析器] 项目类型: ${this.metadata.businessType}`);
    if (this.metadata.usesApollo) {
      console.log('[分析器] 检测到Apollo架构');
    }
    if (this.metadata.usesEcpreset) {
      console.log('[分析器] 检测到ECPreset框架');
    }
  }

  /**
   * 扫描代码结构
   */
  _scanCodeStructure() {
    console.log('[分析器] 扫描代码结构...');

    let pythonFilesCount = 0;

    walkDir(this.projectPath, (filePath) => {
      if (filePath.endsWith('.py')) {
        pythonFilesCount++;
        try {
          this._analyzePythonFile(filePath);
        } catch (err) {
          console.log(`[分析器] 警告: 分析文件失败 ${filePath} - ${err.message}`);
        }
      }
    });

    console.log(`[分析器] 发现 ${pythonFilesCount} 个Python文件`);
    console.log(`[分析器] 发现 ${Object.keys(this.codeStructure.systems).length} 个Systems`);
    console.log(`[分析器] 发现 ${Object.keys(this.codeStructure.presets).length} 个Presets`);
  }

  /**
   * 分析单个Python文件
   * @param {string} filePath
   */
  _analyzePythonFile(filePath) {
    const content = readFile(filePath);

    // 检测System类
    const systemPattern = /class\s+(\w+)\s*\(\s*(ServerSystem|ClientSystem)\s*\)/g;
    let match;
    while ((match = systemPattern.exec(content)) !== null) {
      const [, className, baseClass] = match;
      this.codeStructure.addSystem(className, filePath, baseClass, content);
    }

    // 检测Preset类
    const presetPattern = /class\s+(\w+)\s*\(\s*ECPresetDefinition\s*\)/g;
    while ((match = presetPattern.exec(content)) !== null) {
      const [, className] = match;
      this.codeStructure.addPreset(className, filePath, content);
    }
  }

  /**
   * 检查现有文档
   */
  _checkDocumentation() {
    console.log('[分析器] 检查现有文档...');

    const markdownDir = path.join(this.projectPath, 'markdown');
    if (!fs.existsSync(markdownDir)) {
      console.log('[分析器] markdown/目录不存在');
      return;
    }

    walkDir(markdownDir, (filePath) => {
      if (filePath.endsWith('.md')) {
        this.docCoverage.addExistingDoc(filePath);
      }
    });

    console.log(`[分析器] 发现 ${this.docCoverage.existingDocs.length} 个现有文档`);
  }

  /**
   * 计算项目规模
   */
  _calculateProjectScale() {
    const systemsCount = Object.keys(this.codeStructure.systems).length;

    if (systemsCount <= SCALE_THRESHOLDS.small) {
      this.metadata.scale = 'small';
    } else if (systemsCount <= SCALE_THRESHOLDS.medium) {
      this.metadata.scale = 'medium';
    } else {
      this.metadata.scale = 'large';
    }

    console.log(`[分析器] 项目规模: ${this.metadata.scale} (${systemsCount} Systems)`);
  }

  /**
   * 生成分析报告
   * @returns {AnalysisReport}
   */
  generateReport() {
    return new AnalysisReport(
      this.metadata,
      this.codeStructure,
      this.docCoverage
    );
  }

  /**
   * 尝试多种检测方式
   * @returns {Object}
   */
  _tryMultipleDetections() {
    const result = {
      modMainPath: null,
      projectType: 'unknown',
      hints: []
    };

    // 方式1: 查找 modMain.py
    const modMainPath = findFile(this.projectPath, 'modMain.py');
    if (modMainPath) {
      result.modMainPath = modMainPath;
      result.projectType = 'standard';
      result.hints.push('modMain.py');
      return result;
    }

    // 方式2: behavior_packs/（网易地图）
    const behaviorPacksPath = path.join(this.projectPath, 'behavior_packs');
    if (fs.existsSync(behaviorPacksPath)) {
      result.projectType = 'netease-map';
      result.hints.push('behavior_packs/');
    }

    // 方式3: deploy.json（Apollo）
    const deployJsonPath = path.join(this.projectPath, 'deploy.json');
    if (fs.existsSync(deployJsonPath)) {
      result.projectType = 'apollo';
      result.hints.push('deploy.json');
    }

    // 方式4: .mcs/（网易开发工具）
    const mcsPath = path.join(this.projectPath, '.mcs');
    if (fs.existsSync(mcsPath)) {
      result.hints.push('.mcs/');
    }

    return result;
  }

  /**
   * 检测是否使用Apollo
   * @param {Object} detectionResult - 检测结果
   * @returns {boolean}
   */
  _detectApollo(detectionResult = {}) {
    // 方式1: 检查 modMain.py 内容
    if (this.metadata.modMainPath) {
      const content = readFile(this.metadata.modMainPath);
      if (content.toLowerCase().includes('apollo')) {
        return true;
      }
    }

    // 方式2: 检查 deploy.json
    const deployJsonPath = path.join(this.projectPath, 'deploy.json');
    if (fs.existsSync(deployJsonPath)) {
      return true;
    }

    // 方式3: 从检测结果推断
    if (detectionResult.projectType === 'apollo') {
      return true;
    }

    return false;
  }

  /**
   * 检测是否使用ECPreset
   * @returns {boolean}
   */
  _detectEcpreset() {
    return Object.keys(this.codeStructure.presets).length > 0;
  }

  /**
   * 推断业务类型
   * @returns {string}
   */
  _inferBusinessType() {
    const systemNames = Object.keys(this.codeStructure.systems).map(name => name.toLowerCase());

    // 计算每种类型的匹配分数
    const scores = {};
    for (const [businessType, keywords] of Object.entries(PROJECT_TYPE_KEYWORDS)) {
      scores[businessType] = systemNames.reduce((score, name) => {
        return score + (keywords.some(keyword => name.includes(keyword)) ? 1 : 0);
      }, 0);
    }

    // 选择得分最高的类型
    const maxType = Object.keys(scores).reduce((a, b) => scores[a] > scores[b] ? a : b, 'General');
    return scores[maxType] > 0 ? maxType : 'General';
  }
}

/**
 * 项目元数据
 */
class ProjectMetadata {
  constructor() {
    this.isModsdk = false;
    this.projectName = '';
    this.modMainPath = '';
    this.usesApollo = false;
    this.usesEcpreset = false;
    this.businessType = 'General';
    this.scale = 'small'; // small / medium / large
  }
}

/**
 * 代码结构
 */
class CodeStructure {
  constructor() {
    this.systems = {}; // {systemName: SystemInfo}
    this.presets = {}; // {presetName: PresetInfo}
    this.dependencies = {}; // {systemName: [依赖的system]}
  }

  addSystem(name, filePath, type, content) {
    this.systems[name] = new SystemInfo(name, filePath, type, content);
  }

  addPreset(name, filePath, content) {
    this.presets[name] = new PresetInfo(name, filePath, content);
  }
}

/**
 * System信息
 */
class SystemInfo {
  constructor(name, filePath, type, content) {
    this.name = name;
    this.filePath = filePath;
    this.type = type; // ServerSystem / ClientSystem
    this.content = content;

    // 分析代码复杂度
    this.linesOfCode = content.split('\n').length;
    this.methodCount = (content.match(/def\s+\w+\s*\(/g) || []).length;
    this.eventListeners = (content.match(/ListenForEvent/g) || []).length;

    // 计算复杂度分数
    this.complexityScore = this._calculateComplexity();
  }

  /**
   * 计算复杂度分数
   * @returns {number}
   */
  _calculateComplexity() {
    let score = 0;

    // 因素1: 代码行数
    if (this.linesOfCode > 500) {
      score += 3;
    } else if (this.linesOfCode > 200) {
      score += 2;
    } else {
      score += 1;
    }

    // 因素2: 方法数量
    if (this.methodCount > 15) {
      score += 2;
    } else if (this.methodCount > 5) {
      score += 1;
    }

    // 因素3: 事件监听数量
    if (this.eventListeners > 5) {
      score += 1;
    }

    // 因素4: 核心System判断
    const coreKeywords = ['core', 'manager', 'game', 'state', 'main'];
    if (coreKeywords.some(keyword => this.name.toLowerCase().includes(keyword))) {
      score += 2;
    }

    // 因素5: 依赖关系（通过import数量估算）
    const importCount = (this.content.match(/from\s+\w+\s+import/g) || []).length;
    if (importCount > 5) {
      score += 2;
    } else if (importCount > 2) {
      score += 1;
    }

    return score;
  }

  /**
   * 获取推荐的文档详细度
   * @returns {string}
   */
  getDetailLevel() {
    if (this.complexityScore >= COMPLEXITY_THRESHOLDS.detailed) {
      return 'detailed';
    } else if (this.complexityScore >= COMPLEXITY_THRESHOLDS.medium) {
      return 'medium';
    } else {
      return 'simple';
    }
  }
}

/**
 * Preset信息
 */
class PresetInfo {
  constructor(name, filePath, content) {
    this.name = name;
    this.filePath = filePath;
    this.content = content;
  }
}

/**
 * 文档覆盖率
 */
class DocumentationCoverage {
  constructor() {
    this.existingDocs = [];
    this.missingDocs = [];
    this.lowQualityDocs = [];
  }

  addExistingDoc(docPath) {
    this.existingDocs.push(docPath);
  }
}

/**
 * 分析报告
 */
class AnalysisReport {
  constructor(metadata, codeStructure, docCoverage) {
    this.metadata = metadata;
    this.codeStructure = codeStructure;
    this.docCoverage = docCoverage;
  }

  /**
   * 生成Markdown格式报告
   * @returns {string}
   */
  toMarkdown() {
    const lines = [];

    lines.push('# 📊 项目分析报告\n');

    // 项目概况
    lines.push('## 🎯 项目概况\n');
    lines.push(`- **项目名称**: ${this.metadata.projectName}`);
    lines.push(`- **项目类型**: ${this.metadata.businessType}`);
    lines.push(`- **项目规模**: ${this.metadata.scale}`);
    lines.push('- **架构特征**:');
    lines.push(`  - Apollo架构: ${this.metadata.usesApollo ? '✅' : '❌'}`);
    lines.push(`  - ECPreset框架: ${this.metadata.usesEcpreset ? '✅' : '❌'}`);
    lines.push('');

    // 代码结构
    lines.push('## 📐 代码结构\n');
    lines.push(`- **Systems数量**: ${Object.keys(this.codeStructure.systems).length}`);
    lines.push(`- **Presets数量**: ${Object.keys(this.codeStructure.presets).length}`);
    lines.push('');

    // Systems列表（按复杂度排序，只显示前10个）
    lines.push('### Systems清单（按复杂度排序，前10个）\n');
    lines.push('| System名称 | 类型 | 代码行数 | 方法数 | 复杂度 | 推荐详细度 |');
    lines.push('|-----------|------|---------|--------|--------|-----------|');

    const sortedSystems = Object.values(this.codeStructure.systems)
      .sort((a, b) => b.complexityScore - a.complexityScore);

    for (const system of sortedSystems.slice(0, 10)) {
      lines.push(`| ${system.name} | ${system.type} | ${system.linesOfCode} | ${system.methodCount} | ${system.complexityScore}/10 | ${system.getDetailLevel()} |`);
    }

    if (sortedSystems.length > 10) {
      lines.push('| ... | ... | ... | ... | ... | ... |');
      lines.push(`| *共${sortedSystems.length}个Systems* | | | | | |`);
    }
    lines.push('');

    // 文档覆盖率
    lines.push('## 📚 文档覆盖率\n');
    lines.push(`- **现有文档**: ${this.docCoverage.existingDocs.length} 个`);
    lines.push(`- **Systems缺失文档**: ${Object.keys(this.codeStructure.systems).length} 个`);
    lines.push('');

    // 预计生成
    lines.push('## 📝 预计生成文档\n');
    lines.push('- **Layer 1（通用层）**: 约13个文件');
    lines.push('  - CLAUDE.md、开发规范.md、问题排查.md等');
    lines.push('  - .claude/commands/mc.md ⭐');
    lines.push('  - markdown/ai/（3个AI补充文档）');
    lines.push(`- **Layer 2（架构层）**: ${Object.keys(this.codeStructure.systems).length}个系统文档`);
    if (Object.keys(this.codeStructure.presets).length > 0) {
      lines.push(`  - ${Object.keys(this.codeStructure.presets).length}个Preset文档`);
    }
    lines.push('- **Layer 3（业务层）**: 框架文档（待后续补充）');
    lines.push('');

    // 预估消耗
    const systemsCount = Object.keys(this.codeStructure.systems).length;
    const estimatedTokens = 30000 + systemsCount * 1000;
    const estimatedTime = Math.max(5, Math.floor(systemsCount / 3));

    lines.push('## ⏱️ 预估消耗\n');
    lines.push(`- **预计Token消耗**: 约${Math.floor(estimatedTokens / 1000)}k tokens`);
    lines.push(`- **预计执行时间**: 约${estimatedTime}分钟`);
    lines.push('');

    return lines.join('\n');
  }
}

module.exports = {
  ProjectAnalyzer,
  ProjectMetadata,
  CodeStructure,
  SystemInfo,
  PresetInfo,
  DocumentationCoverage,
  AnalysisReport
};
