"""
A module for implementing classes that can be loaded from dictionaries and
exported as dictionaries.
"""

# built-in
import abc as _abc
from typing import Type as _Type
from typing import TypeVar as _TypeVar

# internal
from vcorelib.io import ARBITER as _ARBITER
from vcorelib.io import DataArbiter as _DataArbiter
from vcorelib.io.types import EncodeResult as _EncodeResult
from vcorelib.io.types import JsonObject as _JsonObject
from vcorelib.paths import Pathlike as _Pathlike
from vcorelib.schemas.base import SchemaMap as _SchemaMap
from vcorelib.schemas.mixins import SchemaMixin

T = _TypeVar("T", bound="DictCodec")


class DictCodec(_abc.ABC, SchemaMixin):
    """
    A class implementing an interface for objects that can be decoded from
    disk and encoded back to disk.
    """

    def __eq__(self, other) -> bool:
        """Determine if this instance is equal to another."""

        # Allow direct comparison with another dictionary, but not an arbitrary
        # mapping.
        if isinstance(other, dict):
            to_cmp = other
        else:
            to_cmp = other.asdict()

        return self.asdict() == to_cmp

    def __str__(self) -> str:
        """
        Use the dictionary representation of this instance for string
        representation.
        """
        return str(self.asdict())

    def __init__(
        self,
        data: _JsonObject,
        schemas: _SchemaMap = None,
        dest_attr: str = "data",
        verify: bool = True,
    ) -> None:
        """Initialize this instance."""

        setattr(self, dest_attr, data)

        # Validate the instance's dictionary data based on a schema.
        if schemas is not None:
            super().__init__(schemas, valid_attr=dest_attr)

        self.init(getattr(self, dest_attr))

        # After initialization, creating a new dictionary from this object
        # should be equivalent to the one provided to the constructor. This
        # can be disabled for special cases.
        if verify:
            assert self == data, f"'{self}' != '{data}' after initialization!"

    @_abc.abstractmethod
    def init(self, data: _JsonObject) -> None:
        """Perform implementation-specific initialization."""

    @_abc.abstractmethod
    def asdict(self) -> _JsonObject:
        """Obtain a dictionary representing this instance."""

    def encode(
        self, pathlike: _Pathlike, arbiter: _DataArbiter = _ARBITER, **kwargs
    ) -> _EncodeResult:
        """Encode this object instance to a file."""
        return arbiter.encode(pathlike, self.asdict(), **kwargs)

    @classmethod
    def decode(
        cls: _Type[T],
        pathlike: _Pathlike,
        arbiter: _DataArbiter = _ARBITER,
        schemas: _SchemaMap = None,
        dest_attr: str = "data",
        verify: bool = True,
        **kwargs,
    ) -> T:
        """Decode an object instance from data loaded from a file."""

        return cls(
            arbiter.decode(pathlike, require_success=True, **kwargs).data,
            schemas=schemas,
            dest_attr=dest_attr,
            verify=verify,
        )


class BasicDictCodec(DictCodec):
    """The simplest possible dictionary codec implementation."""

    def init(self, data: _JsonObject) -> None:
        """Initialize this instance."""
        self.data = data

    def asdict(self) -> _JsonObject:
        """Obtain a dictionary representing this instance."""
        return self.data
