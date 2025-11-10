/**
 * Adaptive Document Discovery System
 *
 * 自适应文档发现系统 - MODSDK工作流核心模块
 *
 * 核心功能：
 * 1. 自动扫描项目代码，发现组件类型（System、Component及任意自定义模式）
 * 2. 推断项目的文档组织方式（目录结构、命名规则）
 * 3. 生成组件到文档路径的映射规则
 *
 * 设计原则：
 * - 只保留MODSDK官方定义的核心概念（System、Component）
 * - 自动识别项目自定义的组织模式（State、Preset、Manager等）
 * - 零配置，完全基于代码分析
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

class AdaptiveDocDiscovery {
  constructor(projectRoot) {
    this.projectRoot = projectRoot;
    this.behaviorPackPath = null;
    this.discoveredPatterns = {
      officialConcepts: {
        systems: [],
        components: []
      },
      customPatterns: {}
    };
  }

  /**
   * 主入口：发现项目结构
   * @returns {Object} 发现的组件模式和映射规则
   */
  async discoverProjectStructure() {
    console.log('🔍 开始自适应扫描项目结构...\n');

    // 1. 定位behavior_packs目录
    this.behaviorPackPath = this.locateBehaviorPacks();
    if (!this.behaviorPackPath) {
      console.log('⚠️  未找到behavior_packs目录，可能不是MODSDK项目');
      return null;
    }

    console.log(`📂 Behavior包路径: ${this.behaviorPackPath}\n`);

    // 2. 扫描所有Python类
    const allClasses = await this.scanAllClasses();
    console.log(`📊 发现 ${allClasses.length} 个Python类\n`);

    // 3. 识别MODSDK官方核心概念
    await this.identifyOfficialConcepts(allClasses);

    // 4. 推断项目自定义模式
    await this.inferCustomPatterns(allClasses);

    // 5. 推断目录结构
    await this.inferDirectoryLayout();

    // 6. 生成文档路径映射
    const pathMap = this.generateDocPathMap();

    // 7. 输出发现报告
    this.printDiscoveryReport();

    return {
      patterns: this.discoveredPatterns,
      pathMap: pathMap
    };
  }

  /**
   * 定位behavior_packs目录
   */
  locateBehaviorPacks() {
    const possiblePaths = [
      path.join(this.projectRoot, 'behavior_packs'),
      path.join(this.projectRoot, 'behavior_pack'),
      path.join(this.projectRoot, 'behaviorPacks'),
    ];

    for (const p of possiblePaths) {
      if (fs.existsSync(p)) {
        return p;
      }
    }

    // 尝试递归查找（深度限制为2层）
    try {
      const result = execSync(`find "${this.projectRoot}" -maxdepth 2 -type d -name "behavior_pack*"`, {
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'ignore']
      }).trim();

      if (result) {
        return result.split('\n')[0]; // 取第一个匹配
      }
    } catch (e) {
      // find命令失败，忽略
    }

    return null;
  }

  /**
   * 扫描所有Python类定义
   */
  async scanAllClasses() {
    try {
      // 使用grep搜索所有class定义
      const result = execSync(
        `grep -r "^class " "${this.behaviorPackPath}" --include="*.py" || true`,
        { encoding: 'utf-8', maxBuffer: 10 * 1024 * 1024 }
      );

      const classes = [];
      const lines = result.split('\n').filter(l => l.trim());

      for (const line of lines) {
        const match = line.match(/^([^:]+):class\s+(\w+)/);
        if (match) {
          const [, filePath, className] = match;
          classes.push({
            className,
            filePath: filePath.trim(),
            fileDir: path.dirname(filePath.trim())
          });
        }
      }

      return classes;
    } catch (error) {
      console.error('扫描类定义失败:', error.message);
      return [];
    }
  }

  /**
   * 识别MODSDK官方核心概念（System和Component）
   */
  async identifyOfficialConcepts(allClasses) {
    console.log('🎯 识别MODSDK官方核心概念...\n');

    // 识别System（ServerSystem/ClientSystem）
    for (const cls of allClasses) {
      if (cls.className.endsWith('ServerSystem') || cls.className.endsWith('ClientSystem')) {
        this.discoveredPatterns.officialConcepts.systems.push(cls);
      }
    }

    // 识别Component（查找RegisterComponent调用）
    // TODO: 实现Component识别（需要分析代码调用）

    console.log(`  ✅ 发现 ${this.discoveredPatterns.officialConcepts.systems.length} 个System类`);
    console.log(`  ✅ 发现 ${this.discoveredPatterns.officialConcepts.components.length} 个Component类\n`);
  }

  /**
   * 推断项目自定义模式
   */
  async inferCustomPatterns(allClasses) {
    console.log('🔮 推断项目自定义组织模式...\n');

    // 提取所有类名后缀
    const suffixCounts = {};
    const suffixExamples = {};

    for (const cls of allClasses) {
      // 跳过已识别的System
      if (cls.className.endsWith('ServerSystem') || cls.className.endsWith('ClientSystem')) {
        continue;
      }

      // 识别后缀（大写字母开头的单词）
      const match = cls.className.match(/([A-Z][a-z]+)$/);
      if (match) {
        const suffix = match[1];
        suffixCounts[suffix] = (suffixCounts[suffix] || 0) + 1;

        if (!suffixExamples[suffix]) {
          suffixExamples[suffix] = [];
        }
        suffixExamples[suffix].push(cls);
      }
    }

    // 筛选：出现3次以上的后缀认为是项目使用的模式
    for (const [suffix, count] of Object.entries(suffixCounts)) {
      if (count >= 3) {
        this.discoveredPatterns.customPatterns[suffix.toLowerCase()] = {
          suffix: suffix,
          count: count,
          examples: suffixExamples[suffix].slice(0, 5), // 最多保留5个示例
          docDirCandidate: this.guessDocDir(suffix) // 推断文档目录名
        };

        console.log(`  ✅ 发现 [${suffix}模式] - ${count}个类`);
      }
    }

    console.log('');
  }

  /**
   * 推断文档目录名
   */
  guessDocDir(suffix) {
    // 规则：
    // State -> states/
    // Preset -> presets/
    // Manager -> managers/
    // 等等
    const lower = suffix.toLowerCase();
    return `${lower}s/`; // 简单复数化
  }

  /**
   * 推断目录结构（检查是否已有分类目录）
   */
  async inferDirectoryLayout() {
    console.log('📁 推断目录结构...\n');

    const markdownDir = path.join(this.projectRoot, 'markdown');
    if (!fs.existsSync(markdownDir)) {
      console.log('  ℹ️  markdown/目录不存在，将使用推断的目录结构\n');
      return;
    }

    // 检查已存在的子目录
    const existingDirs = fs.readdirSync(markdownDir, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);

    console.log(`  📂 已存在的目录: ${existingDirs.join(', ')}\n`);

    // 更新customPatterns的docDirCandidate，优先使用已存在的目录
    for (const [patternKey, pattern] of Object.entries(this.discoveredPatterns.customPatterns)) {
      const guessedDir = pattern.docDirCandidate;
      const dirName = guessedDir.replace('/', '');

      if (existingDirs.includes(dirName)) {
        pattern.docDirCandidate = guessedDir;
        pattern.docDirExists = true;
      } else {
        pattern.docDirExists = false;
      }
    }
  }

  /**
   * 生成文档路径映射
   */
  generateDocPathMap() {
    const pathMap = {
      // System映射
      system: (className) => {
        // ShopServerSystem -> markdown/systems/商店系统.md（需要AI推断中文名）
        return {
          dir: 'markdown/systems/',
          pattern: 'System',
          needsChineseNaming: true
        };
      }
    };

    // 为每个自定义模式生成映射
    for (const [patternKey, pattern] of Object.entries(this.discoveredPatterns.customPatterns)) {
      pathMap[patternKey] = (className) => {
        return {
          dir: `markdown/${pattern.docDirCandidate}`,
          pattern: pattern.suffix,
          needsChineseNaming: true,
          exists: pattern.docDirExists
        };
      };
    }

    return pathMap;
  }

  /**
   * 打印发现报告
   */
  printDiscoveryReport() {
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 自适应发现报告');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('## MODSDK官方核心概念\n');
    console.log(`  📦 Systems: ${this.discoveredPatterns.officialConcepts.systems.length}个`);
    this.discoveredPatterns.officialConcepts.systems.slice(0, 3).forEach(cls => {
      console.log(`     - ${cls.className}`);
    });
    if (this.discoveredPatterns.officialConcepts.systems.length > 3) {
      console.log(`     ... 等${this.discoveredPatterns.officialConcepts.systems.length}个`);
    }
    console.log('');

    console.log('## 项目自定义组织模式\n');
    const patternCount = Object.keys(this.discoveredPatterns.customPatterns).length;

    if (patternCount === 0) {
      console.log('  ℹ️  未发现项目自定义模式（这是正常的，说明项目只使用了MODSDK官方概念）\n');
    } else {
      for (const [key, pattern] of Object.entries(this.discoveredPatterns.customPatterns)) {
        const status = pattern.docDirExists ? '✅ 已存在' : '📝 需创建';
        console.log(`  🔹 [${pattern.suffix}模式] - ${pattern.count}个类`);
        console.log(`     文档目录: ${pattern.docDirCandidate} ${status}`);
        console.log(`     示例: ${pattern.examples.slice(0, 2).map(e => e.className).join(', ')}`);
        console.log('');
      }
    }

    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
  }

  /**
   * 导出发现结果到JSON（供其他工具使用）
   */
  exportToJSON(outputPath) {
    const result = {
      timestamp: new Date().toISOString(),
      projectRoot: this.projectRoot,
      behaviorPackPath: this.behaviorPackPath,
      patterns: this.discoveredPatterns
    };

    fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), 'utf-8');
    console.log(`✅ 发现结果已导出到: ${outputPath}\n`);
  }
}

// 导出
module.exports = { AdaptiveDocDiscovery };

// CLI支持（如果直接运行）
if (require.main === module) {
  const projectRoot = process.argv[2] || process.cwd();

  console.log('🚀 启动自适应文档发现系统\n');
  console.log(`📍 项目根目录: ${projectRoot}\n`);

  const discovery = new AdaptiveDocDiscovery(projectRoot);

  discovery.discoverProjectStructure().then(result => {
    if (result) {
      // 导出结果
      const outputPath = path.join(projectRoot, '.claude', 'discovered-patterns.json');
      discovery.exportToJSON(outputPath);

      console.log('✅ 自适应发现完成！');
    } else {
      console.log('❌ 发现失败：不是有效的MODSDK项目');
      process.exit(1);
    }
  }).catch(error => {
    console.error('❌ 发生错误:', error);
    process.exit(1);
  });
}
