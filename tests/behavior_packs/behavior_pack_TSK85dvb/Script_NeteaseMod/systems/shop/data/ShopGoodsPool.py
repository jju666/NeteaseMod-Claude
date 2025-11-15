# -*- coding: utf-8 -*-
from mod.common.minecraftEnum import ItemColor, EnchantType

from .ShopGoodsStaticConfig import ShopGoodsStaticConfig, add_item_to_player
import mod.server.extraServerApi as serverApi


def get_player_team(part, player_id):
	"""
	获取玩家所在队伍
	:param part: ShopContextAdapter实例（适配器）
	:param player_id: 玩家ID
	:return: 队伍ID或None
	"""
	# 新架构：通过适配器获取RoomManagementSystem
	if hasattr(part, 'room_management_system') and part.room_management_system:
		team_module = part.room_management_system.team_module
		if team_module:
			return team_module.get_player_team(player_id)
	return None


def get_player_team_item_color(part, player_id):
	"""
	获取玩家所在队伍的物品颜色（羊毛）
	:param part: ShopContextAdapter实例（适配器）
	:param player_id: 玩家ID
	:return: ItemColor枚举值
	"""
	# 新架构：从系统模块导入team_types
	from Script_NeteaseMod.systems.team.TeamType import team_types
	team = get_player_team(part, player_id)
	if team is None or team not in team_types:
		return ItemColor.Black
	return team_types[team].item_color


ordered_armor_chestplate = [
	"minecraft:leather_chestplate",
	"minecraft:chainmail_chestplate",
	"minecraft:iron_chestplate",
	"minecraft:gold_chestplate",
	"minecraft:diamond_chestplate",
	"minecraft:netherite_chestplate",
]


def is_player_chestplate_better_than(player_id, armor_item_name):
	comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
	chestplate = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 1)
	if chestplate is None:
		return False
	if armor_item_name not in ordered_armor_chestplate:
		print("ShopGoodsPool.is_player_chestplate_better_than: {} not in ordered_armor_chestplate".format(armor_item_name))
		return False
	index = ordered_armor_chestplate.index(chestplate['newItemName'])
	return ordered_armor_chestplate.index(armor_item_name) <= index


ordered_leggings = [
	"minecraft:leather_leggings",
	"minecraft:chainmail_leggings",
	"minecraft:iron_leggings",
	"minecraft:gold_leggings",
	"minecraft:diamond_leggings",
	"minecraft:netherite_leggings",
]

def is_player_leggings_better_than(player_id, armor_item_name):
	comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
	leggings = comp.GetPlayerItem(serverApi.GetMinecraftEnum().ItemPosType.ARMOR, 2)
	if leggings is None:
		return False
	if armor_item_name not in ordered_leggings:
		print("ShopGoodsPool.is_player_leggings_better_than: {} not in ordered_leggings".format(armor_item_name))
		return False
	index = ordered_leggings.index(leggings['newItemName'])
	return ordered_leggings.index(armor_item_name) <= index


ordered_swords = [
	"minecraft:wooden_sword",
	"minecraft:stone_sword", 
	"minecraft:iron_sword",
	"minecraft:diamond_sword",
	"minecraft:netherite_sword",
]

def is_player_sword_better_than(part, player_id, sword_item_name):
	"""检查玩家是否已拥有比指定剑更好品质的剑（同时检查记录和背包）"""
	from ...ECBedWars.ECBedWarsPartTool import try_get_bedwars_part
	bedwars_part = try_get_bedwars_part()
	if not bedwars_part or not hasattr(bedwars_part, 'player_sword_record'):
		return False
	
	if sword_item_name not in ordered_swords:
		print("ShopGoodsPool.is_player_sword_better_than: {} not in ordered_swords".format(sword_item_name))
		return False
	
	new_sword_quality = ordered_swords.index(sword_item_name)
	
	# 方法1：检查玩家的剑类购买记录
	current_sword_record = bedwars_part.player_sword_record.get(player_id, "minecraft:wooden_sword")
	record_quality = 0
	if current_sword_record in ordered_swords:
		record_quality = ordered_swords.index(current_sword_record)
	
	# 方法2：检查玩家背包中实际拥有的最高品质剑
	import mod.server.extraServerApi as serverApi
	comp = serverApi.GetEngineCompFactory().CreateItem(player_id)
	inv_items = comp.GetPlayerAllItems(serverApi.GetMinecraftEnum().ItemPosType.INVENTORY)
	
	highest_inv_sword_quality = 0
	for item in inv_items:
		if item and item.get('newItemName') in ordered_swords:
			item_quality = ordered_swords.index(item.get('newItemName'))
			if item_quality > highest_inv_sword_quality:
				highest_inv_sword_quality = item_quality
	
	# 使用记录和背包中的较高品质作为判断依据
	# 但是背包检查有更高的优先级，因为这反映了玩家当前实际拥有的剑
	effective_quality = max(record_quality, highest_inv_sword_quality)
	
	# 如果玩家背包中没有剑但有购买记录，且记录比要购买的剑好，仍然禁止购买
	# 这是为了防止玩家通过丢剑来绕过限制重复购买低级剑
	if highest_inv_sword_quality == 0 and record_quality > new_sword_quality:
		return True
	
	# 如果玩家背包中有剑，以背包中的剑为准
	if highest_inv_sword_quality > 0:
		return new_sword_quality <= highest_inv_sword_quality
	
	# 如果背包中没有剑且没有购买记录，允许购买
	return False


GOODS_POOL = {
	# region 方块
	"block.wool":
		ShopGoodsStaticConfig.builder("block.wool")
		.name("羊毛")
		.intro("可用于搭桥穿越岛屿")
		.show_item_dict_factory(lambda part, player_id: {"newItemName": "minecraft:wool", "newAuxValue": get_player_team_item_color(part, player_id), "count": 16})
		.buy_callable(lambda part, player_id: add_item_to_player(player_id, {"newItemName": "minecraft:wool", "newAuxValue": get_player_team_item_color(part, player_id), "count": 16}))
		.build(),
	"block.hay":
		ShopGoodsStaticConfig.builder("block.hay")
		.name("干草块")
		.intro("干草块？？")
		.simple_item({"newItemName": "minecraft:hay_block", "count": 16})
		.build(),
	"block.clay":
		ShopGoodsStaticConfig.builder("block.clay")
		.name("硬化粘土")
		.intro("用于保卫床的基础方块")
		.show_item_dict_factory(lambda part, player_id: {"newItemName": "minecraft:stained_hardened_clay", "newAuxValue": get_player_team_item_color(part, player_id), "count": 16})
		.buy_callable(lambda part, player_id: add_item_to_player(player_id, {"newItemName": "minecraft:stained_hardened_clay", "newAuxValue": get_player_team_item_color(part, player_id), "count": 16}))
		.build(),
	"block.sandstone":
		ShopGoodsStaticConfig.builder("block.sandstone")
		.name("沙石")
		.intro("用于保卫家的基础方块")
		.simple_item({"newItemName": "minecraft:sandstone", "count": 16})
		.build(),
	"block.plank":
		ShopGoodsStaticConfig.builder("block.plank")
		.name("木板")
		.intro("用于保卫床的优质方块。 能有效抵御镐子的破坏")
		.simple_item({"newItemName": "minecraft:planks", "count": 16})
		.build(),
	"block.wood":
		ShopGoodsStaticConfig.builder("block.wood")
		.name("原木")
		.intro("用于保卫床的优质方块。 能有效抵御镐子的破坏")
		.simple_item({"newItemName": "minecraft:log", "count": 16})
		.build(),
	"block.end-stone":
		ShopGoodsStaticConfig.builder("block.end-stone")
		.name("末地石")
		.intro("用于保卫床的坚固方块。")
		.simple_item({"newItemName": "minecraft:end_stone", "count": 16})
		.build(),
	"block.purpur":
		ShopGoodsStaticConfig.builder("block.purpur")
		.name("紫珀方块(防御使用)")
		.intro("防御使用的方块，和末地石差不多")
		.simple_item({"newItemName": "minecraft:purpur_block", "count": 16})
		.build(),
	"block.end-stone.12":
		ShopGoodsStaticConfig.builder("block.end-stone.12")
		.name("末地石")
		.intro("用于保卫床的坚固方块。")
		.simple_item({"newItemName": "minecraft:end_stone", "count": 12})
		.build(),
	"block.ladder":
		ShopGoodsStaticConfig.builder("block.ladder")
		.name("梯子")
		.intro("可用于救助树上卡住的猫")
		.simple_item({"newItemName": "minecraft:ladder", "count": 16})
		.build(),
	"block.obsidian":
		ShopGoodsStaticConfig.builder("block.obsidian")
		.name("黑曜石")
		.intro("百分百保护你的床")
		.simple_item({"newItemName": "minecraft:obsidian", "count": 1})
		.build(),
	"block.obsidian.4":
		ShopGoodsStaticConfig.builder("block.obsidian.4")
		.name("黑曜石")
		.intro("百分百保护你的床")
		.simple_item({"newItemName": "minecraft:obsidian", "count": 4})
		.build(),
	"block.glass":
		ShopGoodsStaticConfig.builder("block.glass")
		.name("防爆玻璃")
		.intro("免疫爆炸")
		.show_item_dict_factory(lambda part, player_id: {
			"newItemName": "minecraft:stained_glass",
			"newAuxValue": get_player_team_item_color(part, player_id),
			"count": 8
		})
		.buy_callable(lambda part, player_id: add_item_to_player(
			player_id,
			{
				"newItemName": "minecraft:stained_glass",
				"newAuxValue": get_player_team_item_color(part, player_id),
				"count": 8
			}
		))
		.build(),
	"block.chest":
		ShopGoodsStaticConfig.builder("block.chest")
		.name("箱子")
		.intro("用于奇怪用途的箱子？")
		.simple_item({"newItemName": "minecraft:chest", "count": 1})
		.build(),
	"block.cobweb":
		ShopGoodsStaticConfig.builder("block.cobweb")
		.name("蜘蛛网")
		.intro("阻碍敌人移动的极佳方法")
		.simple_item({"newItemName": "minecraft:web", "count": 1})
		.build(),
	# "block.lantern":
	# 	ShopGoodsStaticConfig.builder("block.lantern")
	# 	.name("灯笼")
	# 	.intro("用于照明")
	# 	.simple_item({"newItemName": "minecraft:lantern", "count": 1})
	# 	.build(),
	# endregion
	# region 护甲
	"armor.gold":
		ShopGoodsStaticConfig.builder("armor.gold")
		.name("黄金套装")
		.intro("包含黄金胸甲和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:golden_chestplate") else None)
		.simple_item(
			{"newItemName": "minecraft:golden_chestplate", "count": 1},
			{"newItemName": "minecraft:golden_boots", "count": 1},
		)
		.build(),
	"armor.chain":
		ShopGoodsStaticConfig.builder("armor.chain")
		.name("锁链套装")
		.intro("包含锁链胸甲和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:chainmail_chestplate") else None)
		.simple_item(
			{"newItemName": "minecraft:chainmail_chestplate", "count": 1},
			{"newItemName": "minecraft:chainmail_boots", "count": 1},
		)
		.build(),
	"armor.iron":
		ShopGoodsStaticConfig.builder("armor.iron")
		.name("铁套装")
		.intro("包含铁胸甲和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:iron_chestplate") else None)
		.simple_item(
			{"newItemName": "minecraft:iron_chestplate", "count": 1},
			{"newItemName": "minecraft:iron_boots", "count": 1},
		)
		.build(),
	"armor.diamond":
		ShopGoodsStaticConfig.builder("armor.diamond")
		.name("钻石套装")
		.intro("包含钻石胸甲和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_chestplate_better_than(player_id, "minecraft:diamond_chestplate") else None)
		.simple_item(
			{"newItemName": "minecraft:diamond_chestplate", "count": 1},
			{"newItemName": "minecraft:diamond_boots", "count": 1},
		)
		.build(),
	"armor.gold.r":
		ShopGoodsStaticConfig.builder("armor.gold.r")
		.name("黄金套装")
		.intro("包含黄金护腿和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:golden_leggings") else None)
		.simple_item(
			{"newItemName": "minecraft:golden_leggings", "count": 1},
			{"newItemName": "minecraft:golden_boots", "count": 1},
		)
		.build(),
	"armor.chain.r":
		ShopGoodsStaticConfig.builder("armor.chain.r")
		.name("锁链套装")
		.intro("包含锁链护腿和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:chainmail_leggings") else None)
		.simple_item(
			{"newItemName": "minecraft:chainmail_leggings", "count": 1},
			{"newItemName": "minecraft:chainmail_boots", "count": 1},
		)
		.build(),
	"armor.iron.r":
		ShopGoodsStaticConfig.builder("armor.iron.r")
		.name("铁套装")
		.intro("包含铁护腿和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:iron_leggings") else None)
		.simple_item(
			{"newItemName": "minecraft:iron_leggings", "count": 1},
			{"newItemName": "minecraft:iron_boots", "count": 1},
		)
		.build(),
	"armor.diamond.r":
		ShopGoodsStaticConfig.builder("armor.diamond.r")
		.name("钻石套装")
		.intro("包含钻石护腿和靴子")
		.check_can_buy(lambda part, player_id: "已拥有更好的护甲" if is_player_leggings_better_than(player_id, "minecraft:diamond_leggings") else None)
		.simple_item(
			{"newItemName": "minecraft:diamond_leggings", "count": 1},
			{"newItemName": "minecraft:diamond_boots", "count": 1},
		)
		.build(),

	# endregion
	# region 剑
	"sword.stone":
		ShopGoodsStaticConfig.builder("sword.stone")
		.name("石剑")
		.intro("每次攻击，造成6HP伤害")
		.check_can_buy(lambda part, player_id: "已拥有高等级剑" if is_player_sword_better_than(part, player_id, "minecraft:stone_sword") else None)
		.simple_item({"newItemName": "minecraft:stone_sword", "count": 1})
		.build(),
	"sword.iron":
		ShopGoodsStaticConfig.builder("sword.iron")
		.name("铁剑")
		.intro("每次攻击，造成7HP伤害")
		.check_can_buy(lambda part, player_id: "已拥有高等级剑" if is_player_sword_better_than(part, player_id, "minecraft:iron_sword") else None)
		.simple_item({"newItemName": "minecraft:iron_sword", "count": 1})
		.build(),
	"sword.diamond":
		ShopGoodsStaticConfig.builder("sword.diamond")
		.name("钻石剑")
		.intro("每次攻击，造成8HP伤害")
		.check_can_buy(lambda part, player_id: "已拥有高等级剑" if is_player_sword_better_than(part, player_id, "minecraft:diamond_sword") else None)
		.simple_item({"newItemName": "minecraft:diamond_sword", "count": 1})
		.build(),
	"sword.knock":
		ShopGoodsStaticConfig.builder("sword.knock")
		.name("击退棒")
		.intro("把敌人打下虚空！")
		.simple_item({
			"newItemName": "easecation:blaze_rod",
			"count": 1,
			"enchantData": [
				(EnchantType.WeaponKnockback, 2)
			],
			"customTips": "击退棒%category%%enchanting%"
		})
		.build(),
	"sword.fishing-rod":
		ShopGoodsStaticConfig.builder("sword.fishing-rod")
		.name("鱼竿")
		.intro("把敌人钓上钩！")
		.simple_item({"newItemName": "minecraft:fishing_rod", "count": 1})
		.build(),
	# endregion

	# region 弓箭
	"arrow.0":
		ShopGoodsStaticConfig.builder("arrow.0")
		.name("普通 弓")
		.intro("平平无奇的弓")
		.simple_item({
			"newItemName": "minecraft:bow",
			"count": 1
		})
		.build(),
	"arrow.1":
		ShopGoodsStaticConfig.builder("arrow.1")
		.name("力量 附魔弓")
		.intro("拥有力量附魔的弓！")
		.simple_item({
			"newItemName": "minecraft:bow",
			"count": 1,
			"enchantData": [
				(EnchantType.BowDamage, 1)
			]
		})
		.build(),
	"arrow.1.5":
		ShopGoodsStaticConfig.builder("arrow.1.5")
		.name("力量I 冲击I 附魔弓")
		.intro("拥有力量附魔和击退的弓！")
		.simple_item({
			"newItemName": "minecraft:bow",
			"count": 1,
			"enchantData": [
				(EnchantType.BowDamage, 1),
				(EnchantType.BowKnockback, 1)
			]
		})
		.build(),
	"arrow.2":
		ShopGoodsStaticConfig.builder("arrow.2")
		.name("力量 击退 火焰 附魔弓")
		.intro("让敌人着火！")
		.simple_item({
			"newItemName": "minecraft:bow",
			"count": 1,
			"enchantData": [
				(EnchantType.BowDamage, 1),
				(EnchantType.BowKnockback, 1),
				(EnchantType.BowFire, 1)
			]
		})
		.build(),
	"arrow.arrow":
		ShopGoodsStaticConfig.builder("arrow.arrow")
		.name("箭")
		.intro("搭配弓使用")
		.simple_item({"newItemName": "minecraft:arrow", "count": 1})
		.build(),
	"arrow.arrow5":
		ShopGoodsStaticConfig.builder("arrow.arrow5")
		.name("箭")
		.intro("一次性买5支，搭配弓使用")
		.simple_item({"newItemName": "minecraft:arrow", "count": 5})
		.build(),
	"arrow.arrow6":
		ShopGoodsStaticConfig.builder("arrow.arrow6")
		.name("箭")
		.intro("一次性买6支，搭配弓使用")
		.simple_item({"newItemName": "minecraft:arrow", "count": 6})
		.build(),
	# endregion

	# region 工具
	"tool.shear":
		ShopGoodsStaticConfig.builder("tool.shear")
		.name("剪刀")
		.intro("适用于破坏羊毛， 每次重生时都会获得剪刀。")
		.simple_item({"newItemName": "minecraft:shears", "count": 1})
		.build(),
	"tool.stone-pickaxe":
		ShopGoodsStaticConfig.builder("tool.stone-pickaxe")
		.name("石镐")
		.intro("可以快速破坏石头类方块的道具")
		.simple_item({"newItemName": "minecraft:stone_pickaxe", "count": 1})
		.build(),
	"tool.iron-pickaxe":
		ShopGoodsStaticConfig.builder("tool.iron-pickaxe")
		.name("铁镐")
		.intro("可以快速破坏石头类方块的道具")
		.simple_item({"newItemName": "minecraft:iron_pickaxe", "count": 1})
		.build(),
	"tool.gold-pickaxe":
		ShopGoodsStaticConfig.builder("tool.gold-pickaxe")
		.name("金镐")
		.intro("可以快速破坏石头类方块的道具")
		.simple_item({"newItemName": "minecraft:golden_pickaxe", "count": 1})
		.build(),
	"tool.diamond-pickaxe":
		ShopGoodsStaticConfig.builder("tool.diamond-pickaxe")
		.name("钻石镐")
		.intro("可以快速破坏石头类方块的道具")
		.simple_item({"newItemName": "minecraft:diamond_pickaxe", "count": 1})
		.build(),
	"tool.iron-axe":
		ShopGoodsStaticConfig.builder("tool.iron-axe")
		.name("铁斧")
		.intro("可以快速破坏木头方块的道具")
		.simple_item({"newItemName": "minecraft:iron_axe", "count": 1})
		.build(),
	# endregion

	# region 道具
	"prop.golden-apple":
		ShopGoodsStaticConfig.builder("prop.golden-apple")
		.name("金苹果")
		.intro("全面治愈")
		.simple_item({"newItemName": "minecraft:golden_apple", "count": 1})
		.build(),
	"prop.ender-pearl":
		ShopGoodsStaticConfig.builder("prop.ender-pearl")
		.name("末影珍珠")
		.intro("入侵敌人基地的最快方法")
		.simple_item({"newItemName": "minecraft:ender_pearl", "count": 1})
		.build(),
	"prop.snow-ball":
		ShopGoodsStaticConfig.builder("prop.snow-ball")
		.name("雪球")
		.intro("远距离把敌人打入虚空！")
		.simple_item({"newItemName": "minecraft:snowball", "count": 5})
		.build(),
	"prop.egg":
		ShopGoodsStaticConfig.builder("prop.egg")
		.name("爆炸鸡蛋")
		.intro("远程投掷的鸡蛋，落地后产生奇妙的爆炸")
		.simple_item({"newItemName": "minecraft:egg", "count": 1})
		.build(),
	"prop.tnt":
		ShopGoodsStaticConfig.builder("prop.tnt")
		.name("爆炸的TNT")
		.intro("瞬间点燃， 适用于摧毁沿途的防御工事")
		.simple_item({
			"newItemName": "minecraft:tnt",
			"count": 1,
			"customTips": "爆炸的TNT%category%\n瞬间点燃， 适用于摧毁沿途的防御工事"
		})
		.build(),
	"prop.bedbug":
		ShopGoodsStaticConfig.builder("prop.bedbug")
		.name("床虱")
		.intro("在虫蛋落地之处生成蠹虫， 干扰你的对手。")
		.simple_item({"newItemName": "ecbedwars:bedbug", "count": 1})
		.build(),
	"prop.dream-guardian":
		ShopGoodsStaticConfig.builder("prop.dream-guardian")
		.name("梦境守护者")
		.intro("铁傀儡能守护你的基地")
		.simple_item({"newItemName": "ecbedwars:iron_golem", "count": 1})
		.build(),
	"prop.speed":
		ShopGoodsStaticConfig.builder("prop.speed")
		.name("速度药水[60秒]")
		.intro("喝下它，你将获得速度效果")
		.simple_item({"newItemName": "ecbedwars:potion_speed", "count": 1})
		.build(),
	"prop.leaping":
		ShopGoodsStaticConfig.builder("prop.leaping")
		.name("跳跃药水[60秒]")
		.intro("喝下它，你将获得跳跃效果")
		.simple_item({"newItemName": "ecbedwars:potion_leaping", "count": 1})
		.build(),
	"prop.invisible":
		ShopGoodsStaticConfig.builder("prop.invisible")
		.name("隐身药水[60秒]")
		.intro("喝下它，你将获得隐身效果")
		.simple_item({"newItemName": "ecbedwars:potion_invisibility", "count": 1})
		.build(),
	"prop.fireball":
		ShopGoodsStaticConfig.builder("prop.fireball")
		.name("烈焰弹")
		.intro("右键发射！ 击飞在桥上行走的敌人")
		.simple_item({"newItemName": "ecbedwars:fireball", "count": 1})
		.build(),
	"prop.bucket":
		ShopGoodsStaticConfig.builder("prop.bucket")
		.name("水桶")
		.intro("能很好地降低来犯敌人的速度\n也可以抵消TNT的伤害")
		.simple_item({"newItemName": "minecraft:water_bucket", "count": 1})
		.build(),
	"prop.magic-milk":
		ShopGoodsStaticConfig.builder("prop.magic-milk")
		.name("神奇牛奶")
		.intro("使用后，30秒内避免触发任何陷阱")
		.simple_item({
			"newItemName": "minecraft:milk_bucket", 
			"count": 1,
			"customTips": "神奇牛奶%category%\n使用后，30秒内避免触发任何陷阱"
		})
		.build(),
	"prop.sponge":
		ShopGoodsStaticConfig.builder("prop.sponge")
		.name("干海绵")
		.intro("用于吸收水分")
		.simple_item({"newItemName": "minecraft:sponge", "count": 4})
		.build(),
	"prop.bridge-egg":
		ShopGoodsStaticConfig.builder("prop.bridge-egg")
		.name("搭桥蛋")
		.intro("扔出蛋后，会在其飞行轨迹上生成一座桥")
		.simple_item({"newItemName": "ecbedwars:bridge_egg", "count": 1})
		.build(),
	"prop.defense-tower":
		ShopGoodsStaticConfig.builder("prop.defense-tower")
		.name("紧凑型防御塔")
		.intro("建造一个速建防御塔！")
		.simple_item({"newItemName": "ecbedwars:defense_tower", "count": 1})
		.build(),

	# endregion

	# region 升级
	"upgrade.health":
		ShopGoodsStaticConfig.builder("upgrade.health")
		.name("升级 全队最高血量")
		.intro("提升己方所有成员的血量上限！")
		.levels_intro([
			"+ 3HP",
			"+ 6HP",
			"+ 10HP",
		])
		.simple_upgrade(
			upgrade_key="health",
			enchantment=None,
			item_names=["minecraft:redstone"]
		)
		.build(),
	"upgrade.armor":
		ShopGoodsStaticConfig.builder("upgrade.armor")
		.name("升级 全队护甲保护等级")
		.intro("己方所有成员的盔甲将获得永久保护附魔！")
		.levels_intro([
			"保护I",
			"保护II",
			"保护III",
			"保护IV"
		])
		.simple_upgrade(
			upgrade_key="armor",
			enchantment=(EnchantType.ArmorAll, 1),
			item_names=["minecraft:golden_chestplate", "minecraft:diamond_chestplate", "minecraft:diamond_chestplate", "minecraft:diamond_chestplate"]
		)
		.build(),
	"upgrade.sword":
		ShopGoodsStaticConfig.builder("upgrade.sword")
		.name("升级 全队武器锋利等级")
		.intro("己方全部成员将获得锋利附魔！")
		.levels_intro([
			"锋利附魔I",
		])
		.simple_upgrade(
			upgrade_key="sword",
			enchantment=(EnchantType.WeaponDamage, 1),
			item_names=["minecraft:diamond_sword"]
		)
		.build(),
	"upgrade.super-miner":
		ShopGoodsStaticConfig.builder("upgrade.super-miner")
		.name("升级 超级矿工")
		.intro("己方所有队员将获得急迫效果！")
		.levels_intro([
			"急迫I",
			"急迫II"
		])
		.simple_upgrade(
			upgrade_key="miner",
			enchantment=(EnchantType.WeaponDamage, 1),
			item_names=["minecraft:golden_pickaxe"]
		)
		.build(),
	"upgrade.bedwars-gen":
		ShopGoodsStaticConfig.builder("upgrade.bedwars-gen")
		.name("升级 队伍产矿机")
		.intro("提升自己岛屿上的资源生成效率")
		.levels_intro([
			"+50%资源",
			"+100%资源",
			"生成绿宝石",
			"+200%资源"
		])
		.simple_upgrade(
			upgrade_key="generator",
			enchantment=(EnchantType.WeaponDamage, 1),
			item_names=["minecraft:furnace"]
		)
		.build(),
	"upgrade.healing-pool":
		ShopGoodsStaticConfig.builder("upgrade.healing-pool")
		.name("治愈池")
		.intro("基地附近的本队成员将获得生命恢复效果")
		.simple_upgrade(
			upgrade_key="healing_pool",
			enchantment=(EnchantType.WeaponDamage, 1),
			item_names=["minecraft:beacon"]
		)
		.build(),
	"upgrade.compass-tracking":
		ShopGoodsStaticConfig.builder("upgrade.compass-tracking")
		.name("指南针追踪")
		.intro("队伍全员的指南针将指向距离最近的敌人")
		.simple_upgrade(
			upgrade_key="compass_tracking",
			enchantment=None,
			item_names=["minecraft:compass"]
		)
		.build(),
	"tool.pickaxe-upgrade":
		ShopGoodsStaticConfig.builder("tool.pickaxe-upgrade")
		.name("稿子")
		.intro("该道具可升级\n\n重生后自动降低一级\n\n每次重生时，至少是最低等级")
		.levels_intro([
			"木稿 (效率I)",
			"石稿 (效率II)",
			"铁稿 (效率III)",
			"钻石稿 (效率IV)"
		])
		.simple_item_upgrade([
			{
				"newItemName": "minecraft:wooden_pickaxe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 1)
				],
				"count": 1
			},
			{
				"newItemName": "minecraft:stone_pickaxe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 2)
				],
				"count": 1
			},
			{
				"newItemName": "minecraft:iron_pickaxe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 3)
				],
				"count": 1
			},
			{
				"newItemName": "minecraft:diamond_pickaxe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 4)
				],
				"count": 1
			}
		])
		.build(),
	"tool.axe-upgrade":
		ShopGoodsStaticConfig.builder("tool.axe-upgrade")
		.name("斧子")
		.intro("该道具可升级\n\n重生后自动降低一级\n\n每次重生时，至少是最低等级")
		.levels_intro([
			"木斧 (效率I)",
			"石斧 (效率I)",
			"铁斧 (效率II)",
			"钻石斧 (效率III)"
		])
		.simple_item_upgrade([
			{
				"newItemName": "minecraft:wooden_axe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 1)
				],
				"count": 1
			},
			{
				"newItemName": "minecraft:stone_axe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 1)
				],
				"count": 1
			},
			{
				"newItemName": "minecraft:iron_axe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 2)
				],
				"count": 1
			},
			{
				"newItemName": "minecraft:diamond_axe",
				"enchantData": [
					(EnchantType.MiningEfficiency, 3)
				],
				"count": 1
			}
		])
		.build(),

	# endregion

	# region 陷阱

	"trap.slowness":
		ShopGoodsStaticConfig.builder("trap.slowness")
		.name("这是个陷阱！")
		.intro("给予入侵的敌人短暂的失明+缓慢效果")
		.show_item_dict_factory(lambda part, player_id: {"newItemName": "minecraft:tripwire_hook", "count": 1})
		.simple_trap("slowness")
		.build(),

	"trap.beat-back":
		ShopGoodsStaticConfig.builder("trap.beat-back")
		.name("反击陷阱")
		.intro("当敌人入侵时，我方队员将获得短暂的速度II+跳跃II")
		.show_item_dict_factory(lambda part, player_id: {"newItemName": "minecraft:feather", "count": 1})
		.simple_trap("beat-back")
		.build(),

	"trap.alert":
		ShopGoodsStaticConfig.builder("trap.alert")
		.name("报警陷阱")
		.intro("这个陷阱可以发现处于隐身状态的入侵者")
		.show_item_dict_factory(lambda part, player_id: {"newItemName": "minecraft:redstone_torch", "count": 1})
		.simple_trap("alert")
		.build(),

	"trap.fatigue":
		ShopGoodsStaticConfig.builder("trap.fatigue")
		.name("挖掘疲劳陷阱")
		.intro("给予入侵者挖掘疲劳效果")
		.show_item_dict_factory(lambda part, player_id: {"newItemName": "minecraft:iron_pickaxe", "count": 1})
		.simple_trap("fatigue")
		.build(),

	# endregion
}

# 创建BedWarsShopConfig实例
from .BedWarsShopConfig import BedWarsShopConfig
from .BedWarsShopCategoryConfig import BedWarsShopCategoryConfig

BEDWARS_SHOP_CONFIG = BedWarsShopConfig(
	name=u"起床战争商店",
	intro=u"购买物品和升级",
	showRecommend=False,
	shopCategoriesConfig=[
		# 1. 方块分类
		BedWarsShopCategoryConfig(
			name=u"方块",
			intro=u"购买建筑方块",
			goods_ids=[
				"block.wool",
				"block.clay",
				"block.plank",
				"block.end-stone",
				"block.obsidian",
				"block.glass",
				"block.ladder",
				"block.cobweb",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "blocks"
			}
		),

		# 2. 武器分类
		BedWarsShopCategoryConfig(
			name=u"武器",
			intro=u"购买武器",
			goods_ids=[
				"sword.stone",
				"sword.iron",
				"sword.diamond",
				"sword.knock",
				"sword.fishing-rod",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "weapons"
			}
		),

		# 3. 护甲分类
		BedWarsShopCategoryConfig(
			name=u"护甲",
			intro=u"购买护甲装备",
			goods_ids=[
				"armor.chain",
				"armor.iron",
				"armor.diamond",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "armor"
			}
		),

		# 4. 工具分类
		BedWarsShopCategoryConfig(
			name=u"工具",
			intro=u"购买工具",
			goods_ids=[
				"tool.shear",
				"tool.stone-pickaxe",
				"tool.iron-pickaxe",
				"tool.diamond-pickaxe",
				"tool.iron-axe",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "tools"
			}
		),

		# 5. 弓箭分类
		BedWarsShopCategoryConfig(
			name=u"弓箭",
			intro=u"购买弓和箭",
			goods_ids=[
				"arrow.0",
				"arrow.1",
				"arrow.2",
				"arrow.arrow",
				"arrow.arrow6",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "arrows"
			}
		),

		# 6. 药水分类
		BedWarsShopCategoryConfig(
			name=u"药水",
			intro=u"购买药水",
			goods_ids=[
				"prop.golden-apple",
				"prop.speed",
				"prop.leaping",
				"prop.invisible",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "potions"
			}
		),

		# 7. 特殊道具分类
		BedWarsShopCategoryConfig(
			name=u"特殊道具",
			intro=u"购买特殊道具",
			goods_ids=[
				"prop.ender-pearl",
				"prop.fireball",
				"prop.bridge-egg",
				"prop.tnt",
				"prop.bedbug",
				"prop.dream-guardian",
				"prop.defense-tower",
				"prop.bucket",
				"prop.sponge",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "special"
			}
		),

		# 8. 队伍升级分类
		BedWarsShopCategoryConfig(
			name=u"队伍升级",
			intro=u"购买队伍升级",
			goods_ids=[
				"upgrade.health",
				"upgrade.armor",
				"upgrade.sword",
				"upgrade.super-miner",
				"upgrade.bedwars-gen",
				"upgrade.healing-pool",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "upgrades"
			}
		),

		# 9. 陷阱分类
		BedWarsShopCategoryConfig(
			name=u"陷阱",
			intro=u"购买陷阱",
			goods_ids=[
				"trap.slowness",
				"trap.beat-back",
				"trap.alert",
				"trap.fatigue",
			],
			ui={
				"layout": "GRID",
				"recommend": False,
				"title": "traps"
			}
		),
	]
)