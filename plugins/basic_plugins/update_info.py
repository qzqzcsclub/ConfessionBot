from pathlib import Path

from nonebot import get_driver

from utils.database import database_connect, database_info_init

driver = get_driver()


@driver.on_bot_connect
async def update_info():
    '''
    开启自动更新数据库基本信息
    '''
    # 初始化数据库 info 表
    await database_info_init()

    # 连接数据库
    conn = await database_connect()
    current_path = str(Path.cwd())
    await conn.execute("UPDATE info SET current_path = $1", current_path)
    await conn.close()
