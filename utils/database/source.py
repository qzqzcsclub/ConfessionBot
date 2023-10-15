from pathlib import Path

import asyncpg
import ujson as json
from nonebot import logger

from utils.config import Config


async def database_connect():
    '''
    连接数据库
    '''
    database = Config.get_value("database", "database")
    user = Config.get_value("database", "user")
    password = Config.get_value("database", "password")
    host = Config.get_value("database", "host")
    port = Config.get_value("database", "port")
    conn = await asyncpg.connect(database=database, user=user, password=password, host=host, port=port)
    logger.trace("连接数据库成功")
    return conn


async def database_audit_init():
    '''
    初始化数据库 audit 表
    '''
    conn = await database_connect()
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS audit (
            id INTEGER,
            is_examining BOOL,
            examining_post_id TEXT
            )"""
    )
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS temp_audit (
            id INTEGER
            )"""
    )

    audit_data_file = Path() / "data" / "audit.json"
    audit_data_file.parent.mkdir(exist_ok=True, parents=True)
    admin_data_file = Path() / "data" / "admin.json"
    admin_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(audit_data_file, "r", encoding="utf-8") as f:
        audit_data = json.load(f)
    with open(admin_data_file, "r", encoding="utf-8") as f:
        admin_data = json.load(f)
    audit_data = audit_data + admin_data
    audit_data = list(set(audit_data))

    # 将id列表插入临时表
    await conn.executemany("INSERT INTO temp_audit (id) VALUES ($1)", [(user_id,) for user_id in audit_data])
    # 更新audit表，不覆盖已存在的id
    await conn.execute(
        """INSERT OR IGNORE INTO audit (id, is_examining, examining_post_id)
        SELECT id, is_examining, examining_post_id FROM temp_audit"""
    )
    # 删除audit表中不存在于用户id列表的id所在的行
    await conn.execute("DELETE FROM audit WHERE id NOT IN (SELECT id FROM temp_audit)")
    # 删除临时表
    await conn.execute("DROP TABLE IF EXISTS temp_audit")

    await conn.close()


async def database_info_init():
    '''
    初始化数据库 info 表
    '''
    conn = await database_connect()
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS info (
            used_id TEXT,
            current_path TEXT
            )"""
    )

    row = await conn.fetchrow("SELECT used_id FROM info")
    if not row:
        await conn.execute("INSERT INTO info (used_id) VALUES ($1)", 0)

    await conn.close()


async def database_unverified_post_init():
    '''
    初始化数据库 unverified_post 表
    '''
    conn = await database_connect()
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS unverified_post (
            id TEXT,
            commit_time TEXT,
            examine_begin_time TEXT,
            user_id TEXT,
            path_pic_post TEXT,
            path_post_data TEXT,
            post_type INTEGER,
            status_anon INTEGER,
            auditor_number INTEGER,
            max_auditor_number INTEGER,
            have_video BOOL,
            video_number INTEGER
            )"""
    )
    await conn.close()


async def database_approved_post_init():
    '''
    初始化数据库 approved_post 表
    '''
    conn = await database_connect()
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS approved_post (
            id TEXT,
            commit_time TEXT,
            user_id TEXT,
            path_pic_post TEXT,
            path_post_data TEXT,
            post_type INTEGER,
            status_anon INTEGER,
            status_post BOOL,
            have_video BOOL,
            video_number INTEGER
            )"""
    )
    await conn.close()


async def database_disapproved_post_init():
    '''
    初始化数据库 disapproved_post 表
    '''
    conn = await database_connect()
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS disapproved_post (
            id TEXT,
            commit_time TEXT,
            user_id TEXT,
            path_pic_post TEXT,
            path_post_data TEXT,
            post_type INTEGER,
            status_anon INTEGER,
            have_video BOOL,
            video_number INTEGER
            )"""
    )
    await conn.close()


async def database_unpublished_post_init():
    '''
    初始化数据库 unpublished_post 表
    '''
    conn = await database_connect()
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS unpublished_post (
            id TEXT,
            commit_time TEXT,
            have_video BOOL,
            video_number INTEGER
            )"""
    )
    await conn.close()
