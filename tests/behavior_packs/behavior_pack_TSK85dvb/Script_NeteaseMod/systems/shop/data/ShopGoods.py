# -*- coding: utf-8 -*-
from .ShopGoodsStaticConfig import ShopGoodsStaticConfig
from .GoodsPrice import GoodsPrice


class ShopGoods:

	def __init__(self, good_config, price_supplier, buy_callback=None):
		self.good_config = good_config  # type: ShopGoodsStaticConfig
		self.price_supplier = price_supplier  # type: callable  # -> list[GoodsPrice]
		self.buy_callback = buy_callback  # type: callable

	def get_price_from_player(self, part, player_id):
		"""
		从玩家获取当前价格
		:type part: BedWarsShopPart
		:type player_id: str
		:rtype: GoodsPrice
		"""
		current_level = self.good_config.check_next_price_level(part, player_id) if self.good_config.check_next_price_level is not None else 0
		return self.get_price(current_level)

	def get_price(self, level):
		"""
		获取价格
		:type level: int
		:rtype: GoodsPrice
		"""
		prices = self.price_supplier()
		if level >= len(prices):
			level = len(prices) - 1
		return prices[level]

	def get_detail_intros_and_price(self, part, player_id):
		"""
		获取价格列表
		:rtype: str
		"""
		lines = []
		if self.good_config.upgrade_type:
			levels_intro = self.good_config.levels_intro
			self.get_cannot_buy_msg(part, player_id)
			prices = self.price_supplier()
			next_level = self.good_config.check_next_price_level(part, player_id)
			for i in range(1, len(prices)):
				if i - 1 < len(levels_intro):
					intro = levels_intro[i - 1]
				else:
					intro = "?"
				line = str(i) + "级: " + intro + "  " + prices[i].get_price_icon_string()
				if i == next_level:
					line = "§b" + line
				elif i < next_level:
					line = "§a" + line
				else:
					line = "§7" + line
				lines.append(line)
		else:
			price = self.get_price_from_player(part, player_id)
			lines.append(price.get_price_icon_string())
		cannot_buy_msg = self.get_cannot_buy_msg(part, player_id)
		if cannot_buy_msg:
			cannot_buy_msg = "§c" + cannot_buy_msg
		else:
			cannot_buy_msg = ""
		return "§7" + self.good_config.intro + "\n\n" + "\n".join(lines) + "\n\n" + cannot_buy_msg

	def buy_it(self, part, player_id):
		"""
		购买物品
		:type part: BedWarsShopPart
		:type player_id: str
		"""
		price = self.get_price_from_player(part, player_id)
		if not price.can_afford(player_id):
			return False
		price.pay(player_id)
		if self.good_config.buy_callable is not None:
			self.good_config.buy_callable(part, player_id)
		if self.buy_callback is not None:
			self.buy_callback(player_id)
		part.BroadcastPresetSystemEvent("BedWarsShopBuy", {
			"dimension": part.GetParent().dimension,
			"player_id": player_id,
			"good_key": self.good_config.key,
		})
		return True

	def get_cannot_buy_msg(self, part, player_id):
		rs = None
		if self.good_config.check_can_buy is not None:
			rs = self.good_config.check_can_buy(part, player_id)
		if rs is None:
			price = self.get_price_from_player(part, player_id)
			if not price.can_afford(player_id):
				rs = "余额不足"
		return rs

	def to_ui_dict(self, part, player_id):
		return {
			"key": self.good_config.key,
			"name": self.good_config.name,
			"intro": self.good_config.intro,
			"levels_intro": self.good_config.levels_intro,
			"upgrade_type": self.good_config.upgrade_type,
			"show_item_dict": self.good_config.show_item_dict_factory(part, player_id),
			"cannot_buy_msg": self.get_cannot_buy_msg(part, player_id),
			"price": self.get_price_from_player(part, player_id).get_price_icon_string(),
			"detail_intros": self.get_detail_intros_and_price(part, player_id)
		}