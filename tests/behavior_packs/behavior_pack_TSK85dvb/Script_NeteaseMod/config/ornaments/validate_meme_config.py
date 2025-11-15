# -*- coding: utf-8 -*-
"""
墓碑配置文件验证脚本

用法:
    python validate_meme_config.py
"""

import json
import codecs
import os


def validate_meme_config():
    """验证墓碑配置文件"""
    print("=" * 60)
    print("墓碑配置文件验证")
    print("=" * 60)

    # 获取配置文件路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, 'meme.json')

    # 检查文件是否存在
    print("\n[1] 检查文件存在性...")
    if not os.path.exists(config_path):
        print("    ❌ 配置文件不存在: {}".format(config_path))
        return False
    print("    ✅ 配置文件存在")

    # 加载 JSON
    print("\n[2] 加载 JSON...")
    try:
        with codecs.open(config_path, 'r', 'utf-8') as f:
            data = json.load(f)
        print("    ✅ JSON 格式正确")
    except Exception as e:
        print("    ❌ JSON 格式错误: {}".format(str(e)))
        return False

    # 检查结构
    print("\n[3] 检查配置结构...")
    if 'meme_ornaments' not in data:
        print("    ❌ 缺少 'meme_ornaments' 字段")
        return False
    print("    ✅ 结构正确")

    # 检查墓碑数量
    meme_list = data['meme_ornaments']
    print("\n[4] 墓碑数量: {}".format(len(meme_list)))
    if len(meme_list) != 8:
        print("    ⚠️ 预期 8 个墓碑，实际 {} 个".format(len(meme_list)))
    else:
        print("    ✅ 墓碑数量正确")

    # 验证每个墓碑配置
    print("\n[5] 验证墓碑配置...")
    required_fields = ['id', 'name', 'variant', 'entity_type', 'duration',
                       'display_on_death', 'display_on_resource_collect']

    expected_ids = ['smile', 'black', 'embrace', 'huaji', 'angry', 'qm', 'ec', 'anubis']
    expected_variants = [1, 2, 3, 4, 5, 6, 7, 8]

    found_ids = []
    found_variants = []

    for i, meme in enumerate(meme_list):
        meme_id = meme.get('id', '<未设置>')
        print("\n    墓碑 #{}: {}".format(i + 1, meme_id))

        # 检查必填字段
        missing_fields = []
        for field in required_fields:
            if field not in meme:
                missing_fields.append(field)

        if missing_fields:
            print("      ❌ 缺少字段: {}".format(', '.join(missing_fields)))
        else:
            print("      ✅ 所有字段完整")

        # 检查字段值
        if 'id' in meme:
            found_ids.append(meme['id'])
            print("      - ID: {}".format(meme['id']))

        if 'variant' in meme:
            found_variants.append(meme['variant'])
            print("      - Variant: {}".format(meme['variant']))

        if 'name' in meme:
            print("      - 名称: {}".format(meme['name']))

        if 'duration' in meme:
            print("      - 持续时间: {} 秒".format(meme['duration']))

        if 'display_on_death' in meme:
            print("      - 死亡显示: {}".format('是' if meme['display_on_death'] else '否'))

        if 'display_on_resource_collect' in meme:
            print("      - 资源显示: {}".format('是' if meme['display_on_resource_collect'] else '否'))

    # 检查 ID 唯一性
    print("\n[6] 检查 ID 唯一性...")
    if len(found_ids) != len(set(found_ids)):
        print("    ❌ 存在重复的 ID")
        duplicates = [id for id in found_ids if found_ids.count(id) > 1]
        print("       重复的 ID: {}".format(set(duplicates)))
    else:
        print("    ✅ 所有 ID 唯一")

    # 检查 variant 唯一性
    print("\n[7] 检查 Variant 唯一性...")
    if len(found_variants) != len(set(found_variants)):
        print("    ❌ 存在重复的 Variant")
        duplicates = [v for v in found_variants if found_variants.count(v) > 1]
        print("       重复的 Variant: {}".format(set(duplicates)))
    else:
        print("    ✅ 所有 Variant 唯一")

    # 检查预期的 ID
    print("\n[8] 检查预期的墓碑 ID...")
    missing_ids = [id for id in expected_ids if id not in found_ids]
    if missing_ids:
        print("    ⚠️ 缺少预期的 ID: {}".format(', '.join(missing_ids)))
    else:
        print("    ✅ 所有预期 ID 存在")

    # 检查预期的 Variant
    print("\n[9] 检查预期的 Variant...")
    missing_variants = [v for v in expected_variants if v not in found_variants]
    if missing_variants:
        print("    ⚠️ 缺少预期的 Variant: {}".format(', '.join(map(str, missing_variants))))
    else:
        print("    ✅ 所有预期 Variant 存在")

    # 总结
    print("\n" + "=" * 60)
    print("验证完成！")
    print("=" * 60)

    return True


if __name__ == '__main__':
    try:
        validate_meme_config()
    except Exception as e:
        print("\n❌ 验证过程出错: {}".format(str(e)))
        import traceback
        traceback.print_exc()
