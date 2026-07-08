from textwrap import dedent
from typing import Mapping, NamedTuple, Sequence

from yamcs.pymdb.commands import (
    ArgumentEntry,
    ArrayArgument,
    BinaryArgument,
    Command,
    FixedValueEntry,
    IntegerArgument,
    AggregateArgument,
)
from yamcs.pymdb.containers import Container, ParameterEntry
from yamcs.pymdb.datatypes import BinaryMember, IntegerMember, Epoch, BooleanMember
from yamcs.pymdb.encodings import (
    uint1_t,
    uint16_t,
    uint4_t,
    uint8_t,
    uint32_t,
    BinaryEncoding,
    IntegerEncoding,
    IntegerEncodingScheme,
    BinaryTimeEncoding
)
from yamcs.pymdb.expressions import ParameterMember, EqExpression, ArgumentMember
from yamcs.pymdb.parameters import AggregateParameter, IntegerParameter, AbsoluteTimeParameter
from yamcs.pymdb.systems import System
from yamcs.pymdb.encodings import IntegerTimeEncoding
from yamcs.pymdb.algorithms import Algorithm, InputParameter, OutputParameter, ParameterTrigger, UnnamedJavaAlgorithm

from .ccsds import CcsdsHeader, add_ccsds_header


# User settings
BASIC_TIME_SIZE = 32
FRACTIONAL_TIME_SIZE = 16

class CucTime(NamedTuple):
    epoch: Epoch
    pfield: int

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

def add_pus_header(system: System, cuctime_fields: CucTime) -> PusHeader:
    ccsds_header: CcsdsHeader = add_ccsds_header(system)
    
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
        encoding=uint4_t
    )

    pus_service_type_member = IntegerMember(
        name="pus_service_type",
        signed=False,
        encoding=uint8_t
    )
    pus_subservice_type_member = IntegerMember(
        name="pus_subservice_type",
        signed=False,
        encoding=uint8_t
    )
    pus_tm_message_type = AggregateParameter(
        system=system,
        name="pus_message_type",
        members=[
            pus_service_type_member,
            pus_subservice_type_member
        ],
    )

    pus_message_type_counter = IntegerParameter(
        system=system,
        name="pus_message_type_counter",
        signed=False,
        encoding=uint16_t
    )
    pus_tm_destination_id = IntegerParameter(
        system=system,
        name="pus_destination_id",
        signed=False,
        encoding=uint16_t
    )
    
    basic_time_member = IntegerMember(
        name="basic_time",
        signed=False,
        encoding=IntegerEncoding(
            bits=BASIC_TIME_SIZE
        )
    )
    fractional_time_member = IntegerMember(
        name="fractional_time",
        signed=False,
        encoding=IntegerEncoding(
            bits=FRACTIONAL_TIME_SIZE
        )
    )
    absolute_time = AggregateParameter(
        system=system,
        name="absolute_time",
        members=[
            basic_time_member,
            fractional_time_member
        ],
    )
    onboard_cuctime = AbsoluteTimeParameter(
        system=system,
        name="onboard_cuctime",
        encoding=BinaryTimeEncoding(
            bits=-1,
            decoder=UnnamedJavaAlgorithm(
                java=
                    f"""
                    org.yamcs.algo.TimeBinaryDecoder({{
                        type: CUC,
                        epoch: {cuctime_fields.epoch.name},
                        implicitPField: {cuctime_fields.pfield}
                    }})
                    """.strip()
            )
        )
    )
    
    pus_tm_nontime_container = Container(
        system=system,
        name="pus_space_packet",
        abstract=True,
        base=ccsds_header.tm_container,
        bits=ccsds_header.tm_container.bits + (((FRACTIONAL_TIME_SIZE // 8) + (BASIC_TIME_SIZE // 8) + 7) * 8), # type: ignore
        entries=[
            ParameterEntry(pus_tm_version),
            ParameterEntry(pus_spacecraft_time_reference_status_member),
            ParameterEntry(pus_tm_message_type),
            ParameterEntry(pus_message_type_counter),
            ParameterEntry(pus_tm_destination_id),
            ParameterEntry(absolute_time),
            ParameterEntry(
                onboard_cuctime,
                offset=-(FRACTIONAL_TIME_SIZE + BASIC_TIME_SIZE)
            )
        ],
    )

    pus_tm_time_container = Container(
        system=system,
        name="pus_time_packet",
        abstract=False,
        base=ccsds_header.tm_container,
        bits=ccsds_header.tm_container.bits + (FRACTIONAL_TIME_SIZE + BASIC_TIME_SIZE), # type: ignore
        entries=[
            ParameterEntry(absolute_time),
            ParameterEntry(
                onboard_cuctime,
                offset=-(FRACTIONAL_TIME_SIZE + BASIC_TIME_SIZE)
            )
        ],
        condition=EqExpression(
            ref=ccsds_header.tm_apid,
            value=0
        )
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
        initial_value="Present"
    )
    start_exec_flag = BooleanMember(
        name="pus_start_exec_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present",
        initial_value="NotPresent"
    )
    progress_exec_flag = BooleanMember(
        name="pus_progress_exec_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present",
        initial_value="NotPresent"
    )
    completion_flag = BooleanMember(
        name="pus_completion_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present",
        initial_value="Present"
    )
    pus_tc_acknowlegement_flags = AggregateArgument(
        name="pus_tc_acknowledgement_flags",
        members=[
            acceptance_flag,
            start_exec_flag,
            progress_exec_flag,
            completion_flag
        ]
    )
    pus_tc_service_type = IntegerArgument(
        name="pus_service_type",
        signed=False,
        encoding=uint8_t
    )
    pus_tc_subservice_type = IntegerArgument(
        name="pus_subservice_type",
        signed=False,
        encoding=uint8_t
    )
    pus_tc_source_id = IntegerArgument(
        name="pus_source_id",
        signed=False,
        encoding=uint16_t,
        default=0
    )

    pus_tc_command = Command(
        system=system,
        name="pus_space_packet",
        abstract=True,
        base=ccsds_header.tc_command,
        assignments={
            ccsds_header.tc_secondary_header.name: "Present"
        },
        arguments=[
            pus_tc_acknowlegement_flags,
            pus_tc_service_type,
            pus_tc_subservice_type,
            pus_tc_source_id
        ],
        entries=[
            FixedValueEntry(
                name="pus_tc_version",
                binary="02",
                bits=4
            ),
            ArgumentEntry(pus_tc_acknowlegement_flags),
            ArgumentEntry(pus_tc_service_type),
            ArgumentEntry(pus_tc_subservice_type),
            ArgumentEntry(pus_tc_source_id)
        ]   
    )

    pus_tc_acceptance_flag = ArgumentMember(
        pus_tc_acknowlegement_flags,
        acceptance_flag
    )
    pus_tc_start_exec_flag = ArgumentMember(
        pus_tc_acknowlegement_flags,
        start_exec_flag
    )
    pus_tc_progress_exec_flag = ArgumentMember(
        pus_tc_acknowlegement_flags,
        progress_exec_flag
    )
    pus_tc_completion_flag = ArgumentMember(
        pus_tc_acknowlegement_flags,
        completion_flag
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
        pus_tc_command
    )
