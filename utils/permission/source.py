import os
from pathlib import Path

import ujson as json
from nonebot.adapters import Event
from nonebot.permission import Permission


async def audit_checker(event: Event):
    '''
    审核组权限检查（不包括审核组管理员）
    '''
    audit_data_file = Path() / "data" / "audit.json"
    audit_data_file.parent.mkdir(exist_ok=True, parents=True)
    if not os.path.exists(audit_data_file):
        with open(audit_data_file, 'w', encoding="utf-8") as f:
            f.write("[]")
    with open(audit_data_file, "r", encoding="utf-8") as f:
        audit_data = json.loads(f.read())
    for i in audit_data:
        if str(event.get_session_id()) == str(i):
            return True
    return False

async def admin_checker(event: Event):
    '''
    审核组管理员权限检查
    '''
    admin_data_file = Path() / "data" / "admin.json"
    admin_data_file.parent.mkdir(exist_ok=True, parents=True)
    if not os.path.exists(admin_data_file):
        with open(admin_data_file, 'w', encoding="utf-8") as f:
            f.write("[]")
    with open(admin_data_file, "r", encoding="utf-8") as f:
        admin_data = json.loads(f.read())
    for i in admin_data:
        if str(event.get_session_id()) == str(i):
            return True
    return False

# 审核组权限
AUDIT = Permission(audit_checker, admin_checker)

# 审核组管理员权限
ADMIN = Permission(admin_checker)
