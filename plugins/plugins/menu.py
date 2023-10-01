import random

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, PrivateMessageEvent
from nonebot.permission import SUPERUSER

from utils.permission import ADMIN, AUDIT, USER


help_user = on_command(
    '帮助',
    permission=USER,
    block=True,
    priority=10
)

help_audit = on_command(
    '帮助',
    permission=AUDIT,
    block=True,
    priority=10
)

help_admin = on_command(
    '帮助',
    permission=ADMIN,
    block=True,
    priority=10
)

help_superuser = on_command(
    '帮助',
    permission=SUPERUSER,
    block=True,
    priority=9
)

other = on_command(
    '',
    priority=999
)


# 用户功能响应体
@help_user.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    data = f"欢迎使用{list(bot.config.nickname)[0]}\n发帖命令:\n发帖 <对话/文章> <实名/半实名/匿名>\n例: 发帖 文章 实名\n不带参数默认为对话和实名\n文章类型说明:\n对话就是你可以发送多条信息，可以含文字、图片、视频（非图片形式的表情包不支持）会记录自开始到你发送“结束”命令前的所有信息，类似传统截图表白墙采用方式。\n文章就是只能发送一条消息，可以包含文字、图片。\n两种文章类型生成的帖子效果图略有区别。\n匿名类型说明:\n实名会公开头像、用户名、QQ号。\n半实名会公开头像。\n匿名什么信息都不会公开。\n表白墙审核机制说明:\n帖子提交后会自动推送帖子至审核组进行审核，匿名状态下审核组无法知道发送者信息（如果有严重违纪行为，机器人维护者有权查看发送者信息），帖子审核通过后会在一定时间内发送至QQ空间\n防封编码:"
    data += str(random.randint(10000, 99999))
    await help_user.finish(data)


# 审核组功能响应体
@help_audit.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    data = f"欢迎使用{list(bot.config.nickname)[0]}\n权限组:审核组\n\n用户功能说明:\n发帖命令:\n发帖 <对话/文章> <实名/半实名/匿名>\n例: 发帖 文章 实名\n不带参数默认为对话和实名\n文章类型说明:\n对话就是你可以发送多条信息，可以含文字、图片、视频（非图片形式的表情包不支持）会记录自开始到你发送“结束”命令前的所有信息，类似传统截图表白墙采用方式。\n文章就是只能发送一条消息，可以包含文字、图片。\n两种文章类型生成的帖子效果图略有区别。\n匿名类型说明:\n实名会公开头像、用户名、QQ号。\n半实名会公开头像。\n匿名什么信息都不会公开。\n表白墙审核机制说明:\n帖子提交后会自动推送帖子至审核组进行审核，匿名状态下审核组无法知道发送者信息（如果有严重违纪行为，机器人维护者有权查看发送者信息），帖子审核通过后会在一定时间内发送至QQ空间\n\n审核组功能说明:\n机器人会自动推送要审核的帖子，请根据推送时的提示进行审核\n防封编码:"
    data += str(random.randint(10000, 99999))
    await help_audit.finish(data)


# 审核组管理员功能响应体
@help_admin.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    data = f"欢迎使用{list(bot.config.nickname)[0]}\n权限组:审核组管理员（含审核组权限）\n\n用户功能说明:\n发帖命令:\n发帖 <对话/文章> <实名/半实名/匿名>\n例: 发帖 文章 实名\n不带参数默认为对话和实名\n文章类型说明:\n对话就是你可以发送多条信息，可以含文字、图片、视频（非图片形式的表情包不支持）会记录自开始到你发送“结束”命令前的所有信息，类似传统截图表白墙采用方式。\n文章就是只能发送一条消息，可以包含文字、图片。\n两种文章类型生成的帖子效果图略有区别。\n匿名类型说明:\n实名会公开头像、用户名、QQ号。\n半实名会公开头像。\n匿名什么信息都不会公开。\n表白墙审核机制说明:\n帖子提交后会自动推送帖子至审核组进行审核，匿名状态下审核组无法知道发送者信息（如果有严重违纪行为，机器人维护者有权查看发送者信息），帖子审核通过后会在一定时间内发送至QQ空间\n\n审核组功能说明:\n机器人会自动推送要审核的帖子，请根据推送时的提示进行审核\n\n审核组管理员功能说明:\n命令:\n审核组列表\n删除/添加审核员 <用户ID>\n防封编码:"
    data += str(random.randint(10000, 99999))
    await help_admin.finish(data)


# 机器人维护组功能响应体
@help_superuser.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    data = f"欢迎使用{list(bot.config.nickname)[0]}\n权限组:机器人维护组\n\n用户功能说明:\n发帖命令:\n发帖 <对话/文章> <实名/半实名/匿名>\n例: 发帖 文章 实名\n不带参数默认为对话和实名\n文章类型说明:\n对话就是你可以发送多条信息，可以含文字、图片、视频（非图片形式的表情包不支持）会记录自开始到你发送“结束”命令前的所有信息，类似传统截图表白墙采用方式。\n文章就是只能发送一条消息，可以包含文字、图片。\n两种文章类型生成的帖子效果图略有区别。\n匿名类型说明:\n实名会公开头像、用户名、QQ号。\n半实名会公开头像。\n匿名什么信息都不会公开。\n表白墙审核机制说明:\n帖子提交后会自动推送帖子至审核组进行审核，匿名状态下审核组无法知道发送者信息（如果有严重违纪行为，机器人维护者有权查看发送者信息），帖子审核通过后会在一定时间内发送至QQ空间\n\n审核组功能说明:\n机器人会自动推送要审核的帖子，请根据推送时的提示进行审核\n\n机器人维护者功能说明:\n命令:\n审核组管理员列表\n删除/添加审核组管理员 <用户ID>\n防封编码:"
    data += str(random.randint(10000, 99999))
    await help_admin.finish(data)


# 未匹配的消息响应体
@other.handle()
async def _(bot: Bot, event: PrivateMessageEvent):
    data = f"请发送“帮助”查看{list(bot.config.nickname)[0]}功能说明\n防封编码:"
    data += str(random.randint(10000, 99999))
    await other.finish(data)
