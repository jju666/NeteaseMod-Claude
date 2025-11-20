# 常见问题与解决方案

> **FAQ - Frequently Asked Questions**
>
> 涵盖安装、配置、调试、平台兼容性等常见问题

---

## 📦 安装与部署

### Q1: initmc部署失败，提示"找不到behavior_packs目录"

**症状**：
```
错误: 未找到behavior_packs或resource_packs目录
请确认当前目录是网易MOD项目根目录
```

**原因**：
- 当前目录不是网易MOD项目根目录
- 项目结构不符合网易MODSDK标准

**解决方案**：
```bash
# 1. 确认目录结构
ls
# 应该看到 behavior_packs/ 和/或 resource_packs/

# 2. 如果在子目录，切换到根目录
cd ..

# 3. 重新执行部署
initmc

# 4. 如果是全新项目，先创建标准结构
mkdir -p behavior_packs resource_packs
initmc
```

### Q2: Python依赖安装失败

**症状**：
```
pip install anthropic portalocker plyer
ERROR: Could not find a version that satisfies the requirement...
```

**解决方案**：

**方案1：升级pip**
```bash
python -m pip install --upgrade pip
pip install anthropic portalocker plyer
```

**方案2：使用国内镜像**
```bash
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple anthropic portalocker plyer
```

**方案3：手动指定版本**
```bash
pip install anthropic>=0.17.0 portalocker>=2.7.0 plyer>=2.1.0
```

**方案4：使用虚拟环境**
```bash
# 创建虚拟环境
python -m venv .venv

# Windows激活
.venv\Scripts\activate

# macOS/Linux激活
source .venv/bin/activate

# 安装依赖
pip install anthropic portalocker plyer
```

### Q3: Node.js版本过低

**症状**：
```
错误: initmc需要Node.js v16.0+，当前版本: v14.x
```

**解决方案**：

**Windows**：
1. 访问 https://nodejs.org/
2. 下载LTS版本（推荐18.x或20.x）
3. 运行安装程序
4. 重启终端验证：`node --version`

**macOS（使用Homebrew）**：
```bash
brew install node@20
echo 'export PATH="/opt/homebrew/opt/node@20/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
node --version
```

**Linux（使用nvm）**：
```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install 20
nvm use 20
node --version
```

---

## 🔧 配置问题

### Q4: Windows UTF-8编码乱码

**症状**：
- Hook输出中文显示为`???`或乱码
- task-meta.json文件中文字段损坏
- 桌面通知显示异常

**完整解决方案**：

#### 方法1：系统级UTF-8配置（推荐）

**适用于**：Windows 10 1903+ / Windows 11

**步骤**：
1. 打开"设置" → "时间和语言" → "语言和区域"
2. 点击"管理语言设置"
3. 点击"更改系统区域设置"
4. 勾选"Beta: 使用UTF-8提供全球语言支持"
5. **重启计算机**（必须）

**验证**：
```powershell
# 检查系统代码页（应为65001）
chcp
# 输出: Active code page: 65001

# 测试Python UTF-8
python -c "print('中文测试')"
# 应正确显示中文
```

#### 方法2：环境变量配置（临时）

**适用于**：无法修改系统设置的环境

**PowerShell**：
```powershell
# 临时设置（当前会话）
$env:PYTHONIOENCODING="utf-8"
chcp 65001

# 永久设置（添加到配置文件）
notepad $PROFILE
# 添加以下内容：
$env:PYTHONIOENCODING="utf-8"
chcp 65001 > $null
```

**CMD**：
```cmd
# 临时设置
set PYTHONIOENCODING=utf-8
chcp 65001

# 永久设置（添加到环境变量）
setx PYTHONIOENCODING utf-8
```

#### 方法3：修改Hook脚本（兼容性最强）

编辑 `.claude/hooks/core/task_meta_manager.py`：

```python
import sys
import io

# 强制UTF-8编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
```

**重新部署**：
```bash
initmc --force
```

### Q5: Claude API密钥未配置

**症状**：
```
⚠️ LLM分析失败，使用降级方案: No API key provided
```

**解决方案**：

**检查API密钥**：
```bash
# Windows PowerShell
echo $env:ANTHROPIC_API_KEY

# macOS/Linux
echo $ANTHROPIC_API_KEY
```

**设置API密钥**：

**Windows PowerShell**：
```powershell
# 临时设置
$env:ANTHROPIC_API_KEY="sk-ant-api03-..."

# 永久设置
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'sk-ant-api03-...', 'User')
```

**macOS/Linux**：
```bash
# 添加到 ~/.bashrc 或 ~/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.bashrc
source ~/.bashrc
```

**Claude Code配置文件**：
```json
// ~/.config/claude/settings.json
{
  "anthropicApiKey": "sk-ant-api03-..."
}
```

### Q6: 桌面通知不显示

**症状**：
- 任务完成后没有弹窗通知
- Hook日志显示"通知发送失败"

**排查步骤**：

**1. 检查plyer库**：
```bash
pip list | grep plyer
# 如果未安装
pip install plyer
```

**2. 检查系统通知权限**：

**Windows 10/11**：
- 设置 → 系统 → 通知和操作
- 确保"获取来自应用和其他发送者的通知"已开启
- 找到"Python"或"终端"，开启通知权限

**macOS**：
- 系统偏好设置 → 通知与专注模式
- 找到"终端"或"iTerm"
- 设置通知样式为"横幅"或"提醒"

**Linux (Ubuntu/Debian)**：
```bash
# 安装通知守护进程
sudo apt-get install libnotify-bin

# 测试通知
notify-send "测试" "通知功能正常"
```

**3. 手动测试通知**：
```python
# test_notification.py
from plyer import notification

notification.notify(
    title="测试通知",
    message="如果你看到这条消息，说明通知功能正常",
    timeout=10
)
```

运行测试：
```bash
python test_notification.py
```

**4. 禁用通知（如果不需要）**：

编辑 `.claude/hooks/core/notification_sender.py`：
```python
def send_notification(title, message):
    """发送桌面通知"""
    # 禁用通知
    return

    # 原代码...
```

---

## 🐛 运行时问题

### Q7: Hook系统未生效

**症状**：
- 输入`/mc`后，AI没有创建任务目录
- 没有看到任务仪表盘（Dashboard）
- AI行为与普通对话无异

**排查步骤**：

**1. 检查Hook目录**：
```bash
ls .claude/hooks/
# 应该看到 core/, lifecycle/, orchestrator/, archiver/

# 检查关键Hook文件
ls .claude/hooks/orchestrator/user_prompt_handler.py
ls .claude/hooks/lifecycle/session_start.py
```

**2. 检查Hook权限**：
```bash
# macOS/Linux
chmod +x .claude/hooks/**/*.py

# Windows（无需特殊权限）
```

**3. 手动测试Hook**：
```bash
# 测试SessionStart
python .claude/hooks/lifecycle/session_start.py

# 应该输出任务仪表盘或"未检测到进行中的任务"
```

**4. 检查Python路径**：
```bash
# Hook使用的Python版本
which python  # macOS/Linux
where python  # Windows

# 应该与安装依赖的Python一致
python --version
```

**5. 检查Claude Code版本**：
```bash
# 确保使用最新版本
claude --version

# 如果过旧，更新
# Windows/macOS: 重新下载安装包
# Linux: 使用包管理器更新
```

**6. 重新部署Hook系统**：
```bash
# 强制重新部署（覆盖现有文件）
initmc --force
```

### Q8: 状态转移失败

**症状**：
- 输入"是"后，状态未从planning切换到implementation
- task-meta.json中的current_stage没有变化
- AI继续停留在方案制定阶段

**原因分析**：

1. **LLM API调用失败**
   - 网络问题
   - API密钥配额不足
   - Claude API服务异常

2. **用户输入不明确**
   - 使用了模糊表达（如"可以"、"好的"、"行"）
   - LLM置信度低于阈值（<0.7）

3. **文件锁冲突**（极少见）
   - 多个Hook同时尝试写入task-meta.json
   - portalocker超时

**解决方案**：

**方案1：使用明确的确认词**
```
推荐表达：
- "是" / "同意" / "开始实施" / "执行方案"（planning → implementation）
- "完成" / "测试通过" / "修复成功"（implementation → finalization）
- "重新设计" / "不对" / "回退"（implementation → planning）

避免模糊表达：
- "可以"、"好的"、"行"、"OK"
```

**方案2：检查LLM日志**
```bash
# 查看Hook输出
# 应该看到类似：
# 🤖 LLM分析结果: {"category": "confirmation", "confidence": 0.95}

# 如果看到：
# ⚠️ LLM分析失败，使用降级方案
# 说明API调用失败，检查网络和API密钥
```

**方案3：手动修复状态**（仅紧急情况）
```bash
# 备份原文件
cp tasks/任务-xxx/.task-meta.json tasks/任务-xxx/.task-meta.json.backup

# 编辑文件
nano tasks/任务-xxx/.task-meta.json

# 修改以下字段：
{
  "current_stage": "implementation",  # 改为目标状态
  "allowed_transitions": ["finalization", "planning"]  # 更新允许转移
}

# 保存后，告诉AI：
"当前状态已更新为implementation，请继续实施方案"
```

**方案4：检查API配额**
```bash
# 访问 https://console.anthropic.com/settings/limits
# 检查API密钥的使用配额

# 或使用curl测试
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-sonnet-4-5-20250929","max_tokens":100,"messages":[{"role":"user","content":"测试"}]}'
```

### Q9: task-meta.json文件损坏

**症状**：
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**恢复方案**：

**方案1：从备份恢复**（如果启用了备份）
```bash
# 查找备份文件
ls tasks/任务-xxx/.task-meta.json.*

# 恢复最近的备份
cp tasks/任务-xxx/.task-meta.json.backup-20251120 tasks/任务-xxx/.task-meta.json
```

**方案2：手动重建**
```bash
# 1. 查看现有文件（可能只是部分损坏）
cat tasks/任务-xxx/.task-meta.json

# 2. 使用JSON验证工具修复
python -m json.tool tasks/任务-xxx/.task-meta.json

# 3. 如果完全损坏，创建最小结构
cat > tasks/任务-xxx/.task-meta.json <<EOF
{
  "task_id": "任务-1120-描述",
  "architecture_version": "21.0",
  "state_machine_version": "3.0",
  "current_stage": "planning",
  "allowed_transitions": ["implementation", "activation"],
  "task_type": "bug_fix",
  "user_request": "/mc 任务描述",
  "planning_summary": "",
  "steps": [],
  "metadata": {
    "created_at": "2025-11-20T00:00:00Z",
    "last_updated": "2025-11-20T00:00:00Z",
    "total_steps": 0,
    "current_step": 0
  }
}
EOF
```

### Q10: 并发冲突导致任务状态不一致

**症状**：
- 同时打开多个Claude Code窗口编辑同一任务
- task-meta.json中的steps数组缺失某些步骤
- current_stage在不同窗口显示不一致

**预防措施**：

**1. 避免多窗口同时编辑**
```
⚠️ 不要在多个Claude Code实例中同时操作同一任务
✅ 使用单一实例，必要时使用会话恢复功能
```

**2. 检查文件锁**
```bash
# 查看是否有进程持有锁
lsof .claude/.task-meta.lock  # macOS/Linux

# Windows使用句柄查看工具
# https://learn.microsoft.com/en-us/sysinternals/downloads/handle
handle.exe .task-meta.lock
```

**3. 启用调试日志**

编辑 `.claude/hooks/core/task_meta_manager.py`：
```python
import logging

logging.basicConfig(
    filename='.claude/task-meta-debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class TaskMetaManager:
    def atomic_update(self, update_func):
        logging.debug(f"尝试获取锁: {self.lock_file}")
        with portalocker.Lock(self.lock_file, timeout=5):
            logging.debug("锁已获取")
            # ...
            logging.debug("更新完成，释放锁")
```

**恢复方案**：
```bash
# 1. 关闭所有Claude Code实例
# 2. 删除锁文件
rm tasks/任务-xxx/.task-meta.lock

# 3. 检查task-meta.json完整性
python -m json.tool tasks/任务-xxx/.task-meta.json

# 4. 从单一实例重新打开
```

---

## 🧪 测试与调试

### Q11: 如何手动测试Hook功能

**单元测试方法**：

**1. 测试SessionStart**
```bash
# 创建测试任务
mkdir -p tests/tasks/任务-test-123
cat > tests/tasks/任务-test-123/.task-meta.json <<EOF
{
  "task_id": "任务-test-123",
  "current_stage": "planning",
  "task_type": "bug_fix",
  "user_request": "/mc 测试任务",
  "planning_summary": "这是一个测试任务",
  "steps": [],
  "metadata": {"created_at": "2025-11-20T00:00:00Z"}
}
EOF

# 运行SessionStart Hook
cd tests
python .claude/hooks/lifecycle/session_start.py

# 期望输出：任务仪表盘显示"任务-test-123"
```

**2. 测试UserPromptHandler**
```bash
# 模拟用户输入
echo "/mc 修复测试BUG" | python .claude/hooks/orchestrator/user_prompt_handler.py

# 期望：创建新任务目录，初始化task-meta.json
```

**3. 测试ClaudeSemanticAnalyzer**
```python
# test_llm.py
import sys
sys.path.insert(0, '.claude/hooks/core')

from claude_semantic_analyzer import ClaudeSemanticAnalyzer
import os

analyzer = ClaudeSemanticAnalyzer(api_key=os.getenv("ANTHROPIC_API_KEY"))

# 测试完成确认
result = analyzer.analyze("测试通过，完成", "implementation")
print(f"分类: {result['category']}, 置信度: {result['confidence']}")
# 期望: category="complete_success", confidence>0.9

# 测试部分成功
result = analyzer.analyze("基本正确,但还有个小BUG", "implementation")
print(f"分类: {result['category']}, 置信度: {result['confidence']}")
# 期望: category="partial_success", confidence>0.9
```

**4. 测试StateTransitionValidator**
```python
# test_validator.py
import sys
sys.path.insert(0, '.claude/hooks/core')

from state_transition_validator import StateTransitionValidator

validator = StateTransitionValidator()

# 测试合法转移
assert validator.validate_transition("planning", "implementation") == True

# 测试非法转移
assert validator.validate_transition("activation", "finalization") == False

print("✅ 状态转移验证测试通过")
```

### Q12: 如何查看Hook执行日志

**方法1：实时输出（默认）**
```
Hook的print()输出会直接显示在Claude Code界面
无需额外配置
```

**方法2：文件日志**

编辑任意Hook脚本（如 `session_start.py`）：
```python
import logging

logging.basicConfig(
    filename='.claude/hooks.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 在关键位置添加日志
logging.info("SessionStart Hook执行开始")
logging.debug(f"扫描目录: {tasks_dir}")
logging.warning("未找到进行中的任务")
```

查看日志：
```bash
tail -f .claude/hooks.log
```

**方法3：调试模式**

创建 `.claude/debug.py`：
```python
import sys
import json

# 拦截所有Hook的stdin/stdout
def debug_hook(hook_name):
    print(f"\n{'='*60}")
    print(f"🔍 调试: {hook_name}")
    print(f"{'='*60}")

    # 打印环境变量
    import os
    print(f"当前目录: {os.getcwd()}")
    print(f"Python版本: {sys.version}")

    # 打印stdin内容
    if not sys.stdin.isatty():
        stdin_data = sys.stdin.read()
        print(f"\n📥 stdin内容:\n{stdin_data}")

        # 尝试解析JSON
        try:
            data = json.loads(stdin_data)
            print(f"\n📊 解析后的JSON:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            pass

    print(f"{'='*60}\n")

# 使用方法：在Hook脚本开头添加
# import debug
# debug.debug_hook("SessionStart")
```

### Q13: 如何验证部署正确性

**完整验证清单**：

```bash
#!/bin/bash
# verify_deployment.sh - 部署验证脚本

echo "🔍 NeteaseMod-Claude 部署验证"
echo "=============================="

# 1. 检查Hook目录结构
echo "\n1️⃣ 检查Hook目录..."
if [ -d ".claude/hooks/core" ] && [ -d ".claude/hooks/lifecycle" ]; then
    echo "✅ Hook目录结构正确"
else
    echo "❌ Hook目录结构缺失"
    exit 1
fi

# 2. 检查关键文件
echo "\n2️⃣ 检查关键文件..."
REQUIRED_FILES=(
    ".claude/hooks/core/task_meta_manager.py"
    ".claude/hooks/core/claude_semantic_analyzer.py"
    ".claude/hooks/lifecycle/session_start.py"
    ".claude/hooks/orchestrator/user_prompt_handler.py"
    ".claude/rules/activation.yaml"
    ".claude/commands/mc.md"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file 缺失"
        exit 1
    fi
done

# 3. 检查Python依赖
echo "\n3️⃣ 检查Python依赖..."
python -c "import anthropic; print('✅ anthropic')" 2>/dev/null || echo "❌ anthropic未安装"
python -c "import portalocker; print('✅ portalocker')" 2>/dev/null || echo "❌ portalocker未安装"
python -c "import plyer; print('✅ plyer')" 2>/dev/null || echo "❌ plyer未安装"

# 4. 检查API密钥
echo "\n4️⃣ 检查API密钥..."
if [ -n "$ANTHROPIC_API_KEY" ]; then
    echo "✅ ANTHROPIC_API_KEY已配置"
else
    echo "⚠️ ANTHROPIC_API_KEY未配置（LLM功能将降级）"
fi

# 5. 测试Hook执行
echo "\n5️⃣ 测试Hook执行..."
python .claude/hooks/lifecycle/session_start.py >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ SessionStart Hook执行成功"
else
    echo "❌ SessionStart Hook执行失败"
    exit 1
fi

echo "\n=============================="
echo "✅ 部署验证通过！"
```

运行验证：
```bash
chmod +x verify_deployment.sh
./verify_deployment.sh
```

---

## 🌐 平台兼容性

### Q14: macOS上的特殊问题

**问题1：权限被拒绝**
```bash
# 症状
-bash: .claude/hooks/lifecycle/session_start.py: Permission denied

# 解决方案
chmod +x .claude/hooks/**/*.py

# 或全局授权
find .claude/hooks -name "*.py" -exec chmod +x {} \;
```

**问题2：Python路径问题**
```bash
# macOS可能同时安装了python2和python3
# 确保使用python3
which python3  # /usr/local/bin/python3

# 修改Hook脚本首行shebang（如需要）
#!/usr/bin/env python3
```

**问题3：通知权限**
```bash
# 首次运行需要授权终端发送通知
# 系统偏好设置 → 通知与专注模式 → 终端
# 设置为"允许通知"
```

### Q15: Linux特定问题

**问题1：libnotify缺失**
```bash
# 症状
ModuleNotFoundError: No module named '_notify'

# 解决方案 (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install libnotify-bin python3-notify2

# Fedora/RHEL
sudo dnf install libnotify python3-notify2

# Arch Linux
sudo pacman -S libnotify python-notify2
```

**问题2：文件锁权限**
```bash
# 症状
PermissionError: [Errno 13] Permission denied: '.task-meta.lock'

# 检查文件所有者
ls -la tasks/任务-xxx/.task-meta.lock

# 修复权限
chmod 666 tasks/任务-xxx/.task-meta.lock
```

**问题3：Python虚拟环境**
```bash
# 推荐使用虚拟环境隔离依赖
python3 -m venv .venv
source .venv/bin/activate
pip install anthropic portalocker plyer

# 确保Claude Code使用虚拟环境的Python
which python  # 应该指向 .venv/bin/python
```

### Q16: WSL (Windows Subsystem for Linux)

**配置要点**：

**1. UTF-8编码**
```bash
# 在 ~/.bashrc 添加
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
source ~/.bashrc
```

**2. 桌面通知**
```bash
# WSL2无法直接发送Windows通知
# 需要使用wslu工具

# 安装wslu
sudo apt update
sudo apt install wslu

# 测试通知
wslview https://example.com  # 应该在Windows浏览器打开
```

**3. 文件权限**
```bash
# WSL访问Windows文件系统时，避免使用/mnt/c/
# 推荐在WSL文件系统工作（如~/projects/）

# 如果必须访问Windows文件
sudo umount /mnt/c
sudo mount -t drvfs C: /mnt/c -o metadata,uid=1000,gid=1000
```

---

## 📊 性能优化

### Q17: Hook执行缓慢

**症状**：
- SessionStart Hook耗时超过5秒
- 每次工具调用后明显延迟

**优化方案**：

**1. 减少文件扫描范围**

编辑 `.claude/hooks/lifecycle/session_start.py`：
```python
def scan_tasks():
    tasks_dir = "tasks"

    # 优化前：扫描所有子目录
    # for root, dirs, files in os.walk(tasks_dir):

    # 优化后：仅扫描一级目录
    for task_name in os.listdir(tasks_dir):
        task_path = os.path.join(tasks_dir, task_name)
        if os.path.isdir(task_path) and task_name.startswith("任务-"):
            # 处理任务...
```

**2. 缓存任务列表**

创建 `.claude/.task-cache.json`：
```python
import json
import os
from datetime import datetime, timedelta

CACHE_FILE = ".claude/.task-cache.json"
CACHE_TTL = timedelta(hours=1)

def get_cached_tasks():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            cache_time = datetime.fromisoformat(cache['timestamp'])
            if datetime.now() - cache_time < CACHE_TTL:
                return cache['tasks']

    # 缓存过期，重新扫描
    tasks = scan_tasks()
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'tasks': tasks
        }, f)
    return tasks
```

**3. 禁用可选功能**

如果不需要某些功能，可以禁用：
```python
# .claude/hooks/lifecycle/session_start.py

# 禁用任务仪表盘
ENABLE_DASHBOARD = False

# 禁用桌面通知
ENABLE_NOTIFICATIONS = False

# 禁用上下文注入（会影响任务恢复）
ENABLE_CONTEXT_INJECTION = True  # 建议保持开启
```

---

## 🔄 版本迁移

### Q18: 从v20.x升级到v21.0+

**自动迁移**（推荐）：
```bash
# initmc会自动检测v20.x任务并迁移
initmc

# 迁移过程：
# 1. 检测workflow-state.json
# 2. 合并数据到task-meta.json
# 3. 删除workflow-state.json
# 4. 添加architecture_version: "21.0"
```

**手动迁移**：
```bash
# 1. 备份现有任务
cp -r tasks tasks.backup

# 2. 对每个任务执行迁移
cd tasks/任务-xxx

# 3. 合并workflow-state.json到task-meta.json
python3 <<EOF
import json

# 读取旧文件
with open('workflow-state.json', 'r', encoding='utf-8') as f:
    workflow = json.load(f)
with open('.task-meta.json', 'r', encoding='utf-8') as f:
    meta = json.load(f)

# 合并数据
meta['current_stage'] = workflow.get('state', 'planning')
meta['architecture_version'] = '21.0'
meta['state_machine_version'] = '3.0'

# 写入新文件
with open('.task-meta.json', 'w', encoding='utf-8') as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

# 删除旧文件
import os
os.remove('workflow-state.json')
print('✅ 迁移完成')
EOF
```

**验证迁移**：
```bash
# 检查所有任务
find tasks -name ".task-meta.json" -exec python3 -c '
import json, sys
with open(sys.argv[1], "r", encoding="utf-8") as f:
    meta = json.load(f)
    assert "architecture_version" in meta
    assert meta["architecture_version"] == "21.0"
    print(f"✅ {sys.argv[1]}")
' {} \;
```

---

## 📝 最佳实践

### Q19: 如何高效使用任务工作流

**建议1：明确的任务描述**
```
❌ 不好: /mc 修复BUG
✅ 好: /mc 修复玩家死亡后装备丢失的BUG
```

**建议2：及时确认方案**
```
Planning阶段AI制定方案后：
- ✅ 仔细审查方案的可行性
- ✅ 如果有疑问，明确提出："这个方案会不会影响XX功能？"
- ✅ 确认后使用明确的词："是"、"开始实施"
```

**建议3：分阶段验证**
```
Implementation阶段：
- ✅ 每完成一个关键修改，立即本地测试
- ✅ 发现问题立即反馈："这个修改导致了XX错误"
- ✅ 不要等所有修改完成后才测试
```

**建议4：善用回退机制**
```
如果实施方向错误：
- ✅ 输入："重新设计"触发 implementation → planning
- ✅ 不要强行继续错误的方向
```

### Q20: 如何管理多个任务

**任务归档策略**：
```bash
# 定期归档已完成任务
mv tasks/任务-1115-* tasks/archive/

# 或使用脚本批量归档
find tasks -name ".task-meta.json" \
  -exec python3 -c '
import json, sys, shutil
with open(sys.argv[1], "r", encoding="utf-8") as f:
    meta = json.load(f)
    if meta.get("current_stage") == "finalization":
        task_dir = sys.argv[1].replace("/.task-meta.json", "")
        archive_dir = task_dir.replace("tasks/", "tasks/archive/")
        shutil.move(task_dir, archive_dir)
        print(f"✅ 已归档: {task_dir}")
' {} \;
```

**任务命名规范**：
```
建议格式: 任务-{日期}-{功能模块}-{简短描述}

示例：
- 任务-1120-战斗系统-修复伤害计算
- 任务-1120-UI界面-添加排行榜
- 任务-1120-性能优化-减少tick消耗
```

---

## 📚 更多资源

- **[快速开始](./快速开始.md)** - 安装与基本使用
- **[架构概览](./架构概览.md)** - 系统设计详解
- **[HOOK正确用法文档](./HOOK正确用法文档.md)** - Hook开发标准
- **[Claude Code官方文档](https://code.claude.com/docs/zh-CN/overview)** - 官方参考

---

**文档维护**: Claude Code Development Team
**最后更新**: 2025-11-20
**适用版本**: v25.0+

**问题反馈**: [GitHub Issues](https://github.com/jju666/NeteaseMod-Claude/issues)
