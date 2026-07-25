from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import sys

# 尝试导入 colorama，如果未安装则给出提示
try:
    from colorama import Fore, Style, init, just_fix_windows_console
    # 使用更可靠的 Windows 控制台修复
    if sys.platform == "win32":
        just_fix_windows_console()
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # 定义空颜色常量，避免后续引用报错
    class _DummyFore:
        CYAN = YELLOW = RED = MAGENTA = ""
    class _DummyStyle:
        BRIGHT = RESET_ALL = ""
    Fore = _DummyFore()
    Style = _DummyStyle()


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


def _get_color(level: LogLevel) -> tuple[str, str]:
    """获取日志级别对应的颜色和样式"""
    if not COLORAMA_AVAILABLE:
        return "", ""
    
    colors = {
        LogLevel.INFO: (Fore.CYAN, Style.BRIGHT),
        LogLevel.WARNING: (Fore.YELLOW, Style.BRIGHT),
        LogLevel.ERROR: (Fore.RED, Style.BRIGHT),
        LogLevel.DEBUG: (Fore.MAGENTA, Style.BRIGHT),
        LogLevel.NONE: ("", ""),
    }
    return colors.get(level, ("", ""))


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
    
    # 构建消息：时间戳 + 日志级别（方括号内）+ 内容
    if prefix:
        # 分离方括号内的内容和后面的空格
        # prefix 格式如 "[INFO]"
        bracket_content = prefix[1:-1]  # 获取 INFO, WARNING 等
        full_message = f"[{timestamp}] [{bracket_content}] {text}"
    else:
        full_message = f"[{timestamp}] {text}"

    # 控制台输出（只给方括号内的日志级别添加颜色）
    if COLORAMA_AVAILABLE and level != LogLevel.NONE:
        color, style = _get_color(level)
        if prefix:
            # 构建带颜色的消息：只给 [日志级别] 添加颜色
            colored_message = (
                f"[{timestamp}] "
                f"{style}{color}[{bracket_content}]{Style.RESET_ALL} "
                f"{text}"
            )
        else:
            colored_message = full_message
        print(colored_message)
    else:
        print(full_message)

    # 文件输出（不带颜色，保持纯文本）
    if _LOG_FILE is not None:
        try:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(full_message + "\n")
        except OSError as e:
            error_msg = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [ERROR] 写入日志文件失败: {e}"
            print(error_msg)