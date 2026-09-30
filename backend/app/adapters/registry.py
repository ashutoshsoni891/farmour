"""String-keyed registries for adapter implementations (spec section 16, "Registries").

Each adapter kind registers factories at import time; the active one is chosen by config.
Adding a provider means adding a class and one `register` call, with no edits to callers.
"""

from collections.abc import Callable


class Registry[T]:
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._factories: dict[str, Callable[[], T]] = {}
        self._instances: dict[str, T] = {}

    def register(self, name: str, factory: Callable[[], T]) -> None:
        if name in self._factories:
            raise ValueError(f"{self.kind} adapter {name!r} already registered")
        self._factories[name] = factory

    def get(self, name: str) -> T:
        if name not in self._instances:
            try:
                factory = self._factories[name]
            except KeyError:
                known = ", ".join(sorted(self._factories)) or "none"
                raise LookupError(
                    f"unknown {self.kind} adapter {name!r} (known: {known})"
                ) from None
            self._instances[name] = factory()
        return self._instances[name]

    def override(self, name: str, instance: T) -> None:
        """Replace the active instance (tests only)."""
        self._instances[name] = instance

    def names(self) -> list[str]:
        return sorted(self._factories)
