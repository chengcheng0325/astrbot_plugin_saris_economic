from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .SignIn import create_check_in_card
import os
import datetime
import requests
import json
import time
import random
from data.plugins.astrbot_plugin_database.main import open_databases, DATABASE_FILE

# 路径配置output_path
PLUGIN_DIR = os.path.join('data', 'plugins', 'astrbot_plugin_economic')
IMAGE_FOLDER = os.path.join(PLUGIN_DIR, "backgrounds")
FONT_PATH = os.path.join(PLUGIN_DIR, "font.ttf")
# OUTPUT_PATH = os.path.join('data', "output_path")
RUNNING_SCRIPT_DIRECTORY = os.getcwd()
OUTPUT_PATH = os.path.join(RUNNING_SCRIPT_DIRECTORY, os.path.join('data', 'output_path'))

def get_formatted_time():
    """
    获取格式化后的时间字符串，格式为：2025-3-24 01:09:32 星期三
    """
    now = datetime.datetime.now()
    # 获取年份、月份、日期
    year = now.year
    month = now.month
    day = now.day
    # 获取小时、分钟、秒
    hour = now.hour
    minute = now.minute
    second = now.second
    # 获取星期几（返回 0-6，0 代表星期一）
    weekday = now.weekday()
    # 将数字星期转换为中文星期
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    weekday_name = weekday_names[weekday]
    # 格式化时间字符串
    formatted_time = f"{year}-{month}-{day} {hour:02}:{minute:02}:{second:02} {weekday_name}"
    return formatted_time

def get_hitokoto():
    """
    从 https://hitokoto.152710.xyz/ 获取一句一言（hitokoto）。
    返回一个包含 JSON 数据的字典。
    """
    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.get("https://hitokoto.152710.xyz/")
            # 检查请求是否成功
            response.raise_for_status()  # 如果状态码不是 200，则抛出 HTTPError 异常
            # 解析 JSON 响应
            data = response.json()
            return data
        except requests.exceptions.RequestException as e:
            if response.status_code == 429 and attempt < max_retries - 1:
                print(f"请求过多，等待 5 秒后重试... ({attempt + 1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"请求出错: {e}")
                return None  # 或抛出异常，取决于你的错误处理策略
        except json.JSONDecodeError as e:
            print(f"JSON 解析出错: {e}")
            return None


@register("Economic", "城城", "经济插件", "1.0.0")
class EconomicPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.database_plugin = self.context.get_registered_star("Database")
        if self.database_plugin is None:
            logger.error("缺少 Database 插件，请先加载该插件。")
        # 确保获取的是一个实例，并且拥有 config 和 database_file 属性
        else:
            self.database_plugin_config = self.database_plugin.config
    
    def _init_env(self):
        # os.makedirs(os.path.dirname(DATABASE_FILE), exist_ok=True)
        os.makedirs(OUTPUT_PATH, exist_ok=True)

    @filter.command("签到")
    async def helloworld(self, event: AstrMessageEvent):
        '''签到功能'''
        if self.database_plugin is None:
            yield event.plain_result(f"缺少 Database 插件，签到功能无法使用。")
            return
        
        user_id = event.get_sender_id()         # 获取用户 ID

        try:
            with open_databases(self.database_plugin_config,DATABASE_FILE, user_id) as (db_user, db_economy):
                user_name = event.get_sender_name()     # 获取用户名
                admin = event.message_obj               # 判断是否为管理员
                if admin:
                    admin = "管理员"
                else:
                    admin = "普通用户"
                formatted_time = get_formatted_time()   # 获取格式化的时间字符串
                sign_number = db_user.query_sign_in_count()           # 查询用户签到次数
                hitokoto_data = get_hitokoto()
                random_number = round(random.uniform(50, 100), 2)  # 生成 50 到 100 之间的浮点数
                
                Sign_date = db_user.query_last_sign_in_date()
                # logger.info(f"签到日期: {Sign_date}")
                now = datetime.datetime.now().strftime("%Y-%m-%d")
                user_economy = db_economy.get_economy()[0]
                user_info = [
                    user_id,
                    admin,
                    user_name
                ]
                bottom_left_info = [
                    f"当前时间: {formatted_time}",
                ]
                bottom_right_top_info = []

                bottom_right_bottom_info = [
                    f"{hitokoto_data['hitokoto']}"
                    "\n",
                    f"————{hitokoto_data['from']} - {hitokoto_data['from_who']}"
                ]
                if Sign_date < now:
                    db_user.update_sign_in(random_number)
                    db_economy.add_economy(random_number)

                    bottom_left_info.append(f"签到日期: {now}")
                    bottom_left_info.append(f"金币: {user_economy+random_number}")

                    bottom_right_top_info.append(f"签到成功")
                    bottom_right_top_info.append(f"签到天数: {sign_number[0]+1}")
                    bottom_right_top_info.append(f"获取金币: {random_number}")

                else:
                    bottom_left_info.append(f"签到日期: {Sign_date}")
                    bottom_left_info.append(f"金币: {user_economy}")

                    bottom_right_top_info.append(f"今日已签到")
                    bottom_right_top_info.append(f"签到天数: {sign_number[0]}")
                    bottom_right_top_info.append(f"获取金币: {db_user.query_sign_in_coins()}")

                sign_image = create_check_in_card(
                    avatar_path=f"https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640",                            # 头像路径
                    user_info=user_info,                                # 用户信息
                    bottom_left_info=bottom_left_info,                  # 左下角信息
                    bottom_right_top_info=bottom_right_top_info,        # 右下角上部信息
                    bottom_right_bottom_info=bottom_right_bottom_info,  # 右下角下部信息
                    output_path=os.path.join(OUTPUT_PATH, f"{user_id}.png"),         # 输出文件名
                    image_folder=IMAGE_FOLDER,                          # 背景图片文件夹
                    font_path=FONT_PATH                                 # 字体文件路径  
                )
                yield event.image_result(sign_image) # 发送图片
                logger.info(f"签到成功，签到图片已保存至" + os.path.join(OUTPUT_PATH, f"{user_id}.png"))




        except Exception as e:
            logger.error(f"调用 open_databases 失败: {e}")
            yield event.plain_result(f"签到时发生错误，请稍后再试。") # 通知用户签到失败，避免用户困惑
            return # 确保退出函数，避免执行后续可能出错的代码

    async def terminate(self):
        '''可选择实现 terminate 函数，当插件被卸载/停用时会调用。'''
