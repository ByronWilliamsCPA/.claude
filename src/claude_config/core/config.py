"""Configuration settings for Claude Code projects."""

from typing import Literal

from pydantic import BaseModel


class Settings(BaseModel):
    """Application configuration settings.

    Attributes:
        log_level (Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]):
            Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs (bool): Whether to output logs in JSON format.
        include_timestamp (bool): Whether to include timestamps in log output.
    """

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    json_logs: bool = False
    include_timestamp: bool = True
