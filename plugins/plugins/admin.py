from nonebot import on_command
from nonebot.adapters.onebot.v11 import PrivateMessageEvent, Message
from utils.permission import ADMIN
from utils.database import database_audit_init
from nonebot.params import CommandArg
import sqlite3
from pathlib import Path
import ujson as json


audit_list = on_command(
    '审核组列表',
    permission=ADMIN,
    block=True,
    priority=10
)


audit_add = on_command(
    '添加审核员',
    permission=ADMIN,
    block=True,
    priority=10
)


audit_del = on_command(
    '删除审核员',
    permission=ADMIN,
    block=True,
    priority=10
)


@audit_list.handle()
async def _(event: PrivateMessageEvent):
    # 初始化数据库中的 audit 表
    await database_audit_init()

    # 连接数据库
    database_examine_path = Path() / "post" / "database" / "database.db"
    database_examine_path.parent.mkdir(exist_ok=True, parents=True)
    conn = sqlite3.connect(database_examine_path)
    c = conn.cursor()

    # 获取 audit 表所有行的 id
    c.execute("SELECT id FROM audit")
    rows = c.fetchall()
    if not rows:
        await audit_list.finish("审核组无成员")
    id_list = [row[0] for row in rows]

    msg = "审核组列表："
    for id in id_list:
        msg += f"\n{str(id)}"
    await audit_list.finish(msg)
    
    
@audit_add.handle()
async def _(event: PrivateMessageEvent, args: Message = CommandArg()):
    id = args[0].data["text"].strip()
    audit_data_file = Path() / "data" / "audit.json"
    audit_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(audit_data_file, "r", encoding="utf-8") as f:
        audit_data = json.load(f)
    for i in audit_data:
        if str(id) == str(i):
            await audit_add.finish(f"id为 {str(id)} 的用户已在审核组中")
    audit_data.append(int(id))
    with open(audit_data_file, "r", encoding="utf-8") as f:
        audit_data = json.dump(audit_data, f)
    await audit_add.finish("添加成功")


@audit_del.handle()
async def _(event: PrivateMessageEvent, args: Message = CommandArg()):
    id = args[0].data["text"].strip()
    audit_data_file = Path() / "data" / "audit.json"
    audit_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(audit_data_file, "r", encoding="utf-8") as f:
        audit_data = json.load(f)
    if int(id) in audit_data:
        audit_data.remove(int(id))
        await audit_del.finish("删除成功")
    if str(id) in audit_data:
        audit_data.remove(str(id))
        await audit_del.finish("删除成功")
    await audit_del.finish(f"id为 {str(id)} 的用户不在审核组中")
