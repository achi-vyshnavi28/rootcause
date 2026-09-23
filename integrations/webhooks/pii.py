"""Mask personal data (emails, phone numbers) before anything is written to logs."""

import logging
import re

EMAIL = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
PHONE = re.compile(r"(?<!\d)(\+?\d[\d\s-]{7,}\d)(?!\d)")


def mask(text: str) -> str:
    text = EMAIL.sub(r"\1***@\2", text)
    return PHONE.sub(lambda m: "***" + re.sub(r"\D", "", m.group(1))[-2:], text)


class PiiMaskingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = mask(record.getMessage())
        record.args = ()
        return True
