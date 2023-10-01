from pathlib import Path

import ujson as json
from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER


admin_list = on_command(
    '审核组管理员列表',
    permission=SUPERUSER,
    block=True,
    priority=10
)


admin_add = on_command(
    '添加审核组管理员',
    permission=SUPERUSER,
    block=True,
    priority=10
)


admin_del = on_command(
    '删除审核组管理员',
    permission=SUPERUSER,
    block=True,
    priority=10
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
    admin_data.append(int(id))
    with open(admin_data_file, "w", encoding="utf-8") as f:
        admin_data = json.dump(admin_data, f)
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
        await admin_del.finish("删除成功")
    if str(id) in admin_data:
        admin_data.remove(str(id))
        with open(admin_data_file, "w", encoding="utf-8") as f:
            json.dump(admin_data, f)
        await admin_del.finish("删除成功")
    await admin_del.finish(f"id为 {str(id)} 的用户不在审核组管理员中")
