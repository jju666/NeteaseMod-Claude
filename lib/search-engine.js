/**
 * 智能检索引擎
 * 支持多维度检索：标签、关键词、System名、时间范围
 */

const fs = require('fs');
const path = require('path');
const { DocumentIndexer } = require('./indexer');

/**
 * 搜索引擎
 */
class SearchEngine {
  constructor(projectPath) {
    this.projectPath = projectPath;
    this.indexPath = path.join(projectPath, '.claude', 'doc-index.json');
    this.index = null;
  }

  /**
   * 加载索引（如果不存在则构建）
   */
  loadIndex() {
    if (fs.existsSync(this.indexPath)) {
      console.log('[检索] 加载已有索引...');
      this.index = JSON.parse(fs.readFileSync(this.indexPath, 'utf8'));
    } else {
      console.log('[检索] 索引不存在，正在构建...');
      const indexer = new DocumentIndexer(this.projectPath);
      this.index = indexer.buildIndex();

      // 保存索引
      const claudeDir = path.dirname(this.indexPath);
      if (!fs.existsSync(claudeDir)) {
        fs.mkdirSync(claudeDir, { recursive: true });
      }
      fs.writeFileSync(this.indexPath, JSON.stringify(this.index, null, 2));
    }
  }

  /**
   * 搜索（主入口）
   * @param {string} query - 查询字符串
   * @param {Object} options - 选项
   * @returns {Array} 搜索结果
   */
  search(query, options = {}) {
    if (!this.index) {
      this.loadIndex();
    }

    const {
      type = null,        // 类型过滤: 'task' | 'system' | 'guide'
      limit = 10,         // 结果数量限制
      after = null,       // 时间过滤: 'YYYY-MM-DD'
      before = null       // 时间过滤: 'YYYY-MM-DD'
    } = options;

    // 解析查询
    const queryInfo = this._parseQuery(query);

    // 执行搜索
    let results = [];

    if (queryInfo.tag) {
      results = this._searchByTag(queryInfo.tag);
    } else if (queryInfo.system) {
      results = this._searchBySystem(queryInfo.system);
    } else if (queryInfo.keyword) {
      results = this._searchByKeyword(queryInfo.keyword);
    } else {
      // 全文搜索
      results = this._searchFullText(query);
    }

    // 应用过滤器
    if (type) {
      results = results.filter(r => r.type === type);
    }

    if (after) {
      results = results.filter(r => r.lastModified >= after);
    }

    if (before) {
      results = results.filter(r => r.lastModified <= before);
    }

    // 按相关度排序
    results = this._rankResults(results, query);

    // 限制结果数量
    return results.slice(0, limit);
  }

  /**
   * 解析查询字符串
   * @param {string} query
   * @returns {Object}
   */
  _parseQuery(query) {
    const result = {
      tag: null,
      system: null,
      keyword: null
    };

    // tag:标签名
    const tagMatch = query.match(/tag:(\S+)/);
    if (tagMatch) {
      result.tag = tagMatch[1];
      return result;
    }

    // system:SystemName
    const systemMatch = query.match(/system:(\S+)/);
    if (systemMatch) {
      result.system = systemMatch[1];
      return result;
    }

    // keyword:关键词
    const keywordMatch = query.match(/keyword:(\S+)/);
    if (keywordMatch) {
      result.keyword = keywordMatch[1];
      return result;
    }

    // 默认作为关键词
    result.keyword = query.trim();
    return result;
  }

  /**
   * 按标签搜索
   * @param {string} tag
   * @returns {Array}
   */
  _searchByTag(tag) {
    const tagMap = this.index.tagMap || {};
    const items = tagMap[tag] || [];

    // 展开为完整对象
    return items.map(item => this._getFullItem(item));
  }

  /**
   * 按System搜索
   * @param {string} systemName
   * @returns {Array}
   */
  _searchBySystem(systemName) {
    const systemMap = this.index.systemMap || {};
    const items = systemMap[systemName] || [];

    // 包含相关任务
    const results = items.map(item => this._getFullItem(item));

    // 同时返回System文档本身
    const systemDoc = this.index.systems.find(s => s.name === systemName);
    if (systemDoc) {
      results.unshift(systemDoc);
    }

    return results;
  }

  /**
   * 按关键词搜索
   * @param {string} keyword
   * @returns {Array}
   */
  _searchByKeyword(keyword) {
    const keywordMap = this.index.keywordMap || {};

    // 精确匹配
    const exactItems = keywordMap[keyword] || [];
    const results = exactItems.map(item => this._getFullItem(item));

    // 模糊匹配（关键词包含查询词）
    const lowerKeyword = keyword.toLowerCase();
    for (const [key, items] of Object.entries(keywordMap)) {
      if (key.toLowerCase().includes(lowerKeyword) && key !== keyword) {
        results.push(...items.map(item => this._getFullItem(item)));
      }
    }

    // 去重
    const seen = new Set();
    return results.filter(item => {
      const id = item.path;
      if (seen.has(id)) return false;
      seen.add(id);
      return true;
    });
  }

  /**
   * 全文搜索
   * @param {string} query
   * @returns {Array}
   */
  _searchFullText(query) {
    const lowerQuery = query.toLowerCase();
    const results = [];

    // 搜索所有项
    const allItems = [
      ...this.index.tasks,
      ...this.index.systems,
      ...this.index.guides
    ];

    for (const item of allItems) {
      // 检查名称
      if (item.name && item.name.toLowerCase().includes(lowerQuery)) {
        results.push({ ...item, matchField: 'name' });
        continue;
      }

      // 检查标题
      if (item.title && item.title.toLowerCase().includes(lowerQuery)) {
        results.push({ ...item, matchField: 'title' });
        continue;
      }

      // 检查关键词
      const keywords = item.metadata?.keywords || item.keywords || [];
      if (keywords.some(k => k.toLowerCase().includes(lowerQuery))) {
        results.push({ ...item, matchField: 'keywords' });
        continue;
      }

      // 检查描述
      if (item.metadata?.description) {
        if (item.metadata.description.toLowerCase().includes(lowerQuery)) {
          results.push({ ...item, matchField: 'description' });
        }
      }
    }

    return results;
  }

  /**
   * 结果排序（按相关度）
   * @param {Array} results
   * @param {string} query
   * @returns {Array}
   */
  _rankResults(results, query) {
    const lowerQuery = query.toLowerCase();

    return results.map(item => {
      let score = 0;

      // 名称完全匹配 +10
      if (item.name && item.name.toLowerCase() === lowerQuery) {
        score += 10;
      }
      // 名称包含 +5
      else if (item.name && item.name.toLowerCase().includes(lowerQuery)) {
        score += 5;
      }

      // 匹配字段加分
      if (item.matchField === 'name') score += 3;
      if (item.matchField === 'title') score += 2;
      if (item.matchField === 'keywords') score += 1;

      // 类型权重
      if (item.type === 'system') score += 2;
      if (item.type === 'task') score += 1;

      // 最近修改加分
      if (item.lastModified) {
        const daysDiff = this._getDaysDiff(item.lastModified);
        if (daysDiff < 7) score += 3;
        else if (daysDiff < 30) score += 1;
      }

      return { ...item, relevanceScore: score };
    }).sort((a, b) => b.relevanceScore - a.relevanceScore);
  }

  /**
   * 获取完整项信息
   * @param {Object} item
   * @returns {Object}
   */
  _getFullItem(item) {
    const collections = {
      task: this.index.tasks,
      system: this.index.systems,
      guide: this.index.guides
    };

    const collection = collections[item.type];
    if (!collection) return item;

    return collection.find(i => i.path === item.path) || item;
  }

  /**
   * 计算距今天数
   * @param {string} dateStr - YYYY-MM-DD
   * @returns {number}
   */
  _getDaysDiff(dateStr) {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now - date;
    return Math.floor(diff / (1000 * 60 * 60 * 24));
  }

  /**
   * 格式化输出结果
   * @param {Array} results
   * @returns {string}
   */
  formatResults(results) {
    if (results.length === 0) {
      return '未找到匹配结果';
    }

    const lines = [];
    lines.push(`# 搜索结果 (共${results.length}个)\n`);

    for (const item of results) {
      const icon = this._getTypeIcon(item.type);
      const score = item.relevanceScore !== undefined ? ` (相关度: ${item.relevanceScore})` : '';

      lines.push(`## ${icon} ${item.name}${score}\n`);
      lines.push(`**类型**: ${item.type}`);
      lines.push(`**路径**: [${item.path}](${item.path})`);

      if (item.lastModified) {
        lines.push(`**最后修改**: ${item.lastModified}`);
      }

      // 任务特有信息
      if (item.type === 'task' && item.metadata) {
        lines.push(`**任务类型**: ${item.metadata.taskType}`);
        lines.push(`**状态**: ${item.metadata.status}`);
        if (item.metadata.relatedSystems && item.metadata.relatedSystems.length > 0) {
          lines.push(`**关联Systems**: ${item.metadata.relatedSystems.join(', ')}`);
        }
      }

      // 系统特有信息
      if (item.type === 'system' && item.metadata) {
        lines.push(`**System类型**: ${item.metadata.systemType}`);
        if (item.metadata.complexity) {
          lines.push(`**复杂度**: ${item.metadata.complexity}`);
        }
      }

      lines.push('');
    }

    return lines.join('\n');
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
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log('用法: node search-engine.js <查询> [选项]');
    console.log('');
    console.log('查询格式:');
    console.log('  tag:标签名          - 按标签搜索');
    console.log('  system:SystemName   - 按System搜索');
    console.log('  keyword:关键词      - 按关键词搜索');
    console.log('  普通文本            - 全文搜索');
    console.log('');
    console.log('选项:');
    console.log('  --type=task|system|guide  - 类型过滤');
    console.log('  --limit=10                - 结果数量限制');
    console.log('  --after=2025-11-01        - 时间过滤（之后）');
    console.log('  --before=2025-12-01       - 时间过滤（之前）');
    console.log('');
    console.log('示例:');
    console.log('  node search-engine.js "商店"');
    console.log('  node search-engine.js "tag:双端通信"');
    console.log('  node search-engine.js "system:ShopSystem"');
    console.log('  node search-engine.js "商店" --type=task --limit=5');
    process.exit(0);
  }

  const query = args[0];
  const options = {};

  // 解析选项
  for (let i = 1; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith('--')) {
      const [key, value] = arg.substring(2).split('=');
      if (key === 'limit') {
        options.limit = parseInt(value);
      } else if (key === 'type') {
        options.type = value;
      } else if (key === 'after') {
        options.after = value;
      } else if (key === 'before') {
        options.before = value;
      }
    }
  }

  const projectPath = process.cwd();
  const engine = new SearchEngine(projectPath);

  console.log(`[检索] 项目路径: ${projectPath}`);
  console.log(`[检索] 查询: ${query}`);
  console.log('');

  const results = engine.search(query, options);
  const formatted = engine.formatResults(results);

  console.log(formatted);
}

module.exports = {
  SearchEngine
};
