from nonebot import logger, require, get_driver
from nonebot.adapters.onebot.v11 import Message, MessageSegment

require("nonebot_plugin_apscheduler")

import datetime
from pathlib import Path

import ujson as json
from nonebot_plugin_apscheduler import scheduler

from utils.config import Config
from utils.api_qq import send_private_msg

from utils.database import database_connect, database_audit_init, database_unverified_post_init


async def push_handle(auditor, post_id):
    '''
    将指定帖子推送给指定审核人员
    '''
    # 连接数据库
    conn = await database_connect()

    # 获取帖子数据
    row = await conn.fetchrow("SELECT user_id, path_pic_post, path_post_data, have_video FROM unverified_post WHERE id = $1", post_id)
    path_pic_post = Path(row[1])
    path_post_data = Path(row[2])
    have_video = bool(row[3])

    # 有视频就发视频
    if have_video:
        post_videos = []
        with open(path_post_data, "r", encoding="utf-8") as f:
            post_data = json.load(f)
        for segment in post_data:
            if segment["type"] == "video":
                post_videos.append({
                    "url": segment["data"]["url"],
                    "file": Path(segment["data"]["file"])
                })
        for post_video in post_videos:
            # 尝试发送视频文件3次，失败就发送视频链接
            for i in range(3):
                try:
                    video_file = post_video["file"]
                    await send_private_msg(
                        user_id=auditor,
                        message=MessageSegment.video(video_file, timeout=100)
                    )
                    break
                except Exception as e:
                    if i == 2:
                        video_file = post_video["file"]
                        video_url = post_video["url"]
                        logger.error(f"发送视频失败,视频所属帖子ID: {post_id} ,视频地址: {str(video_file)} ,报错信息: {str(e)}")
                        await send_private_msg(
                                user_id=auditor,
                                message=f"发送视频失败,视频所属帖子ID: {post_id} \n视频链接: {video_url}\n如果持续出现该问题请联系机器人维护者"
                            )

    # 发帖子效果图    
    send_message = MessageSegment.image(path_pic_post, timeout=20) + Message(f"帖子ID: {post_id} ,审核通过请回复 通过/是/1 ,不通过请回复 不通过/否/2")
    # 尝试发送文字和帖子效果图3次，失败就结束此次推送
    for i in range(3):
        try:
            await send_private_msg(
                user_id=auditor,
                message=send_message
            )
            break
        except Exception as e:
            if i == 2:
                logger.error(f"帖子效果图发送失败,帖子推送失败,帖子ID: {post_id} ,报错信息: {str(e)}")
                await send_private_msg(
                    user_id=auditor,
                    message=f"帖子效果图发送失败,帖子推送失败。\n帖子ID: {post_id} ,如果问题重复出现请联系机器人维护者"
                )
                # 如果 other-error_alert 配置项为 True 就推送此次报错至机器人维护者(superusers)
                if Config.get_value("other", "error_alert"):
                    for superuser in list(get_driver().config.superusers):
                        await send_private_msg(
                            user_id=int(superuser),
                            message=f"帖子效果图发送失败,帖子推送失败。\n帖子ID: {post_id} ,报错信息: {str(e)}"
                        )
                return None
    
    # 更新数据库信息
    await conn.execute(
        "UPDATE audit SET is_examining = True WHERE id = $1", auditor)
    await conn.execute(
        "UPDATE audit SET examining_post_id = $1 WHERE id = $2",
        post_id, auditor
    )
    await conn.execute(
        "UPDATE unverified_post SET examine_begin_time = $1 WHERE id = $2",
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), post_id
    )
    row = await conn.fetchrow("SELECT auditor_number FROM unverified_post WHERE id = $1", post_id)
    auditor_number = row[0] + 1
    await conn.execute("UPDATE unverified_post SET auditor_number = $1 WHERE id = $2", auditor_number, post_id)
    await conn.close()


async def push():
    '''
    帖子推送给审核组
    '''
    # 初始化数据库中的 audit 表
    await database_audit_init()

    # 连接数据库
    conn = await database_connect()

    # 查询audit表的行数
    row = await conn.fetchrow("SELECT COUNT(*) FROM audit")
    # 获取行数并判断是否为0
    have_data = row[0] > 0
    if not have_data:
        await conn.close()
        logger.warning("审核组无成员,无法完成帖子审核")
        for superuser in list(get_driver().config.superusers):
            await send_private_msg(
                    user_id=int(superuser),
                    message="审核组无成员,无法完成帖子审核"
                )
        # 审核组无成员时结束处理
        return None
    
    rows = await conn.fetch("SELECT id FROM audit WHERE is_examining = False")
    if rows:
        free_audit = [row[0] for row in rows]
    else:
        await conn.close()
        # 审核组无空闲成员时结束处理
        return None

    # 初始化数据库 unverified_post 表
    await database_unverified_post_init()
    
    # 查询 unverified_post 表的行数
    row = await conn.fetchrow("SELECT COUNT(*) FROM unverified_post")
    # 获取行数并判断是否为0
    have_data = row[0] > 0
    if not have_data:
        await conn.close()
        # 无审核的帖子时结束处理
        return None
    
    # 获取 unverified_post 表中的数据至字典
    rows = await conn.fetch("SELECT * FROM unverified_post ORDER BY commit_time ASC")
    data_list = [dict(row) for row in  rows]

    examine_ones_own = Config.get_value("confession", "examine_ones_own")

    # 帖子发布时间越早越优先处理
    for post in data_list:
        add_auditor_number = int(post["max_auditor_number"]) - int(post["auditor_number"])
        if not add_auditor_number:
            pass
        for _ in range(add_auditor_number):
            if not free_audit:
                await conn.close()
                # 审核组无空闲成员时结束处理
                return None
            if examine_ones_own:
                auditor = free_audit.pop()
                await push_handle(auditor, post["id"])
            else:
                # 审核员不能审核自己的帖子
                if free_audit[-1] != post["user_id"]:
                    auditor = free_audit.pop()
                    await push_handle(auditor, post["id"])
                else:
                    if len(free_audit) == 1:
                        break
                    else:
                        last_auditor = free_audit.pop()
                        free_audit.insert(0, last_auditor)


async def post_data_update():
    '''
    更新帖子相关数据
    '''
    # 初始化数据库 unverified_post 表
    await database_unverified_post_init()

    # 连接数据库
    conn = await database_connect()

    # 查询unverified_post表的行数
    row = await conn.fetchrow("SELECT COUNT(*) FROM unverified_post")
    # 获取行数并判断是否为0
    have_data = row[0] > 0
    if not have_data:
        # 无审核的帖子时结束处理
        return None
    
    # 获取unverified_post表中的数据至字典
    rows = await conn.fetch("SELECT * FROM unverified_post ORDER BY commit_time ASC")
    data_list = [dict(row) for row in rows]

    # 帖子最大同时审核人数随审核组未审核时间动态变化
    for post in data_list:
        if post["auditor_number"]:
            examine_begin_time = datetime.datetime.strptime(post["examine_begin_time"], "%Y-%m-%d %H:%M:%S")
            time_now = datetime.datetime.now()
            time_difference = time_now - examine_begin_time
            minutes_difference = time_difference.total_seconds() / 60
            minute = 5
            n = 1
            if minutes_difference < 5:
                return None
            while True:
                minute = minute**n
                if minutes_difference <= minute:
                    break
                n += 1
            await conn.execute(
                "UPDATE unverified_post SET max_auditor_number = $1 WHERE id = $2",
                n, post["id"]
            )
    await conn.close()
            

# 定时推送帖子
scheduler.add_job(
    push, "interval", minutes=10, id="active_push"
)


# 定时更新帖子相关数据
scheduler.add_job(
    post_data_update, "interval", minutes=5, id="post_data_update"
)
