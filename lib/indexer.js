/**
 * 文档索引生成器
 * 扫描项目中的所有文档和任务，生成全局索引
 */

const fs = require('fs');
const path = require('path');
const { walkDir, readFile, writeFile } = require('./utils');
const { extractKeywords } = require('./metadata-schema');

/**
 * 文档索引器
 */
class DocumentIndexer {
  constructor(projectPath) {
    this.projectPath = projectPath;
    this.index = {
      tasks: [],           // 任务索引
      systems: [],         // 系统文档索引
      guides: [],          // 指南文档索引
      references: [],      // 参考文档索引
      tagMap: {},          // 标签映射
      systemMap: {},       // System映射
      keywordMap: {}       // 关键词映射
    };
  }

  /**
   * 构建完整索引
   */
  buildIndex() {
    console.log('[索引器] 开始构建文档索引...');

    // 1. 扫描任务目录
    this._indexTasks();

    // 2. 扫描系统文档
    this._indexSystems();

    // 3. 扫描指南文档
    this._indexGuides();

    // 4. 构建反向索引（标签、关键词）
    this._buildReverseIndex();

    console.log('[索引器] 索引构建完成！');
    console.log(`  - 任务: ${this.index.tasks.length}`);
    console.log(`  - 系统文档: ${this.index.systems.length}`);
    console.log(`  - 指南文档: ${this.index.guides.length}`);
    console.log(`  - 标签: ${Object.keys(this.index.tagMap).length}`);
    console.log(`  - 关键词: ${Object.keys(this.index.keywordMap).length}`);

    return this.index;
  }

  /**
   * 扫描任务目录
   */
  _indexTasks() {
    const tasksDir = path.join(this.projectPath, 'tasks');
    if (!fs.existsSync(tasksDir)) {
      console.log('[索引器] tasks目录不存在，跳过');
      return;
    }

    // 扫描 tasks/ 和 tasks/completed/
    const taskDirs = [tasksDir];
    const completedDir = path.join(tasksDir, 'completed');
    if (fs.existsSync(completedDir)) {
      taskDirs.push(completedDir);
    }

    for (const dir of taskDirs) {
      const entries = fs.readdirSync(dir, { withFileTypes: true });

      for (const entry of entries) {
        if (!entry.isDirectory()) continue;
        if (entry.name === 'completed') continue;

        const taskPath = path.join(dir, entry.name);
        const taskItem = this._indexTaskDir(taskPath, entry.name);
        if (taskItem) {
          this.index.tasks.push(taskItem);
        }
      }
    }
  }

  /**
   * 索引单个任务目录
   * @param {string} taskPath - 任务目录路径
   * @param {string} taskName - 任务名称
   * @returns {Object|null}
   */
  _indexTaskDir(taskPath, taskName) {
    // 检查是否有 metadata.json
    const metadataPath = path.join(taskPath, 'metadata.json');
    let metadata = null;

    if (fs.existsSync(metadataPath)) {
      try {
        metadata = JSON.parse(readFile(metadataPath));
      } catch (err) {
        console.log(`[索引器] 警告: 读取metadata失败 ${metadataPath}`);
      }
    }

    // 如果没有metadata，尝试读取"完整上下文.md"
    if (!metadata) {
      const contextPath = path.join(taskPath, '完整上下文.md');
      if (fs.existsSync(contextPath)) {
        const content = readFile(contextPath);
        metadata = this._extractMetadataFromContext(content, taskName);
      }
    }

    if (!metadata) {
      return null;
    }

    // 确定状态
    const isCompleted = taskPath.includes('completed');
    if (isCompleted && metadata.status === '进行中') {
      metadata.status = '已完成';
    }

    return {
      type: 'task',
      path: path.relative(this.projectPath, taskPath),
      name: taskName,
      metadata,
      lastModified: this._getLastModified(taskPath)
    };
  }

  /**
   * 从完整上下文.md提取元数据
   * @param {string} content - 文档内容
   * @param {string} taskName - 任务名称
   * @returns {Object}
   */
  _extractMetadataFromContext(content, taskName) {
    const metadata = {
      taskName,
      taskType: '🟡 标准任务',
      tags: [],
      relatedSystems: [],
      relatedDocs: [],
      keywords: [],
      status: '进行中'
    };

    // 提取任务类型
    const typeMatch = content.match(/任务类型[：:]\s*([🟢🟡🔴]\s*[^\n]+)/);
    if (typeMatch) {
      metadata.taskType = typeMatch[1].trim();
    }

    // 提取关联系统
    const systemMatches = content.match(/[A-Z][a-zA-Z]+System/g);
    if (systemMatches) {
      metadata.relatedSystems = [...new Set(systemMatches)];
    }

    // 提取关键词
    metadata.keywords = extractKeywords(content, 10);

    return metadata;
  }

  /**
   * 扫描系统文档
   */
  _indexSystems() {
    const systemsDir = path.join(this.projectPath, 'markdown', 'systems');
    if (!fs.existsSync(systemsDir)) {
      console.log('[索引器] markdown/systems目录不存在，跳过');
      return;
    }

    walkDir(systemsDir, (filePath) => {
      if (!filePath.endsWith('.md')) return;
      if (filePath.endsWith('README.md')) return;

      const systemItem = this._indexSystemDoc(filePath);
      if (systemItem) {
        this.index.systems.push(systemItem);
      }
    });
  }

  /**
   * 索引单个系统文档
   * @param {string} filePath - 文档路径
   * @returns {Object|null}
   */
  _indexSystemDoc(filePath) {
    const content = readFile(filePath);
    const metadata = this._parseYAMLFrontMatter(content);

    // 如果没有YAML Front Matter，从内容提取
    if (!metadata.systemName) {
      const fileName = path.basename(filePath, '.md');
      metadata.systemName = fileName;
      metadata.systemType = 'Unknown';
      metadata.tags = extractKeywords(content, 5);
    }

    return {
      type: 'system',
      path: path.relative(this.projectPath, filePath),
      name: metadata.systemName,
      metadata,
      lastModified: this._getLastModified(filePath)
    };
  }

  /**
   * 解析YAML Front Matter
   * @param {string} content - 文档内容
   * @returns {Object}
   */
  _parseYAMLFrontMatter(content) {
    const match = content.match(/^---\n([\s\S]*?)\n---/);
    if (!match) {
      return {};
    }

    const yaml = match[1];
    const metadata = {};

    // 简单YAML解析（仅支持基本格式）
    const lines = yaml.split('\n');
    for (const line of lines) {
      const colonIndex = line.indexOf(':');
      if (colonIndex === -1) continue;

      const key = line.substring(0, colonIndex).trim();
      const value = line.substring(colonIndex + 1).trim();

      // 处理数组 (格式: [item1, item2])
      if (value.startsWith('[') && value.endsWith(']')) {
        metadata[key] = value
          .substring(1, value.length - 1)
          .split(',')
          .map(item => item.trim())
          .filter(Boolean);
      } else {
        metadata[key] = value;
      }
    }

    return metadata;
  }

  /**
   * 扫描指南文档
   */
  _indexGuides() {
    const markdownDir = path.join(this.projectPath, 'markdown');
    if (!fs.existsSync(markdownDir)) {
      console.log('[索引器] markdown目录不存在，跳过');
      return;
    }

    const guideFiles = [
      '开发规范.md',
      '问题排查.md',
      '快速开始.md',
      '开发指南.md',
      '项目状态.md'
    ];

    for (const fileName of guideFiles) {
      const filePath = path.join(markdownDir, fileName);
      if (!fs.existsSync(filePath)) continue;

      const content = readFile(filePath);
      const title = this._extractTitle(content) || fileName;

      this.index.guides.push({
        type: 'guide',
        path: path.relative(this.projectPath, filePath),
        name: fileName.replace('.md', ''),
        title,
        keywords: extractKeywords(content, 15),
        lastModified: this._getLastModified(filePath)
      });
    }
  }

  /**
   * 构建反向索引
   */
  _buildReverseIndex() {
    // 所有索引项
    const allItems = [
      ...this.index.tasks,
      ...this.index.systems,
      ...this.index.guides
    ];

    // 构建标签映射
    for (const item of allItems) {
      const tags = item.metadata?.tags || item.keywords || [];
      for (const tag of tags) {
        if (!this.index.tagMap[tag]) {
          this.index.tagMap[tag] = [];
        }
        this.index.tagMap[tag].push({
          type: item.type,
          path: item.path,
          name: item.name
        });
      }
    }

    // 构建System映射
    for (const item of this.index.tasks) {
      const systems = item.metadata?.relatedSystems || [];
      for (const systemName of systems) {
        if (!this.index.systemMap[systemName]) {
          this.index.systemMap[systemName] = [];
        }
        this.index.systemMap[systemName].push({
          type: 'task',
          path: item.path,
          name: item.name
        });
      }
    }

    // 构建关键词映射
    for (const item of allItems) {
      const keywords = item.metadata?.keywords || item.keywords || [];
      for (const keyword of keywords) {
        if (!this.index.keywordMap[keyword]) {
          this.index.keywordMap[keyword] = [];
        }
        this.index.keywordMap[keyword].push({
          type: item.type,
          path: item.path,
          name: item.name
        });
      }
    }
  }

  /**
   * 生成Markdown格式的索引文档
   * @returns {string}
   */
  generateMarkdown() {
    const lines = [];

    lines.push('# 📚 文档索引\n');
    lines.push('> **自动生成** - 最后更新: ' + new Date().toISOString().split('T')[0]);
    lines.push('>\n> 本文档由索引器自动生成，包含项目中所有文档和任务的索引。\n');

    // 1. 按标签分类
    lines.push('## 🏷️ 按标签分类\n');
    const sortedTags = Object.keys(this.index.tagMap).sort();
    for (const tag of sortedTags.slice(0, 20)) { // 只显示前20个
      const items = this.index.tagMap[tag];
      lines.push(`### ${tag} (${items.length})\n`);
      for (const item of items.slice(0, 5)) { // 每个标签最多显示5个
        const icon = this._getTypeIcon(item.type);
        lines.push(`- ${icon} [${item.name}](${item.path})`);
      }
      if (items.length > 5) {
        lines.push(`- _...等${items.length - 5}个_`);
      }
      lines.push('');
    }

    // 2. 按System分类
    if (Object.keys(this.index.systemMap).length > 0) {
      lines.push('## 🔧 按System分类\n');
      const sortedSystems = Object.keys(this.index.systemMap).sort();
      for (const systemName of sortedSystems) {
        const tasks = this.index.systemMap[systemName];
        lines.push(`### ${systemName} (${tasks.length}个任务)\n`);
        for (const task of tasks.slice(0, 3)) {
          lines.push(`- 📋 [${task.name}](${task.path})`);
        }
        if (tasks.length > 3) {
          lines.push(`- _...等${tasks.length - 3}个_`);
        }
        lines.push('');
      }
    }

    // 3. 所有任务列表
    if (this.index.tasks.length > 0) {
      lines.push('## 📋 任务列表\n');
      lines.push('| 任务名称 | 类型 | 状态 | 关联Systems | 最后修改 |');
      lines.push('|---------|------|------|------------|----------|');

      const sortedTasks = this.index.tasks.sort((a, b) => {
        return new Date(b.lastModified) - new Date(a.lastModified);
      });

      for (const task of sortedTasks.slice(0, 20)) {
        const taskType = task.metadata?.taskType || '未知';
        const status = task.metadata?.status || '未知';
        const systems = (task.metadata?.relatedSystems || []).slice(0, 2).join(', ');
        const systemsText = systems || '-';
        lines.push(`| [${task.name}](${task.path}) | ${taskType} | ${status} | ${systemsText} | ${task.lastModified} |`);
      }

      if (sortedTasks.length > 20) {
        lines.push(`| _...等${sortedTasks.length - 20}个_ | | | | |`);
      }
      lines.push('');
    }

    // 4. 系统文档列表
    if (this.index.systems.length > 0) {
      lines.push('## 📖 系统文档列表\n');
      lines.push('| System名称 | 类型 | 复杂度 | 标签 |');
      lines.push('|-----------|------|--------|------|');

      for (const system of this.index.systems) {
        const systemType = system.metadata?.systemType || 'Unknown';
        const complexity = system.metadata?.complexity || '-';
        const tags = (system.metadata?.tags || []).slice(0, 3).join(', ');
        lines.push(`| [${system.name}](${system.path}) | ${systemType} | ${complexity} | ${tags} |`);
      }
      lines.push('');
    }

    // 5. 快速搜索提示
    lines.push('## 🔍 快速搜索提示\n');
    lines.push('使用 `/cc 搜索` 命令进行智能检索：\n');
    lines.push('```bash');
    lines.push('# 按标签搜索');
    lines.push('/cc 搜索 tag:双端通信\n');
    lines.push('# 按System搜索');
    lines.push('/cc 搜索 system:ShopSystem\n');
    lines.push('# 按关键词搜索');
    lines.push('/cc 搜索 商店购买\n');
    lines.push('# 按时间范围搜索');
    lines.push('/cc 搜索 关键词 after:2025-11-01');
    lines.push('```\n');

    return lines.join('\n');
  }

  /**
   * 保存索引到JSON文件
   * @param {string} outputPath - 输出路径
   */
  saveToJSON(outputPath) {
    const json = JSON.stringify(this.index, null, 2);
    writeFile(outputPath, json);
    console.log(`[索引器] 索引已保存到: ${outputPath}`);
  }

  /**
   * 保存索引到Markdown文件
   * @param {string} outputPath - 输出路径
   */
  saveToMarkdown(outputPath) {
    const markdown = this.generateMarkdown();
    writeFile(outputPath, markdown);
    console.log(`[索引器] Markdown索引已保存到: ${outputPath}`);
  }

  /**
   * 获取文件最后修改时间
   * @param {string} filePath
   * @returns {string}
   */
  _getLastModified(filePath) {
    try {
      const stats = fs.statSync(filePath);
      return stats.mtime.toISOString().split('T')[0];
    } catch {
      return new Date().toISOString().split('T')[0];
    }
  }

  /**
   * 从内容提取标题
   * @param {string} content
   * @returns {string|null}
   */
  _extractTitle(content) {
    const match = content.match(/^#\s+(.+)$/m);
    return match ? match[1].trim() : null;
  }

  /**
   * 获取类型图标
   * @param {string} type
   * @returns {string}
   */
  _getTypeIcon(type) {
    const icons = {
      task: '📋',
      system: '🔧',
      guide: '📖'
    };
    return icons[type] || '📄';
  }
}

// CLI入口
if (require.main === module) {
  const projectPath = process.argv[2] || process.cwd();

  console.log('[索引器] 项目路径:', projectPath);

  const indexer = new DocumentIndexer(projectPath);
  indexer.buildIndex();

  // 保存到两种格式
  const jsonPath = path.join(projectPath, '.claude', 'doc-index.json');
  const mdPath = path.join(projectPath, 'markdown', '索引.md');

  // 确保.claude目录存在
  const fs = require('fs');
  const claudeDir = path.join(projectPath, '.claude');
  if (!fs.existsSync(claudeDir)) {
    fs.mkdirSync(claudeDir, { recursive: true });
  }

  indexer.saveToJSON(jsonPath);
  indexer.saveToMarkdown(mdPath);

  console.log('[索引器] 完成！');
}

module.exports = {
  DocumentIndexer
};
