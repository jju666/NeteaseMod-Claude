# /cc 归档 - 任务归档与知识提炼

你需要帮助用户归档任务到 `tasks/completed/`，并提炼为系统文档。

## 执行步骤

1. **验证任务状态**
   - 检查任务是否完成
   - 确认metadata.json存在

2. **移动任务到completed**
   ```bash
   # 如果任务不在completed目录
   mv tasks/[任务名] tasks/completed/[任务名]
   ```

3. **更新metadata.json**
   - 设置 `status: "已归档"`
   - 设置 `completedAt: "YYYY-MM-DD"`
   - 记录 `commitHash`（如果有git提交）

4. **提炼系统文档**（可选）
   - 如果涉及新System，生成 `markdown/systems/XXXSystem.md`
   - 如果是对现有System的修改，更新对应文档
   - 添加引用链接到任务

5. **更新索引**
   ```bash
   # 重新构建文档索引
   node lib/indexer.js
   ```

## 归档模板

**更新metadata.json**：
```json
{
  "taskName": "商店系统开发",
  "status": "已归档",
  "completedAt": "2025-11-09",
  "commitHash": "abc123def456"
}
```

**在系统文档中添加引用**：
```markdown
## 相关任务
- [商店系统开发](../../tasks/completed/商店系统开发/) - 初始实现
- [商店价格调整](../../tasks/completed/商店价格调整/) - 价格配置优化
```

## 示例

用户: `/cc 归档 商店系统开发`
→ 步骤1: 检查 `tasks/商店系统开发/metadata.json`
→ 步骤2: 移动到 `tasks/completed/商店系统开发/`
→ 步骤3: 更新metadata.json状态
→ 步骤4: 检查是否需要生成ShopSystem.md
→ 步骤5: 运行 `node lib/indexer.js`
→ 完成: 提示用户归档成功

## 注意事项

- ⚠️ 只归档已完成的任务
- ✅ 归档后立即更新索引
- ✅ 如果涉及重要System，建议提炼文档
- ✅ 保留任务的完整历史记录
