from nonebot import logger, require, get_bot, get_driver
from nonebot.adapters.qzone import MessageSegment

require("nonebot_plugin_apscheduler")

import os
import base64
import datetime
import ujson as json
from pathlib import Path

from nonebot_plugin_apscheduler import scheduler

from utils.config import Config
from utils.api_qq import send_private_msg
from utils.database import database_connect, database_unpublished_post_init



async def image_to_uri(path, image_type: str):
    with open(path, "rb") as img:
        binary = img.read()
    code = base64.b64encode(binary).decode("utf-8")
    return f"data:image/{image_type};base64,{code}"


async def video_to_uri(path, video_type: str):
    with open(path, "rb") as video:
        binary = video.read()
    code = base64.b64encode(binary).decode("utf-8")
    return f"data:video/{video_type};base64,{code}"


async def post():
    '''
    检测并发送动态
    '''
    # 连接数据库
    conn = await database_unpublished_post_init()
    conn = await database_connect()

    # 获取 unpublished_post 表中的数据到字典中
    rows = await conn.fetch("SELECT * FROM unpublished_post ORDER BY commit_time ASC")
    data_list = [dict(row) for row in rows]
    
    # 循环以确保所有符合条件的帖子发出
    while data_list:
        # 处理得到该次动态消息占位数和帖子数
        img_number = 0
        post_number = 0
        posts_occupancy = []
        max_post = Config.get_value("confession", "max_post")
        for post in data_list:
            # 帖子效果图占一位
            img_number += 1
            post_occupancy = 1
            # 一个视频占一位
            if post["have_video"]:
                img_number += post["video_number"]
                post_occupancy += post["video_number"]
            if img_number <= max_post or post_number == 0:
                post_number += 1
                posts_occupancy.append(post_occupancy)
            else:
                break
        
        # 如果占位数不够就进行时间检查
        if img_number <= max_post:
            # 时间检查
            post_time = data_list[0]["commit_time"]
            post_time = datetime.datetime.strptime(post_time, "%Y-%m-%d %H:%M:%S")
            time_now = datetime.datetime.now()
            time_difference = time_now - post_time
            minutes_difference = int(time_difference.total_seconds() / 60)
            max_delay_time = Config.get_value("confession", "max_delay_time")
            # 如果没到达最长等待时间就结束处理
            if minutes_difference < max_delay_time:
                return None
            
        bot = get_bot("qzone_bot")
        if not await bot.query():
            logger.warning("空间未登录无法发送帖子")
            # 如果 other-error_alert 配置项为 True 就推送空间未登录的问题至机器人维护者(superusers)
            # 为了防止频繁打扰机器人维护者(superusers)，该问题一天仅提醒一次
            if Config.get_value("other", "error_alert"):
                # 通过读写缓存文件中的信息实现问题一天仅提醒一次
                cache_file = Path() / "cache" / "info.json" # 缓存文件路径
                cache_file.parent.mkdir(exist_ok=True, parents=True)
                if not os.path.exists(cache_file):
                    with open(cache_file, 'w', encoding="utf-8") as f:
                        f.write("{}")
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                if "cache_update_time" not in cache:
                    cache["cache_update_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if "NotLoggedIn_alert" not in cache:
                    cache["NotLoggedIn_alert"] = False
                cache_day = datetime.datetime.strptime(cache["cache_update_time"], "%Y-%m-%d %H:%M:%S").day
                today = datetime.datetime.now().day
                if cache_day != today:
                    cache["NotLoggedIn_alert"] = False
                if not cache["NotLoggedIn_alert"]:
                    for superuser in list(get_driver().config.superusers):
                        await send_private_msg(
                            user_id=int(superuser),
                            message=f"空间未登录无法发送帖子\n(该问题一天仅提醒一次)"
                        )
                cache["cache_update_time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cache["NotLoggedIn_alert"] = True
                with open(cache_file, "w", encoding="utf-8") as f:
                    cache = json.dump(cache, f)
                return None

        # 处理帖子数据并发送动态
        msg_data = False
        for post in data_list[0:post_number]:
            post_id = post["id"]
            row = await conn.fetchrow("SELECT path_pic_post, path_post_data FROM approved_post WHERE id=$1", post_id)
            path_pic_post, path_post_data = row
            image_file_type = path_pic_post.split(".")[-1]
            path_post_data = Path(path_post_data)
            path_pic_post = Path(path_pic_post)
            # 消息添加帖子效果图
            if not msg_data:
                msg_data = MessageSegment.image(await image_to_uri(path_pic_post, image_file_type))
            else:
                msg_data += MessageSegment.image(await image_to_uri(path_pic_post, image_file_type))
            # 消息添加视频
            if post["have_video"]:
                with open(path_post_data, "r", encoding="utf-8") as f:
                    post_data = json.loads(f.read())
                for c in post_data:
                    path_video = Path(c["data"]["file"])
                    video_file_type = c["data"]["file"].split(".")[-1]
                    if c["type"] == "video":
                        msg_data += MessageSegment.video(await video_to_uri(path_video, video_file_type))

        # 动态发送尝试三次
        for i in range(3):
            try:
                qzone_post_id, qzone_source_ids= await bot.publish(msg_data)
                break
            except Exception as e:
                if i == 2:
                    logger.error("发送帖子失败",str(e))
                    raise
        
        # 数据库信息更新
        num = 0
        for post in data_list[0:post_number]:
            qzone_pic_id = qzone_source_ids[0]
            if posts_occupancy[num] != 1:
                qzone_source_id = str(qzone_source_ids[1:posts_occupancy[num]])
            else:
                qzone_source_id = None
            await conn.execute("DELETE FROM unpublished_post WHERE id=$1", post["id"])
            await conn.execute("UPDATE approved_post SET status_post=$1, qzone_post_id=$2, qzone_pic_id=$3, qzone_videos_id=$4 WHERE id=$5", True, qzone_post_id, qzone_pic_id, qzone_source_id, post["id"])
            qzone_source_ids = qzone_source_ids[posts_occupancy[num]:]
            num += 1

        #删除已发送的帖子信息，继续循环处理剩余数据
        del data_list[:post_number]
    await conn.close()
            

# 定时检测并发送动态
scheduler.add_job(
    post, "interval", minutes=1, id="active_post"
)