const fs = require('fs');
const path = require('path');

// 修复源文件
const srcFile = path.join(__dirname, 'bin/quick-deploy.js');
let content = fs.readFileSync(srcFile, 'utf8');

// 移除模板字符串中的 \n
content = content.replace(/`([^`]*?)\\n`/g, '`$1`');

fs.writeFileSync(srcFile, content);
console.log('Fixed source file:', srcFile);

// 修复全局文件（如果存在）
const globalFile = path.join(require('os').homedir(), '.claude-modsdk-workflow/bin/quick-deploy.js');
if (fs.existsSync(globalFile)) {
  let globalContent = fs.readFileSync(globalFile, 'utf8');
  globalContent = globalContent.replace(/`([^`]*?)\\n`/g, '`$1`');
  fs.writeFileSync(globalFile, globalContent);
  console.log('Fixed global file:', globalFile);
}

console.log('Done!');
