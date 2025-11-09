/**
 * 工具函数
 */

const fs = require('fs');
const path = require('path');

/**
 * 递归创建目录
 * @param {string} dirPath - 目录路径
 */
function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

/**
 * 递归复制目录
 * @param {string} src - 源目录
 * @param {string} dest - 目标目录
 */
function copyDir(src, dest) {
  ensureDir(dest);
  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDir(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

/**
 * 递归遍历目录
 * @param {string} dir - 目录路径
 * @param {function} callback - 回调函数 (filePath) => void
 * @param {Array<string>} skipDirs - 跳过的目录名
 */
function walkDir(dir, callback, skipDirs = ['.git', '__pycache__', 'node_modules', 'venv']) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);

    if (entry.isDirectory()) {
      if (!skipDirs.includes(entry.name)) {
        walkDir(fullPath, callback, skipDirs);
      }
    } else {
      callback(fullPath);
    }
  }
}

/**
 * 替换模板中的占位符
 * @param {string} content - 模板内容
 * @param {Object} replacements - 替换映射 { placeholder: value }
 * @returns {string}
 */
function replacePlaceholders(content, replacements) {
  let result = content;
  for (const [placeholder, value] of Object.entries(replacements)) {
    const regex = new RegExp(placeholder.replace(/[{}]/g, '\\$&'), 'g');
    result = result.replace(regex, value);
  }
  return result;
}

/**
 * 检查文件是否存在
 * @param {string} filePath
 * @returns {boolean}
 */
function fileExists(filePath) {
  return fs.existsSync(filePath);
}

/**
 * 读取文件内容
 * @param {string} filePath
 * @param {string} encoding - 默认 utf8
 * @returns {string}
 */
function readFile(filePath, encoding = 'utf8') {
  try {
    return fs.readFileSync(filePath, encoding);
  } catch (err) {
    // 尝试其他编码（Windows GBK）
    try {
      return fs.readFileSync(filePath, 'latin1');
    } catch (e) {
      console.error(`[工具] 无法读取文件: ${filePath}`);
      return '';
    }
  }
}

/**
 * 写入文件
 * @param {string} filePath
 * @param {string} content
 */
function writeFile(filePath, content) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, content, 'utf8');
}

/**
 * 查找文件
 * @param {string} dir - 搜索目录
 * @param {string} filename - 文件名
 * @returns {string|null} 文件路径或null
 */
function findFile(dir, filename) {
  let result = null;

  walkDir(dir, (filePath) => {
    if (path.basename(filePath) === filename) {
      result = filePath;
    }
  });

  return result;
}

/**
 * 跨平台路径转换
 * @param {string} filePath
 * @returns {string} Unix风格路径
 */
function normalizePathForMarkdown(filePath) {
  return filePath.replace(/\\/g, '/');
}

/**
 * 获取相对路径
 * @param {string} from
 * @param {string} to
 * @returns {string}
 */
function getRelativePath(from, to) {
  return path.relative(from, to).replace(/\\/g, '/');
}

module.exports = {
  ensureDir,
  copyDir,
  walkDir,
  replacePlaceholders,
  fileExists,
  readFile,
  writeFile,
  findFile,
  normalizePathForMarkdown,
  getRelativePath
};
