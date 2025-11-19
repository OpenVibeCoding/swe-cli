"""HTTP result type for agent adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union

import requests


@dataclass
class HttpResult:
    """Container describing the outcome of an HTTP request."""

    success: bool
    response: Union[requests.Response, None] = None
    error: Union[str, None] = None
    interrupted: bool = False
