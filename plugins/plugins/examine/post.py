from nonebot import logger, require, get_bot
from nonebot_adapters_qzone import Message, MessageSegment

require("nonebot_plugin_apscheduler")

import datetime
import sqlite3
from pathlib import Path

import ujson as json
from nonebot_plugin_apscheduler import scheduler

from utils.config import Config


async def post():
    '''
    检测并发送动态
    '''
    bot = get_bot("qzone")

    # 连接数据库
    database_path = Path() / "post" / "database" / "database.db"
    database_path.parent.mkdir(exist_ok=True, parents=True)
    conn = sqlite3.connect(database_path)
    c = conn.cursor()
    
    # 获取 unpublished_post 表中的数据到字典中
    c.execute("SELECT * FROM unpublished_post ORDER BY commit_time ASC")
    rows = c.fetchall()
    c.execute("PRAGMA table_info(unpublished_post)")
    columns = [column[1] for column in c.fetchall()]
    data_list = []
    for row in rows:
        data_dict = {}
        for i, value in enumerate(row):
            column_name = columns[i]
            data_dict[column_name] = value
        data_list.append(data_dict)
    
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
                c.execute("SELECT path_pic_post, path_post_data FROM approved_post WHERE id=?", (post_id,))
                row = c.fetchone()
                path_pic_post, path_post_data = row
                path_post_data = Path(path_post_data)
                path_pic_post = Path(path_pic_post).as_uri()
                # 消息添加帖子效果图
                msg_data += MessageSegment(
                    type="image",
                    data={
                        "file": str(path_pic_post)
                    }    
                )
                # 消息添加视频
                if post["have_video"]:
                    with open(path_post_data, "w", encoding="utf-8") as f:
                        post_data = json.loads(f.read())
                    for c in post_data:
                        path_video = Path(c["data"]["file"]).as_uri()
                        if c["type"] == "video":
                            msg_data += MessageSegment(
                                type="video",
                                file=str(path_video)
                            )

            # 动态发送尝试三次
            for i in range(3):
                try:
                    bot.send(msg_data)
                    break
                except:
                    if i == 2:
                        logger.error("发送帖子失败")
                        return None
            
            # 数据库信息更新
            for post in data_list[0:post_number]:
                c.execute("DELETE FROM unpublished_post WHERE id=?", (post["id"],))
                c.execute("UPDATE approved_post SET status_post=? WHERE id=?", (True, post["id"]))

            #删除已发送的帖子信息，继续循环处理剩余数据
            del data_list[:post_number]
            

# 定时检测并发送动态
scheduler.add_job(
    post, "interval", minutes=10, id="active_push"
)