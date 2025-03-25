from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import random
import io
import requests

# 定义文本换行函数
def split_line_into_multiple(line, font, max_width):
    lines = []
    words = line.split()  # 尝试按空格分割单词
    current_line = ''

    if not words:  # 处理无空格的长字符串
        current_line = ''
        for char in line:
            test_line = current_line + char
            if font.getlength(test_line) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return lines

    for word in words:
        test_line = f"{current_line} {word}" if current_line else word
        if font.getlength(test_line) <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            # 处理单词长度超过容器宽度的情况
            if font.getlength(word) > max_width:
                sub_line = ''
                for char in word:
                    if font.getlength(sub_line + char) <= max_width:
                        sub_line += char
                    else:
                        lines.append(sub_line)
                        sub_line = char
                lines.append(sub_line)
            else:
                current_line = word
    if current_line:
        lines.append(current_line)
    return lines

def create_check_in_card(
    avatar_path: str,
    user_info: list[str],
    bottom_left_info: list[str],
    bottom_right_top_info: list[str],
    bottom_right_bottom_info: list[str],
    output_path: str = "check_in_card.png",
    image_folder: str = "images",
    card_width: int = 1200,
    card_height: int = 630,
    avatar_size: int = 150,
    avatar_radius: int = 30,
    font_path: str = "path/to/your/font.ttf",  # 替换为你电脑上的字体文件路径，支持中文
):
    """
    生成签到图。
    """
    try:
        # 1. 选择背景图片
        image_files = [
            f
            for f in os.listdir(image_folder)
            if os.path.isfile(os.path.join(image_folder, f))
            and f.lower().endswith((".png", ".jpg", ".jpeg", ".gif"))
        ]
        if not image_files:
            raise FileNotFoundError(f"未在 {image_folder} 找到任何图片文件。")
        background_image_path = os.path.join(image_folder, random.choice(image_files))
        background = Image.open(background_image_path).convert("RGBA")

        # 获取背景图尺寸，判断横竖版
        bg_width, bg_height = background.size
        is_portrait = bg_height > bg_width

        # 调整背景图片大小以适应卡片尺寸
        if not is_portrait:
            background = background.resize((1200, 630))
        else:
            background = background.resize((900, 1200))
            card_width,card_height = background.size
        # 2. 创建头像
        try:
            if avatar_path.startswith("http://") or avatar_path.startswith("https://"):
                response = requests.get(avatar_path, stream=True)
                response.raise_for_status()  # 检查请求是否成功
                avatar = Image.open(io.BytesIO(response.content)).convert("RGBA")
            else:
                avatar = Image.open(avatar_path).convert("RGBA")
        except Exception as e:
            print(f"加载头像失败: {e}")
            return

        avatar = avatar.resize((avatar_size, avatar_size))

        # 创建圆形遮罩
        mask = Image.new("L", (avatar_size, avatar_size), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, avatar_size, avatar_size), radius=avatar_radius, fill=255)

        # 应用遮罩
        avatar.putalpha(mask)

        # 3. 创建文字图层
        text_color2 = (0, 0, 0, 255)  # 白色
        light_gray_color = (192, 192, 192, 255) #淡灰色
        shadow_color = (0, 0, 0, 128)    # 半透明黑色阴影
        font_size_info1 = avatar_size // 5 # 第一行第二行文字高度，保证三行文字加起来等于头像高度
        font_size_info2 = avatar_size // 5 # 第一行第二行文字高度，保证三行文字加起来等于头像高度
        font_size_info3 = avatar_size // 2 #第三行文字高度
        font_size_bottom = 28 # 底部文字大小
        margin = 20 # 边距
        # 加载字体
        try:
            font_info1 = ImageFont.truetype(font_path, font_size_info1) # 加载第一行字体
            font_info2 = ImageFont.truetype(font_path, font_size_info2) # 加载第二行字体
            font_info3 = ImageFont.truetype(font_path, font_size_info3) # 加载第三行字体
            font_bottom = ImageFont.truetype(font_path, font_size_bottom) # 加载底部字体
        except IOError:
            print(f"找不到字体文件: {font_path}.  请确认字体文件存在，且路径正确。 将使用默认字体。 将使用默认字体。")
            font_info1 = ImageFont.load_default() # 使用默认字体
            font_info2 = ImageFont.load_default() # 使用默认字体
            font_info3 = ImageFont.load_default() # 使用默认字体
            font_bottom = ImageFont.load_default() # 使用默认字体


        # 创建透明图层用于绘制文字和阴影
        text_layer = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(text_layer)

        # 添加阴影效果的函数
        def draw_text_with_shadow(draw_obj, text, font, x, y, text_color, shadow_color, offset=2,shadow=False):
            """在指定位置绘制带阴影的文字"""
            if shadow:
                # 绘制阴影
                draw_obj.text((x + offset, y + offset), text, font=font, fill=shadow_color)
            # 绘制正文
            draw_obj.text((x, y), text, font=font, fill=text_color)

        # 定义绘制圆角模糊框的函数
        def draw_rounded_blur_box(draw_obj, x, y, width, height, corner_radius, blur_radius, opacity):
            """绘制圆角模糊背景框"""
            rounded_mask = Image.new("L", (width, height), 0)
            draw_rounded = ImageDraw.Draw(rounded_mask)
            draw_rounded.rounded_rectangle((0, 0, width, height), radius=corner_radius, fill=opacity)

            blur_box = Image.new("RGBA", (width, height), (255, 255, 255, opacity))
            blur_box = blur_box.filter(ImageFilter.GaussianBlur(radius=blur_radius))
            blur_box.putalpha(rounded_mask)

            draw_obj.paste(blur_box, (x, y), blur_box)

        # 用户信息彩色渐变
        def draw_gradient_text(draw_obj, text, font, x, y, gradient_colors, shadow_color):
            """绘制彩色渐变文字"""
            num_chars = len(text)
            num_colors = len(gradient_colors)
            original_start_x = x
            for i, char in enumerate(text):
                char_width = draw_obj.textlength(char, font=font)
                segment = i / num_chars * (num_colors - 1)
                segment_index = int(segment)
                segment_fraction = segment - segment_index

                color1 = gradient_colors[segment_index]
                color2 = gradient_colors[min(segment_index + 1, num_colors - 1)]

                r = int(color1[0] + (color2[0] - color1[0]) * segment_fraction)
                g = int(color1[1] + (color2[1] - color1[1]) * segment_fraction)
                b = int(color1[2] + (color2[2] - color1[2]) * segment_fraction)
                a = 255

                draw_text_with_shadow(draw_obj, char, font, x, y, (r, g, b, a), shadow_color)
                x += char_width

        # 定义圆角模糊框的默认参数
        blur_radius = 5 # 模糊半径
        opacity = 170  # 透明度 (0-255)
        corner_radius = 10 # 圆角半径

        if not is_portrait:
        # 绘制用户信息(横版)
            start_x = avatar_size + 2 * margin # 文字起始x坐标
            start_y = margin # 文字起始y坐标
            line_spacing = 5 #行间距
            current_y = start_y # 当前y坐标
            draw_text_with_shadow(draw, user_info[0], font_info1, start_x, current_y, light_gray_color, shadow_color,shadow=True) # 绘制第一行
            current_y += font_size_info1 + line_spacing # 更新y坐标
            draw_text_with_shadow(draw, user_info[1], font_info2, start_x, current_y, light_gray_color, shadow_color,shadow=True) # 绘制第二行
            current_y += font_size_info2 - line_spacing # 更新y坐标

            # Gradient color for the third line (with three colors)
            text = user_info[2] # 获取第三行文字
            gradient_colors = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]  # Red -> Green -> Blue # 渐变颜色
            num_chars = len(text) # 文字长度
            num_colors = len(gradient_colors) # 颜色数量

            original_start_x = start_x  # 保存初始的start_x值
            original_start_y = current_y # 保存初始的start_y值

            for i, char in enumerate(text): # 遍历每个字符
                char_width = draw.textlength(char, font=font_info3) # 计算字符宽度

                # Determine which color segment the current character falls into
                segment = i / num_chars * (num_colors - 1) # 计算当前字符在哪个颜色段
                segment_index = int(segment) # 获取颜色段索引
                segment_fraction = segment - segment_index # 获取颜色段偏移

                # Get the two colors for the current segment
                color1 = gradient_colors[segment_index] # 获取颜色1
                color2 = gradient_colors[min(segment_index + 1, num_colors - 1)]  # Ensure not out of bounds # 获取颜色2，防止越界

                # Linear interpolation between color1 and color2
                r = int(color1[0] + (color2[0] - color1[0]) * segment_fraction) # 线性插值红色
                g = int(color1[1] + (color2[1] - color1[1]) * segment_fraction) # 线性插值绿色
                b = int(color1[2] + (color2[2] - color1[2]) * segment_fraction) # 线性插值蓝色
                a = 255 # 透明度

                draw_text_with_shadow(draw, char, font_info3, start_x, current_y, (r, g, b, a), shadow_color) # 绘制字符
                start_x += char_width # 更新x坐标

            # Reset start_x for subsequent text drawing
            start_x = original_start_x #恢复到初始位置
            current_y = original_start_y #恢复到初始y位置

            # 绘制底部信息区域(横版)
            bottom_height = card_height // 3  # 底部区域高度

            # 1. 左下角区域
            bottom_left_x = margin # 左下角x坐标
            bottom_left_y = card_height - bottom_height - margin # 左下角y坐标
            bottom_left_width = card_width // 2 - 10 # 左下角宽度
            bottom_left_height = bottom_height # 左下角高度

            draw_rounded_blur_box(text_layer, bottom_left_x, bottom_left_y, bottom_left_width, bottom_left_height, corner_radius, blur_radius, opacity)

            # 绘制左下角文字
            current_y = bottom_left_y + 10 # 当前y坐标
            font_size_bottom_left = 24 # 左下角文字大小
            try:
                font_bottom_left = ImageFont.truetype(font_path, font_size_bottom_left) # 加载左下角字体
            except IOError:
                font_bottom_left = ImageFont.load_default() # 使用默认字体
            for line in bottom_left_info: # 遍历左下角信息
                draw_text_with_shadow(draw, line, font_bottom_left, bottom_left_x + 10, current_y, text_color2, shadow_color) # 绘制左下角文字
                current_y += font_size_bottom_left + 5 # 更新y坐标


            # 2. 右下角上部区域
            bottom_right_width = card_width // 2 - 2 * margin # 右下角上部宽度
            bottom_right_top_height = bottom_height // 2 - 5 # 右下角上部高度
            bottom_right_x = card_width // 2 + margin # 右下角上部x坐标
            bottom_right_y = card_height - bottom_height - margin # 右下角上部y坐标

            draw_rounded_blur_box(text_layer, bottom_right_x, bottom_right_y, bottom_right_width, bottom_right_top_height, corner_radius, blur_radius, opacity)


            # 绘制右下角上部文字
            current_y = bottom_right_y + 10 # 当前y坐标
            font_size_bottom_right_top = 20 # 右下角上部文字大小
            try:
                font_bottom_right_top = ImageFont.truetype(font_path, font_size_bottom_right_top) # 加载字体
            except IOError:
                font_bottom_right_top = ImageFont.load_default() # 使用默认字体
            for line in bottom_right_top_info: # 遍历右下角上部信息
                draw_text_with_shadow(draw, line, font_bottom_right_top, bottom_right_x + 10, current_y-6, text_color2, shadow_color) # 绘制文字
                current_y += font_size_bottom_right_top + 3 # 更新y坐标

            # 3. 右下角下部区域
            bottom_right_bottom_height = bottom_height // 2 - 5 # 右下角下部高度
            bottom_right_y = card_height - bottom_right_bottom_height - margin # 右下角下部y坐标

            draw_rounded_blur_box(text_layer, bottom_right_x, bottom_right_y, bottom_right_width, bottom_right_bottom_height, corner_radius, blur_radius, opacity)

            # 绘制右下角下部文字
            current_y = bottom_right_y + 10  # 当前y坐标
            font_size_bottom_right_bottom = 20  # 右下角下部文字大小
            try:
                font_bottom_right_bottom = ImageFont.truetype(font_path, font_size_bottom_right_bottom)  # 加载字体
            except IOError:
                font_bottom_right_bottom = ImageFont.load_default()  # 使用默认字体

            # 计算实际可用文本宽度（左右各保留10像素边距）
            max_text_width = bottom_right_width - 20  # 根据实际容器宽度调整

            for line in bottom_right_bottom_info:  # 遍历右下角下部信息
                # 分割文本为多行
                wrapped_lines = split_line_into_multiple(str(line), font_bottom_right_bottom, max_text_width)
                
                for wrapped_line in wrapped_lines:
                    draw_text_with_shadow(draw, wrapped_line, font_bottom_right_bottom, 
                                        bottom_right_x + 10, current_y, text_color2, shadow_color)
                    # 更新y坐标（字号 + 行间距3）
                    current_y += font_size_bottom_right_bottom + 3    
        else:
        # 绘制用户信息(竖版)
            # 头像居中上方
            avatar_x = avatar_size - 100
            avatar_y = margin + 25

            # 用户信息
            text_x = margin
            text_y = avatar_y + margin
            line_spacing = 5
            current_y = text_y
            font_size_user_info = 30 # 用户信息文字大小
            try:
                font_user_info = ImageFont.truetype(font_path, font_size_user_info) # 加载字体
            except IOError:
                font_user_info = ImageFont.load_default() # 使用默认字体

            # Draw the first two lines
            for i in range(2):
                line = user_info[i]
                text_width = draw.textlength(line, font=font_user_info)
                x = (card_width - text_width) // 2
                draw_text_with_shadow(draw, line, font_user_info, x, current_y, light_gray_color, shadow_color,shadow=True)
                current_y += font_size_user_info + line_spacing

            # Gradient color for the third line
            text = user_info[2]  # Get the third line text
            gradient_colors = [(255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255)]  # Red -> Green -> Blue # 渐变颜色
            start_x = margin + (card_width - 2 * margin - sum([draw.textlength(char, font=font_user_info) for char in text])) / 2 # calculate the x position to start drawing gradient text
            gradient_x = start_x
            gradient_y = current_y
            draw_gradient_text(draw, text, font_user_info, gradient_x, gradient_y, gradient_colors, shadow_color) # 绘制渐变色

            # 底部信息
            bottom_height = card_height // 8
            bottom_margin = 10 # 修改底部信息margin
            bottom_y = card_height - 2*bottom_height - 2 * bottom_margin # 修改底部信息y坐标

            # 各个信息栏位的宽度，平均分配
            info_width = (card_width - 2 * bottom_margin) // 2 - 20 # 修改为平分2栏

            # 上方信息
            top_info_x = bottom_margin + 10
            top_info_width = card_width - 2 * bottom_margin-20
            draw_rounded_blur_box(text_layer, top_info_x, bottom_y, top_info_width, bottom_height-10, corner_radius, blur_radius, opacity)

            font_size_bottom_left = 24
            try:
                font_bottom_left = ImageFont.truetype(font_path, font_size_bottom_left) # 加载字体
            except IOError:
                font_bottom_left = ImageFont.load_default() # 使用默认字体

            current_y = bottom_y + 10
            for line in bottom_left_info:
                draw_text_with_shadow(draw, line, font_bottom_left, top_info_x + 10, current_y, text_color2, shadow_color)
                current_y += font_size_bottom_left + line_spacing

            # 下方左侧信息
            bottom_left_x = bottom_margin
            bottom_left_y = card_height - bottom_height - bottom_margin
            draw_rounded_blur_box(text_layer, bottom_left_x+10, bottom_left_y, info_width, bottom_height-10, corner_radius, blur_radius, opacity)

            font_size_bottom_center = 24
            try:
                font_bottom_center = ImageFont.truetype(font_path, font_size_bottom_center)  # 加载字体
            except IOError:
                font_bottom_center = ImageFont.load_default()  # 使用默认字体

            current_y = bottom_left_y + 0
            for line in bottom_right_top_info:
                draw_text_with_shadow(draw, line, font_bottom_center, bottom_left_x + 20, current_y, text_color2, shadow_color)
                current_y += font_size_bottom_center + line_spacing


            # 下方右侧信息
            bottom_right_x = card_width - bottom_margin - info_width
            draw_rounded_blur_box(text_layer, bottom_right_x-10, bottom_left_y, info_width, bottom_height-10, corner_radius, blur_radius, opacity)

            font_size_bottom_right = 24
            try:
                font_bottom_right = ImageFont.truetype(font_path, font_size_bottom_right)
            except IOError:
                font_bottom_right = ImageFont.load_default()

            # 计算实际可用文本宽度（左右各保留10像素边距）
            max_text_width = info_width - 20

            current_y = bottom_left_y + 10
            for line in bottom_right_bottom_info:
                # 分割文本为多行
                wrapped_lines = split_line_into_multiple(str(line), font_bottom_right, max_text_width)
                
                for wrapped_line in wrapped_lines:
                    draw_text_with_shadow(draw, wrapped_line, font_bottom_right, 
                                        bottom_right_x + 10, current_y, text_color2, shadow_color)
                    current_y += font_size_bottom_right + line_spacing


        # 4. 合并图层
        if not is_portrait:
            background.paste(avatar, (margin, margin), avatar) # 粘贴头像
        else:
            background.paste(avatar, (avatar_x, avatar_y), avatar)
        background = Image.alpha_composite(background, text_layer)  # 将文字图层覆盖到背景上

        # 确保目标目录存在
        output_dir = os.path.dirname(output_path)  # 从完整路径中提取目录部分
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)  # 如果目录不存在，则创建它

        # 5. 保存图片
        background.save(output_path, "PNG")  # 直接保存为 PNG
        print(f"签到图已保存到: {output_path}")
        return output_path
    except FileNotFoundError as e:
        print(f"文件未找到错误: {e}")
    except Exception as e:
        print(f"发生错误!!!: {e}")

if __name__ == "__main__":
    # 示例用法
    # 1. 准备头像图片 (替换为你的头像路径或URL)
    avatar_path = "tx.jpg"  # 确保图片存在

    # 2. 准备用户信息 (替换为你想显示的信息)
    user_info = [
        "3079233608",
        "群主",
        "城城城城城城"
    ]
    # 3. 准备底部信息 (替换为你想要的信息)
    bottom_left_info = [
        "签到时间: 2025-3-24 01:09:32 星期三",
        "金币: 10000",
        "三行",
        "四行"
    ]
    bottom_right_top_info = [
        "一行",
        "二行",
        "三行",
        "三行"
    ]
    bottom_right_bottom_info = [
        "啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊啊",
        "2",
        "一行一行一行",
        # "三行啊一行一行"
    ]

    # 4.  准备背景图片文件夹 (确保文件夹存在且包含图片)
    image_folder = "backgrounds"  # 创建一个名为 backgrounds 的文件夹，并放入一些图片

    # 5.  指定字体文件路径 (替换为你电脑上的字体文件路径)
    font_path = "font.ttf"  # 例如:  "C:/Windows/Fonts/msyh.ttc" (微软雅黑),  "/System/Library/Fonts/PingFang.ttc" (苹方)

    # 创建一些示例背景图片
    if not os.path.exists("images"):
        os.makedirs("images")

    # 检查 backgrounds 文件夹是否为空，如果为空，则填充一些默认的白色背景图片
    if not os.listdir("backgrounds"):
        print("backgrounds 文件夹为空，正在创建默认背景图片...")
        default_bg = Image.new("RGB", (630, 1200), color="white")
        default_bg.save("backgrounds/default_bg.png")

    # 如果不存在头像，则创建默认的头像
    if not os.path.exists(avatar_path):
        print("avatar.png 不存在, 正在创建默认头像")
        default_avatar = Image.new("RGB", (150, 150), color="lightgray")
        default_avatar.save(avatar_path)


    # 调用函数生成签到图
    create_check_in_card(
        avatar_path=avatar_path,                            # 头像路径
        user_info=user_info,                                # 用户信息
        bottom_left_info=bottom_left_info,                  # 左下角信息
        bottom_right_top_info=bottom_right_top_info,        # 右下角上部信息
        bottom_right_bottom_info=bottom_right_bottom_info,  # 右下角下部信息
        output_path="check_in_card.png",                    # 输出文件名
        image_folder=image_folder,                          # 背景图片文件夹
        font_path=font_path                                 # 字体文件路径
    )
