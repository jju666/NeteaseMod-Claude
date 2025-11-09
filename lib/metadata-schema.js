/**
 * 元数据结构标准定义
 * 用于任务和文档的智能检索
 */

/**
 * 任务元数据结构
 * @typedef {Object} TaskMetadata
 * @property {string} taskName - 任务名称
 * @property {string} taskType - 任务类型 (🟢 微任务 | 🟡 标准任务 | 🔴 复杂任务)
 * @property {string[]} tags - 标签列表
 * @property {string[]} relatedSystems - 关联的System名称列表
 * @property {string[]} relatedDocs - 关联的文档路径列表
 * @property {string[]} keywords - 关键词列表
 * @property {string} createdAt - 创建时间 (YYYY-MM-DD)
 * @property {string} completedAt - 完成时间 (YYYY-MM-DD)
 * @property {string} status - 状态 (进行中 | 已完成 | 已归档)
 * @property {string} commitHash - Git提交哈希
 * @property {string} description - 任务描述
 */

/**
 * 系统文档元数据结构 (YAML Front Matter)
 * @typedef {Object} SystemMetadata
 * @property {string} systemName - System名称
 * @property {string} systemType - System类型 (ServerSystem | ClientSystem)
 * @property {string[]} tags - 标签列表
 * @property {string[]} relatedDocs - 关联的文档路径列表
 * @property {string[]} relatedSystems - 关联的其他System名称列表
 * @property {string} complexity - 复杂度 (simple | medium | detailed)
 * @property {number} linesOfCode - 代码行数
 */

/**
 * 文档索引项结构
 * @typedef {Object} DocumentIndex
 * @property {string} path - 文档相对路径
 * @property {string} title - 文档标题
 * @property {string} type - 文档类型 (system | task | guide | reference)
 * @property {string[]} tags - 标签列表
 * @property {string[]} keywords - 关键词列表
 * @property {string} lastModified - 最后修改时间
 * @property {number} relevanceScore - 相关度评分（检索时计算）
 */

/**
 * 创建任务元数据
 * @param {Object} options - 配置选项
 * @returns {TaskMetadata}
 */
function createTaskMetadata(options = {}) {
  const {
    taskName = '',
    taskType = '🟡 标准任务',
    tags = [],
    relatedSystems = [],
    relatedDocs = [],
    keywords = [],
    description = ''
  } = options;

  const now = new Date();
  const dateStr = now.toISOString().split('T')[0];

  return {
    taskName,
    taskType,
    tags,
    relatedSystems,
    relatedDocs,
    keywords,
    createdAt: dateStr,
    completedAt: '',
    status: '进行中',
    commitHash: '',
    description
  };
}

/**
 * 创建系统文档元数据 (YAML Front Matter)
 * @param {Object} systemInfo - System信息对象
 * @returns {string} YAML格式的Front Matter
 */
function createSystemMetadata(systemInfo) {
  const { name, type, complexityScore, linesOfCode } = systemInfo;

  // 根据复杂度评分确定复杂度级别
  let complexity = 'simple';
  if (complexityScore >= 8) {
    complexity = 'detailed';
  } else if (complexityScore >= 5) {
    complexity = 'medium';
  }

  const yaml = `---
systemName: ${name}
systemType: ${type}
tags: []
relatedDocs: []
relatedSystems: []
complexity: ${complexity}
linesOfCode: ${linesOfCode}
---`;

  return yaml;
}

/**
 * 从文档内容中提取关键词
 * @param {string} content - 文档内容
 * @param {number} limit - 最多提取多少个关键词
 * @returns {string[]} 关键词列表
 */
function extractKeywords(content, limit = 10) {
  // 简单实现：提取高频词
  // 排除常见停用词
  const stopWords = new Set([
    '的', '是', '在', '和', '有', '个', '了', '中', '可以', '如果',
    'System', 'self', 'def', 'import', 'from', 'class', 'return',
    'the', 'a', 'an', 'and', 'or', 'but', 'if', 'then', 'else'
  ]);

  // 提取所有单词
  const words = content
    .replace(/[^a-zA-Z\u4e00-\u9fa5]/g, ' ')
    .split(/\s+/)
    .filter(word => word.length > 1 && !stopWords.has(word));

  // 统计词频
  const freq = {};
  for (const word of words) {
    freq[word] = (freq[word] || 0) + 1;
  }

  // 按频率排序，取前N个
  const sorted = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([word]) => word);

  return sorted;
}

/**
 * 从任务上下文中自动提取元数据
 * @param {string} taskContextMd - 完整上下文.md的内容
 * @param {string} taskName - 任务名称
 * @returns {TaskMetadata}
 */
function extractMetadataFromTask(taskContextMd, taskName) {
  const metadata = createTaskMetadata({ taskName });

  // 提取任务类型
  const typeMatch = taskContextMd.match(/任务类型[：:]\s*([🟢🟡🔴]\s*[^\n]+)/);
  if (typeMatch) {
    metadata.taskType = typeMatch[1].trim();
  }

  // 提取涉及模块（作为relatedSystems）
  const modulesSection = taskContextMd.match(/涉及模块[：:]\s*\n([\s\S]*?)(?=\n##|$)/);
  if (modulesSection) {
    const systemNames = modulesSection[1].match(/[A-Z][a-zA-Z]+System/g);
    if (systemNames) {
      metadata.relatedSystems = [...new Set(systemNames)];
    }
  }

  // 提取文档依据（作为relatedDocs）
  const docsSection = taskContextMd.match(/文档依据[：:]\s*\n([\s\S]*?)(?=\n##|$)/);
  if (docsSection) {
    const docLinks = docsSection[1].match(/\[([^\]]+)\]\(([^)]+)\)/g);
    if (docLinks) {
      metadata.relatedDocs = docLinks.map(link => {
        const match = link.match(/\(([^)]+)\)/);
        return match ? match[1] : '';
      }).filter(Boolean);
    }
  }

  // 提取关键词
  metadata.keywords = extractKeywords(taskContextMd, 10);

  // 提取任务目标作为描述
  const goalSection = taskContextMd.match(/任务目标[：:]\s*\n([\s\S]*?)(?=\n##|$)/);
  if (goalSection) {
    metadata.description = goalSection[1].trim().substring(0, 200);
  }

  return metadata;
}

/**
 * 验证元数据完整性
 * @param {TaskMetadata} metadata
 * @returns {Object} { valid: boolean, errors: string[] }
 */
function validateMetadata(metadata) {
  const errors = [];

  if (!metadata.taskName) {
    errors.push('任务名称不能为空');
  }

  if (!['🟢 微任务', '🟡 标准任务', '🔴 复杂任务'].some(type => metadata.taskType.includes(type))) {
    errors.push('任务类型无效');
  }

  if (!metadata.createdAt || !/^\d{4}-\d{2}-\d{2}$/.test(metadata.createdAt)) {
    errors.push('创建时间格式无效');
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

module.exports = {
  createTaskMetadata,
  createSystemMetadata,
  extractKeywords,
  extractMetadataFromTask,
  validateMetadata
};
