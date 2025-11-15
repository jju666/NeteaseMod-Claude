# -*- coding: utf-8 -*-
from collections import OrderedDict

from BedWarsShopCategoryConfig import BedWarsShopCategoryConfig
from ShopGoods import ShopGoods
from GoodsPrice import GoodsPrice
from ShopGoodsPool import GOODS_POOL
from ShopGoodsStaticConfig import ShopGoodsStaticConfig


class ShopInstanceCategory:

	def __init__(self, part, name, intro, category_config, price_config):
		# price_config: 'itemPrices' 与 'upgradePrices' 的dict
		def get_price(key):
			if key in price_config['item']:
				return [GoodsPrice.from_array(price_config['item'][key])]
			elif key in price_config['upgrade']:
				rs = []
				for arr in price_config['upgrade'][key]:
					rs.append(GoodsPrice.from_array(arr))
				return rs
			else:
				part.LogError("ShopInstance.init_categories 找不到价格配置：" + key)
				return [GoodsPrice.of_free()]

		self.name = name  # type: str
		self.intro = intro  # type: str
		self.category_config = category_config  # type: BedWarsShopCategoryConfig
		self.goods = OrderedDict()  # type: dict[str, ShopGoods]
		# 从配置中实例化goods（商品实例）
		for good_id in self.category_config.goods:
			if good_id not in GOODS_POOL:
				part.LogError("ShopInstance.init_categories 找不到商品配置：" + good_id)
				continue
			good = GOODS_POOL[good_id]  # type: ShopGoodsStaticConfig
			def get_price_lambda(_good_id):
				return lambda: get_price(_good_id)
			self.goods[good_id] = good.build_shop_goods(get_price_lambda(good_id))

	def to_ui_dict(self, part, player_id):
		ui_dict = {
			"name": self.name,
			"intro": self.intro,
			"ui": self.category_config.uiModUI.to_dict(),
			"goods": [
				good.to_ui_dict(part, player_id) for good in self.goods.values()
			]
		}
		return ui_dict