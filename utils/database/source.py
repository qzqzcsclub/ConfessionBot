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
            id TEXT,
            is_examining BOOL,
            examining_post_id TEXT
            )"""
    )

    # 获取本地文件的数据
    audit_data_file = Path() / "data" / "audit.json"
    audit_data_file.parent.mkdir(exist_ok=True, parents=True)
    admin_data_file = Path() / "data" / "admin.json"
    admin_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(audit_data_file, "r", encoding="utf-8") as f:
        audits_data = json.load(f)
    with open(admin_data_file, "r", encoding="utf-8") as f:
        admins_data = json.load(f)
    audits_new = audits_data + admins_data
    audits_new = list(set(audits_new)) # 合并重复的元素

    # 获取数据库的数据
    rows = await conn.fetch("SELECT * FROM audit")
    audits_old = [dict(row) for row in rows]
    audit_old_id = []
    for audit_old in audits_old:
        audit_old_id.append(audit_old["id"])

    # 删除数据库中本地文件没有的数据
    for audit_old in audits_old:
        if audit_old["id"] not in audits_new:
            await conn.execute("DELETE FROM audit WHERE id=$1", audit_old["id"])
    
    # 新增数据库中没有的数据
    for audit_new in audits_new:
        if audit_new not in audit_old_id:
            await conn.execute("INSERT INTO audit (id, is_examining) VALUES ($1, $2)", audit_new, False)

    await conn.close()


async def database_info_init():
    '''
    初始化数据库 info 表
    '''
    conn = await database_connect()
    await conn.execute(
        """CREATE TABLE IF NOT EXISTS info (
            used_id INTEGER,
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
