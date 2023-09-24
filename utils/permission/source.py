from pathlib import Path

import ujson as json
from nonebot.adapters import Bot, Event
from nonebot.permission import Permission


async def audit_checker(event: Event):
    '''
    审核组权限检查（不包括审核组管理员）
    '''
    audit_data_file = Path() / "data" / "audit.json"
    audit_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(audit_data_file, "r", encoding="utf-8") as f:
        audit_data = json.load(f)
    if event.get_session_id() in audit_data:
        return True
    else:
        return False

async def admin_checker(event: Event):
    '''
    审核组管理员权限检查
    '''
    admin_data_file = Path() / "data" / "admin.json"
    admin_data_file.parent.mkdir(exist_ok=True, parents=True)
    with open(admin_data_file, "r", encoding="utf-8") as f:
        admin_data = json.load(f)
    if event.get_session_id() in admin_data:
        return True
    else:
        return False

# 审核组权限
AUDIT = Permission(audit_checker, admin_checker)

# 审核组管理员权限
ADMIN = Permission(admin_checker)

async def user_checker(bot: Bot,event: Event):
    '''
    普通用户权限检查
    '''
    result_audit_checker: bool = await AUDIT(bot, event)
    result_admin_checker: bool = await ADMIN(bot, event)
    if not result_audit_checker and not result_admin_checker:
        return True
    else:
        return False

# 普通用户权限
USER = Permission(user_checker)
