import platform
import subprocess
import os
from pathlib import Path

from nonebot import on_command, get_driver, logger, require
from nonebot.adapters import Bot, Event
from nonebot.permission import SUPERUSER
from nonebot.params import ArgStr
from nonebot.rule import to_me

require("nonebot_plugin_saa")
from nonebot_plugin_saa import Text

from utils.api import send_private_msg


driver = get_driver()


restart = on_command(
    "重启",
    permission=SUPERUSER,
    rule=to_me(),
    priority=1,
    block=True,
)


@restart.got("flag", prompt=f"确定是否重启机器人？确定请回复[是|好|确定]（重启失败咱们将失去联系，请谨慎！）")
async def _(event: Event, flag: str = ArgStr("flag")):
    if flag.lower() in ["true", "是", "好", "确定", "确定是"]:
        await Text("开始重启机器人..请稍等...").send()
        await bot_restart(event)
    else:
        await Text("已取消操作...").send()


async def bot_restart(event=None):
    with open("is_restart", "w", encoding="utf-8") as f:
        if event:
            f.write(event.get_session_id())
    if str(platform.system()).lower() == "windows":
        subprocess.run(["restart.bat"], cwd=Path())
    else:
        subprocess.run(["sudo", "./restart.sh"], cwd=Path())


@driver.on_bot_connect
async def restart_handle(bot: Bot):
    '''
    机器人连接时自动生成重启文件
    '''
    if str(platform.system()).lower() == "windows":
        restart = Path() / "restart.bat"
        port = str(bot.config.port)
        script = f'''
@echo off
set PORT={port}

for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%"') do (
taskkill /PID %%a /F
goto :RunPoetry
)

:RunPoetry
call poetry run nb run
'''
        with open(restart, "w", encoding="utf-8") as f:
            f.write(script)
        logger.info("已自动生成 restart.bat(重启) 文件，请检查脚本是否与本地指令符合")
    else:
        restart = Path() / "restart.sh"
        port = str(bot.config.port)
        script = f'''
pid=$(netstat -tunlp | grep {port} | awk '{{print $7}}')
pid=${{pid%/*}}
kill -9 $pid
sleep 3
poetry run nb run
'''
        with open(restart, "w", encoding="utf-8") as f:
            f.write(script)
        os.system("chmod +x ./restart.sh")
        logger.info("已自动生成 restart.sh(重启) 文件，请检查脚本是否与本地指令符合")
    is_restart_file = Path() / "is_restart"
    if is_restart_file.exists():
        with open(is_restart_file, "r", encoding="utf-8") as f:
            user_id=f.read()
        if user_id:
            await send_private_msg(
                user_id=int(user_id),
                message=Text("机器人重启完毕"),
            )
        is_restart_file.unlink()
        