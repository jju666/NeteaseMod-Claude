# -*- coding: utf-8 -*-
"""
预设配置验证脚本

验证转换后的预设配置文件的完整性和正确性

验证项:
1. 预设总数匹配 (应该约1257个)
2. 所有维度都有配置文件
3. 无重复preset_id
4. Team属性值有效
5. Resource_type属性值有效
6. 位置坐标有效
"""

from __future__ import print_function
import json
import os
import sys
from collections import defaultdict

# 有效的队伍ID
VALID_TEAMS = {'RED', 'BLUE', 'GREEN', 'YELLOW', 'AQUA', 'WHITE', 'LIGHT_PURPLE', 'GRAY'}

# 有效的资源类型
VALID_RESOURCE_TYPES = {'iron', 'gold', 'diamond', 'emerald'}


class PresetValidator(object):
    """预设配置验证器"""

    def __init__(self, config_dir):
        """
        初始化验证器

        Args:
            config_dir: 配置目录路径
        """
        self.config_dir = config_dir

        # 统计信息
        self.stats = {
            'total_files': 0,
            'total_presets': 0,
            'by_type': defaultdict(int),
            'by_dimension': defaultdict(int),
        }

        # 验证结果
        self.errors = []
        self.warnings = []

        # 预设ID集合 (用于检测重复)
        self.preset_ids = set()

    def load_all_configs(self):
        """
        加载所有配置文件

        Returns:
            list: [(dimension_id, presets), ...]
        """
        print("[1/6] 加载所有配置文件...")

        all_configs = []
        for filename in os.listdir(self.config_dir):
            if filename.startswith('dimension_') and filename.endswith('.json'):
                filepath = os.path.join(self.config_dir, filename)
                with open(filepath, 'r') as f:
                    config = json.load(f)

                dimension_id = config.get('dimension_id')
                presets = config.get('presets', [])

                all_configs.append((dimension_id, presets))
                self.stats['total_files'] += 1
                self.stats['total_presets'] += len(presets)
                self.stats['by_dimension'][dimension_id] = len(presets)

        print("  加载了 {} 个配置文件".format(self.stats['total_files']))
        print("  总预设数: {}".format(self.stats['total_presets']))

        return all_configs

    def validate_preset_count(self):
        """验证预设总数"""
        print("\n[2/6] 验证预设总数...")

        expected_min = 1200
        expected_max = 1300
        actual = self.stats['total_presets']

        if expected_min <= actual <= expected_max:
            print("  OK 预设总数正常: {} (预期范围: {}-{})".format(
                actual, expected_min, expected_max
    ))
        else:
            error_msg = "预设总数异常: {} (预期范围: {}-{})".format(
                actual, expected_min, expected_max
            )
            self.errors.append(error_msg)
            print("  ERR {}".format(error_msg))

    def validate_no_duplicate_ids(self, all_configs):
        """验证无重复ID"""
        print("\n[3/6] 验证预设ID唯一性...")

        duplicates = []
        for dimension_id, presets in all_configs:
            for preset in presets:
                preset_id = preset.get('preset_id')
                if preset_id in self.preset_ids:
                    duplicates.append((dimension_id, preset_id))
                else:
                    self.preset_ids.add(preset_id)

        if not duplicates:
            print("  OK 所有预设ID唯一")
        else:
            for dim, pid in duplicates[:5]:  # 只显示前5个
                error_msg = "重复的preset_id: {} (维度: {})".format(pid, dim)
                self.errors.append(error_msg)
                print("  ERR {}".format(error_msg))

            if len(duplicates) > 5:
                print("  ... 还有 {} 个重复ID".format(len(duplicates) - 5))

    def validate_team_values(self, all_configs):
        """验证Team属性值"""
        print("\n[4/6] 验证Team属性...")

        invalid_teams = []
        for dimension_id, presets in all_configs:
            for preset in presets:
                team = preset.get('properties', {}).get('team')
                if team and team not in VALID_TEAMS:
                    invalid_teams.append((dimension_id, preset.get('preset_id'), team))

        if not invalid_teams:
            print("  OK 所有Team属性值有效")
        else:
            for dim, pid, team in invalid_teams[:5]:
                error_msg = "无效的team值: {} (维度: {}, preset_id: {})".format(
                    team, dim, pid
                )
                self.errors.append(error_msg)
                print("  ERR {}".format(error_msg))

            if len(invalid_teams) > 5:
                print("  ... 还有 {} 个无效Team值".format(len(invalid_teams) - 5))

    def validate_resource_types(self, all_configs):
        """验证Resource_type属性值"""
        print("\n[5/6] 验证Resource_type属性...")

        invalid_resources = []
        for dimension_id, presets in all_configs:
            for preset in presets:
                resource_type = preset.get('properties', {}).get('resource_type_id')
                if resource_type and resource_type not in VALID_RESOURCE_TYPES:
                    invalid_resources.append((
                        dimension_id,
                        preset.get('preset_id'),
                        resource_type
                    ))

        if not invalid_resources:
            print("  OK 所有Resource_type属性值有效")
        else:
            for dim, pid, res_type in invalid_resources[:5]:
                error_msg = "无效的resource_type: {} (维度: {}, preset_id: {})".format(
                    res_type, dim, pid
                )
                self.errors.append(error_msg)
                print("  ERR {}".format(error_msg))

            if len(invalid_resources) > 5:
                print("  ... 还有 {} 个无效Resource_type值".format(
                    len(invalid_resources) - 5
    ))

    def validate_positions(self, all_configs):
        """验证位置坐标"""
        print("\n[6/6] 验证位置坐标...")

        invalid_positions = []
        for dimension_id, presets in all_configs:
            for preset in presets:
                position = preset.get('position', {})
                x = position.get('x')
                y = position.get('y')
                z = position.get('z')

                # 检查坐标是否为数字
                if not all(isinstance(coord, (int, float)) for coord in [x, y, z]):
                    invalid_positions.append((
                        dimension_id,
                        preset.get('preset_id'),
                        position
                    ))

        if not invalid_positions:
            print("  OK 所有位置坐标有效")
        else:
            for dim, pid, pos in invalid_positions[:5]:
                error_msg = "无效的位置坐标: {} (维度: {}, preset_id: {})".format(
                    pos, dim, pid
                )
                self.errors.append(error_msg)
                print("  ERR {}".format(error_msg))

            if len(invalid_positions) > 5:
                print("  ... 还有 {} 个无效位置".format(len(invalid_positions) - 5))

    def generate_report(self):
        """生成验证报告"""
        report_path = os.path.join(self.config_dir, '_validation_report.txt')

        with open(report_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("EC起床战争 - 预设配置验证报告\n")
            f.write("=" * 60 + "\n\n")

            f.write("总体统计:\n")
            f.write("  配置文件数: {}\n".format(self.stats['total_files']))
            f.write("  总预设数: {}\n".format(self.stats['total_presets']))
            f.write("  唯一预设ID: {}\n".format(len(self.preset_ids)))
            f.write("\n")

            f.write("验证结果:\n")
            if not self.errors and not self.warnings:
                f.write("  OK 所有验证项通过!\n")
            else:
                f.write("  错误数: {}\n".format(len(self.errors)))
                f.write("  警告数: {}\n".format(len(self.warnings)))
            f.write("\n")

            if self.errors:
                f.write("错误列表:\n")
                for i, error in enumerate(self.errors, 1):
                    f.write("  {}. {}\n".format(i, error))
                f.write("\n")

            if self.warnings:
                f.write("警告列表:\n")
                for i, warning in enumerate(self.warnings, 1):
                    f.write("  {}. {}\n".format(i, warning))
                f.write("\n")

            f.write("=" * 60 + "\n")
            f.write("验证完成!\n")
            f.write("=" * 60 + "\n")

        print("\n验证报告已保存: {}".format(report_path))

    def run(self):
        """执行验证流程"""
        print("=" * 60)
        print("EC起床战争 - 预设配置验证脚本")
        print("=" * 60)
        print("")

        # 1. 加载所有配置
        all_configs = self.load_all_configs()

        # 2. 验证预设总数
        self.validate_preset_count()

        # 3. 验证无重复ID
        self.validate_no_duplicate_ids(all_configs)

        # 4. 验证Team属性
        self.validate_team_values(all_configs)

        # 5. 验证Resource_type属性
        self.validate_resource_types(all_configs)

        # 6. 验证位置坐标
        self.validate_positions(all_configs)

        # 7. 生成报告
        self.generate_report()

        # 打印总结
        print("\n" + "=" * 60)
        print("验证完成!")
        print("=" * 60)
        if not self.errors and not self.warnings:
            print("  OK 所有验证项通过!")
        else:
            print("  错误数: {}".format(len(self.errors)))
            print("  警告数: {}".format(len(self.warnings)))
        print("=" * 60)

        return len(self.errors) == 0


def main():
    """主函数"""
    # 配置路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(
        os.path.dirname(script_dir),
        'config', 'rooms'
    )

    print("配置目录: {}".format(config_dir))
    print("")

    # 检查目录是否存在
    if not os.path.exists(config_dir):
        print("[ERROR] 配置目录不存在: {}".format(config_dir))
        return 1

    # 创建验证器并执行
    validator = PresetValidator(config_dir)
    success = validator.run()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
