/**
 * 智能文档维护器
 * 为任意类型的组件生成和维护文档
 */

const fs = require('fs');
const path = require('path');
const { ensureDir, readFile, writeFile } = require('./utils');
const { getCurrentDate } = require('./config');

/**
 * 智能文档维护器
 */
class IntelligentDocMaintenance {
  constructor(projectPath) {
    this.projectPath = projectPath;
  }

  /**
   * 维护所有组件的文档
   * @param {Array} mappings - 文档映射关系
   */
  async maintainAllDocs(mappings) {
    console.log('\n[维护器] 开始维护文档...\n');

    let generatedCount = 0;
    let skippedCount = 0;
    let updatedCount = 0;

    for (const mapping of mappings) {
      const result = await this.maintainComponentDocs(mapping);

      generatedCount += result.generated;
      skippedCount += result.skipped;
      updatedCount += result.updated;
    }

    console.log(`\n[维护器] ✅ 文档维护完成：`);
    console.log(`  - 新生成: ${generatedCount} 个文档`);
    console.log(`  - 已跳过: ${skippedCount} 个高质量文档`);
    console.log(`  - 已更新: ${updatedCount} 个文档`);
  }

  /**
   * 维护单个组件的文档
   * @param {Object} mapping - 组件映射
   * @returns {Object} 统计结果
   */
  async maintainComponentDocs(mapping) {
    const stats = { generated: 0, skipped: 0, updated: 0 };
    const docDir = path.join(this.projectPath, mapping.docDir);

    if (!mapping.exists) {
      // 文档目录不存在，创建并生成
      console.log(`[维护器] 📝 新组件类型: ${path.basename(mapping.codeDir)}`);
      await this._generateDocsForNewComponent(mapping, docDir, stats);
    } else {
      // 文档目录存在，检查并补充
      console.log(`[维护器] 🔍 检查已有文档: ${path.basename(mapping.docDir)}`);
      await this._updateExistingDocs(mapping, docDir, stats);
    }

    return stats;
  }

  /**
   * 为新组件生成文档
   */
  async _generateDocsForNewComponent(mapping, docDir, stats) {
    // 1. 创建文档目录
    ensureDir(docDir);

    // 2. 生成 README.md
    const readmeContent = this._generateComponentReadme(mapping);
    writeFile(path.join(docDir, 'README.md'), readmeContent);
    stats.generated++;

    // 3. 扫描组件文件
    const componentFiles = this._scanComponentFiles(mapping.codeDir);
    console.log(`   发现 ${componentFiles.length} 个组件文件`);

    // 4. 为每个文件生成文档
    for (const file of componentFiles) {
      const componentName = this._extractComponentName(file);

      // ⭐ 使用AI智能推断中文文件名
      const chineseFileName = this._inferChineseNameByAI(file, componentName, mapping);

      // 生成文档
      const docContent = this._generateGenericDoc(file, mapping, componentName);

      writeFile(path.join(docDir, chineseFileName), docContent);
      console.log(`   ✓ 生成文档: ${chineseFileName}`);
      stats.generated++;
    }
  }

  /**
   * 更新现有文档
   */
  async _updateExistingDocs(mapping, docDir, stats) {
    const componentFiles = this._scanComponentFiles(mapping.codeDir);

    // ⭐ 学习现有文档的命名模式
    const learnedPatterns = this._learnNamingPatternFromExistingDocs(docDir);

    for (const file of componentFiles) {
      const componentName = this._extractComponentName(file);

      // 使用智能检测（包含学习到的模式）
      const existingDoc = this._detectExistingDoc(componentName, docDir, mapping, learnedPatterns);

      if (existingDoc && existingDoc.quality >= 3) {
        console.log(`   ✓ 保留高质量文档: ${existingDoc.fileName} (${existingDoc.quality}/5)`);
        stats.skipped++;
        continue;
      }

      // 生成或覆盖文档
      const docContent = this._generateGenericDoc(file, mapping, componentName);

      // 使用AI智能推断中文文件名
      const chineseFileName = existingDoc ? existingDoc.fileName : this._inferChineseNameByAI(file, componentName, mapping);

      writeFile(path.join(docDir, chineseFileName), docContent);
      console.log(`   ✓ ${existingDoc ? '更新' : '新增'}文档: ${chineseFileName}`);
      stats[existingDoc ? 'updated' : 'generated']++;
    }
  }

  /**
   * 智能检测现有文档（通用版本，支持任意组件类型）
   */
  _detectExistingDoc(componentName, docDir, mapping, learnedPatterns = null) {
    if (!fs.existsSync(docDir)) {
      return null;
    }

    const files = fs.readdirSync(docDir)
      .filter(f => f.endsWith('.md') && f !== 'README.md');

    const candidates = [];

    for (const fileName of files) {
      const filePath = path.join(docDir, fileName);
      const content = readFile(filePath);

      // 级别1: 精确文件名匹配
      const isExactMatch = fileName === `${componentName}.md`;

      // 级别2: 内容智能匹配
      const isContentMatch = this._isComponentDocMatch(componentName, content, mapping);

      // 级别3: 模式学习匹配（使用学习到的命名模式）
      const isPatternMatch = learnedPatterns && this._matchWithLearnedPattern(
        componentName,
        fileName,
        content,
        learnedPatterns
      );

      if (isExactMatch || isContentMatch || isPatternMatch) {
        const quality = this._assessDocQuality(content);
        candidates.push({
          fileName,
          filePath,
          quality,
          matchType: isExactMatch ? 'exact' : (isContentMatch ? 'content' : 'pattern')
        });
      }
    }

    if (candidates.length === 0) {
      return null;
    }

    // 选择质量最高的
    candidates.sort((a, b) => {
      if (b.quality !== a.quality) return b.quality - a.quality;
      return a.matchType === 'content' ? -1 : 1;
    });

    return candidates[0];
  }

  /**
   * 判断文档内容是否匹配组件
   */
  _isComponentDocMatch(componentName, content, mapping) {
    // 策略1: 标题包含组件名
    const titlePattern = new RegExp(`^#\\s+.*${componentName}`, 'mi');
    if (titlePattern.test(content)) {
      return true;
    }

    // 策略2: 类定义引用
    const classPattern = new RegExp(`class\\s+${componentName}`, 'm');
    if (classPattern.test(content)) {
      return true;
    }

    // 策略3: 去掉后缀的关键词匹配（如 ShopPresetDefServer → Shop）
    const coreNamePatterns = [
      componentName.replace(/(Def)?(Server|Client)$/i, ''),
      componentName.replace(/(Preset|System|Manager|Handler)(Def)?(Server|Client)?$/i, ''),
      componentName.replace(/System$/i, '')
    ];

    for (const coreName of coreNamePatterns) {
      if (coreName !== componentName && coreName.length >= 3) {
        const corePattern = new RegExp(`^#\\s+.*${coreName}`, 'mi');
        if (corePattern.test(content)) {
          return true;
        }
      }
    }

    return false;
  }

  /**
   * 评估文档质量
   */
  _assessDocQuality(content) {
    let score = 0;

    if (/```/.test(content)) score += 1;
    if (/mermaid|graph|flowchart|```diagram/.test(content)) score += 1;
    if (/示例|Example|案例|使用方法|Usage/.test(content)) score += 1;
    if (content.length > 500) score += 1;
    if (!/⚠️\s*\*\*待补充\*\*/.test(content)) score += 1;

    return score;
  }

  /**
   * 扫描组件文件
   */
  _scanComponentFiles(codeDir) {
    if (!fs.existsSync(codeDir)) {
      return [];
    }

    const files = [];
    const entries = fs.readdirSync(codeDir);

    for (const entry of entries) {
      const fullPath = path.join(codeDir, entry);
      const stat = fs.statSync(fullPath);

      if (stat.isFile() && entry.endsWith('.py') && entry !== '__init__.py') {
        files.push(fullPath);
      } else if (stat.isDirectory() && !entry.startsWith('.')) {
        // 递归扫描子目录（仅一层）
        const subFiles = fs.readdirSync(fullPath)
          .filter(f => f.endsWith('.py') && f !== '__init__.py')
          .map(f => path.join(fullPath, f));
        files.push(...subFiles);
      }
    }

    return files;
  }

  /**
   * 提取组件名称（从文件中提取类名）
   */
  _extractComponentName(filePath) {
    try {
      const content = readFile(filePath);

      // 提取主要的类名
      const classPattern = /class\s+(\w+)\s*\(/g;
      const matches = [];
      let match;

      while ((match = classPattern.exec(content)) !== null) {
        matches.push(match[1]);
      }

      if (matches.length > 0) {
        // 返回最长的类名（通常是主类）
        return matches.reduce((a, b) => a.length > b.length ? a : b);
      }
    } catch (err) {
      // 忽略错误
    }

    // 回退：使用文件名
    return path.basename(filePath, '.py');
  }

  /**
   * ⭐ AI智能推断中文名称（核心方法）
   * @param {string} filePath - Python文件路径
   * @param {string} componentName - 类名（如 ShopServerSystem）
   * @param {Object} mapping - 组件映射信息
   * @returns {string} 中文文档名（如 "商店系统.md"）
   */
  _inferChineseNameByAI(filePath, componentName, mapping) {
    // 1. 读取Python文件内容并提取语义信息
    const semanticInfo = this._extractSemanticInfo(filePath, componentName);

    // 2. 基于语义规则推断中文名称
    const chineseName = this._inferNameBySemanticRules(semanticInfo, componentName, mapping);

    return `${chineseName}.md`;
  }

  /**
   * 提取语义信息
   */
  _extractSemanticInfo(filePath, className) {
    const info = {
      className: className,
      docstring: null,
      comments: [],
      methodNames: [],
      fileContent: ''
    };

    try {
      const content = readFile(filePath);
      info.fileContent = content;

      // 提取类的docstring
      const classDocPattern = new RegExp(
        `class\\s+${className}[^:]*:\\s*[\\r\\n]+\\s*"""([\\s\\S]*?)"""`,
        'm'
      );
      const docMatch = content.match(classDocPattern);
      if (docMatch) {
        info.docstring = docMatch[1].trim();
      }

      // 提取注释（# 开头的行，包含中文的）
      const commentPattern = /#\s*(.+)/g;
      let commentMatch;
      while ((commentMatch = commentPattern.exec(content)) !== null) {
        const comment = commentMatch[1].trim();
        // 只保留包含中文或长度>5的注释
        if (/[\u4e00-\u9fa5]/.test(comment) || comment.length > 5) {
          info.comments.push(comment);
        }
      }

      // 提取方法名（推断功能）
      const methodPattern = /def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(/g;
      let methodMatch;
      while ((methodMatch = methodPattern.exec(content)) !== null) {
        if (!methodMatch[1].startsWith('_')) {  // 只取公开方法
          info.methodNames.push(methodMatch[1]);
        }
      }
    } catch (err) {
      console.log(`   [警告] 无法读取文件: ${filePath}`);
    }

    return info;
  }

  /**
   * 基于语义规则推断中文名称
   */
  _inferNameBySemanticRules(info, componentName, mapping) {
    // 策略1: 优先从docstring提取中文（最准确）
    if (info.docstring && /[\u4e00-\u9fa5]/.test(info.docstring)) {
      // 提取第一行中文描述
      const firstLine = info.docstring.split('\n')[0].trim();
      const chineseMatch = firstLine.match(/[\u4e00-\u9fa5]+/);
      if (chineseMatch) {
        console.log(`   [AI命名] docstring中文: ${chineseMatch[0]}`);
        return chineseMatch[0];
      }
    }

    // 策略2: 从注释中提取中文
    for (const comment of info.comments) {
      if (/[\u4e00-\u9fa5]/.test(comment)) {
        const chineseMatch = comment.match(/[\u4e00-\u9fa5]+/);
        if (chineseMatch) {
          console.log(`   [AI命名] 注释中文: ${chineseMatch[0]}`);
          return chineseMatch[0];
        }
      }
    }

    // 策略3: 分析类名结构 + 方法名推断功能
    const functionality = this._inferFunctionality(info.methodNames, componentName);
    const typeSuffix = this._inferTypeSuffix(componentName, mapping);

    // 分解类名（如 ShopServerSystem → Shop + Server + System）
    const classWords = componentName
      .replace(/([A-Z])/g, ' $1')
      .trim()
      .split(/\s+/)
      .filter(w => !['Server', 'Client', 'Def', 'System', 'Preset', 'Manager', 'Handler'].includes(w));

    if (classWords.length > 0) {
      const coreWord = classWords[0];
      const translatedWord = this._translateCoreWord(coreWord);
      console.log(`   [AI命名] 类名分析: ${coreWord} → ${translatedWord}`);
      return `${translatedWord}${typeSuffix}`;
    }

    // 策略4: 回退到组件类型
    return `${componentName}${typeSuffix}`;
  }

  /**
   * 推断功能（从方法名推断）
   */
  _inferFunctionality(methodNames, className) {
    const keywords = {
      buy: '购买',
      sell: '出售',
      shop: '商店',
      team: '队伍',
      game: '游戏',
      player: '玩家',
      spawn: '生成',
      trap: '陷阱',
      upgrade: '升级',
      bed: '床位',
      generator: '生成器',
      npc: 'NPC',
      item: '物品',
      weapon: '武器',
      armor: '护甲',
      tool: '工具',
      resource: '资源',
      coin: '金币',
      point: '点数',
      score: '分数',
      rank: '排名',
      achievement: '成就',
      quest: '任务',
      skill: '技能',
      buff: '增益',
      debuff: '减益',
      damage: '伤害',
      heal: '治疗',
      death: '死亡',
      respawn: '重生',
      teleport: '传送',
      chat: '聊天',
      message: '消息',
      ui: 'UI',
      hud: 'HUD',
      menu: '菜单',
      button: '按钮',
      state: '状态',
      phase: '阶段',
      round: '回合',
      match: '比赛',
      lobby: '大厅',
      waiting: '等待',
      starting: '开始',
      playing: '游戏中',
      ending: '结束',
      winner: '胜利',
      loser: '失败'
    };

    for (const method of methodNames) {
      const lowerMethod = method.toLowerCase();
      for (const [key, value] of Object.entries(keywords)) {
        if (lowerMethod.includes(key)) {
          return value;
        }
      }
    }

    return null;
  }

  /**
   * 推断类型后缀
   */
  _inferTypeSuffix(className, mapping) {
    if (/System$/i.test(className)) return '系统';
    if (/Manager$/i.test(className)) return '管理器';
    if (/Handler$/i.test(className)) return '处理器';
    if (/Preset$/i.test(className)) return '预设';
    if (/State$/i.test(className)) return '状态';
    if (/Controller$/i.test(className)) return '控制器';
    if (/Service$/i.test(className)) return '服务';
    if (/Component$/i.test(className)) return '组件';
    if (/Helper$/i.test(className)) return '辅助器';
    if (/Util$/i.test(className)) return '工具';

    // 根据mapping类型推断
    const type = mapping.subtype || mapping.type;
    if (type === 'system') return '系统';
    if (type === 'preset') return '预设';
    if (type === 'state') return '状态';
    if (type === 'manager') return '管理器';
    if (type === 'handler') return '处理器';

    return '';
  }

  /**
   * 翻译核心词（60+关键词映射）
   */
  _translateCoreWord(coreWord) {
    const dictionary = {
      // 游戏核心
      Shop: '商店',
      Team: '队伍',
      Game: '游戏',
      Player: '玩家',
      Spawn: '生成',
      Trap: '陷阱',
      Upgrade: '升级',
      Bed: '床位',
      Generator: '生成器',
      Npc: 'NPC',
      NPC: 'NPC',

      // 物品相关
      Item: '物品',
      Weapon: '武器',
      Armor: '护甲',
      Tool: '工具',
      Resource: '资源',

      // 货币积分
      Coin: '金币',
      Point: '点数',
      Score: '分数',
      Rank: '排名',

      // 任务成就
      Achievement: '成就',
      Quest: '任务',

      // 战斗相关
      Skill: '技能',
      Buff: '增益',
      Debuff: '减益',
      Damage: '伤害',
      Heal: '治疗',
      Attack: '攻击',
      Defense: '防御',

      // 生命周期
      Death: '死亡',
      Respawn: '重生',
      Teleport: '传送',

      // UI相关
      Chat: '聊天',
      Message: '消息',
      UI: 'UI',
      Hud: 'HUD',
      Menu: '菜单',
      Button: '按钮',
      Panel: '面板',
      Dialog: '对话框',

      // 游戏状态
      State: '状态',
      Phase: '阶段',
      Round: '回合',
      Match: '比赛',
      Lobby: '大厅',
      Waiting: '等待',
      Starting: '开始',
      Playing: '游戏中',
      Ending: '结束',
      Winner: '胜利',
      Loser: '失败',

      // 实体相关
      Entity: '实体',
      Mob: '生物',
      Monster: '怪物',
      Boss: 'Boss',
      Pet: '宠物',

      // 特殊机制
      Portal: '传送门',
      Chest: '箱子',
      Door: '门',
      Button: '按钮',
      Lever: '拉杆',
      Sign: '告示牌',

      // 起床战争特定
      BedWars: '起床战争',
      Iron: '铁',
      Gold: '金',
      Diamond: '钻石',
      Emerald: '绿宝石',
      Golem: '傀儡',

      // 其他常用词
      Core: '核心',
      Main: '主',
      Base: '基础',
      Common: '通用',
      Custom: '自定义',
      Default: '默认',
      Config: '配置',
      Data: '数据',
      Info: '信息',
      Log: '日志',
      Debug: '调试',
      Test: '测试'
    };

    return dictionary[coreWord] || coreWord;
  }

  /**
   * ⭐ 从现有文档学习命名模式
   * @param {string} docDir - 文档目录
   * @returns {Object} 学习到的模式映射
   */
  _learnNamingPatternFromExistingDocs(docDir) {
    const patterns = {};

    if (!fs.existsSync(docDir)) {
      return patterns;
    }

    const files = fs.readdirSync(docDir)
      .filter(f => f.endsWith('.md') && f !== 'README.md');

    for (const fileName of files) {
      const filePath = path.join(docDir, fileName);
      const content = readFile(filePath);

      // 提取类名（从文档内容中）
      const classPattern = /class\s+(\w+)\s*\(/g;
      let match;

      while ((match = classPattern.exec(content)) !== null) {
        const className = match[1];
        const chineseName = path.basename(fileName, '.md');

        // 记录映射关系
        patterns[className] = chineseName;

        // 同时记录简化版本（去掉Server/Client等后缀）
        const simplifiedClassName = className.replace(/(Def)?(Server|Client)$/i, '');
        if (simplifiedClassName !== className) {
          patterns[simplifiedClassName] = chineseName;
        }
      }
    }

    if (Object.keys(patterns).length > 0) {
      console.log(`   [文档学习] 学习到 ${Object.keys(patterns).length} 个命名模式`);
    }

    return patterns;
  }

  /**
   * 使用学习到的模式匹配
   */
  _matchWithLearnedPattern(componentName, fileName, content, learnedPatterns) {
    if (!learnedPatterns || Object.keys(learnedPatterns).length === 0) {
      return false;
    }

    // 尝试精确匹配
    if (learnedPatterns[componentName] === path.basename(fileName, '.md')) {
      return true;
    }

    // 尝试简化版本匹配
    const simplifiedComponentName = componentName.replace(/(Def)?(Server|Client)$/i, '');
    if (learnedPatterns[simplifiedComponentName] === path.basename(fileName, '.md')) {
      return true;
    }

    // 检查文档内容是否引用了该类名
    if (content.includes(componentName)) {
      return true;
    }

    return false;
  }

  /**
   * 推断文档文件名（已弃用，使用 _inferChineseNameByAI 代替）
   */
  _inferDocFileName(componentName, mapping) {
    return `${componentName}.md`;
  }

  /**
   * 生成组件 README
   */
  _generateComponentReadme(mapping) {
    const componentType = mapping.subtype || mapping.type;
    const componentName = path.basename(mapping.codeDir);

    return `# ${componentName} 文档索引

> **组件类型**: ${componentType}
> **代码目录**: \`${mapping.codeDir}\`
> **最后更新**: ${getCurrentDate()}

---

## 📋 组件列表

_待补充：文档将在生成后自动列出_

---

## 📚 使用说明

本目录包含所有 ${componentName} 相关组件的技术文档。

⚠️ **待补充**: 请在后续开发中补充使用说明和最佳实践。

---

_自动生成于 ${getCurrentDate()}_
`;
  }

  /**
   * 生成通用文档（适用于任意组件）
   */
  _generateGenericDoc(filePath, mapping, componentName) {
    const content = readFile(filePath);
    const relativePath = path.relative(this.projectPath, filePath).replace(/\\/g, '/');

    // 提取类信息
    const classes = this._extractClasses(content);
    const methods = this._extractMethods(content);

    const componentType = mapping.subtype || mapping.type;

    return `# ${componentName}

> **类型**: ${componentType}
> **文件路径**: \`${relativePath}\`
> **最后更新**: ${getCurrentDate()}

---

## 📋 概述

${componentName} 是项目中的 ${componentType} 组件。

⚠️ **待补充**: 请在后续开发中补充该组件的详细业务逻辑和使用说明。

---

## 🏗️ 类结构

${classes.length > 0 ? classes.map(cls => `### ${cls.name}

\`\`\`python
${cls.signature}
\`\`\`

**主要方法**:
${cls.methods.slice(0, 10).map(m => `- \`${m}()\``).join('\n')}
${cls.methods.length > 10 ? `\n... 共 ${cls.methods.length} 个方法` : ''}

`).join('\n') : '⚠️ **待补充**: 未检测到类定义'}

---

## 📊 主要方法

${methods.length > 0 ? methods.slice(0, 20).map(m => `- \`${m}()\` - 待补充说明`).join('\n') : '⚠️ **待补充**: 无方法信息'}

${methods.length > 20 ? `\n... 共 ${methods.length} 个方法` : ''}

⚠️ **待补充**: 请在后续开发中补充主要方法的详细说明和示例。

---

## 💡 使用示例

⚠️ **待补充**: 请在后续开发中补充使用示例。

\`\`\`python
# 示例代码
\`\`\`

---

## ❓ 常见问题

⚠️ **待补充**: 在开发过程中遇到问题时补充到此处。

---

## 📚 相关文档

- [开发规范](../开发规范.md)
- [问题排查](../问题排查.md)

---

_最后更新: ${getCurrentDate()} | 自动生成_
`;
  }

  /**
   * 提取类信息
   */
  _extractClasses(content) {
    const classes = [];
    const classPattern = /class\s+(\w+)\s*\(([^)]+)\):/g;
    let match;

    while ((match = classPattern.exec(content)) !== null) {
      const [fullMatch, className, baseClass] = match;
      const methods = this._extractMethodsForClass(content, className);

      classes.push({
        name: className,
        baseClass: baseClass.trim(),
        signature: fullMatch,
        methods: methods
      });
    }

    return classes;
  }

  /**
   * 提取方法名
   */
  _extractMethods(content) {
    const methods = [];
    const methodPattern = /def\s+(\w+)\s*\(/g;
    let match;

    while ((match = methodPattern.exec(content)) !== null) {
      methods.push(match[1]);
    }

    return methods;
  }

  /**
   * 提取特定类的方法
   */
  _extractMethodsForClass(content, className) {
    // 简化版：提取类定义后的方法（直到下一个类或文件结束）
    const classStartPattern = new RegExp(`class\\s+${className}\\s*\\(`);
    const classStartMatch = classStartPattern.exec(content);

    if (!classStartMatch) {
      return [];
    }

    const classContent = content.substring(classStartMatch.index);
    const nextClassMatch = /\nclass\s+\w+\s*\(/.exec(classContent.substring(1));
    const classEndIndex = nextClassMatch ? nextClassMatch.index + 1 : classContent.length;

    const classScope = classContent.substring(0, classEndIndex);

    const methods = [];
    const methodPattern = /def\s+(\w+)\s*\(/g;
    let match;

    while ((match = methodPattern.exec(classScope)) !== null) {
      methods.push(match[1]);
    }

    return methods;
  }
}

module.exports = { IntelligentDocMaintenance };
