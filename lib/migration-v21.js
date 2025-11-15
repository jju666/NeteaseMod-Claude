#!/usr/bin/env node
/**
 * v20.x → v21.0 迁移脚本
 * 核心变更：task-meta.json为唯一数据源，删除workflow-state.json
 *
 * @module migration-v21
 * @version 21.0.0
 * @date 2025-11-15
 */

const path = require('path');
const fs = require('fs-extra');
const { readFile, writeFile } = require('./utils');

class MigrationV21 {
  constructor(upstreamPath, downstreamPath) {
    this.upstreamPath = upstreamPath;
    this.downstreamPath = downstreamPath;
    this.claudeDir = path.join(downstreamPath, '.claude');
    this.tasksDir = path.join(downstreamPath, 'tasks');
  }

  /**
   * 检查是否需要迁移
   * @returns {boolean}
   */
  needsMigration() {
    // 检查1: .claude/workflow-state.json 是否存在
    const workflowStatePath = path.join(this.claudeDir, 'workflow-state.json');
    if (fs.existsSync(workflowStatePath)) {
      return true;
    }

    // 检查2: 是否存在旧版task-meta.json（包含workflow_state字段）
    if (!fs.existsSync(this.tasksDir)) {
      return false;
    }

    const taskFolders = fs.readdirSync(this.tasksDir).filter(name => {
      const taskPath = path.join(this.tasksDir, name);
      return fs.statSync(taskPath).isDirectory();
    });

    for (const taskFolder of taskFolders) {
      const metaPath = path.join(this.tasksDir, taskFolder, '.task-meta.json');
      if (fs.existsSync(metaPath)) {
        try {
          const meta = JSON.parse(readFile(metaPath));
          // 检查是否有旧版字段
          if (meta.workflow_state || meta.archived_snapshot || !meta.architecture_version) {
            return true;
          }
        } catch (e) {
          // JSON解析失败，跳过
          continue;
        }
      }
    }

    return false;
  }

  /**
   * 执行迁移
   * @param {Object} options - 迁移选项
   * @param {boolean} options.autoConfirm - 是否自动确认
   * @returns {Promise<Object>} 迁移结果
   */
  async migrate(options = {}) {
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('🔄 NeteaseMod-Claude v21.0 迁移向导');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    console.log('📋 核心变更说明：');
    console.log('  - task-meta.json 为唯一数据源（删除 workflow-state.json）');
    console.log('  - 简化状态管理，减少数据不一致风险');
    console.log('  - 使用 TaskMetaManager 替代 StateManager');
    console.log('  - 所有运行时状态集中在 task-meta.json\n');

    const result = {
      success: true,
      tasksProcessed: 0,
      tasksMigrated: 0,
      tasksSkipped: 0,
      errors: [],
      workflowStateDeleted: false
    };

    // 1. 迁移活跃任务（如果存在workflow-state.json）
    const workflowStatePath = path.join(this.claudeDir, 'workflow-state.json');
    if (fs.existsSync(workflowStatePath)) {
      console.log('🔍 检测到活跃任务状态文件: workflow-state.json');

      try {
        const workflowState = JSON.parse(readFile(workflowStatePath));
        const taskId = workflowState.task_id;

        if (taskId) {
          const taskDir = path.join(this.tasksDir, taskId);
          const metaPath = path.join(taskDir, '.task-meta.json');

          if (fs.existsSync(metaPath)) {
            console.log(`📦 迁移活跃任务: ${taskId}`);

            // 合并workflow_state到task-meta.json
            const meta = JSON.parse(readFile(metaPath));
            const migratedMeta = this._migrateTaskMeta(meta, workflowState);
            writeFile(metaPath, JSON.stringify(migratedMeta, null, 2));

            result.tasksMigrated++;
            console.log(`  ✅ 已迁移: ${taskId}`);
          } else {
            console.log(`  ⚠️  任务元数据缺失，跳过迁移: ${taskId}`);
            result.tasksSkipped++;
          }
        }

        // 删除workflow-state.json
        fs.removeSync(workflowStatePath);
        result.workflowStateDeleted = true;
        console.log('  🗑️  已删除: workflow-state.json\n');

      } catch (e) {
        console.error(`  ❌ 迁移活跃任务失败: ${e.message}`);
        result.errors.push(`活跃任务迁移失败: ${e.message}`);
      }
    }

    // 2. 迁移所有历史任务
    if (!fs.existsSync(this.tasksDir)) {
      console.log('ℹ️  无历史任务，跳过任务迁移\n');
      return result;
    }

    console.log('🔍 扫描历史任务目录...\n');

    const allFolders = this._getAllTaskFolders();

    for (const { folder, relativePath } of allFolders) {
      const metaPath = path.join(folder, '.task-meta.json');

      if (!fs.existsSync(metaPath)) {
        continue;
      }

      result.tasksProcessed++;

      try {
        const meta = JSON.parse(readFile(metaPath));

        // 检查是否需要迁移
        if (meta.architecture_version === '21.0') {
          result.tasksSkipped++;
          continue; // 已是v21.0格式，跳过
        }

        // 执行迁移
        const migratedMeta = this._migrateTaskMeta(meta, null);
        writeFile(metaPath, JSON.stringify(migratedMeta, null, 2));

        result.tasksMigrated++;
        console.log(`  ✅ 已迁移: ${relativePath}`);

      } catch (e) {
        console.error(`  ❌ 迁移失败 ${relativePath}: ${e.message}`);
        result.errors.push(`${relativePath}: ${e.message}`);
      }
    }

    // 3. 输出迁移报告
    console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log('📊 迁移报告');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
    console.log(`  - 已处理任务: ${result.tasksProcessed}`);
    console.log(`  - 已迁移任务: ${result.tasksMigrated}`);
    console.log(`  - 已跳过任务: ${result.tasksSkipped}`);
    console.log(`  - workflow-state.json: ${result.workflowStateDeleted ? '已删除' : '不存在'}`);

    if (result.errors.length > 0) {
      console.log(`\n  ⚠️  错误数量: ${result.errors.length}`);
      result.errors.forEach((err, idx) => {
        console.log(`    ${idx + 1}. ${err}`);
      });
    }

    console.log('\n💡 提示：');
    console.log('  - 所有任务状态现在集中在 .task-meta.json');
    console.log('  - Hook系统自动使用 TaskMetaManager 管理状态');
    console.log('  - 旧版 StateManager 已移除\n');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');

    result.success = result.errors.length === 0;
    return result;
  }

  /**
   * 迁移单个task-meta.json
   * @param {Object} meta - 旧版元数据
   * @param {Object|null} workflowState - 工作流状态（如果有）
   * @returns {Object} v21.0格式的元数据
   */
  _migrateTaskMeta(meta, workflowState) {
    const migrated = { ...meta };

    // 1. 添加v21.0架构版本标记
    migrated.architecture_version = '21.0';

    // 2. 如果有外部传入的workflow_state，合并
    if (workflowState) {
      migrated.current_step = workflowState.current_step || migrated.current_step;
      migrated.steps = workflowState.steps || migrated.steps;
      migrated.metrics = workflowState.metrics || migrated.metrics;
      migrated.bug_fix_tracking = workflowState.bug_fix_tracking || migrated.bug_fix_tracking;
    }

    // 3. 删除旧版字段（如果存在）
    delete migrated.workflow_state; // v20.2.x 冗余字段
    delete migrated.workflow_state_ref; // v20.3.x 引用指针
    delete migrated.archived_snapshot; // v20.x 归档快照

    // 4. 确保必需字段存在
    if (!migrated.steps) {
      migrated.steps = {
        step0_context: { status: 'pending' },
        step1_understand: { status: 'pending' },
        step3_execute: { status: 'pending' },
        step4_cleanup: { status: 'pending' }
      };
    }

    if (!migrated.metrics) {
      migrated.metrics = {
        docs_read: [],
        code_changes: [],
        tool_calls: []
      };
    }

    if (!migrated.current_step) {
      migrated.current_step = 'step0_context';
    }

    return migrated;
  }

  /**
   * 获取所有任务文件夹（包括子目录如"已失败"、"已取消"）
   * @returns {Array<{folder: string, relativePath: string}>}
   */
  _getAllTaskFolders() {
    const results = [];

    if (!fs.existsSync(this.tasksDir)) {
      return results;
    }

    const traverse = (dir, relativePath = '') => {
      const entries = fs.readdirSync(dir);

      for (const entry of entries) {
        const fullPath = path.join(dir, entry);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory()) {
          const relPath = relativePath ? `${relativePath}/${entry}` : entry;

          // 如果包含.task-meta.json，则是任务目录
          const metaPath = path.join(fullPath, '.task-meta.json');
          if (fs.existsSync(metaPath)) {
            results.push({
              folder: fullPath,
              relativePath: relPath
            });
          } else {
            // 否则递归遍历子目录
            traverse(fullPath, relPath);
          }
        }
      }
    };

    traverse(this.tasksDir);
    return results;
  }
}

module.exports = { MigrationV21 };
