from pathlib import Path

import nonebot
import nonebot.adapters


nonebot.adapters.__path__.append(
    str((Path(__file__).parent / "adapters").resolve())
)


from nonebot.adapters.onebot.v11 import Adapter as ONEBOT_V11Adapter
from nonebot.adapters.qzone import Adapter as QzoneAdapter


nonebot.init(driver="~fastapi+~httpx")

driver = nonebot.get_driver()
driver.register_adapter(ONEBOT_V11Adapter)
driver.register_adapter(QzoneAdapter)


nonebot.load_from_toml("pyproject.toml")

if __name__ == "__main__":
    nonebot.run()