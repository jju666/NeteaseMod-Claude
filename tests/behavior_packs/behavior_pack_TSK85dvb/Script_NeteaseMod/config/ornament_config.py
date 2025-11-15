# -*- coding: utf-8 -*-
"""
装饰系统配置文件 (从老项目100%还原)

包含所有装饰物品的配置数据
总计161个装扮 (与老项目一致)

包含10种装扮类型:
1. 击杀信息 (kill-broadcast)
2. 亡语 (kill-sound)
3. 床装饰 (bed-ornament)
4. 破坏床广播 (bed-destroy-message)
5. 破坏床特效 (bed-destroy-effect)
6. 表情包 (meme)
7. 商店NPC外观 (shop-npc-skin)
8. 胜利之舞 (winner-effect)
9. 个性商店 (personalized-shop)
10. 喷漆 (spray)

每个装饰物配置包含:
- prop_id: 装饰物唯一标识符
- name: 显示名称
- introduce: 介绍
- price: 价格(0=默认解锁, -1=活动限定, "ornament-fragment:N"=碎片兑换)
- default_own: 是否默认拥有

注意: 本配置文件从老项目UnlockUpgradeConfig.py自动转换生成,确保100%一致性
"""


# ==================== 10种装扮类型配置 ====================

ORNAMENT_TYPES = [
    # 1. kill-broadcast ({bold}{blue}击杀信息) - 21个
    {
        "type_id": "kill-broadcast",
        "type_name": u"{bold}{blue}击杀信息",
        "have_state": True,
        "introduce": u"当你击杀对手时，聊天栏将会发送的消息！",
        "ornaments": [
            {
                "prop_id": "kill-broadcast.default",
                "name": u"{bold}{light-purple}默认捆绑包",
                "introduce": u"默认：【受害者】{dark-aqua} 被 {red}【击杀者】 {dark-aqua}终结啦！",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "kill-broadcast.arena-package",
                "name": u"{bold}{light-purple}擂台捆绑包",
                "introduce": u"在一场擂台比赛中击败对手（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】在一场拳击比赛中输给了【击杀者】{enter}【受害者】被【击杀者】击倒{enter}【受害者】被推倒，击杀者：【击杀者】{enter}【受害者】在和【击杀者】的对决中被按在地上",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.crap-package",
                "name": u"{bold}{light-purple}废话文学捆绑包",
                "introduce": u"净说废话。（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】死于和【击杀者】的对战{enter}【受害者】在和【击杀者】的对战中忘记了自己的血量{enter}【受害者】在和【击杀者】的对战中忘记了自己还有多少方块{enter}【受害者】在和【击杀者】的对战中战至边缘",
                "price": 850,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.bbq-package",
                "name": u"{bold}{light-purple}烧烤派对捆绑包",
                "introduce": u"击败对手，但是烧烤派对（3条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】被【击杀者】烤成了肉串{enter}【受害者】踩到了【击杀者】的烧烤酱{enter}【受害者】被和【击杀者】炭烧",
                "price": 950,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.touhou-package",
                "name": u"{bold}{red}在东方的目标捆绑包",
                "introduce": u"《博丽神主的游戏为先还是⑨为先》（3条消息，每次击杀时随机选择一条发送）{enter}{enter}包含封印、化为光、囧仙等3条有意思的消息内容！{enter}{enter}{yellow}具体是些什么？解锁后试试看！",
                "price": 1300,
                "default_own": False
            },

            {
                "prop_id": "kill-broadcast.emotion-package",
                "name": u"{bold}{light-purple}情感捆绑包",
                "introduce": u"钢铁直男的首选！（5条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】受到【击杀者】的冷淡{enter}【受害者】被【击杀者】浓妆艳抹{enter}【受害者】被【击杀者】无情拒绝{enter}【受害者】被【击杀者】发射的爱情炸弹击中{enter}【受害者】在一场暴风雪中被【击杀者】拒之门外",
                "price": 1450,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.west-package",
                "name": u"{bold}{light-purple}西部捆绑包",
                "introduce": u"这是西部的主流文化。（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】遭遇【击杀者】的枪杀{enter}【受害者】在一场淘金比赛中输给了【击杀者】{enter}【受害者】死于【击杀者】召唤的扬沙{enter}【受害者】被斩于马下，是ta干的！【击杀者】",
                "price": 1950,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.zhangsan-package",
                "name": u"{bold}{light-purple}张三捆绑包",
                "introduce": u"世界上最守法的公民。（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】在和【击杀者】的对战中击杀未遂而被反杀{enter}【受害者】在和【击杀者】的对决辩论中证据不足{enter}【受害者】在一次袭击中受到【击杀者】的牵连{enter}【受害者】被【击杀者】绳之以法",
                "price": 2250,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.exag-package",
                "name": u"{bold}{light-purple}夸张捆绑包",
                "introduce": u"用最夸张的消息证明你有多狂！（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】被【击杀者】吵死了{enter}【受害者】被【击杀者】化为粉尘{enter}【受害者】被【击杀者】践踏{enter}【受害者】被【击杀者】正义执行",
                "price": 2700,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.yyw-package",
                "name": u"{bold}{red}音游”王”捆绑包",
                "introduce": u"什么时候有音游可以和俺们联动呢？（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 包含：{enter}【受害者】用心，【击杀者】可以绝对放心 等4条有意思的消息！{enter}{enter}{yellow}具体是些什么？解锁后试试看！",
                "price": 4000,
                "default_own": False
            },

            {
                "prop_id": "kill-broadcast.hp-package",
                "name": u"{bold}{light-purple}哈{light-purple}利法{light-purple}杖混搭{light-purple}包",
                "introduce": u"你听说过神奇的扫帚吗？（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} ",
                "price": "ornament-fragment:200",
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.count-package",
                "name": u"{bold}{red}统计次数捆绑包",
                "introduce": u"自豪地向他人展示你的击杀次数（3条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】成为【击杀者】击杀的第x个玩家{enter}【受害者】让【击杀者】达成了x次击杀{enter}【受害者】是【击杀者】抓捕的第x只怪兽{enter}",
                "price": "ornament-fragment:300",
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.cry-package",
                "name": u"{bold}【梦境限定】 {red}爱哭宝宝捆绑包",
                "introduce": u"有妈妈保护的宝宝。 （5条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【受害者】输给了有妈妈保护的【击杀者】{enter}【受害者】被【击杀者】的奶瓶击中{enter}【受害者】同样需要妈妈保护，击杀者：【击杀者】{enter}【受害者】哭了，击杀者：【击杀者】{enter}【受害者】发出奇怪的声音，击杀者：【击杀者】",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.school-package",
                "name": u"{bold}【梦境限定】{red}老师模拟器捆绑包",
                "introduce": u"让你在课后游玩EaseCation时感到关怀备至。{enter}{enter}具体内容详见起床战争大厅展示台",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.hunter-package",
                "name": u"{bold}【奇迹猎人】{red} 奇迹猎人捆绑包",
                "introduce": u"你逃不过猎手的攻击， 除非......除非你也是猎手！ {enter}{enter}{yellow}【包含】{enter}射杀对手、收入囊中、掉入陷阱、囚禁等消息提示！ 前往起床战争大厅展示台查看详细信息！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "kill-broadcast.halloween",
                "name": u"{bold}【梦境限定】 {red}幽灵之夜",
                "introduce": u"长夜漫漫，一个神秘的身影浮现在背后......{enter}{enter}{yellow}梦境限定，请到起床战争大厅的相应展示台查看所有提示消息！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.spring2023",
                "name": u"{red}{bold}【2023春】 烟火之夜混搭包",
                "introduce": u"新春快乐~{enter}收下这份新年礼物，或者送一份给对手！(请前往BEDWARS大厅展示台查看完整击杀广播内容)",
                "price": "ornament-fragment:10",
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.translate",
                "name": u"{bold}{red}翻译腔捆绑包",
                "introduce": u"给你十分纯正的翻译体验。 （4条消息，在击杀敌人时随机选择一条发送）{enter}{enter}请到起床战争大厅展示台查看所有消息！",
                "price": "ornament-fragment:200",
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.gold-package",
                "name": u"{bold}{light-purple}【星火限定】 {bold}{gold}金黄{red}捆绑包",
                "introduce": u"极度稀有的金黄色击杀信息提示！ 这是实力的证明， 只有在盛大的{bold}{red}星火杯{reset}活动中斩获佳绩的冒险者才有机会获得......{enter}{enter}请前往起床战争大厅的展示台来查看详细的信息内容！",
                "price": "ornament-fragment:200",
                "default_own": False
            },
            {
                "prop_id": "kill-broadcast.cfyz-package",
                "name": u"{bold}{red}【一周年】乘风驭舟-击杀捆绑包",
                "introduce": u"欢迎来到起床1周年庆典！{enter}（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【击杀者】用奶油蛋糕糊了【受害者】一脸{enter}【击杀者】用派对彩条捆住了【受害者】{enter}【击杀者】用蛋糕蜡烛点燃了【受害者】{enter}【击杀者】用派对烟花将【受害者】带上天空",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "kill-broadcast.mine-package",
                "name": u"{bold}{red}【梦境限定】 诡异矿洞混搭包",
                "introduce": u"”关于符文那点事，唉，自己看吧。“{enter}（4条消息，每次击杀时随机选择一条发送）{enter}{enter}{yellow} 内含：【击杀者】将符文贴在【受害者】的脸上{enter}【受害者】被主角团正义执行，击杀者：【击杀者】{enter}【击杀者】在【受害者】身边试图召唤矿长{enter}【击杀者】转生成矿工并击杀了【受害者】！",
                "price": -1,
                "default_own": False
            }
        ]
    },

    # 2. kill-sound ({bold}{blue}亡语) - 10个
    {
        "type_id": "kill-sound",
        "type_name": u"{bold}{blue}亡语",
        "have_state": True,
        "introduce": u"达成最终击杀时，向所有人播放声音",
        "ornaments": [
            {
                "prop_id": "kill-sound.default",
                "name": u"{bold}{light-purple}默认亡语捆绑包",
                "introduce": u"最初始的最终击杀声音特效！",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "kill-sound.animal-package",
                "name": u"{bold}{light-purple}动物亡语捆绑包",
                "introduce": u"一些小动物的叫声将证明你的功绩，比如说牛、羊等小动物！（达成最终击杀时，从中随机播放一种声音）",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "kill-sound.ghost-package",
                "name": u"{bold}{light-purple}亡灵亡语捆绑包",
                "introduce": u"让敌人在死前感受亡灵生物的怒吼，比如僵尸、骷髅（？）看看他被吓坏了没有（达成最终击杀时，从中随机播放一种声音）",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "kill-sound.forest-package",
                "name": u"{bold}{light-purple}丛林英雄亡语捆绑包",
                "introduce": u"冒险者在丛林中会听到什么？蜘蛛？还是……?（达成最终击杀时，从中随机播放一种声音）",
                "price": 950,
                "default_own": False
            },
            {
                "prop_id": "kill-sound.friend-package",
                "name": u"{bold}{light-purple}最好的朋友亡语捆绑包",
                "introduce": u"可能是…..猫和狗……或者……其他的声音！只要是你的好朋友！（达成最终击杀时，从中随机播放一种声音）",
                "price": 1750,
                "default_own": False
            },

            {
                "prop_id": "kill-sound.nether-package",
                "name": u"{bold}{light-purple}下界亡语捆绑包",
                "introduce": u"溢出屏幕的压迫感，伴随地狱生物的低吟，震慑全场。（达成最终击杀时，从中随机播放一种声音）",
                "price": 1950,
                "default_own": False
            },
            {
                "prop_id": "kill-sound.end-package",
                "name": u"{bold}{red}末地亡语捆绑包",
                "introduce": u"感受末影人冗长深沉的低吼，抑或是龙的怒火，总之，这一定会有很好的效果！（达成最终击杀时，从中随机播放一种声音）",
                "price": "ornament-fragment:150",
                "default_own": False
            },
            {
                "prop_id": "kill-sound.joker-package",
                "name": u"{bold}{red}王牌亡语捆绑包",
                "introduce": u"这是最有震慑力的声音，你听说过击杀雷击吗？（达成最终击杀时，从中随机播放一种声音）",
                "price": "ornament-fragment:200",
                "default_own": False
            },
            {
                "prop_id": "kill-sound.cry-package",
                "name": u"{bold}{light-purple}哭泣亡语捆绑包",
                "introduce": u"充满着奇怪的哭腔，是有些奇怪吧",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "kill-sound.villager",
                "name": u"{bold}【梦境限定】 {red}村民风格亡语",
                "introduce": u"“别打村民，你这个海豚！”",
                "price": -1,
                "default_own": False
            }
        ]
    },

    # 3. bed-ornament ({bold}{dark-aqua}床的装饰) - 15个
    {
        "type_id": "bed-ornament",
        "type_name": u"{bold}{dark-aqua}床的装饰",
        "have_state": True,
        "introduce": u"本队床上的可爱装饰品！",
        "ornaments": [
            {
                "prop_id": "bed-ornament.default",
                "name": u"{bold}{light-purple}默认无装饰",
                "introduce": u"没有装饰，快去解锁一个试试！{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "bed-ornament.crystal",
                "name": u"{bold}{light-purple}沉睡的水晶",
                "introduce": u"水晶沉睡着， 请务必守护它的床。{enter}{enter}{yellow}（仅为装饰，没有碰撞体积。每局游戏从本队玩家中随机选择一名玩家的装饰设定作为本局的床装饰）",
                "price": 20,
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.green",
                "name": u"{bold}{light-purple}绿帽子装饰",
                "introduce": u"象征和平的绿色，降临在床上{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.rabbit",
                "name": u"{bold}{light-purple}兔耳朵装饰",
                "introduce": u"可可爱爱的兔子耳朵{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": 950,
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.steve",
                "name": u"{bold}{light-purple}沉睡史蒂夫装饰",
                "introduce": u"Steve你怎么了啊Steve{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": 1950,
                "default_own": False
            },

            {
                "prop_id": "bed-ornament.succulent",
                "name": u"{bold}{light-purple}多肉植物装饰",
                "introduce": u"生机勃勃。{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": 2250,
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.huaji",
                "name": u"{bold}{light-purple}滑稽装饰",
                "introduce": u"让大家看看幽默的你！{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": "ornament-fragment:190",
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.py",
                "name": u"{bold}{red}小彭越装饰",
                "introduce": u"吉祥物小彭越睡着啦！{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": "ornament-fragment:190",
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.bedrock",
                "name": u"{bold}{red}基岩床",
                "introduce": u"“但愿它真的能那么坚固（）”。{enter}{enter}{yellow}每局游戏从本队中随机选择一名玩家的装饰设定作为本局的床装饰！",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.tnt",
                "name": u"{bold}{red}TNT床",
                "introduce": u"说不定里面有烈性炸药呢？{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": 750,
                "default_own": False
            },

            {
                "prop_id": "bed-ornament.airship",
                "name": u"{red}{bold}太空飞艇床",
                "introduce": u"“遨游太空，躺在上面一定很舒适——除了被摧毁的时候。”{enter}{enter}{yellow}每局游戏从本队中随机选择一名玩家的装饰设定作为本局的床装饰！",
                "price": "ornament-fragment:150",
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.racing",
                "name": u"{red}{bold}赛车床",
                "introduce": u"“绝对的超音速。”{enter}{enter}{yellow}每局游戏从本队中随机选择一名玩家的装饰设定作为本局的床装饰！",
                "price": "ornament-fragment:120",
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.snake",
                "name": u"{bold}{light-purple}积木蛇装饰",
                "introduce": u"快跑！你的床上有条蛇！{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.balloon",
                "name": u"{bold}{red}【一周年】乘风驭舟-气球装饰",
                "introduce": u"起床一周年庆典上漏气掉落在床上的气球（听说可以随着队伍的改变换颜色？）{enter}{enter}（床的装饰仅作为特效，没有碰撞体积，每局游戏每队随机选择一人的设定进行装饰）",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-ornament.anubis",
                "name": u"阿努比斯",
                "introduce": u"阿努比斯的小可爱赖在床上不走了～",
                "price": 1950,
                "default_own": False
            }
        ]
    },

    # 4. bed-destroy-message ({bold}{dark-aqua}破坏床广播) - 18个
    {
        "type_id": "bed-destroy-message",
        "type_name": u"{bold}{dark-aqua}破坏床广播",
        "have_state": True,
        "introduce": u"当你破坏床时，向全局发送的消息",
        "ornaments": [
            {
                "prop_id": "bed-destroy-message.default",
                "name": u"{bold}{light-purple}默认广播",
                "introduce": u"默认广播信息{enter}",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "bed-destroy-message.crap",
                "name": u"{bold}{light-purple}废话广播",
                "introduce": u"【队伍】床被【玩家】破坏了，所以破坏了",
                "price": 200,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.tea",
                "name": u"{bold}{light-purple}下午茶毁床广播",
                "introduce": u"【队伍】床被【玩家】做成茶和烤面包",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.fire",
                "name": u"{bold}{light-purple}火焰广播",
                "introduce": u"【队伍】床被【玩家】焚烧！",
                "price": 1550,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.biaoqingbao",
                "name": u"{bold}{light-purple}表情包广播",
                "introduce": u"【队伍】床被【玩家】做成表情包",
                "price": 1950,
                "default_own": False
            },

            {
                "prop_id": "bed-destroy-message.math",
                "name": u"{bold}{red}数学广播",
                "introduce": u"【队伍】没有定义域，是他干的【玩家】",
                "price": 2200,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.wenyanwen",
                "name": u"{bold}{red}文言文毁床广播",
                "introduce": u"【队伍】床为【玩家】所摧，悲！",
                "price": 2700,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.shengtian",
                "name": u"{bold}{red}升天广播",
                "introduce": u"【队伍】的床因【玩家】而升天",
                "price": 2900,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.count",
                "name": u"{bold}{red}统计广播",
                "introduce": u"【队伍】是破坏的第X张床！",
                "price": "ornament-fragment:300",
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.qingchun",
                "name": u"{bold}【梦境限定】{red} “青春”广播",
                "introduce": u"他破坏床的动作太令人感动了，他真的...我哭死！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "bed-destroy-message.school",
                "name": u"{bold}【梦境限定】{red}写作业广播",
                "introduce": u"写作业狂魔， 将作业写在对方床上？！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.hunter",
                "name": u"{bold}【奇迹猎人】 {red}奇迹猎人广播",
                "introduce": u"对于猎手来说，偷床轻而易举。",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.halloween",
                "name": u"{bold}【梦境限定】 {red}万圣破坏床广播",
                "introduce": u"在这个百鬼夜行的夜晚，和鬼魂们庆祝万圣节的到来！{enter}{enter}【队伍】 的床被【玩家】 的扫帚击中",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.christmas-a",
                "name": u"{bold}【2022圣诞】 {red}包装礼物破坏床广播",
                "introduce": u"让圣诞礼物中装有对方的床，这真的令人兴奋呢。",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.ec-8-ann",
                "name": u"{bold}【8周年限定】{red}烟花盛宴",
                "introduce": u"在EaseCation的8周年庆典上放烟花，将这份美好的回忆带入游戏中，配合8周年粉红烟花一起使用效果拔群！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "bed-destroy-message.cfyz",
                "name": u"{bold}{red}【一周年】乘风驭舟-拆床捆绑包",
                "introduce": u"【玩家】在室内燃放烟花，炸毁了【队伍】的床",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.rune",
                "name": u"{bold}{red}【梦境限定】符咒破坏床广播",
                "introduce": u"好吧，你应当承认此次拆床行动有符文的一份功劳，不是吗？{enter}{enter}{yellow}【玩家】按照符文上的教程破坏了【队伍】的床",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-message.pyramid",
                "name": u"{bold}{light-purple}金字塔毁床广播",
                "introduce": u"【队伍】的床被【玩家】亲手送入了金字塔",
                "price": 1950,
                "default_own": False
            }
        ]
    },

    # 5. bed-destroy-effect ({bold}{dark-aqua}破坏床特效) - 11个
    {
        "type_id": "bed-destroy-effect",
        "type_name": u"{bold}{dark-aqua}破坏床特效",
        "have_state": True,
        "introduce": u"当你破坏床时，向全局展示特效",
        "ornaments": [
            {
                "prop_id": "bed-destroy-effect.default",
                "name": u"{bold}{light-purple}默认特效",
                "introduce": u"{bold}{blue}默认特效",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "bed-destroy-effect.yanhua",
                "name": u"{bold}{light-purple}烟花特效",
                "introduce": u"在你破坏床时，放烟花来庆祝！",
                "price": 200,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-effect.gold",
                "name": u"{bold}{light-purple}金黄毁床特效",
                "introduce": u"金光闪闪！亮瞎狗眼！",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-effect.cow",
                "name": u"{bold}{light-purple}勇敢牛牛特效",
                "introduce": u"生成一只牛……",
                "price": 1950,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-effect.heart",
                "name": u"{bold}{light-purple}爱心特效",
                "introduce": u"在你破坏床时让世界充满爱，爱心粒子！",
                "price": 2700,
                "default_own": False
            },

            {
                "prop_id": "bed-destroy-effect.boom",
                "name": u"{bold}{red}爆炸毁床特效",
                "introduce": u"引爆TNT特效！（仅特效，没有任何伤害、击退）",
                "price": "ornament-fragment:190",
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-effect.lightning",
                "name": u"{bold}{red}雷击特效",
                "introduce": u"引雷，威震天下！（仅特效，没有任何伤害、击退）",
                "price": "ornament-fragment:300",
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-effect.qingchun",
                "name": u"{bold}【梦境限定】 {red}青春飞扬特效",
                "introduce": u"生机勃勃的绿色烟花，配上升天的小鸡，彰显青春活力。",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-effect.shijuan",
                "name": u"{bold}【梦境限定】{red}试卷特效",
                "introduce": u"这次毁床行动，我给打满分！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "bed-destroy-effect.halloween",
                "name": u"【梦境限定】 {red}百鬼夜行毁床特效",
                "introduce": u"让他们目睹床的鬼魂消散，颤抖吧！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "bed-destroy-effect.ec-8-ann",
                "name": u"{bold}【8周年限定】{red}粉红烟花",
                "introduce": u"在EaseCation的8周年庆典上放烟花，让这粉红的烟花升上天空，庆祝床被摧毁的喜悦。",
                "price": -1,
                "default_own": False
            }
        ]
    },

    # 6. meme ({bold}{blue}表情包) - 9个
    {
        "type_id": "meme",
        "type_name": u"{bold}{blue}表情包",
        "have_state": True,
        "introduce": u"收集绿宝石/钻石时，在产矿机上方展示",
        "ornaments": [
            {
                "prop_id": "meme.default",
                "name": u"{bold}{red}默认无表情包",
                "introduce": u"没有表情",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "meme.smile",
                "name": u"{bold}{red}笑脸表情包",
                "introduce": u"炫耀自己拿到高级资源时的喜悦{enter}{enter}（收集到绿宝石/钻石时，产矿机上方将展示表情！）",
                "price": 200,
                "default_own": False
            },
            {
                "prop_id": "meme.black",
                "name": u"{bold}{red}黑脸表情包",
                "introduce": u"好吧……我们暂时沉默。{enter}{enter}（收集到绿宝石/钻石时，产矿机上方将展示表情！）",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "meme.embrace",
                "name": u"{bold}{red}尴尬表情包",
                "introduce": u"你做了什么奇怪的事情吗{enter}{enter}（收集到绿宝石/钻石时，产矿机上方将展示表情！）",
                "price": 1900,
                "default_own": False
            },
            {
                "prop_id": "meme.huaji",
                "name": u"{bold}{red}滑稽表情包",
                "introduce": u"滑稽（斜眼笑~~~{enter}{enter}（收集到绿宝石/钻石时，产矿机上方将展示表情！）",
                "price": 1950,
                "default_own": False
            },

            {
                "prop_id": "meme.angry",
                "name": u"{bold}{red}狂怒表情包",
                "introduce": u"谁又惹你生气啦{enter}{enter}（收集到绿宝石/钻石时，产矿机上方将展示表情！）",
                "price": 2250,
                "default_own": False
            },
            {
                "prop_id": "meme.qm",
                "name": u"{bold}{red}问号表情包",
                "introduce": u"？？？你说什么？？{enter}{enter}（收集到绿宝石/钻石时，产矿机上方将展示表情！）",
                "price": 2900,
                "default_own": False
            },
            {
                "prop_id": "meme.ec",
                "name": u"{bold}{red}ECLOGO表情包",
                "introduce": u"壮哉我大EaseCation！！！{enter}{enter}（收集到绿宝石/钻石时，产矿机上方将展示表情！）",
                "price": "ornament-fragment:200",
                "default_own": False
            },
            {
                "prop_id": "meme.anubis",
                "name": u"阿努比斯",
                "introduce": u"阿努比斯的小可爱",
                "price": 1950,
                "default_own": False
            }
        ]
    },

    # 7. shop-npc-skin ({bold}{blue}商店NPC外观) - 10个
    {
        "type_id": "shop-npc-skin",
        "type_name": u"{bold}{blue}商店NPC外观",
        "have_state": True,
        "introduce": u"本队的两个商店NPC皮肤外观！",
        "ornaments": [
            {
                "prop_id": "shop-npc-skin.default",
                "name": u"{bold}{light-purple}默认商人外观",
                "introduce": u"默认村民,支持村庄更新版本的村民外观！",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "shop-npc-skin.ghost",
                "name": u"{bold}{light-purple}亡灵商人外观",
                "introduce": u"僵尸和骷髅{enter}{enter}（每局游戏每队随机选择一名玩家的设定应用）",
                "price": 250,
                "default_own": False
            },
            {
                "prop_id": "shop-npc-skin.nether",
                "name": u"{bold}{light-purple}下界商人外观",
                "introduce": u"猪人+凋零骷髅{enter}{enter}（每局游戏每队随机选择一名玩家的设定应用）",
                "price": 950,
                "default_own": False
            },
            {
                "prop_id": "shop-npc-skin.end",
                "name": u"{bold}{light-purple}末地商人外观",
                "introduce": u"末影人，末影龙人{enter}{enter}（每局游戏每队随机选择一名玩家的设定应用）",
                "price": 1900,
                "default_own": False
            },
            {
                "prop_id": "shop-npc-skin.desert-ice",
                "name": u"{bold}{light-purple}沙漠冰河商人外观",
                "introduce": u"尸壳+流浪者{enter}{enter}（每局游戏每队随机选择一名玩家的设定应用）",
                "price": 2900,
                "default_own": False
            },

            {
                "prop_id": "shop-npc-skin.me-robot",
                "name": u"{bold}{red}我与机器人商人外观",
                "introduce": u"你的皮肤+机器人{enter}{enter}（每局游戏每队随机选择一名玩家的设定应用）",
                "price": "ornament-fragment:200",
                "default_own": False
            },
            {
                "prop_id": "shop-npc-skin.me-py",
                "name": u"{bold}{red}我与彭越商人外观",
                "introduce": u"你的皮肤+彭越NPC{enter}{enter}（每局游戏每队随机选择一名玩家的设定应用）",
                "price": "ornament-fragment:320",
                "default_own": False
            },
            {
                "prop_id": "shop-npc-skin.halloween",
                "name": u"{bold}【梦境限定】 {red}我和女巫商人皮肤",
                "introduce": u"带上南瓜头，和女巫站在一起！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "shop-npc-skin.me-py-chr",
                "name": u"{bold}【2022圣诞梦境】{red} 我和圣诞彭越商人外观",
                "introduce": u"圣诞版本彭越化身商人进入《起床战争》啦！ 参与2022圣诞梦境挑战来获得！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "shop-npc-skin.elliepunk",
                "name": u"{bold}{red}【DREAM】Rune Legend NPC(s)",
                "introduce": u"不要误解，艾莉和庞克一直是很好的朋友，仅此而已。",
                "price": -1,
                "default_own": False
            }
        ]
    },

    # 8. winner-effect ({bold}{dark-aqua}胜利之舞) - 7个
    {
        "type_id": "winner-effect",
        "type_name": u"{bold}{dark-aqua}胜利之舞",
        "have_state": True,
        "introduce": u"在你赢得游戏后的庆祝特效！",
        "ornaments": [
            {
                "prop_id": "winner-effect.default",
                "name": u"{bold}{light-purple}默认胜利之舞",
                "introduce": u"默认的特效",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "winner-effect.futou",
                "name": u"{bold}{light-purple}斧头胜利之舞",
                "introduce": u"头顶喷斧头特效，让别人看看你有多快乐（）",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "winner-effect.lightining",
                "name": u"{bold}{red}闪电胜利之舞",
                "introduce": u"召唤闪电！电闪雷鸣欢庆胜利！",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "winner-effect.space",
                "name": u"{bold}{light-purple}外太空胜利之舞",
                "introduce": u"来自外太空的祝福，你们将获得太空人的效果",
                "price": 1750,
                "default_own": False
            },
            {
                "prop_id": "winner-effect.yanhua",
                "name": u"{bold}{light-purple}圣灵烟花胜利之舞",
                "introduce": u"放烟花！砰！——————{enter}纯洁的烟花象征正义的胜利",
                "price": 2700,
                "default_own": False
            },

            {
                "prop_id": "winner-effect.dragon",
                "name": u"{bold}{red}末影龙胜利之舞",
                "introduce": u"骑着末影龙环顾四周！享受最美妙的庆祝方式！",
                "price": "ornament-fragment:2700",
                "default_own": False
            },
            {
                "prop_id": "winner-effect.chr",
                "name": u"{bold}【2022圣诞】{red}圣诞烟火",
                "introduce": u"用烟花来庆祝圣诞！",
                "price": -1,
                "default_own": False
            }
        ]
    },

    # 9. personalized-shop ({bold}{dark-aqua}个性商店) - 6个
    {
        "type_id": "personalized-shop",
        "type_name": u"{bold}{dark-aqua}个性商店",
        "have_state": True,
        "introduce": u"解锁局内商店购买方块的材质！",
        "ornaments": [
            {
                "prop_id": "personalized-shop.default",
                "name": u"{bold}{light-purple}默认木板外观",
                "introduce": u"{yellow}橡木木板{white}{enter}{enter}注意！解锁并装备后，在游戏内商店购买木板时会给予这个材质的木板！这些材质的性能相同，不会破坏游戏平衡。",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "personalized-shop.baihua",
                "name": u"{bold}{light-purple}白桦木木板外观",
                "introduce": u"{yellow}白桦木木板{white}{enter}{enter}注意！解锁并装备后，在游戏内商店购买木板时会给予这个材质的木板！这些材质的性能相同，不会破坏游戏平衡。",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "personalized-shop.jinhehuan",
                "name": u"{bold}{light-purple}金合欢木板外观",
                "introduce": u"{yellow}金合欢木板{white}{enter}{enter}注意！解锁并装备后，在游戏内商店购买木板时会给予这个材质的木板！这些材质的性能相同，不会破坏游戏平衡。",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "personalized-shop.shensexiangmu",
                "name": u"{bold}{light-purple}深色橡木木板外观",
                "introduce": u"{yellow}深色橡木木板{white}{enter}{enter}注意！解锁并装备后，在游戏内商店购买木板时会给予这个材质的木板！这些材质的性能相同，不会破坏游戏平衡。",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "personalized-shop.conglin",
                "name": u"{bold}{light-purple}丛林木板外观",
                "introduce": u"{yellow}从林木木板{white}{enter}{enter}注意！解锁并装备后，在游戏内商店购买木板时会给予这个材质的木板！这些材质的性能相同，不会破坏游戏平衡。",
                "price": 450,
                "default_own": False
            },

            {
                "prop_id": "personalized-shop.yunshan",
                "name": u"{bold}{light-purple}云杉木板外观",
                "introduce": u"{yellow}云杉木木板{white}{enter}{enter}注意！解锁并装备后，在游戏内商店购买木板时会给予这个材质的木板！这些材质的性能相同，不会破坏游戏平衡。",
                "price": 450,
                "default_own": False
            }
        ]
    },

    # 10. spray ({bold}{dark-aqua}喷漆) - 54个
    {
        "type_id": "spray",
        "type_name": u"{bold}{dark-aqua}喷漆",
        "have_state": True,
        "introduce": u"向他人展示你对岛屿的的占有欲！",
        "ornaments": [
            {
                "prop_id": "spray.default",
                "name": u"{bold}{light-purple}默认喷漆",
                "introduce": u"这是默认的喷漆！ 你可以试着解锁更多喷漆样式！{enter}{enter}在游戏中点击物品展示框来使用",
                "price": 0,
                "default_own": True
            },
            {
                "prop_id": "spray.diamond_sword",
                "name": u"{bold}{light-purple}纯洁的钻石剑",
                "introduce": u"炫耀你的强悍，这是1.16前的最强武器（）{enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "spray.crystal",
                "name": u"{bold}{light-purple}能量水晶",
                "introduce": u"水晶会守护你们的。{enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": 450,
                "default_own": False
            },
            {
                "prop_id": "spray.logo_tech",
                "name": u"{bold}{light-purple}科技主题logo",
                "introduce": u"暗蓝色和亮蓝色在简约科技配色组合！{enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": 750,
                "default_own": False
            },
            {
                "prop_id": "spray.logo_neon",
                "name": u"{bold}{light-purple}霓虹主题logo",
                "introduce": u"我们的新大厅的霓虹炫彩配色！{enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": 750,
                "default_own": False
            },

            {
                "prop_id": "spray.megawalls",
                "name": u"{bold}{light-purple}超级战墙主题logo",
                "introduce": u"你玩过《超级战墙》吗？{enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": 950,
                "default_own": False
            },
            {
                "prop_id": "spray.luckyblock",
                "name": u"{bold}{light-purple}幸运方块主题logo",
                "introduce": u"那么，你觉得你幸运吗？{enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": 1250,
                "default_own": False
            },
            {
                "prop_id": "spray.logo_tree",
                "name": u"{bold}{red}植树主题logo",
                "introduce": u"植树快乐！哈哈哈哈哈哈哈哈{enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": 1550,
                "default_own": False
            },
            {
                "prop_id": "spray.logo_newyear",
                "name": u"{bold}{red}新年快乐！",
                "introduce": u"给大家拜年啦！",
                "price": 1550,
                "default_own": False
            },
            {
                "prop_id": "spray.logo_aids",
                "name": u"{bold}{red}公益宣传logo",
                "introduce": u"这个喷漆只能会通过我们的“人文关怀”以及相关公益活动获取！{enter}用红丝带结出温温暖情，为艾滋病伸出关怀之手。 {enter}{enter}{yellow}【使用方法】{enter}点击地图中的物品展示框",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.py1",
                "name": u"{bold}{red}彭越嘲笑",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py2",
                "name": u"{red}{bold}圣诞彭越の疑惑",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py3",
                "name": u"{red}{bold}魔术师彭越",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py4",
                "name": u"{bold}{red}彭越你好",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py5",
                "name": u"{bold}{red}新春彭越",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.py6",
                "name": u"{bold}{red}圣诞彭越",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py7",
                "name": u"{bold}{red}音乐家彭越",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py8",
                "name": u"{bold}{red}彭越和EC宝典",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py9",
                "name": u"{bold}{red}彭越小姐和草帽",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py10",
                "name": u"{red}{bold}神父彭越",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.py11",
                "name": u"{red}{bold}花嫁彭越小姐",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.pangbai",
                "name": u"{bold}{red}旁白(旧版)-Vilrot",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.gezi",
                "name": u"{red}{bold}鸽子-黑原灵",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.dao",
                "name": u"{red}{bold}终界一刀-黑原灵",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.huli",
                "name": u"{bold}{red}狐狸_GuGu",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.hua",
                "name": u"{red}{bold}游戏画面改编-画画的嗨皮",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.shou",
                "name": u"{bold}{red}兽兽EC娘-汤圆喵ink",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.bao",
                "name": u"{bold}{red}下界夺宝-触屏defend弱鸡",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.color",
                "name": u"{red}{bold}色盲海洋之旅-GOOD_Sh1X1n",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.dream",
                "name": u"{bold}追逐梦想",
                "introduce": u"驿路相逢，为了共同的梦想。{enter}{enter}【使用方法】{enter}在《起床战争》游戏中点击地图内的物品展示框即可喷漆！",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.qingchun",
                "name": u"{bold}【梦境限定】{red}青春·喷漆",
                "introduce": u"我好像看懂你的表情了。 （点击地图中的物品展示框来使用）",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.sun",
                "name": u"{bold}【梦境限定】{red}太阳当空照",
                "introduce": u"好大的太阳啊{enter}(点击地图内物品展示框使用)",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py_sgqs",
                "name": u"{bold}{red}圣光骑士彭越",
                "introduce": u"【像素EC活动作品】{enter}点击地图内的物品展示框喷漆！{enter}收集更多的喷漆样式吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py_football",
                "name": u"PY足球盛宴喷漆",
                "introduce": u"可爱的彭彭正在灯光璀璨球场上，赶紧来一起享受这场足球盛宴吧！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.snow",
                "name": u"{bold}【2022圣诞梦境】{red} 初雪林喷漆",
                "introduce": u"似乎在下雪的静谧森林......（点击地图中的物品展示框来使用）",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.gingerbread",
                "name": u"{bold}【2022圣诞】 {red}诡笑姜饼人",
                "introduce": u"姜饼人将以诡异的笑容面对将会享用它的人。（点击地图内物品展示框来使用）",
                "price": "ornament-fragment:10",
                "default_own": False
            },
            {
                "prop_id": "spray.rl",
                "name": u"{bold}【RL】{gold}圣符传说喷漆",
                "introduce": u"参与沉浸式解密&PVE剧情游戏《圣符传说》相关活动来获得！（点击游戏内的物品展示框来使用）",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.vilrot",
                "name": u"Vilrot",
                "introduce": u"Vilrot!",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.rl_minemaster",
                "name": u"诅咒矿长",
                "introduce": u"愚人节快乐!\n奖励一个矿长和庞克的地下矿洞一日游(\n真是难得的和谐啊",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.purple-cry",
                "name": u"{bold}{dark-purple}【S4赛季限定】紫光水晶喷漆",
                "introduce": u"(点击地图内物品展示框来使用！){enter}S4赛季限定喷漆",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.purple-night",
                "name": u"{bold}{dark-purple}【S4赛季限定】紫光之夜喷漆",
                "introduce": u"(点击地图内物品展示框来使用！){enter}S4赛季限定喷漆",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py-ysj",
                "name": u"艺术家PY",
                "introduce": u"【八周年同人创作活动精选奖限定喷漆】\n拿起画笔，绘出美好的回忆\n感谢您一路的支持",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.ec-8-ann",
                "name": u"{bold}【8周年限定】{red}2023周年庆",
                "introduce": u"庆祝EaseCation的8周年，一路走来，一路有你！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.ecgirl",
                "name": u"EC娘",
                "introduce": u"新晋EC吉祥物之一！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.cfyz",
                "name": u"{bold}{red}【一周年】乘风驭舟-喷漆",
                "introduce": u"起床一周年派对上的美丽蛋糕（点击地图中的物品展示框来使用）",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.villahead",
                "name": u"村长私人照片喷漆",
                "introduce": u"不要误解，但他的确是个称职的村长（点击地图中的物品展示框来使用）",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py-px",
                "name": u"圣光骑士PY·捧星",
                "introduce": u"shop.bedwars.spray.py-px.intro",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.rl_miner",
                "name": u"庞克探险队",
                "introduce": u"曾经的庞克探险队",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.la",
                "name": u"太阳神·拉",
                "introduce": u"这可能就是太阳神？",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.py-sb",
                "name": u"赛博彭越",
                "introduce": u"酷酷的彭越，谁能不喜欢呢？",
                "price": -1,
                "default_own": False
            },

            {
                "prop_id": "spray.py-naughty",
                "name": u"调皮的小PY",
                "introduce": u"小PY又调皮了！",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.ecgirl-winter",
                "name": u"冬季EC娘",
                "introduce": u"冬天到了，大家要注意保暖呀",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.ycxndxrkhs",
                "name": u"永存信念的向日葵花神",
                "introduce": u"【2024频道新春同人创作活动奖励】\n“成神之路并不简单，对吧。”",
                "price": -1,
                "default_own": False
            },
            {
                "prop_id": "spray.ecnal",
                "name": u"EC娘·爱恋",
                "introduce": u"【wiki编辑者的特别奖励】\n感谢您对EaseCation Wiki的贡献！",
                "price": -1,
                "default_own": False
            }
        ]
    }

]


# ==================== 导出的配置字典 ====================
# 以下配置字典用于各个Manager加载配置

def _build_config_dict(type_id):
    """
    从ORNAMENT_TYPES中提取指定类型的配置字典

    Args:
        type_id (str): 装饰类型ID

    Returns:
        dict: 配置字典 {prop_id: {name, introduce, price, default_own}}
    """
    config_dict = {}
    for ornament_type in ORNAMENT_TYPES:
        if ornament_type["type_id"] == type_id:
            for ornament in ornament_type["ornaments"]:
                prop_id = ornament["prop_id"]
                config_dict[prop_id] = {
                    "name": ornament["name"],
                    "introduce": ornament["introduce"],
                    "price": ornament["price"],
                    "default_own": ornament["default_own"]
                }
            break
    return config_dict


# 1. 喷漆配置 (spray)
SPRAY_CONFIG = _build_config_dict("spray")

# 2. 击杀广播配置 (kill-broadcast)
# 注意：击杀广播需要特殊格式，包含messages字段
KILL_BROADCAST_CONFIG = {}
for ornament_type in ORNAMENT_TYPES:
    if ornament_type["type_id"] == "kill-broadcast":
        for ornament in ornament_type["ornaments"]:
            prop_id = ornament["prop_id"]
            # 击杀广播的introduce可能包含消息内容，这里暂时使用空列表
            # TODO: 后续需要从introduce中解析或从其他地方加载消息列表
            KILL_BROADCAST_CONFIG[prop_id] = {
                "name": ornament["name"],
                "messages": []  # 暂时为空，需要补充实际消息
            }
        break

# 3. 胜利之舞配置 (winner-effect)
VICTORY_DANCE_CONFIG = _build_config_dict("winner-effect")

# 4. 击杀音效配置 (kill-sound)
# 注意：击杀音效需要特殊格式，包含sounds字段
KILL_SOUND_CONFIG = {}
for ornament_type in ORNAMENT_TYPES:
    if ornament_type["type_id"] == "kill-sound":
        for ornament in ornament_type["ornaments"]:
            prop_id = ornament["prop_id"]
            # 击杀音效需要音效列表，暂时使用空列表
            # TODO: 后续需要补充实际音效文件名
            KILL_SOUND_CONFIG[prop_id] = {
                "name": ornament["name"],
                "sounds": []  # 暂时为空，需要补充实际音效
            }
        break

# 5. 表情包配置 (meme)
MEME_CONFIG = _build_config_dict("meme")

# 6. 床装饰配置 (bed-ornament)
BED_ORNAMENT_CONFIG = _build_config_dict("bed-ornament")

# 7. 破坏床广播配置 (bed-destroy-message)
BED_DESTROY_MESSAGE_CONFIG = _build_config_dict("bed-destroy-message")

# 8. 破坏床特效配置 (bed-destroy-effect)
BED_DESTROY_EFFECT_CONFIG = _build_config_dict("bed-destroy-effect")

# 9. 商店NPC外观配置 (shop-npc-skin)
SHOP_NPC_SKIN_CONFIG = _build_config_dict("shop-npc-skin")

# 10. 个性商店配置 (personalized-shop)
PERSONALIZED_SHOP_CONFIG = _build_config_dict("personalized-shop")
