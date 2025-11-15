# -*- coding: utf-8 -*-
class ShopCurrency:

	def __init__(self, name, item_dict, icon_text, text_color):
		self.name = name
		self.item_dict = item_dict
		self.icon_text = icon_text
		self.text_color = text_color

	def __hash__(self):
		return hash(self.name)

	def __eq__(self, other):
		return self.name == other.name

	def check_item_valid(self, item_dict):
		"""
		对比物品是否是该货币
		"""
		if item_dict is None:
			return False
		if 'newItemName' not in item_dict:
			return False
		if 'newAuxValue' not in item_dict:
			return False
		return item_dict['newItemName'] == self.item_dict['newItemName'] and item_dict['newAuxValue'] == self.item_dict['newAuxValue']

	def get_player_have(self, player_id):
		"""
		获取玩家拥有的货币数量
		"""
		import mod.server.extraServerApi as serverApi
		if self == EXP:
			comp_lv = serverApi.GetEngineCompFactory().CreateLv(player_id)
			return comp_lv.GetPlayerLevel()
		comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
		all_items = comp.GetPlayerAllItems(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY)
		count = 0
		for item in all_items:
			if self.check_item_valid(item):
				count += item['count']
		return count

	def pay_for_it(self, player_id, count, skip_check=False):
		"""
		支付货币
		"""
		import mod.server.extraServerApi as serverApi
		if not skip_check:
			player_have = self.get_player_have(player_id)
			if player_have < count:
				return False
		if self == EXP:
			comp_lv = serverApi.GetEngineCompFactory().CreateLv(player_id)
			comp_lv.AddPlayerLevel(-count)
			return True
		comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
		for index in range(36):
			item = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY, index)
			if self.check_item_valid(item):
				if item['count'] >= count:
					item['count'] -= count
					comp.SetInvItemNum(index, item['count'])
					return True
				else:
					count -= item['count']
					item['count'] = 0
					comp.SetInvItemNum(index, 0)


COPPER = ShopCurrency(
	"铜锭",
	{
		'newItemName': 'minecraft:iron_ingot',
		'newAuxValue': 0,
		'count': 1
	},
	u"\uE1AB".encode("utf-8"),
	"§6"
)

IRON = ShopCurrency(
	"铁锭",
	{
		'newItemName': 'minecraft:iron_ingot',
		'newAuxValue': 0,
		'count': 1
	},
	u"\uE1AC".encode("utf-8"),
	"§f"
)

GOLD = ShopCurrency(
	"金锭",
	{
		'newItemName': 'minecraft:gold_ingot',
		'newAuxValue': 0,
		'count': 1
	},
	u"\uE1AD".encode("utf-8"),
	"§e"
)

DIAMOND = ShopCurrency(
	"钻石",
	{
		'newItemName': 'minecraft:diamond',
		'newAuxValue': 0,
		'count': 1
	},
	u"\uE1AE".encode("utf-8"),
	"§b"
)

EMERALD = ShopCurrency(
	"绿宝石",
	{
		'newItemName': 'minecraft:emerald',
		'newAuxValue': 0,
		'count': 1
	},
	u"\uE1AF".encode("utf-8"),
	"§a"
)

EXP = ShopCurrency(
	"经验",
	None,
	u"\uE1AF".encode("utf-8"),
	"§a"
)

CURRENCY_DICT = {
	"COPPER": COPPER,
	"IRON": IRON,
	"GOLD": GOLD,
	"DIAMOND": DIAMOND,
	"EMERALD": EMERALD,
	"EXP": EXP
}