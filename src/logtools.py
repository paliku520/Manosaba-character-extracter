import queue
import sys
import threading
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

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

    @property
    def rank(self) -> int:
        """级别数值（越小越详细，用于按最低级别过滤）；NONE 无级别消息始终输出"""
        return {
            LogLevel.DEBUG: 0,
            LogLevel.INFO: 1,
            LogLevel.WARNING: 2,
            LogLevel.ERROR: 3,
            LogLevel.NONE: 99,
        }[self]

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
_LOG_STREAM = sys.stdout  # 控制台输出流（Electron 后端子进程可改为 stderr，避免污染 JSON 协议）
_ENABLE_COLOR = True       # 是否输出 ANSI 颜色（管道转发场景建议关闭，避免外部终端乱码）

# 异步日志写入：log() 只入队，由独立 daemon 线程消费写流/文件。
# 避免 stderr 管道缓冲满（Electron 终端渲染慢/下游未及时读取）时阻塞调用线程（worker）。
_LOG_QUEUE: "queue.Queue[Optional[tuple]]" = queue.Queue()
_LOG_WRITER: Optional[threading.Thread] = None
_WRITER_LOCK = threading.Lock()


def _writer_loop() -> None:
    """后台日志线程：消费队列，分别写入控制台流与文件"""
    while True:
        item = _LOG_QUEUE.get()
        if item is None:
            return
        stream_msg, file_msg, stream, log_file = item
        if stream is not None and stream_msg is not None:
            try:
                stream.write(stream_msg + "\n")
                stream.flush()
            except Exception:
                pass
        if log_file is not None and file_msg is not None:
            try:
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(file_msg + "\n")
            except OSError:
                pass


def _ensure_writer() -> None:
    """确保日志后台线程已启动（懒启动）"""
    global _LOG_WRITER
    if _LOG_WRITER is not None:
        return
    with _WRITER_LOCK:
        if _LOG_WRITER is None:
            _LOG_WRITER = threading.Thread(target=_writer_loop, name="log-writer", daemon=True)
            _LOG_WRITER.start()


def flush_logs(timeout: float = 2.0) -> None:
    """退出前同步消费日志队列直到空（确保日志完整落盘/输出）"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            item = _LOG_QUEUE.get(timeout=0.1)
        except queue.Empty:
            if _LOG_QUEUE.empty():
                return
            continue
        _writer_loop_item(item)


def _writer_loop_item(item) -> None:
    """处理单个队列条目（供 flush 与后台线程复用）"""
    stream_msg, file_msg, stream, log_file = item
    if stream is not None and stream_msg is not None:
        try:
            stream.write(stream_msg + "\n")
            stream.flush()
        except Exception:
            pass
    if log_file is not None and file_msg is not None:
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(file_msg + "\n")
        except OSError:
            pass


def configure(
    log_file: Optional[str | Path] = None,
    level: str = "info",
    stream=None,
    color: bool = True,
) -> None:
    """
    配置日志系统

    Args:
        log_file: 日志文件路径，为 None 则仅输出到控制台
        level: 最低输出级别（debug/info/warning/error/none）
        stream: 控制台输出流（默认 sys.stdout；Electron 后端子进程建议传 sys.stderr）
        color: 是否输出 ANSI 颜色（默认 True；重定向/管道转发场景建议 False 避免乱码）
    """
    global _LOG_FILE, _LOG_LEVEL, _LOG_STREAM, _ENABLE_COLOR
    if log_file is not None:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        _LOG_FILE = path
    if stream is not None:
        _LOG_STREAM = stream
    _ENABLE_COLOR = color
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


def _get_source_color(source: str) -> str:
    """来源标识颜色：PY 青色、JS 品红（区分 Python / JavaScript 日志）"""
    if not COLORAMA_AVAILABLE:
        return ""
    return Fore.MAGENTA if source == "JS" else Fore.CYAN


def log(log_type: str, text: str, source: str = "PY") -> None:
    """
    输出日志

    Args:
        log_type: 日志类型（info/warning/error/debug/none）
        text: 日志文本
        source: 日志来源标识（PY=Python / JS=JavaScript，默认 PY）
    """
    level = LogLevel.from_string(log_type)
    # 低于配置的最低级别则跳过（例如 level=info 时忽略 debug 日志）
    if _LOG_LEVEL is not None and level.rank < _LOG_LEVEL.rank:
        return
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    prefix = level.value
    src = (source.upper() or "PY").strip()

    # 构建消息：时间戳 + 来源 + 日志级别 + 内容
    if prefix:
        bracket_content = prefix[1:-1]  # 获取 INFO, WARNING 等
        full_message = f"[{timestamp}] [{src}] [{bracket_content}] {text}"
    else:
        full_message = f"[{timestamp}] [{src}] {text}"

    # 控制台输出（给来源与日志级别添加颜色；禁用颜色时输出纯文本）
    if COLORAMA_AVAILABLE and _ENABLE_COLOR and level != LogLevel.NONE:
        color, style = _get_color(level)
        src_color = _get_source_color(src)
        if prefix:
            colored_message = (
                f"[{timestamp}] "
                f"{src_color}[{src}]{Style.RESET_ALL} "
                f"{style}{color}[{bracket_content}]{Style.RESET_ALL} "
                f"{text}"
            )
        else:
            colored_message = f"[{timestamp}] {src_color}[{src}]{Style.RESET_ALL} {text}"
    else:
        colored_message = full_message

    # 异步输出（入队，后台线程写流与文件；不阻塞调用线程）
    _ensure_writer()
    _LOG_QUEUE.put((colored_message, full_message, _LOG_STREAM, _LOG_FILE))


def log_raw(text: str) -> None:
    """原样输出一行到控制台流（无时间戳/级别前缀，不进日志文件）。

    与 log() 共用同一后台写线程与队列，保证与普通日志串行输出、互不粘连
    （用于启动/退出 banner 等需要整行原样显示、且不能与日志并发写同一流导致换行丢失的场景）。
    """
    _ensure_writer()
    _LOG_QUEUE.put((str(text), None, _LOG_STREAM, None))


def clear_logs() -> int:
    """
    清理日志目录中的所有 .log 文件（含历史启动日志）

    Returns:
        删除的日志文件数量
    """
    if _LOG_FILE is None:
        return 0
    count = 0
    try:
        for f in _LOG_FILE.parent.glob("*.log"):
            try:
                f.unlink()
            except OSError:
                # 文件被占用（如编辑器打开）时退化为清空内容
                try:
                    with open(f, "w", encoding="utf-8") as fh:
                        fh.write("")
                except OSError:
                    continue
            count += 1
    except OSError:
        pass
    return count