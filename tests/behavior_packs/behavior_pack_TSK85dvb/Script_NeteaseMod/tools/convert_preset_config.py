# -*- coding: utf-8 -*-
"""
convert_preset_config.py - 预设配置转换工具

功能:
- 将旧格式的dimension_*.json转换为EC预设模组兼容格式
- 旧格式使用preset_id, preset_type, position, rotation, properties
- 新格式使用type, id, config (position和properties合并到config中)

使用方法:
python convert_preset_config.py
"""

import json
import os


def convert_preset_format(old_preset):
    """
    转换单个预设的格式

    Args:
        old_preset (dict): 旧格式预设配置

    Returns:
        dict: 新格式预设配置
    """
    # 提取基本字段
    preset_id = old_preset.get("preset_id")
    preset_type = old_preset.get("preset_type")

    # 构建config字段,合并position, rotation, properties
    config = {}

    # 添加position (转换为列表格式 [x, y, z])
    position_dict = old_preset.get("position", {})
    config["pos"] = [
        position_dict.get("x", 0),
        position_dict.get("y", 0),
        position_dict.get("z", 0)
    ]

    # 添加rotation (可选)
    rotation_dict = old_preset.get("rotation", {})
    if rotation_dict:
        config["rotation"] = {
            "pitch": rotation_dict.get("pitch", 0),
            "yaw": rotation_dict.get("yaw", 0),
            "roll": rotation_dict.get("roll", 0)
        }

    # 添加properties中的所有字段
    properties = old_preset.get("properties", {})
    for key, value in properties.items():
        # 跳过内部字段
        if key.startswith("_"):
            continue
        config[key] = value

    # 构建新格式
    new_preset = {
        "type": preset_type,
        "id": preset_id,
        "config": config
    }

    return new_preset


def convert_dimension_file(input_path, output_path):
    """
    转换单个dimension文件

    Args:
        input_path (str): 输入文件路径
        output_path (str): 输出文件路径
    """
    try:
        # 读取旧配置
        with open(input_path, 'r') as f:
            old_config = json.load(f)

        dimension_id = old_config.get("dimension_id")
        old_presets = old_config.get("presets", [])

        # 转换所有预设
        new_presets = []
        for old_preset in old_presets:
            new_preset = convert_preset_format(old_preset)
            new_presets.append(new_preset)

        # 构建新配置
        new_config = {
            "dimension_id": dimension_id,
            "preset_count": len(new_presets),
            "presets": new_presets
        }

        # 写入新配置
        with open(output_path, 'w') as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)

        print(u"[SUCCESS] 转换完成: {} ({} 个预设)".format(
            os.path.basename(input_path), len(new_presets)))

        return True

    except Exception as e:
        print(u"[ERROR] 转换失败: {} - {}".format(
            os.path.basename(input_path), str(e)))
        return False


def convert_all_dimension_files(config_dir):
    """
    转换所有dimension_*.json文件

    Args:
        config_dir (str): 配置目录路径
    """
    rooms_dir = os.path.join(config_dir, "rooms")

    if not os.path.exists(rooms_dir):
        print(u"[ERROR] 目录不存在: {}".format(rooms_dir))
        return

    # 创建备份目录
    backup_dir = os.path.join(config_dir, "rooms_backup")
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        print(u"[INFO] 创建备份目录: {}".format(backup_dir))

    # 查找所有dimension_*.json文件
    dimension_files = []
    for filename in os.listdir(rooms_dir):
        if filename.startswith("dimension_") and filename.endswith(".json"):
            dimension_files.append(filename)

    print(u"[INFO] 找到 {} 个dimension文件".format(len(dimension_files)))

    # 转换每个文件
    success_count = 0
    failed_count = 0

    for filename in dimension_files:
        input_path = os.path.join(rooms_dir, filename)
        backup_path = os.path.join(backup_dir, filename)
        output_path = input_path  # 覆盖原文件

        # 备份原文件
        try:
            with open(input_path, 'r') as f_in:
                with open(backup_path, 'w') as f_out:
                    f_out.write(f_in.read())
        except Exception as e:
            print(u"[ERROR] 备份失败: {} - {}".format(filename, str(e)))
            failed_count += 1
            continue

        # 转换文件
        if convert_dimension_file(input_path, output_path):
            success_count += 1
        else:
            failed_count += 1

    # 打印总结
    print(u"\n========== 转换完成 ==========")
    print(u"成功: {} 个文件".format(success_count))
    print(u"失败: {} 个文件".format(failed_count))
    print(u"备份位置: {}".format(backup_dir))


if __name__ == "__main__":
    # 获取脚本所在目录的父目录 (Script_NeteaseMod)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)
    config_dir = os.path.join(parent_dir, "config")

    print(u"========== 预设配置转换工具 ==========")
    print(u"配置目录: {}".format(config_dir))
    print(u"")

    convert_all_dimension_files(config_dir)
