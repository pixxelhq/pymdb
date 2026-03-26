from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum
from typing import TYPE_CHECKING

from yamcs.pymdb.datatypes import (
    AggregateDataType,
    ArgumentValue,
    ArrayDataType,
    ParameterValue,
)

if TYPE_CHECKING:
    from yamcs.pymdb.expressions import Expression
    from yamcs.pymdb.parameters import Parameter
    from yamcs.pymdb.expressions import ParameterMember
    from yamcs.pymdb.systems import System


class RepeatEntry:
    def __init__(
        self,
        count: int | ParameterValue | ArgumentValue,
        offset: int | ParameterValue | ArgumentValue | None = None,
    ) -> None:
        self.count: int | ParameterValue | ArgumentValue = count
        """Number of times the sequence entry repeats."""

        self.offset: int | ParameterValue | ArgumentValue | None = offset
        """Optional offset between repeated instances of the entry."""


class TimeAssociationUnit(Enum):
    SI_NANOSECOND = "si_nanosecond"
    SI_MICROSECOND = "si_microsecond"
    SI_MILLSECOND = "si_millsecond"
    SI_SECOND = "si_second"
    MINUTE = "minute"
    DAY = "day"
    JULIAN_YEAR = "julianYear"


class TimeAssociation:
    def __init__(
        self,
        parameter: Parameter | ParameterMember | str,
        *,
        instance: int = 0,
        use_calibrated_value: bool = True,
        interpolate_time: bool = True,
        offset: float | None = None,
        unit: TimeAssociationUnit = TimeAssociationUnit.SI_SECOND,
    ) -> None:
        self.parameter: Parameter | ParameterMember | str = parameter
        """Absolute time parameter used to time-tag this entry."""

        self.instance: int = instance
        """Requested instance of :attr:`parameter`."""

        self.use_calibrated_value: bool = use_calibrated_value
        """Whether to use the calibrated value of :attr:`parameter`."""

        self.interpolate_time: bool = interpolate_time
        """Whether the reference time should be projected to the current time."""

        self.offset: float | None = offset
        """Optional relative offset from the associated time."""

        self.unit: TimeAssociationUnit = unit
        """Units of :attr:`offset`."""


class ParameterEntry:
    def __init__(
        self,
        parameter: Parameter,
        bitpos: int | None = None,
        *,
        offset: int = 0,
        repeat: RepeatEntry | None = None,
        short_description: str | None = None,
        condition: Expression | None = None,
        time_association: TimeAssociation | None = None,
    ) -> None:
        self.parameter: Parameter = parameter

        self.short_description: str | None = short_description
        """Oneline description"""

        self.bitpos: int | None = bitpos
        """
        Absolute position within the container, in bits.

        If unspecified, this entry is positioned relative to the preceding
        entry.
        """

        self.offset: int = offset
        """
        Distance in bits to the preceding entry.

        While not expected, if both :attr:`bitpos` and :attr:`offset` are
        specified, the two are added together for establishing the real
        absolute bit position.
        """

        self.repeat: RepeatEntry | None = repeat
        """If set, this entry repeats according to the repeat specification."""

        self.condition: Expression | None = condition
        """If set, this entry is only present when the condition is met"""

        self.time_association: TimeAssociation | None = time_association
        """Optional timing metadata associated with this entry."""

    def __str__(self) -> str:
        return self.parameter.__str__()


class IndirectParameterEntry:
    def __init__(
        self,
        parameter_instance: Parameter | str,
        bitpos: int | None = None,
        *,
        instance: int = 0,
        use_calibrated_value: bool = True,
        alias_namespace: str | None = None,
        offset: int = 0,
        repeat: RepeatEntry | None = None,
        short_description: str | None = None,
        condition: Expression | None = None,
        time_association: TimeAssociation | None = None,
    ) -> None:
        self.parameter_instance: Parameter | str = parameter_instance
        """
        Parameter whose value contains the name or alias of the actual
        parameter to extract.
        """

        self.instance: int = instance
        """Requested instance of :attr:`parameter_instance`."""

        self.use_calibrated_value: bool = use_calibrated_value
        """Whether to use the calibrated value of :attr:`parameter_instance`."""

        self.alias_namespace: str | None = alias_namespace
        """Alias namespace for the indirect parameter name, when applicable."""

        self.short_description: str | None = short_description
        """Oneline description"""

        self.bitpos: int | None = bitpos
        """
        Absolute position within the container, in bits.

        If unspecified, this entry is positioned relative to the preceding
        entry.
        """

        self.offset: int = offset
        """
        Distance in bits to the preceding entry.

        While not expected, if both :attr:`bitpos` and :attr:`offset` are
        specified, the two are added together for establishing the real
        absolute bit position.
        """

        self.repeat: RepeatEntry | None = repeat
        """If set, this entry repeats according to the repeat specification."""

        self.condition: Expression | None = condition
        """If set, this entry is only present when the condition is met"""

        self.time_association: TimeAssociation | None = time_association
        """Optional timing metadata associated with this entry."""

    def __str__(self) -> str:
        return str(self.parameter_instance)


class ContainerEntry:
    def __init__(
        self,
        container: Container,
        short_description: str | None = None,
        bitpos: int | None = None,
        offset: int = 0,
        repeat: RepeatEntry | None = None,
        condition: Expression | None = None,
        time_association: TimeAssociation | None = None,
    ) -> None:
        self.container: Container = container

        self.short_description: str | None = short_description
        """Oneline description"""

        self.bitpos: int | None = bitpos
        """
        Absolute position within the container, in bits.

        If unspecified, this entry is positioned relative to the preceding
        entry.
        """

        self.offset: int = offset
        """
        Distance in bits to the preceding entry.

        While not expected, if both :attr:`bitpos` and :attr:`offset` are
        specified, the two are added together for establishing the real
        absolute bit position.
        """

        self.repeat: RepeatEntry | None = repeat
        """If set, this entry repeats according to the repeat specification."""

        self.condition: Expression | None = condition
        """If set, this entry is only present when the condition is met"""

        self.time_association: TimeAssociation | None = time_association
        """Optional timing metadata inherited by entries in this container."""

    def __str__(self) -> str:
        return self.container.__str__()


class Container:
    """
    A collection of entries where each entry may be another container
    or a parameter.
    """

    def __init__(
        self,
        system: System,
        name: str,
        entries: Sequence[
            ParameterEntry | IndirectParameterEntry | ContainerEntry
        ] | None = None,
        *,
        base: Container | str | None = None,
        abstract: bool = False,
        condition: Expression | None = None,
        aliases: Mapping[str, str] | None = None,
        short_description: str | None = None,
        long_description: str | None = None,
        extra: Mapping[str, str] | None = None,
        bits: int | None = None,
        rate: float | None = None,
        hint_partition: bool = False,
    ):
        self.name: str = name
        """Short name of this parameter"""

        self.system: System = system
        """System this container belongs to"""

        self.aliases: dict[str, str] = dict(aliases or {})
        """Alternative names, keyed by namespace"""

        self.short_description: str | None = short_description
        """Oneline description"""

        self.long_description: str | None = long_description
        """Multiline description"""

        self.extra: dict[str, str] = dict(extra or {})
        """Arbitrary information, keyed by name"""

        self.bits: int | None = bits
        """
        Explicit fixed size in bits. Usually unnecessary, because Yamcs
        can derive a lot from the entries.

        If provided, Yamcs can use this information to speed up parameter
        extraction, especially when this container is used as an entry
        into another container.

        If this container extends base container(s), their size should be
        included.
        """

        self.rate: float | None = rate
        """
        Expected rate in seconds.

        For example, a rate of ``2`` means: "one update every 2 seconds" (not
        "2 updates every second").

        This is used by Yamcs to determine parameter expiration. A parameter's
        realtime value is considered expired when ``1.9 * rate`` has passed
        without a new update (where ``1.9`` is a configurable tolerance multiplier).

        If ``None``, the contained parameters are not checked for expiration.
        """

        self.hint_partition: bool = hint_partition
        """
        Hint that this container's name should be used for partitioning when
        stored to Yamcs.
        """

        self.entries: list[ParameterEntry | IndirectParameterEntry | ContainerEntry] = (
            list(entries or [])
        )
        self.base: Container | str | None = base
        self.abstract: bool = abstract
        self.condition: Expression | None = condition
        """Restriction criteria for this container."""

        if name in system._containers_by_name:
            raise Exception(
                "System {} already contains a container {}".format(
                    system.qualified_name, name
                )
            )

        system._containers_by_name[name] = self

    @property
    def qualified_name(self) -> str:
        """
        Absolute path of this item covering the full system tree. For example,
        an item ``C`` in a subystem ``B`` of a top-level system ``A`` is
        represented as ``/A/B/C``
        """
        path = "/" + self.name

        parent = self.system
        while parent:
            path = "/" + parent.name + path
            parent = getattr(parent, "system", None)

        return path

    def fit_entries(self):
        """
        Automatically set a fixed size to this container based on the known entries.
        """
        if self.base:
            raise NotImplementedError()

        max_pos = 0

        prev_pos = 0
        for entry in self.entries:
            if entry.repeat:
                raise NotImplementedError(
                    "Cannot automatically determine size of repeated entries"
                )
            if isinstance(entry, ParameterEntry):
                parameter = entry.parameter
                bits = None
                if isinstance(parameter, ArrayDataType):
                    length = parameter.length
                    encoding = parameter.data_type.encoding
                    if encoding and encoding.bits:
                        if isinstance(length, ParameterValue):
                            raise Exception("Cannot determine parameter value")
                        elif isinstance(length, ArgumentValue):
                            raise Exception("Cannot determine argument value")
                        bits = length * encoding.bits
                elif isinstance(parameter, AggregateDataType):
                    raise NotImplementedError()
                elif parameter.encoding and parameter.encoding.bits:
                    bits = parameter.encoding.bits

                if not bits:
                    raise Exception(f"Cannot determine size of {entry.parameter}")

                pos = entry.bitpos
                if pos is None:
                    pos = prev_pos

                pos += entry.offset
                pos += bits

                prev_pos = pos
                if pos > max_pos:
                    max_pos = pos
            else:
                raise NotImplementedError()

        self.bits = max_pos

    def __lt__(self, other: Container) -> bool:
        return self.qualified_name < other.qualified_name

    def __str__(self) -> str:
        return self.qualified_name
