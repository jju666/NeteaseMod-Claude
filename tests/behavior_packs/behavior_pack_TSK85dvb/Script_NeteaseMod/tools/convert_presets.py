# -*- coding: utf-8 -*-
"""
预设配置转换脚本

将网易Preset系统的presets.json转换为EC预设模组格式

功能:
1. 读取原始presets.json (1266个预设)
2. 按维度分组预设
3. 转换为EC预设配置格式
4. 生成配置文件到config/rooms/目录
5. 生成转换报告

转换规则:
- name → preset_type (映射到EC预设类型)
- objId → preset_id
- dimension → dimension_id
- transform.pos → position
- changes中的childPartInstances[UUID].xxx → 提取到properties
"""

from __future__ import print_function
import json
import os
import sys
from collections import defaultdict

# 预设名称到EC预设类型的映射
PRESET_TYPE_MAPPING = {
    'BedWarsGenerator': 'bedwars:generator',
    'BedWarsShop': 'bedwars:shop',
    'BedWarsBed': 'bedwars:bed',
    'BedWarsSpawn': 'bedwars:spawn',
    'WorldPreviewCameraTrack': 'camera:track_point',
    'BedWarsGuide': 'bedwars:guide',
    'BedWarsGuideShop': 'bedwars:guide_shop',
    'BedWarsGuideBed': 'bedwars:guide_bed',
}

# 需要跳过的预设类型
SKIP_PRESET_NAMES = {
    'BedWarsStageLogic',
    'CustomProps',
    'PlayerClientParticle',
    'StageLogic',
    'ChangeDimensionAnim',
    'ECFocusNodeUI',
    'ECHUD',
}


class PresetConverter(object):
    """预设配置转换器"""

    def __init__(self, input_path, output_dir):
        """
        初始化转换器

        Args:
            input_path: 输入的presets.json路径
            output_dir: 输出目录 (config/rooms/)
        """
        self.input_path = input_path
        self.output_dir = output_dir

        # 统计信息
        self.stats = {
            'total': 0,
            'converted': 0,
            'skipped': 0,
            'errors': 0,
            'by_type': defaultdict(int),
            'by_dimension': defaultdict(int),
        }

        # 错误列表
        self.errors = []

    def load_presets(self):
        """
        加载原始presets.json

        Returns:
            list: 预设列表
        """
        print("[1/5] 加载原始配置文件...")
        print("  文件: {}".format(self.input_path))

        with open(self.input_path, 'r') as f:
            presets = json.load(f)

        self.stats['total'] = len(presets)
        print("  总预设数: {}".format(self.stats['total']))

        return presets

    def group_by_dimension(self, presets):
        """
        按维度分组预设

        Args:
            presets: 预设列表

        Returns:
            dict: {dimension_id: [preset, preset, ...]}
        """
        print("\n[2/5] 按维度分组预设...")

        grouped = defaultdict(list)
        for preset in presets:
            dimension = preset.get('dimension')
            if dimension is not None:
                grouped[dimension].append(preset)

        print("  维度数量: {}".format(len(grouped)))
        for dim, preset_list in sorted(grouped.items()):
            print("    维度 {}: {} 个预设".format(dim, len(preset_list)))
            self.stats['by_dimension'][dim] = len(preset_list)

        return grouped

    def convert_preset(self, preset):
        """
        转换单个预设

        Args:
            preset: 原始预设对象

        Returns:
            dict: EC预设格式,如果跳过则返回None
        """
        name = preset.get('name')

        # 跳过不需要的预设
        if name in SKIP_PRESET_NAMES:
            self.stats['skipped'] += 1
            return None

        # 获取EC预设类型
        preset_type = PRESET_TYPE_MAPPING.get(name)
        if not preset_type:
            error_msg = "未知预设类型: {}".format(name)
            self.errors.append(error_msg)
            self.stats['errors'] += 1
            return None

        # 提取基础信息
        obj_id = preset.get('objId')
        dimension = preset.get('dimension')
        transform = preset.get('transform', {})
        position = transform.get('pos', [0, 0, 0])
        rotation = transform.get('rotation', [0, 0, 0])

        # 提取properties (从changes中)
        properties = self._extract_properties(preset.get('changes', {}))

        # 构建EC预设对象
        ec_preset = {
            'preset_id': obj_id,
            'preset_type': preset_type,
            'dimension': dimension,
            'position': {
                'x': position[0],
                'y': position[1],
                'z': position[2]
            },
            'rotation': {
                'pitch': rotation[0],
                'yaw': rotation[1],
                'roll': rotation[2]
            },
            'properties': properties
        }

        self.stats['converted'] += 1
        self.stats['by_type'][preset_type] += 1

        return ec_preset

    def _extract_properties(self, changes):
        """
        从changes中提取properties

        转换规则:
        - childPartInstances[UUID].xxx → xxx (UUID保存为_child_part_uuid)
        - transform.xxx → 保留在changes中 (已在position/rotation中处理)

        Args:
            changes: changes字典

        Returns:
            dict: properties字典
        """
        properties = {}

        for key, value in changes.items():
            # 处理childPartInstances
            if key.startswith('childPartInstances['):
                # 提取UUID和属性名
                # 格式: childPartInstances[UUID].property_name
                parts = key.split('].')
                if len(parts) == 2:
                    uuid_part = parts[0].replace('childPartInstances[', '')
                    property_name = parts[1]

                    # 保存UUID (只保存一次)
                    if '_child_part_uuid' not in properties:
                        properties['_child_part_uuid'] = uuid_part

                    # 保存属性值
                    properties[property_name] = value

            # 跳过transform相关的changes (已经在position/rotation中处理)
            elif not key.startswith('transform.'):
                # 其他属性直接保存
                properties[key] = value

        return properties

    def save_dimension_config(self, dimension, presets):
        """
        保存单个维度的配置文件

        Args:
            dimension: 维度ID
            presets: 该维度的EC预设列表
        """
        # 构建输出文件路径
        filename = "dimension_{}.json".format(dimension)
        output_path = os.path.join(self.output_dir, filename)

        # 构建配置对象
        config = {
            'dimension_id': dimension,
            'preset_count': len(presets),
            'presets': presets
        }

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 写入文件
        with open(output_path, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print("    已保存: {} ({} 个预设)".format(filename, len(presets)))

    def generate_report(self):
        """生成转换报告"""
        report_path = os.path.join(self.output_dir, '_conversion_report.txt')

        with open(report_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("EC起床战争 - 预设配置转换报告\n")
            f.write("=" * 60 + "\n\n")

            f.write("总体统计:\n")
            f.write("  总预设数: {}\n".format(self.stats['total']))
            f.write("  成功转换: {}\n".format(self.stats['converted']))
            f.write("  跳过: {}\n".format(self.stats['skipped']))
            f.write("  错误: {}\n".format(self.stats['errors']))
            f.write("\n")

            f.write("按预设类型统计:\n")
            for preset_type, count in sorted(self.stats['by_type'].items()):
                f.write("  {}: {}\n".format(preset_type, count))
            f.write("\n")

            f.write("按维度统计:\n")
            for dim, count in sorted(self.stats['by_dimension'].items()):
                f.write("  维度 {}: {}\n".format(dim, count))
            f.write("\n")

            if self.errors:
                f.write("错误列表:\n")
                for i, error in enumerate(self.errors, 1):
                    f.write("  {}. {}\n".format(i, error))
                f.write("\n")

            f.write("=" * 60 + "\n")
            f.write("转换完成!\n")
            f.write("=" * 60 + "\n")

        print("\n转换报告已保存: {}".format(report_path))

    def run(self):
        """执行转换流程"""
        print("=" * 60)
        print("EC起床战争 - 预设配置转换脚本")
        print("=" * 60)
        print("")

        # 1. 加载原始配置
        presets = self.load_presets()

        # 2. 按维度分组
        grouped = self.group_by_dimension(presets)

        # 3. 转换预设
        print("\n[3/5] 转换预设配置...")
        converted_by_dimension = {}

        for dimension, preset_list in sorted(grouped.items()):
            converted_list = []
            for preset in preset_list:
                ec_preset = self.convert_preset(preset)
                if ec_preset:
                    converted_list.append(ec_preset)

            converted_by_dimension[dimension] = converted_list
            print("  维度 {}: {}/{} 转换成功".format(
                dimension, len(converted_list), len(preset_list)
    ))

        # 4. 保存配置文件
        print("\n[4/5] 保存配置文件...")
        for dimension, presets in sorted(converted_by_dimension.items()):
            self.save_dimension_config(dimension, presets)

        # 5. 生成报告
        print("\n[5/5] 生成转换报告...")
        self.generate_report()

        # 打印统计
        print("\n" + "=" * 60)
        print("转换完成!")
        print("=" * 60)
        print("  总预设数: {}".format(self.stats['total']))
        print("  成功转换: {}".format(self.stats['converted']))
        print("  跳过: {}".format(self.stats['skipped']))
        print("  错误: {}".format(self.stats['errors']))
        print("=" * 60)

        return self.stats['errors'] == 0


def main():
    """主函数"""
    # 配置路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Calculate project root
    script_root = os.path.dirname(script_dir)
    behavior_pack_root = os.path.dirname(script_root)
    behavior_packs_dir = os.path.dirname(behavior_pack_root)
    project_root = os.path.dirname(behavior_packs_dir)

    input_path = os.path.join(project_root, 'db', 'presets.json')
    output_dir = os.path.join(
        os.path.dirname(script_dir),
        'config', 'rooms'
    )

    print("输入文件: {}".format(input_path))
    print("输出目录: {}".format(output_dir))
    print("")

    # 检查输入文件是否存在
    if not os.path.exists(input_path):
        print("[ERROR] 输入文件不存在: {}".format(input_path))
        return 1

    # 创建转换器并执行
    converter = PresetConverter(input_path, output_dir)
    success = converter.run()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
