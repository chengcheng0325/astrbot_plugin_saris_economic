from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.api.all import *
from .SignIn import create_check_in_card
import os
import datetime
import requests
import json
import time
import random
import re


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


@register("Economic", "城城", "经济插件", "0.2.4")
class EconomicPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self._init_env()
        self.database_plugin = self.context.get_registered_star("saris_db")
        if not self.database_plugin or not self.database_plugin.activated:
            logger.error("经济插件缺少数据库插件，请先加载 astrbot_plugin_saris_db.\n插件仓库地址：https://github.com/Astron/Astron-packages/tree/main/astrbot_plugin_saris_db")
            self.database_plugin_config = None  # 为了避免后续使用未初始化的属性
            self.database_plugin_activated = False
        else:
            self.database_plugin_config = self.database_plugin.config
            self.database_plugin_activated = True
            from data.plugins.astrbot_plugin_saris_db.main import open_databases, DATABASE_FILE
            self.open_databases = open_databases
            self.DATABASE_FILE = DATABASE_FILE
            


    def _init_env(self):
        """
        初始化插件环境，确保输出路径存在。
        """
        os.makedirs(OUTPUT_PATH, exist_ok=True)
        logger.info("------ saris_Economic ------")
        logger.info(f"经济插件已初始化，签到图输出路径设置为: {OUTPUT_PATH}")
        logger.info(f"如果有问题，请在 https://github.com/chengcheng0325/astrbot_plugin_saris_economic/issues 提出 issue")
        logger.info("或加作者QQ: 3079233608 进行反馈。")
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

    @filter.command("签到",alias={'info', 'sign'})
    async def sign_in(self, event: AstrMessageEvent):
        """
        签到功能：
        - 生成签到卡片并发送。
        """
        if not self.database_plugin_activated:
            yield event.plain_result("数据库插件未加载，签到功能无法使用。\n请先安装并启用 astrbot_plugin_saris_db。\n插件仓库地址：https://github.com/Astron/Astron-packages/tree/main/astrbot_plugin_saris_db")
            return

        user_id = event.get_sender_id()
        try:
            with self.open_databases(self.database_plugin_config, self.DATABASE_FILE, user_id) as (db_user, db_economy, db_fish):
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
                user_economy = db_economy.get_economy()[0]

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

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''
        
