from nonebot import logger, require, get_bot
from nonebot.adapters.qzone import Message, MessageSegment

require("nonebot_plugin_apscheduler")

import base64
import datetime
import ujson as json
from pathlib import Path

from nonebot_plugin_apscheduler import scheduler

from utils.config import Config
from utils.database import database_connect, database_unpublished_post_init



async def to_uri(path):
    with open(path, "rb") as img:
        binary = img.read()
    code = base64.b64encode(binary).decode("utf-8")
    return f"data:image/png;base64,{code}"


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
        max_post = Config.get_value("confession", "max_post")
        for post in data_list:
            # 帖子效果图占一位
            img_number += 1
            # 一个视频占一位
            if post["have_video"]:
                img_number += post["video_number"]
            if img_number <= max_post or post_number == 0:
                post_number += 1
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
        else:   
            # 处理帖子数据并发送动态
            msg_data = Message()
            for post in data_list[0:post_number]:
                post_id = post["id"]
                row = await conn.fetchrow("SELECT path_pic_post, path_post_data FROM approved_post WHERE id=$1", post_id)
                path_pic_post, path_post_data = row
                path_post_data = Path(path_post_data)
                path_pic_post = Path(path_pic_post).as_uri()
                # 消息添加帖子效果图
                msg_data += MessageSegment.image(await to_uri(path_pic_post))
                # 消息添加视频
                if post["have_video"]:
                    with open(path_post_data, "w", encoding="utf-8") as f:
                        post_data = json.loads(f.read())
                    for c in post_data:
                        path_video = Path(c["data"]["file"]).as_uri()
                        if c["type"] == "video":
                            msg_data += MessageSegment.video(await to_uri(path_video))

            # 动态发送尝试三次
            for i in range(3):
                try:
                    bot = get_bot("qzone")
                    bot.send(msg_data)
                    break
                except:
                    if i == 2:
                        logger.error("发送帖子失败")
                        return None
            
            # 数据库信息更新
            for post in data_list[0:post_number]:
                await conn.execute("DELETE FROM unpublished_post WHERE id=$1", post["id"])
                await conn.execute("UPDATE approved_post SET status_post=$1 WHERE id=$2", True, post["id"])

            #删除已发送的帖子信息，继续循环处理剩余数据
            del data_list[:post_number]
    await conn.close()
            

# 定时检测并发送动态
scheduler.add_job(
    post, "interval", minutes=10, id="active_post"
)