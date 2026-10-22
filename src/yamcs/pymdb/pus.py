from typing import NamedTuple
import json

from yamcs.pymdb.commands import (
    ArgumentEntry,
    Command,
    FixedValueEntry,
    IntegerArgument,
    AggregateArgument,
)
from yamcs.pymdb.containers import Container, ParameterEntry
from yamcs.pymdb.datatypes import IntegerMember, Epoch, BooleanMember
from yamcs.pymdb.encodings import (
    uint1_t,
    uint16_t,
    uint4_t,
    uint8_t,
    IntegerEncoding,
    BinaryTimeEncoding,
)
from yamcs.pymdb.expressions import (
    ParameterMember,
    EqExpression,
    ArgumentMember,
    NeExpression,
)
from yamcs.pymdb.parameters import (
    AggregateParameter,
    IntegerParameter,
    AbsoluteTimeParameter,
)
from yamcs.pymdb.systems import System
from yamcs.pymdb.algorithms import UnnamedJavaAlgorithm

from .ccsds import CcsdsHeader, add_ccsds_header


TIME_APID = "Time"


class CucTime(NamedTuple):
    epoch: Epoch
    pfield: int
    pfield_contd: int | None = None

    @property
    def byte_sizes(self) -> tuple[int, int]:
        """Return basic/fractional byte counts for the implicit CUC p-fields."""
        if (
            isinstance(self.pfield, bool)
            or not isinstance(self.pfield, int)
            or not 0 <= self.pfield <= 0xFF
        ):
            raise ValueError("pfield must be an integer between 0 and 255")

        basic_bytes = 1 + ((self.pfield >> 2) & 0x03)
        fractional_bytes = self.pfield & 0x03
        if self.pfield & 0x80:
            if (
                isinstance(self.pfield_contd, bool)
                or not isinstance(self.pfield_contd, int)
                or not 0 <= self.pfield_contd <= 0x7F
            ):
                raise ValueError("An extended pfield requires pfield_contd between 0 and 127")
            if self.pfield_contd & 0x03:
                raise ValueError("The reserved low two bits of pfield_contd must be zero")
            basic_bytes += (self.pfield_contd >> 5) & 0x03
            fractional_bytes += (self.pfield_contd >> 2) & 0x07
        elif self.pfield_contd is not None:
            raise ValueError("pfield_contd requires the pfield extension bit")

        if basic_bytes > 6 or fractional_bytes > 3 or basic_bytes + fractional_bytes > 8:
            raise ValueError(
                "CUC layout exceeds current Yamcs codec support: maximum 6 basic bytes, "
                "3 fractional bytes and 8 total bytes"
            )
        return basic_bytes, fractional_bytes

    @property
    def bits(self) -> int:
        """Number of time-value bits, excluding the implicit p-field octets."""
        return 8 * sum(self.byte_sizes)


class PusHeader(NamedTuple):
    ccsds_header: CcsdsHeader
    onboard_cuctime: AbsoluteTimeParameter

    pus_tm_service_type: ParameterMember
    pus_tm_subservice_type: ParameterMember
    pus_tm_destination_id: IntegerParameter
    pus_tm_nontime_container: Container

    pus_tc_acceptance_flag: ArgumentMember
    pus_tc_start_exec_flag: ArgumentMember
    pus_tc_progress_exec_flag: ArgumentMember
    pus_tc_completion_flag: ArgumentMember
    pus_tc_service_type: IntegerArgument
    pus_tc_subservice_type: IntegerArgument
    pus_tc_source_id: IntegerArgument
    pus_tc_command: Command

    cuctime_fields: CucTime
    tco_service: str | None = None


def add_pus_header(
    system: System,
    cuctime_fields: CucTime,
    *,
    tco_service: str | None = None,
) -> PusHeader:
    if tco_service is not None and not isinstance(tco_service, str):
        raise ValueError("tco_service must be a string or None")
    tco_service = (tco_service.strip() or None) if tco_service else None

    basic_bytes, fractional_bytes = cuctime_fields.byte_sizes
    time_bits = 8 * (basic_bytes + fractional_bytes)

    ccsds_header: CcsdsHeader = add_ccsds_header(system)
    ccsds_header_bits = ccsds_header.tm_container.bits
    assert ccsds_header_bits is not None

    apids: dict[str, str] = json.loads(system.extra.get("apids"))

    pus_tm_version = IntegerParameter(
        system=system,
        name="pus_version",
        signed=False,
        encoding=uint4_t,
    )
    pus_spacecraft_time_reference_status_member = IntegerParameter(
        system=system,
        name="pus_spacecraft_time_reference_status",
        signed=False,
        encoding=uint4_t,
    )

    pus_service_type_member = IntegerMember(
        name="pus_service_type", signed=False, encoding=uint8_t
    )
    pus_subservice_type_member = IntegerMember(
        name="pus_subservice_type", signed=False, encoding=uint8_t
    )
    pus_tm_message_type = AggregateParameter(
        system=system,
        name="pus_message_type",
        members=[pus_service_type_member, pus_subservice_type_member],
    )

    pus_message_type_counter = IntegerParameter(
        system=system, name="pus_message_type_counter", signed=False, encoding=uint16_t
    )
    pus_tm_destination_id = IntegerParameter(
        system=system, name="pus_destination_id", signed=False, encoding=uint16_t
    )

    rate_exponent = IntegerParameter(
        system=system,
        name="rate_exponent",
        signed=False,
        encoding=IntegerEncoding(bits=8),
    )
    basic_time_member = IntegerMember(
        name="basic_time", signed=False, encoding=IntegerEncoding(bits=8 * basic_bytes)
    )
    time_members = [basic_time_member]
    if fractional_bytes:
        time_members.append(
            IntegerMember(
                name="fractional_time",
                signed=False,
                encoding=IntegerEncoding(bits=8 * fractional_bytes),
            )
        )
    absolute_time = AggregateParameter(
        system=system,
        name="absolute_time",
        members=time_members,
    )
    time_decoder_config = {
        "type": "CUC",
        "epoch": cuctime_fields.epoch.name,
        "pField": cuctime_fields.pfield,
    }
    if cuctime_fields.pfield_contd is not None:
        time_decoder_config["pFieldCont"] = cuctime_fields.pfield_contd
    if tco_service:
        time_decoder_config["tcoService"] = tco_service
    onboard_cuctime = AbsoluteTimeParameter(
        system=system,
        name="onboard_cuctime",
        encoding=BinaryTimeEncoding(
            bits=time_bits,
            decoder=UnnamedJavaAlgorithm(
                java=f"org.yamcs.algo.TimeBinaryDecoder({json.dumps(time_decoder_config)})"
            ),
        ),
    )

    Container(
        system=system,
        name="pus_time_packet",
        abstract=False,
        base=ccsds_header.tm_container,
        bits=ccsds_header_bits + 8 + time_bits,
        entries=[
            ParameterEntry(rate_exponent),
            ParameterEntry(absolute_time),
            ParameterEntry(
                onboard_cuctime, offset=-time_bits
            ),
        ],
        condition=EqExpression(
            ref=ccsds_header.tm_apid,
            value=next((k for k, v in apids.items() if int(v) == 0), TIME_APID),
        ),
    )
    pus_tm_nontime_container = Container(
        system=system,
        name="pus_space_packet",
        abstract=True,
        base=ccsds_header.tm_container,
        bits=ccsds_header_bits + 7 * 8 + time_bits,
        entries=[
            ParameterEntry(pus_tm_version),
            ParameterEntry(pus_spacecraft_time_reference_status_member),
            ParameterEntry(pus_tm_message_type),
            ParameterEntry(pus_message_type_counter),
            ParameterEntry(pus_tm_destination_id),
            ParameterEntry(absolute_time),
            ParameterEntry(
                onboard_cuctime, offset=-time_bits
            ),
        ],
        condition=NeExpression(
            ref=ccsds_header.tm_apid,
            value=next((k for k, v in apids.items() if int(v) == 0), TIME_APID),
        ),
    )

    pus_tm_service_type = ParameterMember(
        pus_tm_message_type,
        path=pus_service_type_member,
    )
    pus_tm_subservice_type = ParameterMember(
        pus_tm_message_type,
        path=pus_subservice_type_member,
    )

    acceptance_flag = BooleanMember(
        name="pus_acceptance_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present",
        initial_value="Present",
    )
    start_exec_flag = BooleanMember(
        name="pus_start_exec_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present",
        initial_value="NotPresent",
    )
    progress_exec_flag = BooleanMember(
        name="pus_progress_exec_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present",
        initial_value="NotPresent",
    )
    completion_flag = BooleanMember(
        name="pus_completion_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present",
        initial_value="Present",
    )
    pus_tc_acknowlegement_flags = AggregateArgument(
        name="pus_tc_acknowledgement_flags",
        members=[completion_flag, progress_exec_flag, start_exec_flag, acceptance_flag],
    )
    pus_tc_service_type = IntegerArgument(
        name="pus_service_type", signed=False, encoding=uint8_t
    )
    pus_tc_subservice_type = IntegerArgument(
        name="pus_subservice_type", signed=False, encoding=uint8_t
    )
    pus_tc_source_id = IntegerArgument(
        name="pus_source_id", signed=False, encoding=uint16_t, default=0
    )

    pus_tc_command = Command(
        system=system,
        name="pus_space_packet",
        abstract=True,
        base=ccsds_header.tc_command,
        assignments={ccsds_header.tc_secondary_header.name: "Present"},
        arguments=[
            pus_tc_acknowlegement_flags,
            pus_tc_service_type,
            pus_tc_subservice_type,
            pus_tc_source_id,
        ],
        entries=[
            FixedValueEntry(name="pus_tc_version", binary="02", bits=4),
            ArgumentEntry(pus_tc_acknowlegement_flags),
            ArgumentEntry(pus_tc_service_type),
            ArgumentEntry(pus_tc_subservice_type),
            ArgumentEntry(pus_tc_source_id),
        ],
    )

    pus_tc_acceptance_flag = ArgumentMember(
        pus_tc_acknowlegement_flags, acceptance_flag
    )
    pus_tc_start_exec_flag = ArgumentMember(
        pus_tc_acknowlegement_flags, start_exec_flag
    )
    pus_tc_progress_exec_flag = ArgumentMember(
        pus_tc_acknowlegement_flags, progress_exec_flag
    )
    pus_tc_completion_flag = ArgumentMember(
        pus_tc_acknowlegement_flags, completion_flag
    )

    return PusHeader(
        ccsds_header,
        onboard_cuctime,
        pus_tm_service_type,
        pus_tm_subservice_type,
        pus_tm_destination_id,
        pus_tm_nontime_container,
        pus_tc_acceptance_flag,
        pus_tc_start_exec_flag,
        pus_tc_progress_exec_flag,
        pus_tc_completion_flag,
        pus_tc_service_type,
        pus_tc_subservice_type,
        pus_tc_source_id,
        pus_tc_command,
        cuctime_fields=cuctime_fields,
        tco_service=tco_service,
    )
