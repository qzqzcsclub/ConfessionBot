from nonebot import logger, on_command, require

require("nonebot_plugin_htmlrender")

import io
import sqlite3
from pathlib import Path

import filetype
import httpx
import ujson as json
from nonebot.adapters.onebot.v11 import Bot, Event, Message, MessageSegment, PrivateMessageEvent
from nonebot.params import CommandArg, Received
from nonebot.typing import T_State
from nonebot_plugin_htmlrender import md_to_pic
from PIL import Image

from plugins.plugins.examine import push
from utils.database import database_unverified_post_init


post = on_command(
    "发帖",
    block=True,
    priority=10
)


@post.handle()
async def _(event: PrivateMessageEvent, state: T_State, args: Message = CommandArg()):
    '''
    发帖命令响应器
    '''
    if not args:
        state["post_type"] = 0 # post_type默认为0(对话)
        state["status_anon"] = 2 # status_anon默认为2(实名)
    args.include("text")

    if args[0].data["text"] == "对话":
        state["post_type"] = 0
    elif args[0].data["text"] == "文章":
        state["post_type"] = 1
    else:
        bad_arg = args[0].data["text"]
        await post.finish(f"参数“{bad_arg}”不合法，应为“对话”或“文章”")

    if args[1].data["text"] == "匿名":
        state["status_anon"] = 0
    elif args[1].data["text"] == "半实名":
        state["status_anon"] = 1
    elif args[1].data["text"] == "实名":
        state["status_anon"] = 2
    else:
        bad_arg = args[1].data["text"]
        await post.finish(f"参数“{bad_arg}”不合法，应为“匿名”或“半实名”或“实名”")


@post.receive("handle")
async def _(bot: Bot, event: PrivateMessageEvent, state: T_State, received_event: Event = Received("handle")):
    '''
    帖子消息数据响应器，接收数据后处理数据
    '''
    msg = received_event.get_message()
    post_msg = state.get("post_msg", "")
    if state["post_type"] == 0:
        if "text" in msg:
            if msg[0].data["text"] == "结束":
                await post.send("开始处理数据...")
                await post_handle(bot, event, state)
            elif msg[0].data["text"] == "取消":
                await post.finish("已取消操作...")
        else:
            post_msg += msg
            state["post_msg"] = post_msg
            await post.reject()
    elif state["post_type"] == 1:
        if "text" in msg:
            if msg[0].data["text"] == "取消":
                await post.finish("已取消操作...")
        post_msg = msg
        state["post_msg"] = post_msg
        await post.send("开始处理数据...")
        await post_handle(bot, event, state)


@post.receive("confirm")
async def _(event: PrivateMessageEvent, state: T_State, received_event: Event = Received("confirm")):
    '''
    发帖确认响应器，确认后上传数据至数据库
    '''
    msg = received_event.get_message()
    if "text" in msg:
        if msg[0].data["text"] == "提交":
            # 将帖子数据保存到数据库
            await database_unverified_post_init()
            database_path = Path() / "post" / "database" / "database.db"
            database_path.parent.mkdir(exist_ok=True, parents=True)
            conn = sqlite3.connect(database_path)
            c = conn.cursor()
            c.execute(
                """INSERT INTO unverified_post (id, commit_time, examine_begin_time, user_id, path_pic_post, path_post_data, post_type, status_anon, auditor_number, max_auditor_number, have_video, video_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (state["post_id"], event.time, None, event.get_user_id(), state["path_pic_post"], state["path_post_data"], state["post_type"], state["status_anon"], 0, 1, state["have_video"], state["video_number"])
            )
            conn.commit()
            conn.close()
            await post.send("帖子提交审核成功，审核通过后帖子会发布到空间，请耐心等待，谢谢配合！")
            await push()
    await post.finish("已取消操作...")


async def post_handle(bot, event, state):
    '''
    帖子数据处理函数
    '''
    data_md = ""
    user_id = event.get_user_id()
    user_name = bot.call_api("get_stranger_info", user_id = int(user_id))["nickname"]

    # 生成帖子的 id
    database_path = Path() / "post" / "database" / "database.db"
    database_path.parent.mkdir(exist_ok=True, parents=True)
    conn = sqlite3.connect(database_path)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS post_info (
            used_id INTEGER
            )"""
    )
    c.execute("SELECT used_id FROM post_info")
    row = c.fetchone()
    if row is None:
        post_id = 1
    else:
        post_id = int(row[0]) + 1
    c.execute(
        """UPDATE post_info SET used_id = ?""", 
        (post_id,)
    )
    post_id = str(post_id)
    state["post_id"] = post_id
    conn.commit()
    conn.close()

    if state["status_anon"] == 0:
        data_md += "***FROM： 匿名用户***\n\n---\n\n"
    elif state["status_anon"] == 1:
        data_md += f'***FROM：*** <img src="https://q1.qlogo.cn/g?b=qq&nk={user_id}&s=640" style="width:38px; float:right; margin-right:225px;border-radius:50%">\n\n---\n\n'
    elif state["status_anon"] == 2:
        data_md += f'***FROM:  {user_name}({user_id})***\n\n---\n'
    
    # 处理帖子的消息数据
    data_msg = []
    have_video = False
    video_number = 0
    if state["post_type"] == 0:
        for segment in state["post_msg"]:
            if segment.type == "text":
                msg_text = segment.data["text"]
                data_md += f"\n- **{msg_text}**"
                msg_info = {
                    "type": "text",
                    "data":{
                        "text": segment.data["text"]
                    }
                }
                data_msg.append(msg_info)

            elif segment.type == "image":
                msg_image = segment.data["url"]
                msg_image_name = segment.data["file"].replace(".image", "")
                data_md += f'\n\n<div style="text-align: left;"><img src=" {msg_image} " width="150"></div>\n'
                msg_info = {}
                for i in range(3):
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(msg_image)
                            if resp.status_code == 200:
                                kind = filetype.guess(resp.content)
                                if kind:
                                    extension = kind.extension
                                else:
                                    extension = "jpg" # 默认使用.jpg扩展名
                                image_file_name = f"{msg_image_name}.{extension}"
                                path_image = Path() / "data" / "post" / post_id / image_file_name
                                path_image.parent.mkdir(exist_ok=True, parents=True)
                                with open(path_image, 'wb') as f:
                                    f.write(resp.content)
                                msg_info = {
                                    "type": "image",
                                    "data":{
                                        "url": segment.data["url"],
                                        "file": str(path_image)
                                    }
                                }
                                break
                    except Exception as e:
                        if i == 2:
                            logger.error(f"下载图片 {msg_image} 出错,跳过下载: {str(e)}")
                if not msg_info:
                    msg_info = {
                        "type": "image",
                        "data":{
                            "url": segment.data["url"],
                            "file": None
                        }
                    }
                data_msg.append(msg_info)
            
            elif segment.type == "video":
                have_video = True
                video_number += 1
                msg_video = segment.data["url"]
                msg_video_name = segment.data["file"].replace(".video", "")
                data_md += f'\n\n<div style="display: flex; justify-content: flex-start;"><video src=" {msg_video} " width="150" controls></video></div>\n'
                msg_info = {}
                for i in range(3):
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(msg_video)
                            if resp.status_code == 200:
                                kind = filetype.guess(resp.content)
                                if kind:
                                    extension = kind.extension
                                else:
                                    extension = "mp4" # 默认使用.mp4扩展名
                                video_file_name = f"{msg_video_name}.{extension}"
                                path_video = Path() / "data" / "post" / post_id / video_file_name
                                path_video.parent.mkdir(exist_ok=True, parents=True)
                                with open(path_video, 'wb') as f:
                                    f.write(resp.content)
                                msg_info = {
                                    "type": "video",
                                    "data":{
                                        "url": segment.data["url"],
                                        "file": str(path_video)
                                    }
                                }
                                break
                    except Exception as e:
                        if i == 2:
                            logger.error(f"下载视频 {msg_video} 出错,跳过下载: {str(e)}")
                if not msg_info:
                    msg_info = {
                        "type": "video",
                        "data":{
                            "url": segment.data["url"],
                            "file": None
                        }
                    }
                data_msg.append(msg_info)

    elif state["post_type"] == 1:
        for segment in state["post_msg"]:
            if segment.type == "text":
                msg_text = segment.data["text"]
                data_md += f"\n**{msg_text}**"
                msg_info = {
                    "type": "text",
                    "data":{
                        "text": segment.data["text"]
                    }
                }
                data_msg.append(msg_info)
            elif segment.type == "image":
                msg_image = segment.data["url"]
                msg_image_name = segment.data["file"].replace(".image", "")
                data_md += f'\n\n<div style="text-align: left;"><img src=" {msg_image} " width="150"></div>\n'
                msg_info = {}
                for i in range(3):
                    try:
                        async with httpx.AsyncClient() as client:
                            resp = await client.get(msg_image)
                            if resp.status_code == 200:
                                kind = filetype.guess(resp.content)
                                if kind:
                                    extension = kind.extension
                                else:
                                    extension = "jpg" # 默认使用.jpg扩展名
                                image_file_name = f"{msg_image_name}.{extension}"
                                path_image = Path() / "data" / "post" / post_id / image_file_name
                                path_image.parent.mkdir(exist_ok=True, parents=True)
                                with open(path_image, 'wb') as f:
                                    f.write(resp.content)
                                msg_info = {
                                    "type": "image",
                                    "data":{
                                        "url": segment.data["url"],
                                        "file": str(path_image)
                                    }
                                }
                                break
                    except Exception as e:
                        if i == 2:
                            logger.error(f"下载图片 {msg_image} 出错,跳过下载: {str(e)}")
                if not msg_info:
                    msg_info = {
                        "type": "image",
                        "data":{
                            "url": segment.data["url"],
                            "file": None
                        }
                    }
                data_msg.append(msg_info)
    data_md += "\n\n---"
    state["have_video"] = have_video
    state["video_number"] = video_number
    have_big_image = False
    for segment in state["post_msg"]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(segment.data["url"])
            image_data = resp.content
        image = Image.open(io.BytesIO(image_data))
        width, _ = image.size
        image.close()
        if width >= 640:
            have_big_image = True
            msg_image = segment.data["url"]
            data_md += f'\n\n<div style="text-align: left;"><img src=" {msg_image} "></div>'
    if have_big_image:
        data_md += "\n\n---"
    data_md += f"\n\n***ID: {post_id}***"
    
    # 生成帖子效果图
    pic = await md_to_pic(md=data_md, width=400)
    path_pic_post = Path() / "data" / "post" / post_id / "post.png"
    path_post_data = Path() / "data" / "post" / post_id / "post.json"
    state["path_pic_post"] = str(path_pic_post)
    state["path_post_data"] = path_post_data
    a = Image.open(io.BytesIO(pic))
    a.save(path_pic_post, format="PNG")

    # 保存帖子消息数据
    with open(path_post_data, "w", encoding="utf-8") as f:
        json.dump(data_msg, f)

    # 保存帖子效果图
    reply_msg = MessageSegment.image(pic) + MessageSegment.text("帖子效果图生成完毕（视频将会在墙另外发出），确认提交审核请发送“提交”，发送其他任意消息取消")
    await post.send(reply_msg)
