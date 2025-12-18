import json
from typing import Dict, List, Optional
from config import settings
from utils.logger import logger


class DataManager:
    _instance = None
    _data = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataManager, cls).__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self):
        try:
            with open(settings.DATA_FILE, "r", encoding="utf-8") as f:
                self._data = json.load(f)
                logger.info("Data loaded successfully")
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {
                "sources": {},
                "keywords": [],
                "settings": {
                    "is_running": False,
                    "notifications": True,
                    "delay": 1.0,
                    "use_account": False,
                    "session_file": None,
                    "admins": [settings.ADMIN_ID]
                }
            }
            self.save_data()
            logger.info("Created new data file")

    def save_data(self):
        with open(settings.DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def get_data(self) -> Dict:
        return self._data

    def is_admin(self, user_id: int) -> bool:
        return user_id in self._data["settings"]["admins"]

    def add_admin(self, admin_id: int) -> bool:
        if admin_id not in self._data["settings"]["admins"]:
            self._data["settings"]["admins"].append(admin_id)
            self.save_data()
            return True
        return False

    def remove_admin(self, admin_id: int) -> bool:
        if (admin_id in self._data["settings"]["admins"] and
                admin_id != settings.ADMIN_ID):
            self._data["settings"]["admins"].remove(admin_id)
            self.save_data()
            return True
        return False

    def add_source(
        self,
        source_id: int,
        source_type: str,
        title: str,
        username: Optional[str] = None,
        discussion_chat_id: Optional[int] = None,
        parent_channel: Optional[int] = None
    ) -> bool:
        if str(source_id) not in self._data["sources"]:
            self._data["sources"][str(source_id)] = {
                "type": source_type,
                "title": title,
                "username": username,
                "processed": False
            }
            if discussion_chat_id:
                self._data["sources"][str(source_id)][
                    "discussion_chat_id"
                ] = discussion_chat_id
            if parent_channel:
                self._data["sources"][str(source_id)][
                    "parent_channel"
                ] = parent_channel
            self.save_data()
            return True
        return False

    def remove_source(self, source_id: str) -> bool:
        if source_id in self._data["sources"]:
            del self._data["sources"][source_id]
            self.save_data()
            return True
        return False

    def mark_source_processed(self, source_id: int):
        if str(source_id) in self._data["sources"]:
            self._data["sources"][str(source_id)]["processed"] = True
            self.save_data()

    def is_source_processed(self, source_id: int) -> bool:
        return self._data["sources"].get(
            str(source_id), {}
        ).get("processed", False)

    def get_all_source_ids(self) -> List[int]:
        return [int(sid) for sid in self._data["sources"].keys()]

    def add_keyword(self, keyword: str) -> bool:
        if keyword.lower() not in [
            k.lower() for k in self._data["keywords"]
        ]:
            self._data["keywords"].append(keyword)
            self.save_data()
            return True
        return False

    def remove_keyword(self, index: int) -> Optional[str]:
        if 0 <= index < len(self._data["keywords"]):
            keyword = self._data["keywords"].pop(index)
            self.save_data()
            return keyword
        return None

    def get_keywords(self) -> List[str]:
        return self._data["keywords"]

    def update_setting(self, key: str, value):
        self._data["settings"][key] = value
        self.save_data()

    def get_setting(self, key: str):
        return self._data["settings"].get(key)


data_manager = DataManager()