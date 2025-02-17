"""
A module defining interfaces for schema enforcement.
"""

# built-in
import abc as _abc
from collections import UserDict
from typing import Any as _Any
from typing import Iterator as _Iterator
from typing import MutableMapping as _MutableMapping
from typing import Tuple as _Tuple
from typing import Type as _Type
from typing import TypeVar as _TypeVar

# internal
from vcorelib.io import ARBITER as _ARBITER
from vcorelib.io.types import JsonObject as _JsonObject
from vcorelib.paths import Pathlike as _Pathlike
from vcorelib.paths import get_file_name as _get_file_name
from vcorelib.paths import normalize as _normalize
from vcorelib.paths import resource as _resource

T = _TypeVar("T", bound="Schema")


class Schema(_abc.ABC):
    """A base class for schema enforcement."""

    @_abc.abstractmethod
    def __init__(self, data: _JsonObject, **kwargs) -> None:
        """Initialize this schema."""

    @_abc.abstractmethod
    def __call__(self, data: _Any) -> _Any:
        """Validate input data and return the result."""

    @classmethod
    def from_path(cls: _Type[T], path: _Pathlike, **kwargs) -> T:
        """Load a schema from a data file on disk."""
        return cls(_ARBITER.decode(path, require_success=True).data, **kwargs)


class SchemaMap(
    UserDict,  # type: ignore
    _MutableMapping[str, Schema],
):
    """A class for managing multiple schema objects."""

    @classmethod
    @_abc.abstractmethod
    def kind(cls) -> _Type[Schema]:
        """Implement this to determine the concrete schema type."""

    def __init__(self) -> None:
        """Initialize this schema map."""
        super().__init__(self)

    def load_file(self, path: _Pathlike, **kwargs) -> _Tuple[str, Schema]:
        """Load a schema file into the map."""

        path = _normalize(path)
        name = _get_file_name(path)
        assert name not in self, f"Duplicate schema '{name}'!"
        self[name] = self.kind().from_path(path, **kwargs)
        return name, self[name]

    def load_directory(
        self, path: _Pathlike, **kwargs
    ) -> _Iterator[_Tuple[str, Schema]]:
        """Load a directory of schema files into the map."""

        path = _normalize(path)
        assert path.is_dir(), f"'{path}' isn't a directory!"
        for item in path.iterdir():
            yield self.load_file(item, **kwargs)

    def load_package(
        self,
        package: str,
        path: _Pathlike = "schemas",
        package_subdir: str = "data",
        **kwargs,
    ) -> _Iterator[_Tuple[str, Schema]]:
        """Load schemas from package data."""

        path = _resource(path, package=package, package_subdir=package_subdir)
        assert (
            path is not None and path.is_dir()
        ), f"Can't find schema directory for package '{package}'!"

        yield from self.load_directory(path, **kwargs)

    @classmethod
    def from_package(
        cls,
        package: str,
        **kwargs,
    ) -> "SchemaMap":
        """Create a new JSON-schema map from package data."""

        result = cls()
        list(result.load_package(package, **kwargs))
        return result
