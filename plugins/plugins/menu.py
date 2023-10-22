import random

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent
from nonebot.permission import SUPERUSER

from utils.permission import ADMIN, AUDIT


help = on_command(
    '帮助',
    aliases={"菜单", "功能", "help"},
    block=True,
    priority=10
)

other = on_command(
    '',
    priority=999
)


# 功能响应体
@help.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    is_admin = ADMIN(bot, event)
    is_audit = AUDIT(bot, event)
    is_superuser = SUPERUSER(bot, event)
    data = f"""欢迎使用{list(bot.config.nickname)[0]}
    
用户功能说明:
1. 发帖命令:
   - 发帖 <类型> <匿名>
     - 例: 发帖 对话 实名
     - 不带参数默认为对话和实名
2. 文章类型说明:
   - 对话: 发送多条信息，包含文字、图片、视频（不支持非图片形式的表情包和QQ表情包）。记录从开始到发送“结束”命令前的所有信息，类似传统截图表白墙采用方式。
   - 文章: 只能发送一条消息，可以包含文字、图片。
3. 匿名类型说明:
   - 实名: 公开用户名、QQ号。
   - 半实名: 公开头像。
   - 匿名: 不公开任何信息。

表白墙审核机制说明:
1. 帖子提交后会自动推送给审核组进行审核，匿名状态下审核组无法知道发送者信息（如果有严重违纪行为，机器人维护者有权查看发送者信息）。
2. 审核通过后，帖子会在一定时间内发布到QQ空间。"""
    if is_audit:
        data += "\n\n审核组功能说明:\n机器人会自动推送待审核的帖子，请根据提示进行审核。"
    
    if is_admin:
        data += "\n\n审核组管理员功能说明:\n命令:\n1. 审核组列表\n2. 删除/添加审核员 <用户ID>"
    
    if is_superuser:
        data += "\n\n机器人维护者功能说明:\n命令:\n1. 审核组管理员列表\n2. 删除/添加审核组管理员 <用户ID>"
    
    data += "\n\n防封编码:"
    data += str(random.randint(10000, 99999))
    await help.finish(data)


# 未匹配的消息响应体
@other.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    data = f"请发送“帮助”查看{list(bot.config.nickname)[0]}功能说明\n防封编码:"
    data += str(random.randint(10000, 99999))
    await other.finish(data)
