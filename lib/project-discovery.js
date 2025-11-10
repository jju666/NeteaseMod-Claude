/**
 * 项目结构发现器
 * 自动发现项目中的所有组件类型，无需硬编码
 */

const path = require('path');
const { walkDir, readFile } = require('./utils');

/**
 * 项目结构发现器
 */
class ProjectDiscovery {
  constructor(projectPath) {
    this.projectPath = projectPath;
  }

  /**
   * 发现项目中所有组件
   * @returns {Object} 项目结构地图
   */
  discover() {
    console.log('[发现器] 开始分析项目结构...');

    const allPyFiles = this._scanAllPythonFiles();
    const dirGroups = this._groupByDirectory(allPyFiles);

    const structure = {
      sdkComponents: {},      // MODSDK标准组件
      customComponents: {},   // 项目特定组件（自动发现）
      configFiles: {},        // 配置文件
      utilities: {}           // 工具模块
    };

    // 推断每个目录的用途
    for (const [dirPath, files] of Object.entries(dirGroups)) {
      const purpose = this.inferDirectoryPurpose(dirPath, files);

      if (!purpose.needsDocumentation) {
        continue; // 跳过不重要的目录
      }

      // 分类存储
      if (purpose.type === 'sdk-systems') {
        structure.sdkComponents[dirPath] = purpose;
      } else if (purpose.type === 'custom-component') {
        structure.customComponents[dirPath] = purpose;
      } else if (purpose.type === 'config') {
        structure.configFiles[dirPath] = purpose;
      } else if (purpose.type === 'utility') {
        structure.utilities[dirPath] = purpose;
      }
    }

    this._logDiscoveryResults(structure);
    return structure;
  }

  /**
   * 扫描所有Python文件
   * @returns {Array} Python文件路径列表
   */
  _scanAllPythonFiles() {
    const files = [];
    walkDir(this.projectPath, (filePath) => {
      if (filePath.endsWith('.py')) {
        files.push(filePath);
      }
    });
    return files;
  }

  /**
   * 按目录分组文件
   * @param {Array} files - 文件路径列表
   * @returns {Object} 目录 -> 文件列表
   */
  _groupByDirectory(files) {
    const groups = {};

    for (const file of files) {
      const dir = path.dirname(file);
      if (!groups[dir]) {
        groups[dir] = [];
      }
      groups[dir].push(file);
    }

    return groups;
  }

  /**
   * 推断目录用途（核心算法）
   * @param {string} dirPath - 目录路径
   * @param {Array} files - 目录中的文件列表
   * @returns {Object} 目录用途描述
   */
  inferDirectoryPurpose(dirPath, files) {
    const signals = [];
    const dirName = path.basename(dirPath).toLowerCase();

    // 信号1: 目录名称模式
    this._collectDirectoryNameSignals(dirName, signals);

    // 信号2: 文件内容分析
    this._collectFileContentSignals(files, signals);

    // 信号3: 文件数量和复杂度
    if (files.length >= 3) {
      // 复杂目录，提升置信度
      signals.forEach(s => s.confidence *= 1.1);
    }

    // 信号4: 配置文件特征
    const configFileCount = files.filter(f => /_config\.py$/.test(f)).length;
    if (configFileCount > 0) {
      signals.push({ type: 'config', confidence: 1.0 });
    }

    // 综合判断
    return this._aggregateSignals(signals, dirPath, files);
  }

  /**
   * 收集目录名称相关的信号
   */
  _collectDirectoryNameSignals(dirName, signals) {
    const patterns = [
      { regex: /^systems?$/i, type: 'sdk-systems', confidence: 0.8 },
      { regex: /^presets?$/i, type: 'custom-component', subtype: 'preset', confidence: 0.9 },
      { regex: /^states?$/i, type: 'custom-component', subtype: 'state', confidence: 0.9 },
      { regex: /^modules?$/i, type: 'custom-component', subtype: 'module', confidence: 0.8 },
      { regex: /^configs?$/i, type: 'config', confidence: 0.8 },
      { regex: /^utils?$/i, type: 'utility', confidence: 0.7 },
      { regex: /^helpers?$/i, type: 'utility', confidence: 0.7 },
      { regex: /^common$/i, type: 'utility', confidence: 0.6 },
      { regex: /^components?$/i, type: 'custom-component', subtype: 'component', confidence: 0.8 },
      { regex: /^managers?$/i, type: 'custom-component', subtype: 'manager', confidence: 0.8 },
      { regex: /^handlers?$/i, type: 'custom-component', subtype: 'handler', confidence: 0.8 }
    ];

    for (const pattern of patterns) {
      if (pattern.regex.test(dirName)) {
        signals.push({
          type: pattern.type,
          subtype: pattern.subtype,
          confidence: pattern.confidence,
          source: 'directory-name'
        });
      }
    }
  }

  /**
   * 收集文件内容相关的信号
   */
  _collectFileContentSignals(files, signals) {
    const contentPatterns = [
      { regex: /class\s+\w+\s*\(\s*(ServerSystem|ClientSystem)\s*\)/,
        type: 'sdk-systems', confidence: 1.0 },
      { regex: /class\s+\w+\s*\(\s*PresetDefinition/,
        type: 'custom-component', subtype: 'preset', confidence: 1.0 },
      { regex: /class\s+\w+\s*\(\s*.*State\s*\)/,
        type: 'custom-component', subtype: 'state', confidence: 0.9 },
      { regex: /class\s+\w+\s*\(\s*.*Manager\s*\)/,
        type: 'custom-component', subtype: 'manager', confidence: 0.85 },
      { regex: /class\s+\w+\s*\(\s*.*Handler\s*\)/,
        type: 'custom-component', subtype: 'handler', confidence: 0.85 },
      { regex: /class\s+\w+\s*\(\s*.*Component\s*\)/,
        type: 'custom-component', subtype: 'component', confidence: 0.8 }
    ];

    // 只检查前3个文件（性能优化）
    const samplesToCheck = files.slice(0, Math.min(3, files.length));

    for (const file of samplesToCheck) {
      try {
        const content = readFile(file);

        for (const pattern of contentPatterns) {
          if (pattern.regex.test(content)) {
            signals.push({
              type: pattern.type,
              subtype: pattern.subtype,
              confidence: pattern.confidence,
              source: 'file-content',
              file: path.basename(file)
            });
          }
        }
      } catch (err) {
        // 忽略读取错误
      }
    }
  }

  /**
   * 聚合信号，做出最终判断
   */
  _aggregateSignals(signals, dirPath, files) {
    if (signals.length === 0) {
      return {
        type: 'unknown',
        confidence: 0,
        needsDocumentation: false
      };
    }

    // 按类型分组，计算平均置信度
    const typeScores = {};
    for (const signal of signals) {
      const key = signal.subtype || signal.type;
      if (!typeScores[key]) {
        typeScores[key] = {
          type: signal.type,
          subtype: signal.subtype,
          sum: 0,
          count: 0,
          sources: []
        };
      }
      typeScores[key].sum += signal.confidence;
      typeScores[key].count += 1;
      if (signal.source) {
        typeScores[key].sources.push(signal.source);
      }
    }

    // 选择置信度最高的类型
    let bestMatch = null;
    let bestScore = 0;

    for (const [key, data] of Object.entries(typeScores)) {
      const avgScore = data.sum / data.count;
      if (avgScore > bestScore) {
        bestScore = avgScore;
        bestMatch = data;
      }
    }

    const result = {
      type: bestMatch.type,
      subtype: bestMatch.subtype,
      confidence: bestScore,
      dirPath: dirPath,
      dirName: path.basename(dirPath),
      fileCount: files.length,
      needsDocumentation: bestScore >= 0.6,  // 置信度阈值
      detectionSources: Array.from(new Set(bestMatch.sources))
    };

    return result;
  }

  /**
   * 输出发现结果日志
   */
  _logDiscoveryResults(structure) {
    console.log('\n[发现器] 📊 项目结构发现结果：\n');

    const allComponents = [
      ...Object.values(structure.sdkComponents),
      ...Object.values(structure.customComponents),
      ...Object.values(structure.configFiles),
      ...Object.values(structure.utilities)
    ];

    if (allComponents.length === 0) {
      console.log('  未发现需要文档化的组件');
      return;
    }

    allComponents
      .sort((a, b) => b.confidence - a.confidence)
      .forEach(component => {
        const emoji = this._getComponentEmoji(component.type);
        const typeLabel = component.subtype || component.type;
        const confidenceBar = '█'.repeat(Math.round(component.confidence * 10));

        console.log(`  ${emoji} ${component.dirName}`);
        console.log(`     类型: ${typeLabel}`);
        console.log(`     置信度: ${confidenceBar} ${(component.confidence * 100).toFixed(0)}%`);
        console.log(`     文件数: ${component.fileCount}`);
        console.log();
      });
  }

  /**
   * 获取组件类型对应的 emoji
   */
  _getComponentEmoji(type) {
    const emojiMap = {
      'sdk-systems': '⚙️',
      'custom-component': '🔧',
      'config': '📋',
      'utility': '🛠️'
    };
    return emojiMap[type] || '📦';
  }
}

module.exports = { ProjectDiscovery };
