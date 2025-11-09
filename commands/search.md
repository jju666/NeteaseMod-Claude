# /cc 搜索 - 智能文档检索

你需要使用智能检索引擎帮助用户搜索相关文档和任务。

## 执行步骤

1. **解析用户查询**
   - 提取查询关键词
   - 识别查询类型（标签/System/关键词）

2. **执行检索**
   ```bash
   # 根据查询类型选择命令
   node lib/search-engine.js "用户查询" [选项]
   ```

3. **展示结果**
   - 显示搜索结果（路径、类型、相关度）
   - 如果是任务，显示关联Systems
   - 如果是系统文档，显示复杂度

4. **提供建议**
   - 建议用户查阅最相关的文档
   - 如果结果过多，建议细化查询

## 查询格式

- `tag:标签名` - 按标签搜索
- `system:SystemName` - 按System搜索
- `keyword:关键词` - 按关键词搜索
- 普通文本 - 全文搜索

## 选项

- `--type=task|system|guide` - 类型过滤
- `--limit=10` - 结果数量限制
- `--after=YYYY-MM-DD` - 时间范围（之后）
- `--before=YYYY-MM-DD` - 时间范围（之前）

## 示例

用户: `/cc 搜索 商店系统`
→ 执行: `node lib/search-engine.js "商店系统"`
→ 展示: 相关任务和文档

用户: `/cc 搜索 tag:双端通信`
→ 执行: `node lib/search-engine.js "tag:双端通信"`
→ 展示: 所有带"双端通信"标签的文档

用户: `/cc 搜索 system:ShopSystem`
→ 执行: `node lib/search-engine.js "system:ShopSystem"`
→ 展示: ShopSystem文档和相关任务
