import anyio
from pathlib import Path

from nonebot import get_bot, logger, require

require("nonebot_plugin_saa")
from nonebot_plugin_saa import MessageSegmentFactory, MessageFactory,TargetQQPrivate, TargetTelegramCommon, TargetKaiheilaPrivate

from utils.config import Config


class NoCommandId(Exception):
    '''
    未配置机器人id报错
    '''
    pass

class NoPlatformType(Exception):
    '''
    未配置机器人平台种类报错
    '''
    pass

class UnsupportedPlatformType(Exception):
    '''
    机器人平台种类配置错误报错
    '''
    pass



async def send_private_msg(user_id: int | str, message: MessageSegmentFactory | MessageFactory):
    '''
    发送私聊信息， bot 从配置中获取并逐个尝试发送消息，全部发送失败会报错
    '''
    ids = Config.get_value("bot_info", "command_id")
    platform_type = Config.get_value("bot_info", "platform_type")
    if not ids:
        logger.error("配置组 bot_info 的配置项 command_id 未填写，无法发送消息")
        raise NoCommandId("配置组 bot_info 的配置项 command_id 未填写，无法发送消息")
    if not platform_type:
        logger.error("配置组 bot_info 的配置项 platform_type 未填写，无法发送消息")
        raise NoPlatformType("配置组 bot_info 的配置项 platform_type 未填写，无法发送消息")
    for id in ids:
        bot = get_bot(id)

        if platform_type in ["onebotv11", "onebotv12", "red", "satori"]:
            target = TargetQQPrivate(user_id=int(user_id))
        elif platform_type == "telegram":
            target = TargetTelegramCommon(chat_id=int(user_id))
        elif platform_type == "kaiheila":
            target = TargetKaiheilaPrivate(user_id=str(user_id))
        else:
            logger.error("配置组 bot_info 的配置项 platform_type 填写错误，无法发送消息")
            raise UnsupportedPlatformType("配置组 bot_info 的配置项 platform_type 填写错误，无法发送消息")

        try:
            await message.send_to(
                target=target,
                bot=bot
            )
        except Exception as e:
            if id == ids[-1]:
                raise e
        else:
            return None


async def send_video(user_id: int | str, file):
    '''
    发送私聊视频， bot 从配置中获取并逐个尝试发送消息，全部发送失败会报错
    '''
    ids = Config.get_value("bot_info", "command_id")
    platform_type = Config.get_value("bot_info", "platform_type")
    if not ids:
        logger.error("配置组 bot_info 的配置项 command_id 未填写，无法发送消息")
        raise NoCommandId("配置组 bot_info 的配置项 command_id 未填写，无法发送消息")
    if not platform_type:
        logger.error("配置组 bot_info 的配置项 platform_type 未填写，无法发送消息")
        raise NoPlatformType("配置组 bot_info 的配置项 platform_type 未填写，无法发送消息")
    for id in ids:
        bot = get_bot(id)

        try:
            if platform_type == "onebotv11":                                                                                 
                from nonebot.adapters.onebot.v11 import MessageSegment
                msg = MessageSegment.video(file, timeout=30)
                await bot.send_private_msg(user_id=user_id, message=msg)
            elif platform_type == "onebotv12":
                resp = await bot.upload_file(type="path", name="video", path=str(file))
                file_id = resp["file_id"]
                from nonebot.adapters.onebot.v12 import MessageSegment
                msg = MessageSegment.video(file_id)
                await bot.send_message(detail_type="private", user_id=user_id, message = msg)
            elif platform_type == "red":
                from nonebot.adapters.red import MessageSegment
                msg = MessageSegment.video(file)
                await bot.send_friend_message(target=user_id, message=msg)
            elif platform_type == "satori":
                from nonebot.adapters.satori import MessageSegment
                msg = MessageSegment.video(path=file, timeout=30)
                await bot.send_private_msg(user=str(user_id), message=msg)
            elif platform_type == "telegram":
                from nonebot.adapters.telegram.message import File as TGFile
                video = await anyio.Path(Path(file)).read_bytes()
                msg = TGFile.video(video)
                await bot.send_to(chat_id=user_id, message=msg)
            elif platform_type == "kaiheila":
                file_key = await bot.upload_file(file = str(file), filename = "video")
                msg = MessageSegment.image(file_key)
                await bot.send_private_msg(user_id=user_id, message=msg)
            else:
                logger.error("配置组 bot_info 的配置项 platform_type 填写错误，无法发送消息")
                raise UnsupportedPlatformType("配置组 bot_info 的配置项 platform_type 填写错误，无法发送消息")

        except Exception as e:
            if id == ids[-1]:
                raise e
        else:
            return None
