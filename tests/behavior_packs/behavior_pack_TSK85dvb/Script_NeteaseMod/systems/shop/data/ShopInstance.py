# -*- coding: utf-8 -*-
from .BedWarsShopConfig import BedWarsShopConfig
from .ShopInstanceCategory import ShopInstanceCategory
from .ShopCurrency import ShopCurrency, CURRENCY_DICT


class ShopInstance:

	def __init__(self, part, shop_type, raw_config, price_config, available_currencies):
		self.part = part  # type: BedWarsShopPart
		self.shop_type = shop_type  # type: str
		self.raw_config = raw_config  # type: BedWarsShopConfig
		self.categories = []  # type: list[ShopInstanceCategory]
		for category_config in self.raw_config.shopCategoriesConfig:
			self.categories.append(ShopInstanceCategory(
				self.part,
				category_config.name,
				category_config.intro,
				category_config,
				price_config
			))
		self.currencies = []  # type: list[ShopCurrency]
		for currency_id in available_currencies:
			if currency_id not in CURRENCY_DICT:
				part.LogError("ShopInstance.init_categories 找不到货币配置：" + currency_id)
				continue
			currency = CURRENCY_DICT[currency_id]
			self.currencies.append(currency)

	def format_player_currencies(self, player_id):
		strs = []
		for currency in self.currencies:
			strs.append(currency.icon_text + " " + str(currency.get_player_have(player_id)))
		return " ".join(strs)

	def to_ui_dict(self, player_id):
		return {
			"type": self.shop_type,
			"name": self.raw_config.name,
			"intro": self.raw_config.intro,
			"currencies": self.format_player_currencies(player_id),
			"categories": [category.to_ui_dict(self.part, player_id) for category in self.categories]
		}
