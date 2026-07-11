from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class LogLevel(Enum):
    """日志级别枚举"""
    INFO = "[INFO]"
    WARNING = "[WARNING]"
    ERROR = "[ERROR]"
    DEBUG = "[DEBUG]"
    NONE = ""

    @classmethod
    def from_string(cls, name: str) -> "LogLevel":
        """将字符串转换为 LogLevel（忽略大小写，兼容别名）"""
        alias_map = {
            "info": cls.INFO, "information": cls.INFO,
            "warn": cls.WARNING, "warning": cls.WARNING,
            "error": cls.ERROR,
            "debug": cls.DEBUG,
            "none": cls.NONE, "": cls.NONE,
        }
        key = name.strip().lower()
        if key not in alias_map:
            valid = ", ".join(cls._member_names_)
            raise ValueError(f"不支持的日志类型: '{name}'，有效值: {valid}")
        return alias_map[key]


# 全局配置
_LOG_FILE: Optional[Path] = None
_LOG_LEVEL: LogLevel = LogLevel.INFO


def configure(log_file: Optional[str | Path] = None, level: str = "info") -> None:
    """
    配置日志系统

    Args:
        log_file: 日志文件路径，为 None 则仅输出到控制台
        level: 最低输出级别（debug/info/warning/error/none）
    """
    global _LOG_FILE, _LOG_LEVEL
    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        _LOG_FILE = path
    _LOG_LEVEL = LogLevel.from_string(level)


def log(log_type: str, text: str) -> None:
    """
    输出日志

    Args:
        log_type: 日志类型（info/warning/error/debug/none）
        text: 日志文本
    """
    level = LogLevel.from_string(log_type)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = level.value
    message = f"[{timestamp}] {prefix} {text}" if prefix else f"[{timestamp}] {text}"

    # 控制台输出
    print(message)

    # 文件输出
    if _LOG_FILE is not None:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(message + "\n")
        except OSError as e:
            print(f"[{timestamp}] [ERROR] 写入日志文件失败: {e}")


