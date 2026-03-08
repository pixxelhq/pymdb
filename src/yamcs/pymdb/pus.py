from textwrap import dedent
from typing import NamedTuple

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
    uint32_t
)
from yamcs.pymdb.expressions import ParameterMember, EqExpression, ArgumentMember
from yamcs.pymdb.parameters import AggregateParameter, IntegerParameter, AbsoluteTimeParameter
from yamcs.pymdb.systems import System
from yamcs.pymdb.encodings import IntegerTimeEncoding
from yamcs.pymdb.algorithms import Algorithm, InputParameter, OutputParameter, ParameterTrigger

from .ccsds import CcsdsHeader, add_ccsds_header

class PusHeader(NamedTuple):
    ccsds_header: CcsdsHeader

    pus_tm_service_type: ParameterMember
    pus_tm_subservice_type: ParameterMember
    pus_tm_destination_id: IntegerParameter
    pus_tm_nontime_container: Container

    pus_tc_acceptance_flag: ArgumentMember
    pus_tc_start_exec_flag: ArgumentMember
    pus_tc_progress_exec_flag: ArgumentMember
    pus_tc_completion_flag: ArgumentMember
    pus_tc_service_type: ArgumentMember
    pus_tc_subservice_type: ArgumentMember
    pus_tc_source_id: IntegerArgument
    pus_tc_command: Command

def add_pus_header(system: System) -> PusHeader:
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
        encoding=uint32_t
    )
    fractional_time_member = IntegerMember(
        name="fractional_time",
        signed=False,
        encoding=uint16_t
    )
    absolute_time = AggregateParameter(
        system=system,
        name="absolute_time",
        members=[
            basic_time_member,
            fractional_time_member
        ],
    )    
    
    pus_tm_nontime_container = Container(
        system=system,
        name="pus_space_packet",
        abstract=True,
        base=ccsds_header.tm_container,
        bits=ccsds_header.tm_container.bits + (13 * 8),
        entries=[
            ParameterEntry(pus_tm_version),
            ParameterEntry(pus_spacecraft_time_reference_status_member),
            ParameterEntry(pus_tm_message_type),
            ParameterEntry(pus_message_type_counter),
            ParameterEntry(pus_tm_destination_id),
            ParameterEntry(absolute_time)
        ],
    )

    time_exponential = IntegerParameter(
        system=system,
        name="time_exponential",
        signed=False,
        encoding=uint8_t
    )

    pus_tm_time_container = Container(
        system=system,
        name="pus_time_packet",
        abstract=False,
        base=ccsds_header.tm_container,
        bits=ccsds_header.tm_container.bits + (7 * 8),
        entries=[
            ParameterEntry(time_exponential),
            ParameterEntry(absolute_time)
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
    tm_basic_time = ParameterMember(
        absolute_time,
        path=basic_time_member,
    )
    tm_fractional_time = ParameterMember(
        absolute_time,
        path=fractional_time_member,
    )

    # FIXME: The epoch, scale and offset must be supplied outside
    onboard_time = AbsoluteTimeParameter(
        system=system,
        name="onboard_time",
        reference=Epoch.UNIX,
        encoding=IntegerTimeEncoding(
            bits=32,
            scale=0.001,
            offset=0
        )
    )
    onboard_time_algorithm = Algorithm(
        system=system,
        name="onboard_time_generation",
        language="JavaScript",
        text=dedent(
            """
            gentime.rawValue = basic.rawValue * 1000 + frac.rawValue;
            """
        ),
        outputs=[
            OutputParameter(parameter=onboard_time, name="gentime")
        ],
        triggers=[
            ParameterTrigger(parameter=absolute_time),
        ],
        inputs=[
            InputParameter(parameter=tm_basic_time, name="basic", required=True),
            InputParameter(parameter=tm_fractional_time, name="frac", required=True)
        ]
    )
    
    acceptance_flag = BooleanMember(
        name="pus_acceptance_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present"
    )
    start_exec_flag = BooleanMember(
        name="pus_start_exec_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present"
    )
    progress_exec_flag = BooleanMember(
        name="pus_progress_exec_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present"
    )
    completion_flag = BooleanMember(
        name="pus_completion_flag",
        encoding=uint1_t,
        zero_string_value="NotPresent",
        one_string_value="Present"
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
    pus_tc_message_type = AggregateArgument(
        name="pus_message_type",
        members=[
            pus_service_type_member,
            pus_subservice_type_member
        ],
    )
    pus_tc_source_id = IntegerArgument(
        name="pus_source_id",
        signed=False,
        encoding=uint16_t
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
            pus_tc_message_type,
            pus_tc_source_id
        ],
        entries=[
            FixedValueEntry(
                name="pus_tc_version",
                binary="02",
                bits=4
            ),
            ArgumentEntry(pus_tc_acknowlegement_flags),
            ArgumentEntry(pus_tc_message_type),
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
    pus_tc_service_type = ArgumentMember(
        pus_tc_message_type,
        pus_service_type_member
    )
    pus_tc_subservice_type = ArgumentMember(
        pus_tc_message_type,
        pus_subservice_type_member
    )

    return PusHeader(
        ccsds_header,
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
