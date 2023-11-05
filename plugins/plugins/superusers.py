from pathlib import Path

import ujson as json
from nonebot import on_command, get_bot
from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from utils.database import database_audit_init


admin_list = on_command(
    '审核组管理员列表',
    permission=SUPERUSER,
    priority=10,
    block=True
)


admin_add = on_command(
    '添加审核组管理员',
    permission=SUPERUSER,
    priority=10,
    block=True
)


admin_del = on_command(
    '删除审核组管理员',
    permission=SUPERUSER,
    priority=10,
    block=True
)


qzone_login = on_command(
    '空间登录',
    aliases={"登录", "login"},
    permission=SUPERUSER,
    priority=10,
    block=True
)


qzone_logout = on_command(
    '空间登出',
    aliases={"登出", "logout"},
    permission=SUPERUSER,
    priority=10,
    block=True
)


qzone_query = on_command(
    '空间状态查询',
    aliases={"状态查询", "query"},
    permission=SUPERUSER,
    priority=10,
    block=True
)


@admin_list.handle()
async def _(event: PrivateMessageEvent):
    admin_data_file = Path() / "data" / "admin.json"
    admin_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(admin_data_file, "r", encoding="utf-8") as f:
        admin_data = json.load(f)
    if not admin_data:
        await admin_list.finish("审核组管理员无成员")
    msg = "审核组管理员列表："
    for id in admin_data:
        msg += f"\n{str(id)}"
    await admin_list.finish(msg)
    
    
@admin_add.handle()
async def _(event: PrivateMessageEvent, args: Message = CommandArg()):
    id = args[0].data["text"].strip()
    admin_data_file = Path() / "data" / "admin.json"
    admin_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(admin_data_file, "r", encoding="utf-8") as f:
        admin_data = json.load(f)
    for i in admin_data:
        if str(id) == str(i):
            await admin_add.finish(f"id为 {str(id)} 的用户已在审核组管理员中")
    admin_data.append(str(id))
    with open(admin_data_file, "w", encoding="utf-8") as f:
        admin_data = json.dump(admin_data, f)
    await database_audit_init()
    await admin_add.finish("添加成功")


@admin_del.handle()
async def _(event: PrivateMessageEvent, args: Message = CommandArg()):
    id = args[0].data["text"].strip()
    admin_data_file = Path() / "data" / "admin.json"
    admin_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(admin_data_file, "r", encoding="utf-8") as f:
        admin_data = json.load(f)
    if int(id) in admin_data:
        admin_data.remove(int(id))
        with open(admin_data_file, "w", encoding="utf-8") as f:
            json.dump(admin_data, f)
        await database_audit_init()
        await admin_del.finish("删除成功")
    if str(id) in admin_data:
        admin_data.remove(str(id))
        with open(admin_data_file, "w", encoding="utf-8") as f:
            json.dump(admin_data, f)
        await database_audit_init()
        await admin_del.finish("删除成功")
    await admin_del.finish(f"id为 {str(id)} 的用户不在审核组管理员中")


@qzone_login.handle()
async def _(event: PrivateMessageEvent):
    bot = get_bot("qzone_bot")
    qq_number = await bot.query()
    if qq_number:
        await qzone_login.finish(f"空间已登录，账号ID： {str(qq_number)}")
    else:
        await qzone_login.send("开始尝试空间登录，详见机器人控制台")
        await bot.login()


@qzone_logout.handle()
async def _(event: PrivateMessageEvent):
    bot = get_bot("qzone_bot")
    qq_number = await bot.query()
    if qq_number:
        await bot.logout()
        await qzone_logout.finish(f"空间已登出，账号ID： {str(qq_number)}")
    else:
        await qzone_logout.finish(f"空间未登录")


@qzone_query.handle()
async def _(event: PrivateMessageEvent):
    bot = get_bot("qzone_bot")
    qq_number = await bot.query()
    if qq_number:
        await qzone_query.finish(f"空间已登录，账号ID： {str(qq_number)}")
    else:
        await qzone_query.finish(f"空间未登录")
