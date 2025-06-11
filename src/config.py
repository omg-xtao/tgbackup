import tomllib
from pathlib import Path
import tinydb as tb
from tinydb import where
import logging
from logging.handlers import RotatingFileHandler

if Path("config.toml").is_file():
    config_path = "config.toml"
else:
    config_path = "config_example.toml"
with open(config_path, "rb") as f:
    config_data = tomllib.load(f)


class DB:
    def __init__(self):
        self.mdb = tb.TinyDB(
            config_data["backup"]["db_json"], indent=4, separators=(",", ": ")
        )

    def get_next_msg_id(self, from_entity_id):
        if not self.mdb.get(where("from_entity_id") == from_entity_id):
            self.set_next_msg_id(from_entity_id, 1)
        return self.mdb.get(where("from_entity_id") == from_entity_id)["next_msg_id"]

    def set_next_msg_id(self, from_entity_id, value):
        self.mdb.upsert(
            {"next_msg_id": value, "from_entity_id": from_entity_id},
            where("from_entity_id") == from_entity_id,
        )


db = DB()


global_logger = logging.getLogger("global")
global_logger.setLevel(logging.DEBUG)
format_str = logging.Formatter(
    "%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s"
)
sh = logging.StreamHandler()  # 往屏幕上输出
sh.setFormatter(format_str)
global_logger.addHandler(sh)
# 滚动大小的日志处理器
file_sh = RotatingFileHandler(
    "/data/log.log", maxBytes=1024 * 1024 * 10, encoding="utf-8"
)
file_sh.setFormatter(format_str)
global_logger.addHandler(file_sh)

if __name__ == "__main__":
    for i in range(10):
        print(db.get_next_msg_id("test"))
        db.set_next_msg_id("test", i)
