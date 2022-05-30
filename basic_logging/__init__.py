import logging.config
from datetime import datetime, timezone
from typing import Optional, Union

try:  # pragma: no cover
    from typing import Literal

    LogLevelT = Union[int, Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]]
except ImportError:  # pragma: no cover
    # Python 3.7 and down, we'll use typing_extensions if available -
    try:
        from typing_extensions import Literal

        LogLevelT = Union[int, Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]]
    except ModuleNotFoundError:
        LogLevelT = Union[int, str]

from pythonjsonlogger.jsonlogger import JsonFormatter

__version__ = "0.1.2"

JSON_RENAME_FIELDS = {"asctime": "timestamp", "levelname": "level"}
DEFAULT_FMT = "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s"
DEFAULT_TIME_FMT = "%Y-%m-%d %H:%M:%S.%f%z"


def _validate_parameter_exists() -> bool:  # pragma: no cover
    import sys

    return sys.version_info >= (3, 8)


class ExtendedFormatter(logging.Formatter):
    """Formatter that allows microsecond visibility + tz-aware time, utc by default"""

    def __init__(
        self,
        utc: bool = True,
        fmt: str = None,
        datefmt: str = None,
        style: str = "%",
        validate: bool = True,
    ):
        if _validate_parameter_exists():  # pragma: no cover
            super().__init__(fmt=fmt, datefmt=datefmt, style=style, validate=validate)
        else:  # pragma: no cover
            super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.utc = utc

    @property
    def tz(self) -> Optional[timezone]:
        return timezone.utc if self.utc else None

    def formatTime(
        self, record: logging.LogRecord, datefmt: str = DEFAULT_TIME_FMT
    ) -> str:
        # Make a tz-aware, tz=None will consider it in local tz
        dt = datetime.fromtimestamp(record.created).astimezone(self.tz)
        return dt.strftime(datefmt)


class CustomJsonFormatter(JsonFormatter, ExtendedFormatter):
    def __init__(
        self,
        utc: bool = True,
        fmt: str = None,
        datefmt: str = None,
        style: str = "%",
        validate: bool = True,
        static_fields: dict = None,
        **kw
    ):
        base_params = {
            "fmt": fmt,
            "datefmt": datefmt,
            "style": style,
        }
        if _validate_parameter_exists():  # pragma: no cover
            base_params["validate"] = validate
        ExtendedFormatter.__init__(self, utc=utc, **base_params)
        JsonFormatter.__init__(self, **base_params, **kw)
        self.static_fields = static_fields or {}

    def add_fields(self, log_record: dict, record, message_dict):
        log_record.update(self.static_fields)
        super().add_fields(log_record, record, message_dict)


def deepmerge(mapping: dict, *others: dict):
    """
    Merges nested dictionaries.

    >>> deepmerge(
    ...     {'foo': 'bar', 'more': {'cond': 'true', 'last': 424}},
    ...     {'num': 23, 'foo': 'not-bar', 'more': {'additional': 333}}
    ... )
    {'foo': 'not-bar', 'more': {'cond': 'true', 'last': 424, 'additional': 333}, 'num': 23}
    >>> deepmerge(
    ...     {'l0': {'l1': 'L1', 'l2': 'L2'}},
    ...     {'l0': {'l2': {'l3': 'L3'}}},
    ...     {'foo': 'bar'}
    ... )
    {'l0': {'l1': 'L1', 'l2': {'l3': 'L3'}}, 'foo': 'bar'}
    """
    mapping = mapping.copy()
    for other in others:
        for k, v in other.items():
            if k in mapping and isinstance(mapping[k], dict) and isinstance(v, dict):
                mapping[k] = deepmerge(mapping[k], v)
            else:
                mapping[k] = v
    return mapping


def configure_logging(
    name: str,
    *,
    level: LogLevelT = "INFO",
    fmt: str = DEFAULT_FMT,
    time_fmt: str = DEFAULT_TIME_FMT,
    utc: bool = True,
    json: bool = True,
    rename_fields: dict = JSON_RENAME_FIELDS,  # noqa
    static_fields: dict = None,
    extra: dict = None
) -> logging.Logger:
    """
    Console logging configuration utility.
    Parameters `rename_fields` and `static_fields` are only applicable for json logging.
    This function exposes two formatters `simple` and `json`.
    By default, the datetime is converted to utc, setting utc=False and having `%z` in fmt
    will have local time with its proper utc offset indication.

    Any additional configuration or overwriting can be done by passing `extra` dict.
    Such extra would be merged appropriately to the configuration,
    and can be used for example, to add more handlers,
    optionally using the already defined `simple`/`json` formatters.
    """
    formatter = "json" if json else "simple"
    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "simple": {
                "()": ExtendedFormatter,
                "utc": utc,
                "format": fmt,
                "datefmt": time_fmt,
            },
            "json": {
                "()": CustomJsonFormatter,
                "format": fmt,
                "datefmt": time_fmt,
                "utc": utc,
                "rename_fields": rename_fields,
                "static_fields": static_fields,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": formatter,
                "stream": "ext://sys.stdout",
            }
        },
        "loggers": {name: {"level": level, "handlers": ["console"]}},
    }
    if extra:
        cfg = deepmerge(cfg, extra)
    logging.config.dictConfig(cfg)
    return logging.getLogger(name)
