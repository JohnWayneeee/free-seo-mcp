"""Lifespan state shared by all tools: ctx.request_context.lifespan_context is an AppState."""

from dataclasses import dataclass

from .cache import DiskCache
from .config import Settings
from .http import PoliteClient


@dataclass
class AppState:
    settings: Settings
    http: PoliteClient
    cache: DiskCache
