# -*- coding: utf-8 -*-
class ModUILayout:
    GRID = "GRID"
    BLOCK = "BLOCK"
    DETAIL = "DETAIL"

class ModUIConfig:
    def __init__(self, **kwargs):
        self.layout = None
        self.recommend = False
        self.title = ""
        self.categoryTexture = ""
        # 使用setattr动态设置属性
        for key, value in kwargs.items():
            setattr(self, key, value)
    def __str__(self):
        return "ModUIConfig(layout={}, recommend={}, title={}, categoryTexture={})".format(
            self.layout, self.recommend, self.title, self.categoryTexture)

    def to_dict(self):
        return {
            "layout": self.layout,
            "recommend": self.recommend,
            "title": self.title,
            "categoryTexture": self.categoryTexture
        }

class BedWarsShopCategoryConfig:
    def __init__(self, **kwargs):
        self.name = ""
        self.intro = ""
        self.uiChestItem = 0
        self.uiChestExtra = ""
        self.uiFormImage = ""
        self.uiModUI = None  # type: ModUIConfig | None
        self.goods = []  # type: list[str]
        self.uiFormNeedRepeatBuy = False
        self.randomShowcase = 0
        self.rotating = 0
        self.hideFromPocket = False
        self.hideFromClassic = False
        # 使用setattr动态设置属性
        for key, value in kwargs.items():
            if key == "uiModUI" and isinstance(value, dict):
                # 特别处理ModUIConfig实例的创建
                value = ModUIConfig(**value)
            setattr(self, key, value)

    def __str__(self):
        return "BedWarsShopCategoryConfig(name={}, intro={}, uiChestItem={}, uiChestExtra={}, uiFormImage={}, uiModUI={}, goods={}, uiFormNeedRepeatBuy={}, randomShowcase={}, rotating={}, hideFromPocket={}, hideFromClassic={})".format(
            self.name, self.intro, self.uiChestItem, self.uiChestExtra, self.uiFormImage, self.uiModUI, self.goods, self.uiFormNeedRepeatBuy, self.randomShowcase, self.rotating, self.hideFromPocket, self.hideFromClassic)