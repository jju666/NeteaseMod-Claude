/**
 * 配置和常量
 * 从Python版本翻译而来
 */

const os = require('os');
const path = require('path');
const fs = require('fs');

// 全局安装路径
const GLOBAL_WORKFLOW_HOME = path.join(os.homedir(), '.claude-modsdk-workflow');

// 本地开发路径（lib目录的上一级）
const LOCAL_WORKFLOW_HOME = path.resolve(__dirname, '..');

// 智能选择工作目录：优先使用全局目录，如果不存在则使用本地开发目录
const WORKFLOW_HOME = fs.existsSync(GLOBAL_WORKFLOW_HOME) ? GLOBAL_WORKFLOW_HOME : LOCAL_WORKFLOW_HOME;

// 模板和资源目录
const TEMPLATES_DIR = path.join(WORKFLOW_HOME, 'templates');
const RULES_LIBRARY_DIR = path.join(WORKFLOW_HOME, 'rules-library');
const DOC_TEMPLATES_DIR = path.join(WORKFLOW_HOME, 'doc-templates');

// 官方文档资源（在线）
const MODSDK_WIKI_URL = 'https://github.com/EaseCation/netease-modsdk-wiki';
const BEDROCK_WIKI_URL = 'https://github.com/Bedrock-OSS/bedrock-wiki';

// 版本号
const VERSION = '17.3.0';

// 文档详细度配置
const DETAIL_LEVELS = {
  simple: {
    wordCount: 500,
    description: '简单文档（类结构、方法列表）'
  },
  medium: {
    wordCount: 1500,
    description: '中等详细度（架构、数据流、API）'
  },
  detailed: {
    wordCount: 3000,
    description: '详细文档（完整业务逻辑、示例）'
  }
};

// 复杂度评分阈值
const COMPLEXITY_THRESHOLDS = {
  detailed: 8,   // score >= 8 → detailed
  medium: 5      // score >= 5 → medium, < 5 → simple
};

// 项目规模阈值
const SCALE_THRESHOLDS = {
  small: 10,     // ≤10 Systems
  medium: 30     // 11-30 Systems, >30 → large
};

// 文档质量评估阈值
const QUALITY_THRESHOLDS = {
  high: 80,      // ≥80分 → 保留
  medium: 50     // 50-79分 → 重写, <50分 → 重新生成
};

// 占位符定义
const PLACEHOLDERS = {
  PROJECT_PATH: '{{PROJECT_PATH}}',
  PROJECT_NAME: '{{PROJECT_NAME}}',
  EXAMPLE_TASKS: '{{EXAMPLE_TASKS}}',
  SDK_DOC_PATH: '{{SDK_DOC_PATH}}',
  CRITICAL_RULES: '{{CRITICAL_RULES}}',
  CORE_PATHS: '{{CORE_PATHS}}',
  ARCHITECTURE_DOCS: '{{ARCHITECTURE_DOCS_SECTION}}',
  BUSINESS_DOCS: '{{BUSINESS_DOCS_SECTION}}',
  NBT_CHECK_SECTION: '{{NBT_CHECK_SECTION}}',
  LOG_FILES: '{{LOG_FILES}}',
  CURRENT_DATE: '{{CURRENT_DATE}}',
  PROJECT_DESCRIPTION: '{{PROJECT_DESCRIPTION}}',
  EXTRA_DOCS: '{{EXTRA_DOCS}}',
  CRITICAL_RULES_EXTRA: '{{CRITICAL_RULES_EXTRA}}'
};

// CRITICAL规范映射（根据项目类型选择）
const CRITICAL_RULES_MAP = {
  general: [
    'System生命周期',
    '模块导入规范',
    '双端隔离',
    'Python2.7兼容性'
  ],
  apollo: ['Apollo1.0架构'],
  ecpreset: ['ECPreset数据存储'],
  rpg: ['RPG-NBT兼容性']
};

// 项目类型识别关键词
const PROJECT_TYPE_KEYWORDS = {
  RPG: ['rpg', 'combat', 'weapon', 'armor', 'skill', 'equipment'],
  BedWars: ['bedwars', 'bed', 'generator', 'team'],
  PVP: ['pvp', 'arena', 'duel'],
  Survival: ['survival', 'hunger', 'thirst']
};

/**
 * 获取模板路径
 * @param {string} templateName - 模板名称
 * @param {string} projectType - 项目类型（RPG/BedWars/General）
 * @returns {string} 模板文件的绝对路径
 */
function getTemplatePath(templateName, projectType = 'General') {
  if (templateName === 'CLAUDE.md') {
    return path.join(TEMPLATES_DIR, 'CLAUDE.md.template');
  }
  // v17.1: 6个核心命令（统一/mc前缀）
  else if (templateName === 'mc.md') {
    return path.join(TEMPLATES_DIR, '.claude', 'commands', 'mc.md.template');
  } else if (templateName === 'mc-review.md') {
    return path.join(TEMPLATES_DIR, '.claude', 'commands', 'mc-review.md.template');
  } else if (templateName === 'mc-perf.md') {
    return path.join(TEMPLATES_DIR, '.claude', 'commands', 'mc-perf.md.template');
  } else if (templateName === 'mc-docs.md') {
    return path.join(TEMPLATES_DIR, '.claude', 'commands', 'mc-docs.md.template');
  } else if (templateName === 'mc-why.md') {
    return path.join(TEMPLATES_DIR, '.claude', 'commands', 'mc-why.md.template');
  } else if (templateName === 'mc-discover.md') {
    return path.join(TEMPLATES_DIR, '.claude', 'commands', 'mc-discover.md.template');
  }
  // 其他模板
  else if (templateName === 'README.md') {
    return path.join(TEMPLATES_DIR, 'README.md.template');
  } else if (templateName === 'markdown/README.md') {
    // v16.0: markdown目录导航文档
    return path.join(TEMPLATES_DIR, 'markdown', 'README.md.template');
  } else {
    return path.join(TEMPLATES_DIR, templateName);
  }
}

/**
 * 获取当前日期（格式：YYYY-MM-DD）
 * @returns {string}
 */
function getCurrentDate() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, '0');
  const day = String(now.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

module.exports = {
  VERSION,
  WORKFLOW_HOME,
  TEMPLATES_DIR,
  RULES_LIBRARY_DIR,
  DOC_TEMPLATES_DIR,
  MODSDK_WIKI_URL,
  BEDROCK_WIKI_URL,
  DETAIL_LEVELS,
  COMPLEXITY_THRESHOLDS,
  SCALE_THRESHOLDS,
  QUALITY_THRESHOLDS,
  PLACEHOLDERS,
  CRITICAL_RULES_MAP,
  PROJECT_TYPE_KEYWORDS,
  getTemplatePath,
  getCurrentDate
};
