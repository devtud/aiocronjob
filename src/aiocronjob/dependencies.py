from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .manager import Manager

_manager: Optional["Manager"] = None


def get_manager() -> "Manager":
    global _manager
    return _manager


def set_manager(manager: "Manager") -> None:
    global _manager
    _manager = manager
