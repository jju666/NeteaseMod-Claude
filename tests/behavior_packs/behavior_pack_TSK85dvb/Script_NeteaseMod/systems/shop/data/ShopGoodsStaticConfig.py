# -*- coding: utf-8 -*-
import mod.server.extraServerApi as serverApi


ARMOR_ITEMS = [
	"minecraft:leather_helmet",
	"minecraft:leather_chestplate",
	"minecraft:leather_leggings",
	"minecraft:leather_boots",
	"minecraft:chainmail_helmet",
	"minecraft:chainmail_chestplate",
	"minecraft:chainmail_leggings",
	"minecraft:chainmail_boots",
	"minecraft:iron_helmet",
	"minecraft:iron_chestplate",
	"minecraft:iron_leggings",
	"minecraft:iron_boots",
	"minecraft:golden_helmet",
	"minecraft:golden_chestplate",
	"minecraft:golden_leggings",
	"minecraft:golden_boots",
	"minecraft:diamond_helmet",
	"minecraft:diamond_chestplate",
	"minecraft:diamond_leggings",
	"minecraft:diamond_boots",
	"minecraft:netherite_helmet",
	"minecraft:netherite_chestplate",
	"minecraft:netherite_leggings",
	"minecraft:netherite_boots"
]


def add_item_to_player(player_id, item_dict):
	comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)
	item_name = item_dict["newItemName"] if "newItemName" in item_dict else item_dict["itemName"]
	if item_name in ARMOR_ITEMS:
		item_dict['userData'] = {"minecraft:item_lock": {"__type__": 1, "__value__": True}}
		if 'helmet' in item_name:
			comp_item.SetEntityItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, item_dict, 0)
		elif 'chestplate' in item_name:
			comp_item.SetEntityItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, item_dict, 1)
		elif 'leggings' in item_name:
			comp_item.SetEntityItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, item_dict, 2)
		elif 'boots' in item_name:
			comp_item.SetEntityItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, item_dict, 3)
	else:
		comp_item.SpawnItemToPlayerInv(item_dict, player_id)

def set_item_to_player(player_id, index, item_dict):
	comp_item = serverApi.GetEngineCompFactory().CreateItem(player_id)
	comp_item.SpawnItemToPlayerInv(item_dict, player_id, index)


def try_get_team_beds(dimension_id, team):
	"""
	获取指定队伍的床的Part
	:type dimension_id: int
	:type team: str
	:rtype: list[BedWarsBedPart]
	"""
	from ...BedWarsBed.BedWarsBedPart import BedWarsBedPart
	import Preset.Controller.PresetApi as presetApi
	presets = presetApi.GetPresetsByName("BedWarsBed", dimension_id)
	beds = []
	for preset in presets:
		bed_part = preset.GetPartByType("BedWarsBedPart")
		if isinstance(bed_part, BedWarsBedPart):
			if bed_part.team == team:
				beds.append(bed_part)
	return beds


class CurrentItemFromSet(object):
	def __init__(self, inv_index, inv_item, shop_index, shop_item, have_next_level, shop_index_next_level, shop_item_next_level, have_previous_level, shop_index_previous_level, shop_item_previous_level):
		self.inv_index = inv_index  # type: int
		self.inv_item = inv_item  # type: dict | None
		self.shop_index = shop_index  # type: int
		self.shop_item = shop_item  # type: dict | None
		self.have_next_level = have_next_level  # type: bool
		self.shop_index_next_level = shop_index_next_level  # type: int
		self.shop_item_next_level = shop_item_next_level  # type: dict | None
		self.have_previous_level = have_previous_level  # type: bool
		self.shop_index_previous_level = shop_index_previous_level  # type: int
		self.shop_item_previous_level = shop_item_previous_level  # type: dict | None

	def have_item(self):
		# type: () -> bool
		return self.inv_index >= 0

	@staticmethod
	def find_player_item_from_set(player_id, items):
		"""
		:type player_id: str
		:type items: list[dict]
		:rtype: CurrentItemFromSet
		"""
		comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
		for i in range(len(items)):
			item = items[i]
			inv = comp.GetPlayerAllItems(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY)
			for j in range(len(inv)):
				if inv[j] is None:
					continue
				it = inv[j]
				it_name = it["newItemName"] if "newItemName" in it else it["itemName"]
				it_aux = it["newItemAux"] if "newItemAux" in it else it["itemAux"] if "itemAux" in it else 0
				item_name = item["newItemName"] if "newItemName" in item else item["itemName"]
				item_aux = item["newItemAux"] if "newItemAux" in item else item["itemAux"] if "itemAux" in item else 0
				if it_name == item_name and it_aux == item_aux:
					next_level = min(i + 1, len(items) - 1)
					return CurrentItemFromSet(j, it, i, item, i < len(items) - 1, next_level, items[next_level], i > 0, max(0, i - 1), items[max(0, i - 1)])
		return CurrentItemFromSet(-1, None, 0, items[0], True, 0, items[0], False, 0, items[0])


class ShopGoodsStaticConfig:
	"""
	硬编码的商店的商品的实现，包括如何展示，如何给予等
	"""
	def __init__(self, key, name, intro, levels_intro, show_item_dict_factory, buy_callable, check_next_price_level, check_can_buy, upgrade_type, upgrade_items):
		self.key = key  # type: str
		self.name = name  # type: str
		self.intro = intro  # type: str
		self.levels_intro = levels_intro  # type: list[str]
		self.show_item_dict_factory = show_item_dict_factory  # type: callable  # part, player_id -> dict
		self.buy_callable = buy_callable  # type: callable  # part, player_id -> void
		self.check_next_price_level = check_next_price_level  # type: callable  # part, player_id -> int
		self.check_can_buy = check_can_buy  # type: callable  # part, player_id -> str(失败消息) | None
		self.upgrade_type = upgrade_type  # type: bool
		self.upgrade_items = upgrade_items  # type: list[dict] | None  # 可升级物品的各等级序列

	def build_shop_goods(self, price_supplier):
		"""
		构建一个ShopGoods
		:type price_supplier: callable  # -> list[BedWarsShopGoodsPrice]
		:return:
		"""
		from ShopGoods import ShopGoods
		return ShopGoods(self, price_supplier)

	@staticmethod
	def builder(key):
		return Builder(key)

class Builder:
	def __init__(self, key):
		self._key = key  # type: str
		self._name = None  # type: str | None
		self._intro = None  # type: str | None
		self._levels_intro = None  # type: list[str] | None
		self._show_item_dict_factory = None  # part, player_id -> dict
		self._buy_callable = None  # part, player_id -> void
		self._check_next_price_level = None  # part, player_id -> int
		self._check_can_buy = None  # part, player_id -> str(失败消息) | None
		self._upgrade_type = False  # type: bool
		self._upgrade_items = None  # type: list[dict] | None  # 可升级物品的各等级序列

	def name(self, name):
		self._name = name
		return self

	def intro(self, intro):
		self._intro = intro
		return self

	def levels_intro(self, levels_intro):
		self._levels_intro = levels_intro
		return self

	def show_item_dict_factory(self, show_item_dict_factory):
		self._show_item_dict_factory = show_item_dict_factory
		return self

	def buy_callable(self, buy_callable):
		self._buy_callable = buy_callable
		return self

	def simple_item(self, *item_dict):
		"""
		简单的show_item_dict_factory
		"""
		self.show_item_dict_factory(lambda part, player_id: item_dict[0])
		def buy(part, player_id):
			print("buy", player_id, item_dict)
			for item in item_dict:
				# 检查是否为木板，如果是则应用个性商店装饰品
				if item.get("newItemName") == "minecraft:planks":
					modified_item = apply_personalized_shop_ornament(part, player_id, item)
					add_item_to_player(player_id, modified_item)
				else:
					add_item_to_player(player_id, item)
					
		def apply_personalized_shop_ornament(part, player_id, item):
			"""
			应用个性商店装饰品效果
			"""
			try:
				from ...ECBedWarsOrnament.ECBedWarsOrnamentPart import try_get_bedwars_ornament_part
				ornament_part = try_get_bedwars_ornament_part()
				if ornament_part is not None:
					ornament, data = ornament_part.find_equipped_ornament(player_id, "personalized-shop")
					if ornament is not None:
						# 获取装饰品指定的木板类型
						plank_item_name = ornament.get_plank_item_name()
						print("玩家 {} 装备了个性商店装饰品，将木板替换为: {}".format(player_id, plank_item_name))
						# 创建新的物品字典，替换木板类型
						modified_item = item.copy()
						modified_item["newItemName"] = plank_item_name
						return modified_item
			except Exception as e:
				print("应用个性商店装饰品时出错: {}".format(str(e)))
			
			# 如果没有装备个性商店装饰品或出错，返回原始物品
			return item
		self.buy_callable(buy)
		return self

	def simple_upgrade(self, upgrade_key, item_names, enchantment=None):
		"""
		简单的upgrade
		:type upgrade_key: str
		:type item_names: list[str]
		:type enchantment: tuple[int,int] | None
		:return:
		"""
		def show_item_dict_factory(part, player_id):
			from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
			bedwars_part = try_get_bedwars_part()
			team = bedwars_part.team_module.get_player_team(player_id)
			if team is None:
				return None
			manager = bedwars_part.team_upgrades[team]
			entry = manager.entries[upgrade_key]
			item_name = item_names[min(entry.level, len(item_names) - 1)]
			return {
				"newItemName": item_name,
				"count": max(1, entry.level),
				"enchantData": [enchantment] if enchantment is not None else []
			}
		self.show_item_dict_factory(show_item_dict_factory)
		def check_can_buy_factory(part, player_id):
			from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
			bedwars_part = try_get_bedwars_part()
			team = bedwars_part.team_module.get_player_team(player_id)
			if team is None:
				return "§c你不在队伍中"
			manager = bedwars_part.team_upgrades[team]
			entry = manager.entries[upgrade_key]
			if entry.level >= entry.max_level:
				return "§e已达到最高等级"
			return None
		self.check_can_buy(check_can_buy_factory)
		def next_price_level_factory(part, player_id):
			from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
			bedwars_part = try_get_bedwars_part()
			team = bedwars_part.team_module.get_player_team(player_id)
			if team is None:
				return 0
			manager = bedwars_part.team_upgrades[team]
			entry = manager.entries[upgrade_key]
			return entry.level + 1
		self.check_next_price_level(next_price_level_factory)
		self.upgrade_type(True)
		def buy_factory(part, player_id):
			from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
			bedwars_part = try_get_bedwars_part()
			team = bedwars_part.team_module.get_player_team(player_id)
			if team is None:
				return
			manager = bedwars_part.team_upgrades[team]
			entry = manager.entries[upgrade_key]
			entry.level_up()
		self.buy_callable(buy_factory)
		return self

	def simple_trap(self, trap):
		def buy_factory(part, player_id):
			from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
			bedwars_part = try_get_bedwars_part()
			team = bedwars_part.team_module.get_player_team(player_id)
			if team is None:
				return
			bed_parts = try_get_team_beds(part.GetDimension(), team)
			if len(bed_parts) == 0:
				part.LogError("simple_trap: 没有找到队伍 %s 的床" % team)
				return
			bed_parts[0].trap_manager.add_trap(trap)
		self.buy_callable(buy_factory)
		def check_can_buy_factory(part, player_id):
			from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
			bedwars_part = try_get_bedwars_part()
			team = bedwars_part.team_module.get_player_team(player_id)
			if team is None:
				return "§c你不在队伍中"
			bed_parts = try_get_team_beds(part.GetDimension(), team)
			if len(bed_parts) == 0:
				return "§c你的队伍没有床"
			if bed_parts[0].trap_manager.is_trap_full():
				return "§8所有的陷阱槽位已满"
			return None
		self.check_can_buy(check_can_buy_factory)
		def next_price_level_factory(part, player_id):
			from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
			bedwars_part = try_get_bedwars_part()
			team = bedwars_part.team_module.get_player_team(player_id)
			if team is None:
				return 0
			bed_parts = try_get_team_beds(part.GetDimension(), team)
			if len(bed_parts) == 0:
				return 0
			return len(bed_parts[0].trap_manager.traps)
		self.check_next_price_level(next_price_level_factory)
		return self

	def simple_item_upgrade(self, items):
		"""
		:type: items: list[dict]
		"""
		self._upgrade_items = items
		self.upgrade_type(True)
		self.show_item_dict_factory(lambda part, player_id: CurrentItemFromSet.find_player_item_from_set(player_id, items).shop_item_next_level)
		def buy_factory(part, player_id):
			current = CurrentItemFromSet.find_player_item_from_set(player_id, items)
			if current.inv_index >= 0:
				set_item_to_player(player_id, current.inv_index, current.shop_item_next_level)
			else:
				add_item_to_player(player_id, current.shop_item_next_level)
		self.buy_callable(buy_factory)
		self.check_next_price_level(lambda part, player_id: CurrentItemFromSet.find_player_item_from_set(player_id, items).shop_index_next_level)
		def check_can_buy_factory(part, player_id):
			current = CurrentItemFromSet.find_player_item_from_set(player_id, items)
			if current.have_next_level:
				return None
			return "§c您已购买过该物品！"
		self.check_can_buy(check_can_buy_factory)
		return self

	def check_next_price_level(self, check_next_price_level):
		self._check_next_price_level = check_next_price_level
		return self

	def check_can_buy(self, check_can_buy):
		self._check_can_buy = check_can_buy
		return self

	def upgrade_type(self, upgrade_type):
		self._upgrade_type = upgrade_type
		return self

	def build(self):
		assert self._name is not None, "name is required"
		assert self._show_item_dict_factory is not None, "show_item_dict_factory is required"
		assert self._buy_callable is not None, "buy_callable is required"
		return ShopGoodsStaticConfig(self._key, self._name, self._intro, self._levels_intro, self._show_item_dict_factory, self._buy_callable, self._check_next_price_level, self._check_can_buy, self._upgrade_type, self._upgrade_items)

