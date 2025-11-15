# -*- coding: utf-8 -*-
from BedWarsShopCategoryConfig import BedWarsShopCategoryConfig


class BedWarsShopConfig:
    def __init__(self, **kwargs):
        self.name = ""
        self.intro = ""
        self.shopCategoriesConfig = []  # type: list[BedWarsShopCategoryConfig]
        self.showRecommend = False
        # 使用setattr动态设置属性
        for key, value in kwargs.items():
            if key == "shopCategoriesConfig" and isinstance(value, list):
                # 特别处理shop_categories_config列表，假设列表中的元素是字典，每个字典包含了创建BedWarsShopCategoryConfig实例所需的参数
                processed_list = [BedWarsShopCategoryConfig(**item) if isinstance(item, dict) else item for item in value]
                value = processed_list
            setattr(self, key, value)

    def __str__(self):
        return "BedWarsShopConfig(name={}, intro={}, shopCategoriesConfig={}, showRecommend={})".format(
            self.name, self.intro, self.shopCategoriesConfig, self.showRecommend)