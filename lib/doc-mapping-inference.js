/**
 * 文档映射推断器
 * 自动推断"代码目录 ↔ 文档目录"的对应关系
 */

const fs = require('fs');
const path = require('path');

/**
 * 文档映射推断器
 */
class DocMappingInference {
  constructor(projectPath) {
    this.projectPath = projectPath;
    this.markdownDir = path.join(projectPath, 'markdown');
  }

  /**
   * 推断文档映射关系
   * @param {Object} codebaseStructure - 项目结构（来自 ProjectDiscovery）
   * @returns {Array} 映射关系列表
   */
  inferMappings(codebaseStructure) {
    console.log('[映射器] 开始推断文档映射关系...');

    // 检查是否有markdown目录
    if (!fs.existsSync(this.markdownDir)) {
      console.log('[映射器] markdown/目录不存在，将创建初始映射');
      return this._createInitialMappings(codebaseStructure);
    }

    // 扫描现有文档目录
    const existingDocDirs = this._scanDocDirs();
    console.log(`[映射器] 发现 ${existingDocDirs.length} 个现有文档目录`);

    const mappings = [];

    // 1. 处理SDK组件（systems）
    this._mapSdkComponents(codebaseStructure.sdkComponents, existingDocDirs, mappings);

    // 2. 处理自定义组件（自动推断）
    this._mapCustomComponents(codebaseStructure.customComponents, existingDocDirs, mappings);

    // 3. 处理配置文件
    this._mapConfigFiles(codebaseStructure.configFiles, existingDocDirs, mappings);

    // 4. 处理工具模块
    this._mapUtilities(codebaseStructure.utilities, existingDocDirs, mappings);

    this._logMappingResults(mappings);
    return mappings;
  }

  /**
   * 扫描markdown目录下的所有子目录
   */
  _scanDocDirs() {
    if (!fs.existsSync(this.markdownDir)) {
      return [];
    }

    return fs.readdirSync(this.markdownDir)
      .filter(item => {
        const fullPath = path.join(this.markdownDir, item);
        return fs.statSync(fullPath).isDirectory();
      });
  }

  /**
   * 创建初始映射（没有markdown目录时）
   */
  _createInitialMappings(codebaseStructure) {
    const mappings = [];

    // SDK组件
    for (const [dirPath, component] of Object.entries(codebaseStructure.sdkComponents)) {
      mappings.push({
        codeDir: dirPath,
        docDir: 'markdown/systems',
        type: 'sdk-systems',
        exists: false,
        confidence: component.confidence
      });
    }

    // 自定义组件
    for (const [dirPath, component] of Object.entries(codebaseStructure.customComponents)) {
      const docDirName = this._inferDocDirName(component.dirName, component.subtype);
      mappings.push({
        codeDir: dirPath,
        docDir: `markdown/${docDirName}`,
        type: 'custom-component',
        subtype: component.subtype,
        exists: false,
        inferred: true,
        confidence: component.confidence
      });
    }

    return mappings;
  }

  /**
   * 映射SDK组件
   */
  _mapSdkComponents(sdkComponents, existingDocDirs, mappings) {
    for (const [dirPath, component] of Object.entries(sdkComponents)) {
      mappings.push({
        codeDir: dirPath,
        docDir: 'markdown/systems',
        type: 'sdk-systems',
        exists: existingDocDirs.includes('systems'),
        confidence: component.confidence,
        standard: true  // 标准映射
      });
    }
  }

  /**
   * 映射自定义组件（核心推断逻辑）
   */
  _mapCustomComponents(customComponents, existingDocDirs, mappings) {
    for (const [dirPath, component] of Object.entries(customComponents)) {
      const dirName = component.dirName;
      const subtype = component.subtype;

      // 生成多个候选文档目录名
      const candidates = this._generateDocDirCandidates(dirName, subtype);

      // 检查哪个候选存在
      let matchedDocDir = null;
      let matchConfidence = 0;

      for (const candidate of candidates) {
        if (existingDocDirs.includes(candidate.name)) {
          matchedDocDir = candidate.name;
          matchConfidence = candidate.confidence;
          break;
        }
      }

      // 如果没有匹配，使用默认推断
      if (!matchedDocDir) {
        matchedDocDir = this._inferDocDirName(dirName, subtype);
      }

      mappings.push({
        codeDir: dirPath,
        docDir: `markdown/${matchedDocDir}`,
        type: 'custom-component',
        subtype: subtype,
        exists: matchedDocDir !== null && existingDocDirs.includes(matchedDocDir),
        inferred: true,
        confidence: matchConfidence || component.confidence,
        candidates: candidates.map(c => c.name)
      });
    }
  }

  /**
   * 生成文档目录候选名称
   */
  _generateDocDirCandidates(dirName, subtype) {
    const candidates = [];

    // 候选1: 保持原名
    candidates.push({ name: dirName, confidence: 0.9, reason: 'exact-match' });

    // 候选2: 使用subtype作为目录名
    if (subtype && subtype !== dirName) {
      candidates.push({
        name: subtype,
        confidence: 0.85,
        reason: 'subtype-match'
      });

      // subtype的复数形式
      candidates.push({
        name: this._pluralize(subtype),
        confidence: 0.8,
        reason: 'subtype-plural'
      });
    }

    // 候选3: 复数形式
    if (!dirName.endsWith('s')) {
      candidates.push({
        name: this._pluralize(dirName),
        confidence: 0.75,
        reason: 'plural'
      });
    }

    // 候选4: 单数形式
    if (dirName.endsWith('s')) {
      candidates.push({
        name: this._singularize(dirName),
        confidence: 0.7,
        reason: 'singular'
      });
    }

    return candidates;
  }

  /**
   * 推断文档目录名称（默认规则）
   */
  _inferDocDirName(dirName, subtype) {
    // 优先使用subtype
    if (subtype) {
      return this._pluralize(subtype);
    }

    // 使用目录名，确保复数形式
    if (dirName.endsWith('s')) {
      return dirName;
    }
    return this._pluralize(dirName);
  }

  /**
   * 映射配置文件
   */
  _mapConfigFiles(configFiles, existingDocDirs, mappings) {
    if (Object.keys(configFiles).length === 0) {
      return;
    }

    // 配置文件通常集中在 markdown/config/ 目录
    const docDir = existingDocDirs.includes('config') ? 'config' : 'config';

    for (const [dirPath, component] of Object.entries(configFiles)) {
      mappings.push({
        codeDir: dirPath,
        docDir: `markdown/${docDir}`,
        type: 'config',
        exists: existingDocDirs.includes(docDir),
        confidence: component.confidence
      });
    }
  }

  /**
   * 映射工具模块
   */
  _mapUtilities(utilities, existingDocDirs, mappings) {
    // 工具模块通常不需要独立文档目录
    // 可以在需要时扩展
  }

  /**
   * 复数化
   */
  _pluralize(word) {
    if (word.endsWith('s')) {
      return word;
    }
    if (word.endsWith('y')) {
      return word.slice(0, -1) + 'ies';
    }
    return word + 's';
  }

  /**
   * 单数化
   */
  _singularize(word) {
    if (word.endsWith('ies')) {
      return word.slice(0, -3) + 'y';
    }
    if (word.endsWith('s')) {
      return word.slice(0, -1);
    }
    return word;
  }

  /**
   * 输出映射结果日志
   */
  _logMappingResults(mappings) {
    console.log('\n[映射器] 📋 文档映射结果：\n');

    if (mappings.length === 0) {
      console.log('  未生成任何映射');
      return;
    }

    mappings.forEach(mapping => {
      const status = mapping.exists ? '✅ 已存在' : '📝 待生成';
      const inferredLabel = mapping.inferred ? ' (推断)' : '';
      const typeLabel = mapping.subtype || mapping.type;

      console.log(`  ${status} ${path.basename(mapping.codeDir)}`);
      console.log(`     类型: ${typeLabel}${inferredLabel}`);
      console.log(`     代码: ${mapping.codeDir}`);
      console.log(`     文档: ${mapping.docDir}`);

      if (mapping.candidates && mapping.candidates.length > 1) {
        console.log(`     候选: ${mapping.candidates.slice(1, 3).join(', ')}`);
      }

      console.log();
    });
  }
}

module.exports = { DocMappingInference };
