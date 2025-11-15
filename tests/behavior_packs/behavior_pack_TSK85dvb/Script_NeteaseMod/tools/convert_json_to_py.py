# -*- coding: utf-8 -*-
"""
JSON配置批量转换为Python配置文件

用法: python convert_json_to_py.py
"""

import json
import os
import sys

def json_to_python_value(obj, indent=0):
    """将JSON值转换为Python代码字符串"""
    spaces = "    " * indent

    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = ["{"]
        for key, value in obj.items():
            # 确保键是字符串
            if isinstance(key, unicode if sys.version_info[0] < 3 else str):
                key_str = '"{}"'.format(key)
            else:
                key_str = '"{}"'.format(str(key))

            value_str = json_to_python_value(value, indent + 1)
            lines.append('{}    {}: {},'.format(spaces, key_str, value_str))
        lines.append('{}}}'.format(spaces))
        return '\n'.join(lines)

    elif isinstance(obj, list):
        if not obj:
            return "[]"
        # 如果是简单数组（只包含数字/字符串），单行显示
        if all(isinstance(x, (int, float, bool, type(None))) or
               (isinstance(x, (str, unicode if sys.version_info[0] < 3 else str)) and len(str(x)) < 20)
               for x in obj):
            return "[{}]".format(", ".join(json_to_python_value(x, 0) for x in obj))

        # 复杂数组，多行显示
        lines = ["["]
        for item in obj:
            item_str = json_to_python_value(item, indent + 1)
            lines.append('{}    {},'.format(spaces, item_str))
        lines.append('{}]'.format(spaces))
        return '\n'.join(lines)

    elif isinstance(obj, (str, unicode if sys.version_info[0] < 3 else str)):
        # 检查是否包含中文
        try:
            obj.encode('ascii')
            return '"{}"'.format(obj.replace('\\', '\\\\').replace('"', '\\"'))
        except (UnicodeDecodeError, UnicodeEncodeError):
            return 'u"{}"'.format(obj.replace('\\', '\\\\').replace('"', '\\"'))

    elif isinstance(obj, bool):
        return "True" if obj else "False"

    elif obj is None:
        return "None"

    else:
        return str(obj)

def convert_json_file_to_py(json_path, py_path, var_name="CONFIG"):
    """将JSON文件转换为Python文件"""
    print(u"转换: {} -> {}".format(json_path, py_path))

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 生成Python代码
        python_code = u'# -*- coding: utf-8 -*-\n'
        python_code += u'"""\n'
        python_code += u'自动从JSON转换的配置文件\n'
        python_code += u'原文件: {}\n'.format(os.path.basename(json_path))
        python_code += u'"""\n\n'
        python_code += u'{} = {}\n'.format(var_name, json_to_python_value(data, 0))

        # 写入Python文件 - 确保使用UTF-8编码
        with open(py_path, 'w', encoding='utf-8') as f:
            f.write(python_code)

        print(u"  成功")
        return True

    except Exception as e:
        print(u"  失败: {}".format(e))
        import traceback
        traceback.print_exc()
        return False

def convert_all_configs():
    """转换所有配置文件"""
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_dir = os.path.join(script_dir, "config")

    print(u"配置目录: {}".format(config_dir))
    print(u"=" * 60)

    success_count = 0
    fail_count = 0

    # 遍历config目录下所有JSON文件
    for root, dirs, files in os.walk(config_dir):
        # 跳过备份目录
        if 'backup' in root:
            continue

        for filename in files:
            if not filename.endswith('.json'):
                continue

            json_path = os.path.join(root, filename)
            py_filename = filename.replace('.json', '.py')
            py_path = os.path.join(root, py_filename)

            # 确定变量名
            if filename == 'room_settings.json':
                var_name = 'ROOM_CONFIG'
            elif filename.startswith('dimension_'):
                var_name = 'PRESET_CONFIG'
            elif filename.startswith('team'):
                var_name = 'MODE_CONFIG'
            else:
                var_name = 'CONFIG'

            if convert_json_file_to_py(json_path, py_path, var_name):
                success_count += 1
            else:
                fail_count += 1

    print(u"=" * 60)
    print(u"转换完成! 成功: {}, 失败: {}".format(success_count, fail_count))

    # 创建__init__.py文件
    print(u"\n创建__init__.py文件...")
    for root, dirs, files in os.walk(config_dir):
        init_file = os.path.join(root, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w', encoding='utf-8') as f:
                f.write('# -*- coding: utf-8 -*-\n')
            print(u"  创建: {}".format(init_file))

if __name__ == '__main__':
    convert_all_configs()
