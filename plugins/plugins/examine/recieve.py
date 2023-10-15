from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent

from utils.database import (
    database_connect,
    database_approved_post_init, 
    database_audit_init,
    database_disapproved_post_init,
    database_unpublished_post_init
)
from utils.permission import AUDIT
from utils.config import Config


examine_pass = on_command(
    "通过",
    aliases={"是", "1"},
    permission=AUDIT,
    block=True,
    priority=11
)


examine_nopass = on_command(
    "不通过",
    aliases={"否", "2"},
    permission=AUDIT,
    block=True,
    priority=11
)


@examine_pass.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    # 初始化数据库 audit 表
    await database_audit_init()

    # 连接数据库
    conn = await database_connect()

    audit_id = int(event.get_session_id())

    # 获取数据库信息
    row = await conn.fetchrow("SELECT is_examining, examining_post_id FROM audit WHERE id = $1", audit_id)
    is_examining = bool(row[0])
    examining_post_id = str(row[1])

    if not is_examining:
        await examine_pass.finish("当前无待审核的帖子")
    
    # 将数据库里对应的帖子信息存储到字典中
    row = await conn.fetchrow("SELECT * FROM unverified_post WHERE id=$1", examining_post_id)
    post_data = dict(row)

    # 初始化数据库 approved_post 表
    await database_approved_post_init()
    # 初始化数据库 unpublished_post 表
    await database_unpublished_post_init()

    # 数据库数据更新
    await conn.execute(
        """INSERT INTO approved_post (id, commit_time, user_id, path_pic_post, path_post_data, post_type, status_anon, status_post, have_video, video_number)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
        examining_post_id, post_data["commit_time"], post_data["user_id"], post_data["path_pic_post"], post_data["path_post_data"], post_data["post_type"], post_data["status_anon"], post_data["status_post"], post_data["have_video"], post_data["video_number"]
    )
    await conn.execute(
        """INSERT INTO unpublished_post (id, commit_time, have_video, video_number)
        VALUES ($1, $2, $3, $4)""",
        examining_post_id, post_data["commit_time"], post_data["have_video"], post_data["video_number"]
    )
    await conn.execute("DELETE FROM unverified_post WHERE id=$1", examining_post_id)
    await conn.execute("UPDATE audit SET is_examining=$1, examining_post_id=$2 WHERE id=$3", False, None, audit_id)
    await conn.close()

    await examine_pass.send(f"帖子id: {examining_post_id} ,通过")
    
    max_delay_time = Config.get_value("confession", "max_delay_time")
    await bot.send_private_msg(
        user_id=post_data["user_id"],
        message=f"帖子id: {examining_post_id} ,审核通过\n帖子将在 {str(max_delay_time)} 分钟内发送至墙"
    )


@examine_nopass.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    # 初始化数据库 audit 表
    await database_audit_init()

    # 连接数据库
    conn = await database_connect()

    audit_id = int(event.get_session_id())
    # 获取数据库信息
    row = await conn.fetchrow("SELECT is_examining, examining_post_id FROM audit WHERE id = $1", audit_id)
    is_examining = bool(row[0])
    examining_post_id = str(row[1])

    if not is_examining:
        await examine_pass.finish("当前无待审核的帖子")

    # 将数据库里对应的帖子信息存储到字典中
    row = await conn.fetchrow("SELECT * FROM unverified_post WHERE id=$1", examining_post_id)
    post_data = dict(row)

    # 初始化数据库 disapproved_post 表
    await database_disapproved_post_init()

    # 数据库数据更新
    await conn.execute(
        """INSERT INTO disapproved_post (id, commit_time, user_id, path_pic_post, path_post_data, post_type, status_anon, have_video, video_number)
        VALUES ($1, $1, $3, $4, $5, $6, $7, $8, $9)""",
        examining_post_id, post_data["commit_time"], post_data["user_id"], post_data["path_pic_post"], post_data["path_post_data"], post_data["post_type"], post_data["status_anon"], post_data["have_video"], post_data["video_number"]
    )
    await conn.execute("DELETE FROM unverified_post WHERE id=$1", examining_post_id)
    await conn.execute("UPDATE audit SET is_examining=$1, examining_post_id=$2 WHERE id=$3", False, None, audit_id)
    await conn.close()

    await examine_pass.send(f"帖子id: {examining_post_id} ,不通过")

    await bot.send_private_msg(
        user_id=post_data["user_id"],
        message=f"帖子id: {examining_post_id} ,审核不通过"
    )
