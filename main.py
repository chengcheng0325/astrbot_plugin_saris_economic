from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *
import astrbot.api.message_components as Comp

from .API.SignIn import create_check_in_card
from .API.maintenance import Equipment

import os
import datetime
import requests
import json
import time
import random
import re

    # 自定义的 Jinja2 模板，支持 CSS
TMPL = '''
<style>
/*  inventory 类：整个背包容器的样式 */
.inventory {
    display: grid; /* 使用 grid 布局 */
    grid-template-columns: repeat(5, 360px); /* 定义 grid 布局的列：重复 5 列，每列宽度相同 */
    grid-gap: 10px; /* 设置 grid 单元格之间的间距 */
    padding: 10px; /* 设置容器的内边距 */
    border: 1px solid #ccc; /* 设置容器的边框 */
    background-color: #f9f9f9; /* 设置容器的背景颜色 */
    font-size: 48px; /* 增加了整个背包的默认字体大小 */
}

/* inventory-item 类：每个物品栏的样式 */
.inventory-item {
    border: 1px solid #ddd; /* 设置物品栏的边框 */
    padding: 5px; /* 设置物品栏的内边距 */
    text-align: left; /* 设置文本对齐方式为左对齐 */
    font-size: 36px; /* 设置物品栏内的字体大小 */
    background-color: #fff; /* 设置物品栏的背景颜色 */
}

/* inventory-item p 类：物品栏内段落的样式 */
.inventory-item p {
    margin: 5px 0; /* 设置段落的上下外边距，调整段落间距 */
}

/* inventory-item strong 类：物品栏内加粗文字的样式 */
.inventory-item strong {
    font-size: 36px; /* 设置加粗标签的字体大小 */
}

/*  状态为 False 时的样式（红色） */
.status-false {
    color: red; /*  设置文本颜色为红色 */
}

/*  状态为 True 时的样式（绿色） */
.status-true {
    color: green; /*  设置文本颜色为绿色 */
}
</style>

<div class="inventory">
{% for item in items %}  <!-- 循环遍历 items 列表中的每个 item -->
    <div class="inventory-item"> <!-- 每个物品栏 -->
        <p><strong>ID:</strong> {{ item.id }}</p> <!-- 显示物品的 ID -->
        <p><strong>UserId:</strong> {{ item.user_id }}</p> <!-- 显示物品的 UserId -->
        <p><strong>物品名称:</strong> {{ item.item_name }}</p> <!-- 显示物品的名称 -->
        <p><strong>物品数量:</strong> {{ item.item_count }}</p> <!-- 显示物品的数量 -->
        <p><strong>物品类型:</strong> {{ item.item_type }}</p> <!-- 显示物品的类型 -->
        {% if item.fish_power > 0 %}  <!--  判断是否存在渔力，如果渔力大于0则显示 -->
            <p><strong>渔力:</strong> {{ item.fish_power }}</p> <!--  显示物品的渔力 -->
        {% endif %}
        <p><strong>物品价值:</strong> {{ item.item_value }}</p> <!-- 显示物品的价值 -->

        {% if item.item_max_durability > 0 or item.item_current_durability > 0 %} <!-- 如果最大耐久度或当前耐久度大于 0，则显示耐久度信息 -->
            <p><strong>物品耐久度:</strong> {{ item.item_max_durability }} / {{ item.item_current_durability }}</p> <!-- 显示物品耐久度 -->
        {% endif %}

        <p><strong>物品使用状态:</strong> <span class="status-{% if item.item_use_status == 0 %}false{% else %}true{% endif %}">{% if item.item_use_status == 0 %} False {% else %} True {% endif %}</span></p> <!-- 显示物品的使用状态：如果 item_use_status 为 0，则显示“False”，否则显示“True”，并根据状态应用不同的 CSS 类 -->
    </div>
{% endfor %} <!-- 结束循环 -->
</div>
'''








# 路径配置
PLUGIN_DIR = os.path.join('data', 'plugins', 'astrbot_plugin_saris_economic')
IMAGE_FOLDER = os.path.join(PLUGIN_DIR, "backgrounds")
FONT_PATH = os.path.join(PLUGIN_DIR, "font.ttf")


# 确定输出路径：优先尝试当前工作目录下的 data/sign_image，否则使用插件目录
RUNNING_SCRIPT_DIRECTORY = os.getcwd()
OUTPUT_PATH = os.path.join(RUNNING_SCRIPT_DIRECTORY, 'data', 'sign_image')

def get_formatted_time():
    """
    获取格式化后的时间字符串，格式为：YYYY-MM-DD HH:MM:SS 星期X
    """
    now = datetime.datetime.now()
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_name = weekday_names[now.weekday()]
    return now.strftime(f"%Y-%m-%d %H:%M:%S {weekday_name}")


def get_one_sentence():
    """
    从 https://api.tangdouz.com/a/one.php?return=json 获取一句一言。
    进行错误处理和重试机制，保证服务的稳定性。
    """
    max_retries = 3
    url = "https://api.tangdouz.com/a/one.php?return=json"
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=5)  # 添加超时时间
            response.raise_for_status()  # 检查 HTTP 状态码
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            logger.warning(f"请求 one_sentence 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))  # 增加重试间隔
            else:
                logger.error(f"获取 one_sentence 失败: {e}")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析 one_sentence 失败: {e}")
            return None
    return None


@register("Economic", "城城", "经济插件", "1.1.1")
class EconomicPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        os.makedirs(OUTPUT_PATH, exist_ok=True)

    @filter.on_astrbot_loaded()
    async def on_astrbot_loaded(self):
        """
        插件初始化
        """
        logger.info("------ saris_Economic ------")
        logger.info(f"经济插件已初始化，签到图输出路径设置为: {OUTPUT_PATH}")
        logger.info(f"如果有问题，请在 https://github.com/chengcheng0325/astrbot_plugin_saris_economic/issues 提出 issue")
        logger.info("或加作者QQ: 3079233608 进行反馈。")
        self.database_plugin = self.context.get_registered_star("saris_db")
        self.fish_plugin = self.context.get_registered_star("saris_fish")
        # 数据库插件
        if not self.database_plugin or not self.database_plugin.activated:
            logger.error("经济插件缺少数据库插件，请先加载 astrbot_plugin_saris_db.\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            self.database_plugin_config = None  # 为了避免后续使用未初始化的属性
            self.database_plugin_activated = False
        else:
            self.database_plugin_config = self.database_plugin.config
            self.database_plugin_activated = True
            from data.plugins.astrbot_plugin_saris_db.main import open_databases, DATABASE_FILE
            self.open_databases = open_databases
            self.DATABASE_FILE = DATABASE_FILE
        # 钓鱼插件
        if not self.fish_plugin or not self.fish_plugin.activated:
            self.fish_plugin_activated = False
        else:
            self.fish_plugin_activated = True
        logger.info("------ saris_Economic ------")

    def getGroupUserIdentity(self, is_admin: bool, user_id: str, owner: str):
        """
        判断用户在群内的身份。
        """
        if is_admin:
            return "管理员"
        elif user_id == owner:
            return "群主"
        else:
            return "普通用户"

    # -------------------------- 签到功能 --------------------------
    @filter.command("签到",alias={'info', 'sign'})
    async def sign_in(self, event: AstrMessageEvent):
        """
        - 签到 [生成签到卡片并发送]
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，签到功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                user_name = event.get_sender_name()
                group = await event.get_group(group_id=event.message_obj.group_id)
                owner = group.group_owner
                is_admin = event.is_admin()
                identity = self.getGroupUserIdentity(is_admin, user_id, owner)
                formatted_time = get_formatted_time()
                sign_in_count = db_user.query_sign_in_count()[0]  # 获取签到次数的第一个元素
                one_sentence_data = get_one_sentence()

                # 默认值，防止one_sentence获取失败造成错误
                one_sentence = "今日一言获取失败"
                one_sentence_source = "未知"

                if one_sentence_data:
                    one_sentence = one_sentence_data.get("tangdouz", "今日一言获取失败")
                    one_sentence_source = f"————{one_sentence_data.get('from', '未知')} - {one_sentence_data.get('from_who', '未知')}"

                last_sign_in_date = db_user.query_last_sign_in_date()
                today = datetime.datetime.now().strftime("%Y-%m-%d")
                user_economy = db_economy.get_economy()

                sign_in_reward = 0  # 签到奖励
                is_signed_today = (last_sign_in_date == today)

                if not is_signed_today:
                    sign_in_reward = round(random.uniform(50, 100), 2)
                    db_user.update_sign_in(sign_in_reward)
                    db_economy.add_economy(sign_in_reward)
                    user_economy += sign_in_reward

                user_info = [user_id, identity, user_name]
                bottom_left_info = [
                    f"当前时间: {formatted_time}",
                    f"签到日期: {today if not is_signed_today else last_sign_in_date}",
                    f"金币: {user_economy:.2f}"  # 格式化为两位小数
                ]

                bottom_right_top_info = [
                    "今日已签到" if is_signed_today else "签到成功",
                    f"签到天数: {sign_in_count}" if is_signed_today else f"签到天数: {sign_in_count + 1}",
                    f"获取金币: {db_user.query_sign_in_coins() if is_signed_today else sign_in_reward:.2f}"  # 格式化为两位小数
                ]

                bottom_right_bottom_info = [
                    one_sentence,
                    one_sentence_source,
                ]

                sign_image = create_check_in_card(
                    avatar_path=f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640",
                    user_info=user_info,
                    bottom_left_info=bottom_left_info,
                    bottom_right_top_info=bottom_right_top_info,
                    bottom_right_bottom_info=bottom_right_bottom_info,
                    output_path=os.path.join(OUTPUT_PATH, f"{user_id}.png"),
                    image_folder=IMAGE_FOLDER,
                    font_path=FONT_PATH
                )
                yield event.image_result(sign_image)
                logger.info(f"用户 {user_id} 签到成功，签到卡片已保存至 {os.path.join(OUTPUT_PATH, f'{user_id}.png')}")

        except Exception as e:
            logger.exception(f"用户 {user_id} 签到失败: {e}")
            yield event.plain_result("签到时发生错误，请稍后再试。")
    

    # -------------------------- 商店功能 --------------------------
    @filter.command_group("商店", alias={'store'})
    def Store(self):
        """
        - 商店
        """
        pass

    @Store.command("基础")
    async def store(self, event: AstrMessageEvent):
        """
        - 基础 [购买基础物品] 制作中...
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，商店功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                yield event.plain_result("制作中...")
        except Exception as e:
            logger.exception(f" {e}")
    
    @Store.group("渔具", alias={'钓鱼'})
    def fish_store():
        """
        - 渔具商店
        """
        pass

    @fish_store.command("鱼竿", alias={'钓竿'})
    async def fishing_rod_store(self, event: AstrMessageEvent):
        """
        - 鱼竿商店
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，钓鱼商店功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，钓鱼商店功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return
        bot_id = int(event.get_self_id())
        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                fish_store = db_store.get_all_fishing_rod_store()
                node = [Comp.Node(
                    uin=bot_id,
                    name="saris",
                    content=[
                        Comp.Plain("----- 鱼竿商店 ----"),
                    ]
                )]
                for fish in fish_store:
                    渔力 = db_fish.get_fishing_pole_by_kind(fish[1])[2]
                    test = f"ID: {fish[0]}\n名称: {fish[1]}\n类型: {fish[3]}\n渔力: {渔力}\n价格: {fish[4]}\n数量: {fish[2]}\n耐久：{fish[5]}"
                    node.append(Comp.Node(
                        uin=bot_id,
                        name="saris",
                        content=[
                            Comp.Plain(test)
                        ]
                    ))
                yield event.chain_result([Comp.Nodes(node)])
        except Exception as e:
            logger.exception(f"{e}")
        
    @fish_store.command("鱼饵", alias={'钓饵'})
    async def bait_store(self, event: AstrMessageEvent):
        """
        - 鱼饵商店
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，钓鱼商店功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，钓鱼商店功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return
        bot_id = int(event.get_self_id())
        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                fish_store = db_store.get_all_bait_store()
                node = [Comp.Node(
                    uin=bot_id,
                    name="saris",
                    content=[
                        Comp.Plain("----- 鱼饵商店 ----"),
                    ]
                )]
                for fish in fish_store:
                    渔力 = db_fish.get_bait_by_kind(fish[1])[2]
                    test = f"ID: {fish[0]}\n名称: {fish[1]}\n类型: {fish[3]}\n渔力: {渔力}\n价格: {fish[4]}\n数量: {fish[2]}"
                    node.append(Comp.Node(
                        uin=bot_id,
                        name="saris",
                        content=[
                            Comp.Plain(test)
                        ]
                    ))
                yield event.chain_result([Comp.Nodes(node)])
        except Exception as e:
            logger.exception(f"{e}")
    


    # -------------------------- 购买功能 --------------------------
    @filter.command_group("购买", alias={'buy'})
    def buy(self):
        """
        - 购买物品
        """
        pass

    @buy.group("渔具")
    def fish_buy():
        """
        - 购买渔具
        """
        pass

    @fish_buy.command("鱼竿", alias={'钓竿'})
    async def fishing_rod_buy(self, event: AstrMessageEvent, ID: int):
        """
        - 购买鱼竿。
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，渔具购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return
        
        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                iteam = db_store.get_fishing_rod_store_item(ID)
                if not iteam:
                    yield event.plain_result("该物品不存在。")
                    return
                ItemValue = iteam[4]
                if ItemValue > db_economy.get_economy():
                    yield event.plain_result("您的金币不足。")
                    return
                db_economy.reduce_economy(ItemValue)
                iteam_id = db_backpack.insert_backpack(iteam[1], iteam[2], iteam[3], iteam[4], iteam[5], iteam[5], 0)
                yield event.plain_result(f"购买成功\n物品名称: {iteam[1]}[{iteam_id}]\n物品数量: {iteam[2]}\n物品类型: {iteam[3]}\n物品价值: {iteam[4]}\n物品耐久度: {iteam[5]}\n物品当前耐久度: {iteam[5]}")
        except Exception as e:
            logger.exception(f" {e}")

    @fish_buy.command("鱼饵", alias={'钓饵'})
    async def bait_buy(self, event: AstrMessageEvent, ID: int, num: int = 1):
        """
        - 购买鱼饵。
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，渔具购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return
        
        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                iteam = db_store.get_bait_store_item(ID)
                if not iteam:
                    yield event.plain_result("该物品不存在。")
                    return
                ItemValue = iteam[4] * num
                if ItemValue > db_economy.get_economy():
                    yield event.plain_result("您的金币不足。")
                    return
                db_economy.reduce_economy(ItemValue)
                Iteam = db_backpack.query_backpack_ItemName(iteam[1])
                if Iteam is None:
                    iteam_id = db_backpack.insert_backpack(iteam[1], iteam[2]*num, iteam[3], iteam[4], iteam[5], 0)
                    yield event.plain_result(f"购买成功\n物品名称: {iteam[1]}[{iteam_id}]\n物品数量: {iteam[2]*num}\n物品类型: {iteam[3]}\n物品价值: {iteam[4]}")
                else:
                    db_backpack.update_backpack_item_count(iteam[2]*num, Iteam[0])
                    yield event.plain_result(f"购买成功\n物品名称: {iteam[1]}[{Iteam[0]}]\n物品数量: {Iteam[3]+iteam[2]*num}[+{iteam[2]*num}]\n物品类型: {iteam[3]}\n物品价值: {iteam[4]}")
        except Exception as e:
            logger.exception(f" {e}")

    # -------------------------- 出售功能 --------------------------
    @filter.command("出售", alias={'sell'})
    async def sell(self, event: AstrMessageEvent, ID: int, num: int = 1):
        """
        - 出售物品
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，出售功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                iteam = db_backpack.query_backpack_ID(ID)
                if not iteam:
                    yield event.plain_result("该物品不存在。")
                    return
                quantity = iteam[3]
                if num > quantity:
                    yield event.plain_result(f"{iteam[2]}[{iteam[0]}]数量不足{num}")
                    return
                if quantity == num:
                    db_backpack.delete_backpack(ID)
                else:
                    db_backpack.update_backpack_item_count(-num,ID)
                db_economy.add_economy(iteam[5]*num)
                yield event.plain_result(f"出售成功\n物品名称: {iteam[2]}[{iteam[0]}]\n物品数量: {num}\n物品价值: {iteam[5]*num}")
        except Exception as e:
            logger.exception(f" {e}")






    # -------------------------- 装备功能 --------------------------
    @filter.command_group("使用", alias={'use', '装备'})
    def use(self):
        """
        - 装备
        """
        pass

    @use.command("渔具", alias={'钓鱼'})
    async def equip(self, event: AstrMessageEvent, ID: int, num: int = 1):
        """
        - 装备渔具
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，装备功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，渔具购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return
        
        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                user_backpack = db_backpack.query_backpack()
                user_item = db_backpack.query_backpack_ID(ID)
                equipment = db_user.query_equipment_id(user_item[0])
                if user_item[4] == "饰品":
                    if num >= 1 and num <=3:
                        equipment_type = db_user.query_equipment_type(user_item[4]+str(num))
                        type_name = user_item[4]+str(num)
                    else:
                        yield event.plain_result("请输入正确的饰品栏位。")
                        return
                else:
                    equipment_type = db_user.query_equipment_type(user_item[4])
                    type_name = user_item[4]
                text = ""
                if not user_item:
                    yield event.plain_result("该物品不存在。")
                    return
                if user_item[4] != "鱼竿" and user_item[4] != "鱼饵" and user_item[4] != "头盔" and user_item[4] != "胸甲" and user_item[4] != "护腿" and user_item[4] != "饰品":
                    yield event.plain_result("该物品不能装备。")
                    return
                if user_item[8] == 1 and equipment is not None and equipment_type[3] != user_item[0]:
                    yield event.plain_result("该物品已使用。")
                    return
                if user_item[4] != "饰品":
                    db_user.update_equipment(type_name, user_item[0], user_item[2])
                    for item in user_backpack:
                        if user_item[4] == item[4]:
                            if item[8] == 1:
                                # text += f"物品[{item[0]}]{item[2]}已帮你卸下了。\n"
                                db_backpack.unequip(item[0])
                    db_backpack.equip(ID)
                    text += f"物品[{user_item[0]}]{user_item[2]}已帮你装备上了。\n"
                    # yield event.plain_result(text)
                
                else:
                    # print(user_item[4])
                    if equipment is not None and equipment[2] != type_name:
                        db_backpack.unequip(equipment[2])
                        db_user.remove_accessory(re.search(r'(\d+)\D*$',equipment[2]).group())
                        # text += f"物品[{equipment[3]}]{equipment[4]}已帮你卸下了。\n"
                        if equipment_type[3] != -1 and equipment_type[3] != user_item[0]:
                            db_user.remove_accessory(str(num))
                            # text += f"物品[{equipment_type[3]}]{equipment_type[4]}已帮你卸下了。\n"
                    db_user.add_accessory(str(num), user_item[0], user_item[2])
                    text += f"物品[{user_item[0]}]{user_item[2]}已帮你装备上了。\n"
                
                yield event.plain_result(text)

        except Exception as e:
            logger.exception(f"{e}")

    


    # -------------------------- 背包功能 --------------------------
    @filter.command("我的背包", alias={'背包', 'backpack'})
    async def backpack(self, event: AstrMessageEvent):
        """
        - 背包
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，背包功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        bot_id = int(event.get_self_id())
        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                backpack = db_backpack.query_backpack()
                # print(backpack)
                if not backpack:
                    yield event.plain_result("您的背包为空。")
                    return
                backpack_data = []
                for item in backpack:
                    渔力 = 0
                    if item[4] == "鱼竿":
                        渔力 = db_fish.get_fishing_pole_by_kind(item[2])[2]
                    elif item[4] == "鱼饵":
                        渔力 = db_fish.get_bait_by_kind(item[2])[2]
                    inventory_data = {
                        "id": item[0],
                        "user_id": item[1],
                        "item_name": item[2],
                        "item_count": item[3],
                        "item_type": item[4],
                        "fish_power": 渔力,
                        "item_value": item[5],
                        "item_max_durability": item[6],
                        "item_current_durability": item[7],
                        "item_use_status": item[8]
                    }
                    backpack_data.append(inventory_data)
                try:
                    url = await self.html_render(TMPL, {"items": backpack_data})
                    yield event.image_result(url)
                except Exception as e:
                    logger.error(f"背包数据渲染失败: {e}|使用合并转发功能")
                    node = [Comp.Node(
                        uin=bot_id,
                        name="saris",
                        content=[
                            Comp.Plain("----- 背包 ----"),
                        ]
                    )]
                    for backpack in backpack_data:
                        formatted_string = f"ID: {backpack['id']}\n"
                        formatted_string += f"user_id: {backpack['user_id']}\n"
                        formatted_string += f"物品名称: {backpack['item_name']}\n"
                        formatted_string += f"物品数量: {backpack['item_count']}\n"
                        formatted_string += f"物品类型: {backpack['item_type']}\n"
                        渔力 = backpack.get("渔力", 0)  # 使用get方法，避免KeyError
                        if 渔力 > 0:
                            formatted_string += f"渔力: {渔力}\n"
                        formatted_string += f"物品价值: {backpack['item_value']}\n"
                        item_max_durability = backpack.get("item_max_durability", 0)
                        item_current_durability = backpack.get("item_current_durability", 0)
                        if item_max_durability > 0 or item_current_durability > 0:
                            formatted_string += f"物品耐久度: {item_max_durability}/{item_current_durability}\n"
                        item_use_status = backpack['item_use_status']
                        formatted_string += f"物品使用状态: {'True' if item_use_status != 0 else 'False'}"

                        node.append(Comp.Node(
                            uin=bot_id,
                            name="saris",
                            content=[
                                Comp.Plain(formatted_string)
                            ]
                        ))
                yield event.chain_result([Comp.Nodes(node)])
        except Exception as e:
            logger.error(f"我的背包功能失败: {e}")

    # -------------------------- 开箱功能 -------------------------

    @filter.command("开箱", alias={'open', 'box'})
    async def open_box(self, event: AstrMessageEvent, ID: int, num: int = 1):
        """
        - 开箱子
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，开箱功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                user_backpack = db_backpack.query_backpack()
                user_item = db_backpack.query_backpack_ID(ID)
                text = ""
                if not user_item:
                    yield event.plain_result("该物品不存在。")
                    return
                if user_item[4] != "箱子":
                    yield event.plain_result("该物品不是箱子")
                    return
                if user_item[3] < num:
                    yield event.plain_result(f"该物品数量不足{num}\n你当前拥有{user_item[3]}个。")
                    return
                if user_item[3] == num:
                    db_backpack.delete_backpack(user_item[0])
                else:
                    db_backpack.update_backpack_item_count(-num, user_item[0])
                for i in range(num):
                    box_items = db_fish.get_box_by_name(user_item[2])
                    text += f"------ 第{i+1}个箱子 ------\n"
                    for item in box_items:
                        print(item)
                        if random.random() < item[6]:
                            if item[3] == "钱":
                                金币 = round(random.uniform(item[4], item[5]))
                                text += f"获得金币: {金币}\n"
                                db_economy.add_economy(金币)
                            if item[3] == "鱼饵":
                                Iteam = db_backpack.query_backpack_ItemName(item[2])
                                鱼饵 = random.randint(item[4], item[5])
                                price = db_fish.get_bait_by_kind(item[2])[3]
                                if Iteam is None:
                                    iteam_id = db_backpack.insert_backpack(item[2], 鱼饵, item[3], price)
                                    text += f"获得{item[2]}[ID{iteam_id}]: {鱼饵}\n"
                                else:
                                    db_backpack.update_backpack_item_count(鱼饵, Iteam[0])
                                    text += f"获得{item[2]}: {Iteam[3]+鱼饵}[+{鱼饵}]\n"
                yield event.plain_result(text)
        except Exception as e:
            logger.exception(f" {e}")

    
    # -------------------------- 维修功能 --------------------------
    @filter.command_group("维修", alias={'buy'})
    def maintenance(self):
        """
        - 维修物品
        """
        pass

    @maintenance.command("查询")
    async def maintenance_query(self, event: AstrMessageEvent, ID: int):
        """
        - 查询鱼竿维修价格。
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，渔具购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                iteam = db_backpack.query_backpack_ID(ID)
                # iteam = db_store.get_fishing_rod_store_item(ID)
                if not iteam:
                    yield event.plain_result("该物品不存在。")
                    return
                if iteam[4] != "鱼竿":
                    yield event.plain_result("该物品不是鱼竿。")
                    return
                fishing_pole = db_fish.get_fishing_pole_by_kind(iteam[2])
                sword = Equipment(
                    original_max=fishing_pole[5],
                    current_max=iteam[6],
                    current=iteam[7],
                    original_value=fishing_pole[3]
                )
                all_repair_results = sword.simulate_all_repairs()
                text = "----- 维修查询 -----\n"
                translation = {
                    'cost': '花费',
                    'success': '是否可以维修',
                    'new_current_max': '最大耐久度',
                    'new_current': '当前耐久度',
                    'repair_cost': '维修花费',
                    'low': '低级维修',
                    'medium': '中级维修',
                    'high': '高级维修'
                }
                for level, data in all_repair_results.items():
                    translated_level = translation.get(level, level)  # Translate the level
                    text += f"维修等级: {translated_level}\n"
                    for key, value in data.items():
                        translated_key = translation.get(key, key)  # Translate the key
                        text += f"  {translated_key}: {value}\n"
                yield event.plain_result(text)
        except Exception as e:
            logger.exception(f" {e}")

    @maintenance.command("低级")
    async def maintenance_low(self, event: AstrMessageEvent, ID: int):
        """
        - 低级维修鱼竿。
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，渔具购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                iteam = db_backpack.query_backpack_ID(ID)
                # iteam = db_store.get_fishing_rod_store_item(ID)
                if not iteam:
                    yield event.plain_result("该物品不存在。")
                    return
                if iteam[4] != "鱼竿":
                    yield event.plain_result("该物品不是鱼竿。")
                    return
                fishing_pole = db_fish.get_fishing_pole_by_kind(iteam[2])
                sword = Equipment(
                    original_max=fishing_pole[5],
                    current_max=iteam[6],
                    current=iteam[7],
                    original_value=fishing_pole[3]
                )
                all_repair_results = sword.simulate_all_repairs()
                current_value = all_repair_results['low']['simulated_current_value']
                if float(all_repair_results['low']['cost']) > db_economy.get_economy():
                    yield event.plain_result("低级维修金币不足")
                    return
                db_backpack.update_backpack_all(ID,current_value,all_repair_results['low']['new_current_max'])
                db_economy.reduce_economy(round(float(all_repair_results['low']['cost']), 2))
                yield event.plain_result("低级维修成功")
        except Exception as e:
            logger.exception(f" {e}")
    
    @maintenance.command("中级")
    async def maintenance_medium(self, event: AstrMessageEvent, ID: int):
        """
        - 中级维修鱼竿。
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，渔具购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                iteam = db_backpack.query_backpack_ID(ID)
                # iteam = db_store.get_fishing_rod_store_item(ID)
                if not iteam:
                    yield event.plain_result("该物品不存在。")
                    return
                if iteam[4] != "鱼竿":
                    yield event.plain_result("该物品不是鱼竿。")
                    return
                fishing_pole = db_fish.get_fishing_pole_by_kind(iteam[2])
                sword = Equipment(
                    original_max=fishing_pole[5],
                    current_max=iteam[6],
                    current=iteam[7],
                    original_value=fishing_pole[3]
                )
                all_repair_results = sword.simulate_all_repairs()
                current_value = all_repair_results['medium']['simulated_current_value']
                if float(all_repair_results['medium']['cost']) > db_economy.get_economy():
                    yield event.plain_result("中级维修金币不足")
                    return
                db_backpack.update_backpack_all(ID,current_value,all_repair_results['medium']['new_current_max'])
                db_economy.reduce_economy(round(float(all_repair_results['medium']['cost']), 2))
                yield event.plain_result("中级维修成功")
        except Exception as e:
            logger.exception(f" {e}")
    
    @maintenance.command("高级")
    async def maintenance_high(self, event: AstrMessageEvent, ID: int):
        """
        - 高级维修鱼竿。
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_db")
            return
        if not self.fish_plugin_activated:
            yield event.plain_result("赛博钓鱼插件未加载，渔具购买功能无法使用。\n请先安装并启用 astrbot_plugin_saris_fish。\n插件仓库地址：https://github.com/chengcheng0325/astrbot_plugin_saris_fish")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish, db_backpack, db_store):
                iteam = db_backpack.query_backpack_ID(ID)
                # iteam = db_store.get_fishing_rod_store_item(ID)
                if not iteam:
                    yield event.plain_result("该物品不存在。")
                    return
                if iteam[4] != "鱼竿":
                    yield event.plain_result("该物品不是鱼竿。")
                    return
                fishing_pole = db_fish.get_fishing_pole_by_kind(iteam[2])
                sword = Equipment(
                    original_max=fishing_pole[5],
                    current_max=iteam[6],
                    current=iteam[7],
                    original_value=fishing_pole[3]
                    )
                all_repair_results = sword.simulate_all_repairs()
                current_value = all_repair_results['high']['simulated_current_value']
                if float(all_repair_results['high']['cost']) > db_economy.get_economy():
                    yield event.plain_result("高级维修金币不足")
                    return
                db_backpack.update_backpack_all(ID,current_value,all_repair_results['high']['new_current_max'])
                db_economy.reduce_economy(round(float(all_repair_results['high']['cost']), 2))
                yield event.plain_result("高级维修成功")
        except Exception as e:
            logger.exception(f" {e}")






    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''

        
