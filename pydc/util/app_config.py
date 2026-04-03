import tomli as tomllib
from typing import Any, Dict, Optional
import pydc.util.constants as constants


# Singleton
_app_config: Optional[Dict] = None

def init_app_config():
    global _app_config
    if _app_config is None:
        with open(constants.APP_CONFIG_PATH, "rb") as f:
            config = tomllib.load(f)
            _app_config = config["app"]
    return _app_config

def get(key: str, default: Any = None):
    config = init_app_config() 
    return config.get(key, default)