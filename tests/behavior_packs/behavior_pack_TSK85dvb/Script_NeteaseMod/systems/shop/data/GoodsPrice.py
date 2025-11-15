# -*- coding: utf-8 -*-
from __future__ import print_function
from . import ShopCurrency


class GoodsPrice:

	def __init__(self):
		self.currencies = {}  # type: dict[ShopCurrency.ShopCurrency, int]

	@staticmethod
	def of_full(copper, iron, gold, diamond, emerald, exp):
		price = GoodsPrice()
		if copper > 0: price.currencies[ShopCurrency.COPPER] = copper
		if iron > 0: price.currencies[ShopCurrency.IRON] = iron
		if gold > 0: price.currencies[ShopCurrency.GOLD] = gold
		if diamond > 0: price.currencies[ShopCurrency.DIAMOND] = diamond
		if emerald > 0: price.currencies[ShopCurrency.EMERALD] = emerald
		if exp > 0: price.currencies[ShopCurrency.EXP] = exp
		return price

	@staticmethod
	def of_free():
		return GoodsPrice()

	@staticmethod
	def from_array(arr):
		price = GoodsPrice()
		if len(arr) > 0:
			price.currencies[ShopCurrency.COPPER] = arr[0]
		if len(arr) > 1:
			price.currencies[ShopCurrency.IRON] = arr[1]
		if len(arr) > 2:
			price.currencies[ShopCurrency.GOLD] = arr[2]
		if len(arr) > 3:
			price.currencies[ShopCurrency.DIAMOND] = arr[3]
		if len(arr) > 4:
			price.currencies[ShopCurrency.EMERALD] = arr[4]
		if len(arr) > 5:
			price.currencies[ShopCurrency.EXP] = arr[5]
		return price

	def can_afford(self, player_id):
		for currency, amount in self.currencies.items():
			if currency.get_player_have(player_id) < amount:
				return False
		return True

	def pay(self, player_id):
		for currency, amount in self.currencies.items():
			currency.pay_for_it(player_id, amount)

	def get_price_icon_string(self):
		strs = []
		for currency, amount in self.currencies.items():
			if amount > 0:
				strs.append(currency.icon_text + " " + currency.text_color + str(amount))
		return " ".join(strs)

	def add(self, price):
		"""
		合并另一个price
		:type price: GoodsPrice
		:rtype GoodsPrice
		"""
		for currency, amount in price.currencies.items():
			if currency in self.currencies:
				self.currencies[currency] += amount
			else:
				self.currencies[currency] = amount
		return self

	def multiply(self, multipy):
		"""
		乘以一个数
		:type multipy: int
		:rtype GoodsPrice
		"""
		for currency, amount in self.currencies.items():
			self.currencies[currency] = amount * multipy
		return self