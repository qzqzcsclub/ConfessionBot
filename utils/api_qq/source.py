from nonebot import get_bot, logger

from utils.config import Config


class NoQQ(Exception):
    '''
    未配置机器人qqid报错
    '''
    pass


async def send_private_msg(user_id, message):
    '''
    QQ发送私聊信息， bot 从配置中获取并逐个尝试发送消息，全部发送失败会报错
    '''
    qq_ids = Config.get_value("bot_info", "command_qq_id")
    if not qq_ids:
        logger.error("配置组 bot_info 的配置项 command_qq_id 未填写，无法发送消息")
        raise NoQQ("配置组 bot_info 的配置项 command_qq_id 未填写，无法发送消息")
    for qq_id in qq_ids:
        bot = get_bot(qq_id)
        try:
            await bot.send_private_msg(
                    user_id=user_id,
                    message=message
                )
        except Exception as e:
            if qq_id == qq_ids[-1]:
                raise e
        else:
            return None
