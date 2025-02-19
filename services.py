from __future__ import annotations

import model
from model import OrderLine
from repository import AbstractRepository


def allocate(line: OrderLine, repo: AbstractRepository, session) -> str:
    return "TODO"