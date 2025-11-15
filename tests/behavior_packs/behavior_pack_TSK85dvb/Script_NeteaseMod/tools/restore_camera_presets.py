# -*- coding: utf-8 -*-
"""
批量恢复camera:track_point预设配置

功能:
- 扫描所有dimension_*.py文件
- 查找被注释的camera:track_point配置块
- 计算每个地图的中心点
- 使用默认参数生成camera:track_point配置
- 恢复配置到文件

使用方法:
    python restore_camera_presets.py
"""

import os
import re
import uuid


def calculate_map_center(presets):
    """
    计算地图中心点

    Args:
        presets: 预设列表

    Returns:
        tuple: (x, y, z) 中心点坐标,如果没有有效位置则返回None
    """
    positions = []

    for preset in presets:
        if isinstance(preset, dict) and 'config' in preset:
            pos = preset['config'].get('pos')
            if pos and isinstance(pos, (list, tuple)) and len(pos) >= 3:
                positions.append(pos)

    if not positions:
        return None

    # 计算平均值
    avg_x = sum(p[0] for p in positions) / len(positions)
    avg_y = sum(p[1] for p in positions) / len(positions)
    avg_z = sum(p[2] for p in positions) / len(positions)

    # 四舍五入到1位小数
    return (round(avg_x, 1), round(avg_y, 1), round(avg_z, 1))


def generate_camera_preset(dimension_id, center_pos):
    """
    生成camera:track_point预设配置

    Args:
        dimension_id: int 维度ID
        center_pos: tuple (x, y, z) 中心点位置

    Returns:
        str: 格式化的配置字符串
    """
    preset_id = str(uuid.uuid4()).replace('-', '')

    # 构建配置字符串 - 避免使用format()导致的大括号问题
    config_str = '        {\n'
    config_str += '            "type": "camera:track_point",\n'
    config_str += '            "id": "' + preset_id + '",\n'
    config_str += '            "config": {\n'
    config_str += '                "pos": [' + str(center_pos[0]) + ', ' + str(center_pos[1]) + ', ' + str(center_pos[2]) + '],\n'
    config_str += '                "dimension": ' + str(dimension_id) + ',\n'
    config_str += '                "radius": 50.0,\n'
    config_str += '                "angular_velocity": 0.003,\n'
    config_str += '                "height_offset": 20.0,\n'
    config_str += '            },\n'
    config_str += '        }'

    return config_str


def restore_camera_preset_in_file(filepath):
    """
    恢复单个文件中的camera:track_point预设

    Args:
        filepath: str 文件路径

    Returns:
        dict: {
            'success': bool,
            'dimension_id': int,
            'message': str
        }
    """
    result = {
        'success': False,
        'dimension_id': None,
        'message': ''
    }

    try:
        # 读取文件
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否包含注释的camera配置
        if 'TODO: camera:track_point预设尚未实现' not in content:
            result['message'] = '未找到注释的camera配置'
            return result

        # 执行Python代码获取配置
        namespace = {}
        exec(content, namespace)
        config = namespace.get('PRESET_CONFIG', {})

        if not config:
            result['message'] = '无法解析PRESET_CONFIG'
            return result

        dimension_id = config.get('dimension_id', 0)
        presets = config.get('presets', [])
        result['dimension_id'] = dimension_id

        # 计算地图中心点
        center_pos = calculate_map_center(presets)
        if not center_pos:
            result['message'] = '无法计算地图中心点(没有有效的预设位置)'
            return result

        # 生成camera预设配置
        camera_preset_str = generate_camera_preset(dimension_id, center_pos)

        # 使用正则表达式替换注释块
        # 匹配从TODO注释开始到 # }, 结束的整个块
        pattern = r'        # TODO: camera:track_point预设尚未实现,暂时禁用\n' \
                  r'        # 后续需要:\n' \
                  r'        # 1\. 实现CameraTrackPointPresetDefServer和CameraTrackPointPresetDefClient\n' \
                  r'        # 2\. 在modConfig\.py中注册预设类型\n' \
                  r'        # 3\. 恢复此配置\n' \
                  r'        # \{\n' \
                  r'        #     "type": "camera:track_point",\n' \
                  r'        #     \.\.\.已注释\.\.\.\n' \
                  r'        # \},\n'

        if not re.search(pattern, content):
            result['message'] = '未能匹配注释模式'
            return result

        # 替换注释块
        new_content = re.sub(pattern, camera_preset_str + ',\n\n', content)

        # 写回文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)

        result['success'] = True
        result['message'] = '成功恢复,中心点: {}'.format(center_pos)
        return result

    except Exception as e:
        result['message'] = '处理失败: {}'.format(str(e))
        import traceback
        traceback.print_exc()
        return result


def main():
    """主函数"""
    # 获取rooms目录路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    rooms_dir = os.path.join(
        os.path.dirname(script_dir),
        'config',
        'rooms'
    )

    print("=" * 70)
    print("camera:track_point预设批量恢复工具")
    print("=" * 70)
    print("配置目录: {}".format(rooms_dir))
    print()

    if not os.path.exists(rooms_dir):
        print("[ERROR] 配置目录不存在: {}".format(rooms_dir))
        return

    # 统计
    total_files = 0
    success_count = 0
    skip_count = 0
    fail_count = 0

    success_list = []
    skip_list = []
    fail_list = []

    # 遍历所有dimension_*.py文件
    for filename in sorted(os.listdir(rooms_dir)):
        if not filename.startswith('dimension_') or not filename.endswith('.py'):
            continue

        total_files += 1
        filepath = os.path.join(rooms_dir, filename)

        print("[{}/??] 处理: {}".format(total_files, filename), end=' ... ')

        result = restore_camera_preset_in_file(filepath)

        if result['success']:
            success_count += 1
            success_list.append({
                'file': filename,
                'dimension': result['dimension_id'],
                'message': result['message']
            })
            print("[OK] {}".format(result['message']))
        elif '未找到注释的camera配置' in result['message']:
            skip_count += 1
            skip_list.append({
                'file': filename,
                'dimension': result['dimension_id'],
                'message': result['message']
            })
            print("[SKIP] {}".format(result['message']))
        else:
            fail_count += 1
            fail_list.append({
                'file': filename,
                'dimension': result['dimension_id'],
                'message': result['message']
            })
            print("[FAIL] {}".format(result['message']))

    # 打印报告
    print()
    print("=" * 70)
    print("处理完成!")
    print("=" * 70)
    print("扫描文件总数: {}".format(total_files))
    print("成功恢复: {}".format(success_count))
    print("跳过(无需恢复): {}".format(skip_count))
    print("失败: {}".format(fail_count))
    print()

    if success_list:
        print("成功恢复的文件:")
        print("-" * 70)
        for item in success_list[:10]:  # 只显示前10个
            print("  {} (dimension_{}) - {}".format(
                item['file'],
                item['dimension'],
                item['message']
            ))
        if len(success_list) > 10:
            print("  ... 还有{}个文件".format(len(success_list) - 10))
        print()

    if fail_list:
        print("失败的文件:")
        print("-" * 70)
        for item in fail_list:
            print("  {} - {}".format(item['file'], item['message']))
        print()

    print("=" * 70)
    print("建议后续操作:")
    print("1. 检查配置语法: 运行Python语法检查")
    print("2. 验证配置完整性: 检查pos和dimension字段")
    print("3. 测试加载: 启动游戏验证预设创建成功")
    print("=" * 70)


if __name__ == '__main__':
    main()
