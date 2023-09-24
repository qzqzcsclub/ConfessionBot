import asyncio
import os
import platform
import shutil
import subprocess
import tarfile
from pathlib import Path
from typing import Tuple

import httpx
import toml
import ujson as json
from nonebot import get_driver, logger
from nonebot.adapters import Bot

from utils.config import Config

driver = get_driver()

release_url = Config.get_value("bot_update", "release_url")

_version_file = Path() / "__version__"
update_tar_file = Path() / "update_tar_file.tar.gz"
temp_dir = Path() / "temp"
backup_dir = Path() / "backup"

proxy = Config.get_value("bot_update", "proxy")
if proxy:
    proxies = {
        "http://": proxy,
        "https://": proxy
    }
else:
    proxies = None


class NoVersionData(Exception):
    '''
    无机器人版本信息报错
    '''
    pass


class NoVersionMatch(Exception):
    '''
    无远程仓库对应版本信息报错
    '''
    pass


@driver.on_bot_connect
async def dep_file_handle(bot: Bot):
    '''
    机器人连接时自动生成机器人原始依赖文件和用户依赖文件
    文件位于 /source/dep/
    '''
    dep_file = Path() / "pyproject.toml"
    dep_org_source_file = Path() / "source" / "dep" / "pyproject_org.toml"
    dep_user_source_file = Path() / "source" / "dep" / "pyproject_user.toml"
    dep_org_source_file.parent.mkdir(exist_ok=True, parents=True)
    dep_user_source_file.parent.mkdir(exist_ok=True, parents=True)
    if not dep_file.exists():
        logger.error("重大错误，依赖配置文件 pyproject.toml 不存在")
        return None
    if not dep_org_source_file.exists():
        shutil.copy2(dep_file.absolute(), dep_org_source_file.absolute())
        logger.warning(f"检测到机器人原始依赖文件资源 {dep_org_source_file} 不存在，自动从用户依赖文件 {dep_file} 生成")
    shutil.copy2(dep_file.absolute(), dep_user_source_file.absolute())


@driver.on_bot_connect
async def restart_handle(bot: Bot):
    '''
    机器人连接时自动生成重启文件
    '''
    if str(platform.system()).lower() == "windows":
        restart = Path() / "restart.bat"
        if not restart.exists():
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
        if not restart.exists():
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
            await bot.send_private_msg(
                user_id=int(user_id),
                message="机器人重启完毕",
            )
        is_restart_file.unlink()


async def check_update(bot: Bot) -> Tuple[int, str]:
    '''
    检查更新
    '''
    logger.info("开始检查更新机器人")
    _version = "v0.0.0"
    if _version_file.exists():
        with open(_version_file, "r", encoding="utf-8") as f:
            _version = f.readline().split(":")[-1].strip()
    else:
        raise NoVersionData(f"找不到机器人版本信息文件，无法检测更新，版本信息文件应该位于{_version_file}")
    status_get_version_data, data = await get_version_data()
    if not status_get_version_data:
        return 995, data
    global releases_version
    releases_version = "v0.0.0"
    if data:
        if data[0]["name"] != _version:
            latest_version = data[0]["name"]
            version_match = False
            for releases in data:
                if _version == releases["name"]:
                    version_match = True
                    break
                if not releases["prerelease"] or Config.get_value("releases", "releases") == "dev":
                    releases_version = releases["name"]
                    tar_gz_url = releases["tarball_url"]
                    update_info = releases["body"]
                    time = releases['created_at']
            if version_match != True:
                raise NoVersionMatch(f"找不到与远程仓库版本相匹配的机器人版本信息文件中的版本，无法检测更新，版本信息文件应该位于{_version_file}")
            logger.info(f"检测到机器人需要更新，当前版本：{_version}，下一版本：{releases_version}，最新版本：{latest_version}")
            for superuser in list(bot.config.superusers):
                await bot.send_private_msg(
                    user_id=int(superuser),
                    message=f"检测到机器人需要更新，当前版本：{_version}，下一版本：{releases_version}，最新版本：{latest_version}\n" f"开始更新",
                )
            logger.debug(f"开始下载机器人 {releases_version} 版本文件")
            async with httpx.AsyncClient(proxies=proxies) as client:
                resp = await client.get(tar_gz_url)
                tar_gz_url = resp.headers.get("Location")
            async with httpx.AsyncClient(proxies=proxies) as client:
                resp = await client.get(tar_gz_url)
                status_code = resp.status_code
                file_data = resp.content
            if status_code == 200:
                with open(update_tar_file, "wb") as f:
                    f.write(file_data)
                logger.debug("下载机器人新版文件完成")
                error_info = await asyncio.get_event_loop().run_in_executor(
                    None, _update_handle
                )
                if error_info:
                    return 996, error_info
                logger.info("机器人更新完毕，清理文件完成")
                global nb_config_desc
                global update_desc
                msg = (
                            f"机器人更新完成，版本：{_version} -> {releases_version}\n"
                            f"版本发布日期：{time}\n"
                            f"更新日志：\n"
                            f"{update_info}"
                        )
                if nb_config_desc:
                    msg += f"\nnonebot配置更新说明：\n{nb_config_desc}"
                if update_desc:
                    msg += f"\n更新说明：\n{update_desc}"
                for superuser in list(bot.config.superusers):
                    await bot.send_private_msg(
                        user_id=int(superuser),
                        message=msg
                    )
                return 200, ""
            else:
                error_info = f"下载机器人最新版本失败，版本号：{releases_version}"
                return 997, error_info
        else:
            error_info = f"自动获取机器人版本成功：{_version}，当前版本为最新版，无需更新"
            return 999, error_info
    else:
        error_info = "自动获取机器人版本信息请求成功，但是未获取到有效信息"
        return 998, error_info


def _update_config(update_info):
    '''
    配置更新处理
    '''
    global nb_config_desc
    global update_desc
    add_bot_config = update_info["config"]["bot"]["add_bot_config"]
    delete_bot_config = update_info["config"]["bot"]["delete_bot_config"]
    move_bot_config = update_info["config"]["bot"]["move_bot_config"]
    nb_config_desc = update_info["config"]["nonebot"]["nb_config_desc"]
    update_desc = update_info["desc"]["update_desc"]

    if add_bot_config:
        for c in add_bot_config:
            Config.add_plugin_config(
                module=c["module"],
                key=c["key"],
                value=c["value"],
                help_=c["help"],
                default_value=c["default_value"],
                type_=c["type"]
            )
    if delete_bot_config:
        for c in delete_bot_config:
            Config.delete_plugin_config(
                module=c["module"],
                key=c["key"]
            )
    if move_bot_config:
        for i in move_bot_config:
            c = Config.get_config(
                module=i["old"]["module"],
                key=i["old"]["key"]
            )
            if c:
                Config.add_plugin_config(
                    module=c["new"]["module"],
                    key=c["new"]["key"],
                    value=c.value,
                    help_=c.help_,
                    default_value=c.default_value,
                    type_=c.type_
                )
                Config.delete_plugin_config(
                    module=c["old"]["module"],
                    key=c["old"]["key"]
                )
    logger.debug("配置已更新")


def _update_file(update_info, bot_new_file):
    '''
    文件更新处理
    '''
    update_file = update_info["file"]["update_file"]
    add_file = update_info["file"]["add_file"]
    delete_file = update_info["file"]["delete_file"]
    move_file = update_info["file"]["move_file"]

    dep_file = Path(bot_new_file) / "pyproject.toml"
    dep_org_source_file = Path() / "source" / "dep" / "pyproject_org.toml"
    dep_org_source_file.parent.mkdir(exist_ok=True, parents=True)
    shutil.copy2(dep_file.absolute(), dep_org_source_file.absolute())

    for f in delete_file + update_file:
        file_path = Path() / f.replace('.', r'\.')
        backup_file_path = Path(backup_dir) / f.replace('.', r'\.')
        if file_path.exists():
            backup_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(file_path.absolute(), backup_file_path.absolute())
            if f in delete_file:
                logger.debug(f"已删除并备份文件： {f}")
    for f in add_file + update_file:
        new_file_path = Path(bot_new_file) / f.replace('.', r'\.')
        old_file_path = Path() / f.replace('.', r'\.')
        if old_file_path.exists() and f in add_file:
            backup_file_path = Path(backup_dir) / f.replace('.', r'\.')
            shutil.move(old_file_path.absolute(), backup_file_path.absolute())
            logger.warning(f"文件 {f} 为更新信息中的添加文件，但是该文件已存在，已自动更新该文件为新版本并完成备份")
        elif new_file_path.exists():
            shutil.move(new_file_path.absolute(), old_file_path.absolute())
            if f in add_file:
                logger.debug(f"已更新文件： {f}")
            elif f in update_file:
                logger.debug(f"已更新并备份文件： {f}")
        elif not new_file_path.exists():
            logger.error(f"尝试从新版本文件中更新文件 {f} ，但是新版本文件中不存在该文件")
    for f in move_file:
        new_file_path = Path() / f["new"].replace('.', r'\.')
        old_file_path = Path() / f["old"].replace('.', r'\.')
        old_file = f["old"].replace('.', r'\.')
        new_file = f["new"].replace('.', r'\.')
        if old_file_path.exists():
            new_file_path.parent.mkdir(exist_ok=True, parents=True)
            if new_file_path.exists():
                new_file_backup_path = Path() / "backup" / new_file_path
                logger.warning(f"尝试移动文件 {old_file} 至 {new_file} ，但是目标文件已存在，进行强制覆盖，原文件已备份至 backup 文件夹")
                shutil.move(new_file_path.absolute(), new_file_backup_path.absolute())
            shutil.move(old_file_path.absolute(), new_file_path.absolute())
            logger.debug(f"已移动文件 {old_file} 至 {new_file}")
        else:
            logger.warning(f"尝试移动文件 {old_file} 至 {new_file} ，但是原文件不存在，跳过处理")


def _update_dependency():
    '''
    依赖更新处理
    更新原理：比较原先版本（未经用户增删依赖，在更新时从源码包获取或者首次运行时本地获取的）的 pyproject.toml 和现在使用的文件的不同的依赖，再将这些依赖添加到新版本依赖文件中
    '''
    dep_file_user = Path() / "source" / "dep" / "pyproject_user.toml"
    dep_file_org = Path() / "source" / "dep" / "pyproject_org.toml"
    dep_file_new = Path() / "pyproject.toml"

    with open(dep_file_user, "r") as f:
        dep_data_user = toml.load(f)
    poetry_data_user = dep_data_user['tool']['poetry']['dependencies']
    poetry_data_user = [{"name": k, "version": v} for k, v in poetry_data_user.items() if k != 'python']
    nonebot_plugins_user = dep_data_user['tool']['nonebot']['plugins']

    with open(dep_file_org, "r") as f:
        dep_data_org = toml.load(f)
    poetry_data_org = dep_data_org['tool']['poetry']['dependencies']
    poetry_data_org = [{"name": k, "version": v} for k, v in poetry_data_org.items() if k != 'python']
    nonebot_plugins_org = dep_data_org['tool']['nonebot']['plugins']
    packages_org = [dep['name'] for dep in poetry_data_org]
    
    packages_extra = []
    for package in poetry_data_user:
        if package["name"] not in packages_org:
            packages_extra.append(package)
    
    plugins_extra = []
    for plugin in nonebot_plugins_user:
        if plugin not in nonebot_plugins_org:
            plugins_extra.append(plugin)
    
    with open(dep_file_new, "r") as f:
        dep_data_new = toml.load(f)
    for package in packages_extra:
        dep_data_new['tool']['poetry']['dependencies'][package["neme"]] = package["version"]
    for plugin in plugins_extra:
        dep_data_new['tool']['nonebot']['plugins'].append(plugin)
    dep_date_new_str = toml.dumps(dep_data_new)
    with open(dep_file_new, "w") as f:
        f.write(dep_date_new_str)
    
    logger.debug("依赖处理完成")

    for i in range(1, 4):
        try:
            if packages_extra:
                subprocess.run(['poetry', 'lock'], check=True, cwd=Path())
            subprocess.run(['poetry', 'install'], check=True, cwd=Path())
            logger.debug("依赖安装成功")
            return ""
        except subprocess.CalledProcessError as e:
            error_message = str(e)
            if i == 3:
                error_info = f"更新依赖项失败，请自行排查问题并在机器人目录终端手动尝试更新，更新命令 'poetry install' ，错误信息：{error_message}"
                return error_info

def _update_handle() -> str:
    '''
    更新处理
    '''
    if not temp_dir.exists():
        temp_dir.mkdir(exist_ok=True, parents=True)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    tar_file = None
    backup_dir.mkdir(exist_ok=True, parents=True)
    logger.info("开始解压机器人文件压缩包....")
    tar_file = tarfile.open(update_tar_file)
    tar_file.extractall(temp_dir)
    logger.info("解压机器人文件压缩包完成....")
    bot_new_file = Path(temp_dir) / os.listdir(temp_dir)[0]
    update_info_file = Path(bot_new_file) / "update_info.json"
    with open(update_info_file, "r", encoding="utf-8") as f:
        update_info = json.load(f)
    
    _update_config(update_info)
    _update_file(update_info, bot_new_file)

    if tar_file:
        tar_file.close()
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    if update_tar_file.exists():
        update_tar_file.unlink()
    local_update_info_file = Path() / "update_info.json"
    if local_update_info_file.exists():
        local_update_info_file.unlink()
    global releases_version
    with open(_version_file, "w", encoding="utf-8") as f:
        f.write(f"__version__: {releases_version}")

    error_info = _update_dependency()
    if error_info:
        return error_info
    else:
        return ""


async def get_version_data() -> tuple[bool, any]:
    '''
    获取版本信息
    '''
    for i in range(3):
        try:
            async with httpx.AsyncClient(timeout=30, proxies=proxies) as client:
                resp = await client.get(release_url)
                if resp.status_code == 200:
                    return True, json.loads(resp.text)
        except httpx.ReadTimeout:
            if i == 2:
                error_info = "检查更新机器人获取远程仓库版本超时，请检查网络环境"
                return False, error_info
        except Exception as e:
            if i == 2:
                error_info = f"检查更新机器人获取远程仓库版本失败 {type(e)}：{e}"
                return False, error_info