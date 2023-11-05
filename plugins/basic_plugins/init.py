from nonebot import get_driver, get_bot

from utils.config import Config

driver = get_driver()

@driver.on_bot_connect
async def restart_handle():
    '''
    按照配置自动登录空间
    '''
    auto_login_qzone = Config.get_value("bot_info", "auto_login_qzone")
    if auto_login_qzone:
        bot = get_bot("qzone_bot")
        await bot.login()
        