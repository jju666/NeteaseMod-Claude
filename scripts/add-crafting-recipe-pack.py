# -*- coding: utf-8 -*-
"""
添加物品合成配方系统玩法包到知识库
"""
import json
import os

# 知识库路径
KB_PATH = "D:/EcWork/基于Claude的MODSDK开发工作流/.claude/knowledge-base.json"

# 物品合成配方系统完整代码(精简版)
CRAFTING_RECIPE_CODE = '''# -*- coding: utf-8 -*-
from __future__ import print_function
from mod.server.system.serverSystem import ServerSystem
import mod.server.extraServerApi as serverApi

class CraftingRecipeServerSystem(ServerSystem):
    """物品合成配方系统"""

    def __init__(self, namespace, systemName):
        super(CraftingRecipeServerSystem, self).__init__(namespace, systemName)

        # 自定义合成配方
        self.custom_recipes = [
            {
                "type": "shaped",
                "pattern": [
                    "DDD",
                    "DSD",
                    "DDD"
                ],
                "key": {
                    "D": {"item": "minecraft:diamond"},
                    "S": {"item": "minecraft:stick"}
                },
                "result": {
                    "item": "minecraft:diamond_sword",
                    "count": 1,
                    "data": 0
                },
                "unlock": []
            },
            {
                "type": "shapeless",
                "ingredients": [
                    {"item": "minecraft:iron_ingot"},
                    {"item": "minecraft:iron_ingot"},
                    {"item": "minecraft:redstone"}
                ],
                "result": {
                    "item": "minecraft:piston",
                    "count": 1
                }
            }
        ]

        self.recipe_comp = None
        self.Create()

    def Create(self):
        """初始化组件和注册配方"""
        level_id = serverApi.GetLevelId()
        comp_factory = serverApi.GetEngineCompFactory()

        self.recipe_comp = comp_factory.CreateRecipe(level_id)

        # 注册所有自定义配方
        for recipe in self.custom_recipes:
            self._RegisterRecipe(recipe)

        print("[CraftingRecipe] 已注册 {} 个自定义配方".format(len(self.custom_recipes)))

    def _RegisterRecipe(self, recipe):
        """注册单个配方"""
        recipe_type = recipe.get("type")

        if recipe_type == "shaped":
            # 有序合成配方
            recipe_id = "custom:shaped_{}".format(len(self.custom_recipes))
            pattern = recipe.get("pattern", [])
            key = recipe.get("key", {})
            result = recipe.get("result", {})
            unlock = recipe.get("unlock", [])

            success = self.recipe_comp.RegisterShapedRecipe(
                recipe_id,
                pattern,
                key,
                [result],
                unlock
            )

            if success:
                print("[CraftingRecipe] 注册有序配方: {} -> {}".format(
                    recipe_id, result.get("item")
                ))

        elif recipe_type == "shapeless":
            # 无序合成配方
            recipe_id = "custom:shapeless_{}".format(len(self.custom_recipes))
            ingredients = recipe.get("ingredients", [])
            result = recipe.get("result", {})
            unlock = recipe.get("unlock", [])

            success = self.recipe_comp.RegisterShapelessRecipe(
                recipe_id,
                ingredients,
                [result],
                unlock
            )

            if success:
                print("[CraftingRecipe] 注册无序配方: {} -> {}".format(
                    recipe_id, result.get("item")
                ))

    def AddCustomRecipe(self, recipe):
        """动态添加配方"""
        self.custom_recipes.append(recipe)
        self._RegisterRecipe(recipe)

    def Destroy(self):
        """系统销毁时清理"""
        self.UnListenAllEvents()
'''

# 物品合成配方系统玩法包配置
CRAFTING_RECIPE_PACK = {
    "id": "crafting-recipe-system",
    "name": "物品合成配方系统",
    "keywords": [
        "合成", "配方", "工作台", "有序", "无序", "物品制作",
        "crafting", "recipe", "workbench", "shaped", "shapeless", "craft"
    ],
    "category": "交互玩法",
    "difficulty": "简单",
    "estimated_time": "10分钟",

    "description": "实现自定义物品合成配方的系统,支持有序合成(shaped)和无序合成(shapeless)两种模式",

    "implementation_guide": {
        "principle": "服务端初始化时调用recipeComp.RegisterShapedRecipe/RegisterShapelessRecipe注册配方 → 玩家在工作台中按配方放置物品 → 自动显示合成结果",

        "modsdk_apis": [
            {
                "name": "recipeComp.RegisterShapedRecipe",
                "type": "组件方法",
                "purpose": "注册有序合成配方(物品位置固定)",
                "params": {
                    "recipeId": "配方唯一ID (str)",
                    "pattern": "配方图案 (list of str)",
                    "key": "图案符号映射 (dict)",
                    "result": "合成结果 (list of dict)",
                    "unlock": "解锁条件 (list,可选)"
                },
                "returns": "是否成功 (bool)",
                "doc_path": "MODSDK/Component/recipeComp.md",
                "common_pitfall": "pattern每行长度必须一致;key中必须包含pattern中所有符号"
            },
            {
                "name": "recipeComp.RegisterShapelessRecipe",
                "type": "组件方法",
                "purpose": "注册无序合成配方(物品位置任意)",
                "params": {
                    "recipeId": "配方唯一ID (str)",
                    "ingredients": "材料列表 (list of dict)",
                    "result": "合成结果 (list of dict)",
                    "unlock": "解锁条件 (list,可选)"
                },
                "returns": "是否成功 (bool)",
                "doc_path": "MODSDK/Component/recipeComp.md",
                "common_pitfall": "ingredients中物品顺序不影响合成"
            }
        ],

        "complete_code": {
            "file": "mod/server/system/CraftingRecipeServerSystem.py",
            "content": CRAFTING_RECIPE_CODE
        },

        "config_guide": {
            "description": "在custom_recipes中配置自定义配方",
            "example": {
                "type": "shaped",
                "pattern": ["GGG", "GSG", "GGG"],
                "key": {
                    "G": {"item": "minecraft:gold_ingot"},
                    "S": {"item": "minecraft:stick"}
                },
                "result": {
                    "item": "minecraft:golden_axe",
                    "count": 1,
                    "data": 0
                },
                "unlock": []
            },
            "fields": {
                "type": "配方类型 (str: shaped/shapeless)",
                "pattern": "配方图案 (list,shaped需要)",
                "key": "符号映射 (dict,shaped需要)",
                "ingredients": "材料列表 (list,shapeless需要)",
                "result": "合成结果 (dict)",
                "unlock": "解锁条件 (list,可选)"
            }
        },

        "common_issues": [
            {
                "problem": "配方注册失败",
                "cause": "recipeId重复或pattern格式错误",
                "solution": "确保recipeId唯一;检查pattern每行长度一致"
            },
            {
                "problem": "合成后物品不显示",
                "cause": "result格式错误或物品ID不存在",
                "solution": "确保result包含item和count字段;使用有效的物品identifier"
            },
            {
                "problem": "无序配方不生效",
                "cause": "ingredients数量或类型不匹配",
                "solution": "检查ingredients列表中物品数量和类型是否正确"
            }
        ],

        "related_gameplay": [
            {
                "name": "自定义商店系统",
                "similarity": "物品生成",
                "extension": "可扩展为高级合成台"
            }
        ]
    }
}

def main():
    # 读取现有知识库
    with open(KB_PATH, 'r', encoding='utf-8') as f:
        kb = json.load(f)

    # 检查是否已存在
    existing_ids = [p["id"] for p in kb["gameplay_patterns"]]
    if "crafting-recipe-system" in existing_ids:
        print("[SKIP] Crafting Recipe System pack already exists")
        return

    # 添加新玩法包
    kb["gameplay_patterns"].append(CRAFTING_RECIPE_PACK)

    # 更新元数据
    kb["metadata"]["total_patterns"] = len(kb["gameplay_patterns"])

    # 保存
    with open(KB_PATH, 'w', encoding='utf-8') as f:
        json.dump(kb, f, ensure_ascii=False, indent=2)

    print("[SUCCESS] Crafting Recipe System gameplay pack added!")
    print(f"[INFO] Total patterns: {kb['metadata']['total_patterns']}")
    print(f"[INFO] Keywords: {', '.join(CRAFTING_RECIPE_PACK['keywords'][:8])}")

if __name__ == "__main__":
    main()
