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

      // 生成文档
      const docContent = this._generateGenericDoc(file, mapping, componentName);
      const docFileName = this._inferDocFileName(componentName, mapping);

      writeFile(path.join(docDir, docFileName), docContent);
      console.log(`   ✓ 生成文档: ${docFileName}`);
      stats.generated++;
    }
  }

  /**
   * 更新现有文档
   */
  async _updateExistingDocs(mapping, docDir, stats) {
    const componentFiles = this._scanComponentFiles(mapping.codeDir);

    for (const file of componentFiles) {
      const componentName = this._extractComponentName(file);

      // 使用智能检测（复用已有逻辑）
      const existingDoc = this._detectExistingDoc(componentName, docDir, mapping);

      if (existingDoc && existingDoc.quality >= 3) {
        console.log(`   ✓ 保留高质量文档: ${existingDoc.fileName} (${existingDoc.quality}/5)`);
        stats.skipped++;
        continue;
      }

      // 生成或覆盖文档
      const docContent = this._generateGenericDoc(file, mapping, componentName);
      const docFileName = existingDoc ? existingDoc.fileName : this._inferDocFileName(componentName, mapping);

      writeFile(path.join(docDir, docFileName), docContent);
      console.log(`   ✓ ${existingDoc ? '更新' : '新增'}文档: ${docFileName}`);
      stats[existingDoc ? 'updated' : 'generated']++;
    }
  }

  /**
   * 智能检测现有文档（通用版本，支持任意组件类型）
   */
  _detectExistingDoc(componentName, docDir, mapping) {
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

      if (isExactMatch || isContentMatch) {
        const quality = this._assessDocQuality(content);
        candidates.push({
          fileName,
          filePath,
          quality,
          matchType: isExactMatch ? 'exact' : 'content'
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
   * 推断文档文件名
   */
  _inferDocFileName(componentName, mapping) {
    // 对于中文友好的命名，可以考虑使用编号
    // 例如：01-床位预设.md, 02-生成器预设.md
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
