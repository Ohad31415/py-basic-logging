import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from basic_logging import LogLevelT, configure_logging

FILENAME = os.path.basename(__file__)


@pytest.mark.parametrize(
    "tz_offset",
    [
        timedelta(hours=0),
        timedelta(hours=2),
        timedelta(hours=-3),
    ],
)
@pytest.mark.parametrize(
    "time_fmt",
    [
        "%Y-%m-%d %H:%M:%S.%f%z",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%C",
        "%x %X %Z",
    ],
)
@pytest.mark.parametrize(
    "fmt, fields",
    [
        [
            "%(asctime)s %(levelname)s [%(filename)s:%(lineno)d] %(message)s",
            {"asctime", "levelname", "filename", "message"},
        ],
        ["[%(levelname)s]::%(asctime)s %(message)s", {"asctime", "levelname", "message"}],
    ],
)
@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR"])
@pytest.mark.parametrize(
    "static_fields", [None, {"program": "my-test", "_sig": "me"}, {"foo": "bar"}]
)
@pytest.mark.parametrize(
    "rename_fields", [{"asctime": "ts", "levelname": "log-level"}, {"message": "@msg"}]
)
@pytest.mark.parametrize("as_json", [True, False])
def test_configure_logging(
    capsys: pytest.CaptureFixture,
    as_json: bool,
    level: LogLevelT,
    tz_offset: timedelta,
    fmt: str,
    fields: dict,
    time_fmt: str,
    static_fields: dict,
    rename_fields: dict,
):
    # In a lack of a way to mock system timezone we'll just compensate manually for it,
    # keeping the logic the same.
    # We'll need to inform `freeze_time` of this machine's utc offset
    # to make this test independent of that.
    dt = datetime(2001, 3, 3, 3, 3, 3, 333333, tzinfo=timezone.utc) + tz_offset
    local2utc_offset_hours = dt.astimezone().utcoffset().total_seconds() / (60 * 60)

    # Pop the line number ahead it's too tricky to check:
    fmt = fmt.replace("%(lineno)d", "")

    with freeze_time(dt, tz_offset=local2utc_offset_hours):
        logger = configure_logging(
            "app",
            json=as_json,
            level=level,
            time_fmt=time_fmt,
            fmt=fmt,
            static_fields=static_fields,
            rename_fields=rename_fields,
        )
        level_log_method = getattr(logger, level.lower())
        level_log_method("log message")
        capture = capsys.readouterr()
        log = capture.out
        expected_base = {
            "levelname": level,
            "filename": FILENAME,
            "asctime": dt.strftime(time_fmt),
            "message": "log message",
        }
        if as_json:
            log = json.loads(capture.out)
            expected = {
                **{rename_fields.get(k, k): expected_base[k] for k in fields},
                **(static_fields or {}),
            }
        else:
            log = log.strip()
            expected = fmt % expected_base
        assert log == expected


@pytest.mark.parametrize("as_json", [True, False])
def test_configure_logging_extra(capsys: pytest.CaptureFixture, as_json: bool):
    logger = configure_logging(
        name="app",
        level="INFO",
        fmt="%(message)s",
        json=as_json,
        extra={"handlers": {"console": {"level": "ERROR"}}},
    )
    logger.info("info message that should not be outputted")
    capture = capsys.readouterr()
    assert capture.out == ""
    logger.error("error message that should be outputted")
    capture = capsys.readouterr()
    if as_json:
        assert capture.out.strip() == json.dumps(
            {"message": "error message that should be outputted"}
        )
    else:
        assert capture.out.strip() == "error message that should be outputted"
