============================
Headers and Protocol Helpers
============================

XTCE document headers
=====================

.. index:: Header
.. index:: History
.. index:: ValidationStatus

A ``System`` may carry an XTCE ``Header`` with document-level metadata.
``validation_status`` is mandatory and accepts either a
``ValidationStatus`` enum member or its XTCE string value. Version, date,
classification, classification instructions, authors and version history
are optional:

.. code-block:: python

   metadata = Y.Header(Y.ValidationStatus.WORKING)
   metadata.set_version("1.0")
   metadata.set_date("2026-10-09")
   metadata.set_classification("NotClassified")
   metadata.add_author("Flight Software Team")
   metadata.add_history(
       Y.History("1.0", date="2026-10-09", message="Initial release")
   )

   spacecraft = Y.System("Spacecraft", header=metadata)


Packet protocol helpers
=======================

.. index:: CCSDS
.. index:: CSP

Many missions prefix their telemetry and telecommands with a standard
header. Two common ones are CCSDS Space Packets and the CubeSat Space
Protocol (CSP); other standard and mission-specific headers exist but are
not covered here. PyMDB ships ready-made helpers for CCSDS and CSP, in the
``yamcs.pymdb.ccsds`` and ``yamcs.pymdb.csp`` modules. Each helper adds the
header parameters, an abstract telemetry container and an abstract command
to a system, and returns handles to everything it created — so your own
packets and commands can extend them.

These helpers are also worth reading as *source code*: they are compact,
idiomatic examples of container/command inheritance, and a template for
writing an equivalent helper for a mission-specific header.


CCSDS Space Packets
===================

.. index:: CcsdsHeader

``ccsds.add_ccsds_header(system)`` models the 6-byte primary header of
CCSDS 133.0-B-1. The system must provide an ``apids`` item in ``extra``.
Its value is a JSON object mapping display names to numeric APID strings.
The helper uses this mapping for telemetry and command enumerations. It
returns a ``CcsdsHeader`` named tuple with:

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Field
     - Contents
   * - ``tm_container``
     - Abstract container ``ccsds_space_packet`` with the primary header
   * - ``tm_version``, ``tm_type``, ``tm_secondary_header``, ``tm_apid``
     - ``ParameterMember`` references into the header, ready for use in
       conditions
   * - ``tc_command``
     - Abstract command ``ccsds_space_packet`` encoding the header
   * - ``tc_secondary_header``, ``tc_apid``
     - The command's free arguments

Telemetry packets extend ``tm_container`` and identify themselves by APID
(and other fields as needed):

.. code-block:: python

   import yamcs.pymdb as Y
   from yamcs.pymdb import ccsds

   spacecraft = Y.System(
       "Spacecraft",
       extra={"apids": '{"EPS Housekeeping": "101"}'},
   )
   header = ccsds.add_ccsds_header(spacecraft)

   eps_hk = Y.Container(
       system=spacecraft,
       name="eps_hk",
       base=header.tm_container,
       condition=Y.eq(header.tm_apid, 101),
       entries=[
           # payload fields, positioned after the primary header
       ],
   )

Commands extend ``tc_command``, typically through an intermediate abstract
command that pins the APID once and adds a mission-specific field such as
a command ID:

.. code-block:: python

   command_id = Y.IntegerArgument(name="command_id", signed=False,
                                  encoding=Y.uint16_t)

   project_command = Y.Command(
       system=spacecraft,
       name="MyProjectPacket",
       abstract=True,
       base=header.tc_command,
       assignments={
           header.tc_secondary_header.name: "NotPresent",
           header.tc_apid.name: 101,
       },
       arguments=[command_id],
   )

   reboot = Y.Command(
       system=spacecraft,
       name="Reboot",
       base=project_command,
       assignments={command_id.name: 1},
   )

In the generated command, the sequence count and packet length fields are
zeroed fixed-value entries: Yamcs fills them in during link
post-processing.


PUS packets
===========

.. index:: PusHeader
.. index:: CucTime

``pus.add_pus_header(system, cuctime_fields)`` layers PUS telemetry and
telecommand secondary headers on top of the CCSDS helper. It therefore
uses the same JSON ``apids`` configuration. Reserve APID 0 for the time
packet; the remaining APIDs are treated as ordinary PUS packets.

``cuctime_fields`` is a ``pus.CucTime`` with the epoch and implicit CUC
P-field passed to Yamcs's binary time decoder:

.. code-block:: python

   from yamcs.pymdb import pus

   spacecraft = Y.System(
       "Spacecraft",
       extra={"apids": '{"Time": "0", "PUS": "1"}'},
   )
   pus_header = pus.add_pus_header(
       spacecraft,
       cuctime_fields=pus.CucTime(epoch=Y.Epoch.UNIX, pfield=46),
   )

The returned ``PusHeader`` exposes the underlying CCSDS header, decoded
onboard CUC time, telemetry service fields and container, command
acknowledgement-flag members, command service arguments and the abstract
PUS command.


CubeSat Space Protocol
======================

.. index:: CspHeader

``csp.add_csp_header(system, ids=None, prefix="csp_")`` models the 32-bit
CSP 1.x header, with its priority, source/destination addresses and ports,
and the HMAC/XTEA/RDP/CRC flags.

``ids``
    Optional list of ``(address, name)`` pairs, in the same format as
    enumeration choices (see :doc:`../parameters`). When given, the source
    and destination fields become enumerations instead of plain integers,
    so Yamcs displays node names.

``prefix``
    Prefix for all generated names (default ``csp_``), allowing several
    header sets in one system.

The returned ``CspHeader`` named tuple exposes the telemetry container
(``tm_container``), the abstract command (``tc_container``), and each
individual parameter and argument (``tm_pri``, ``tm_src``, ``tm_dst``,
``tm_dport``, ``tm_sport``, flag parameters, and the ``tc_*``
equivalents).

.. code-block:: python

   import yamcs.pymdb as Y

   satellite = Y.System("MySat")
   csp = Y.csp.add_csp_header(satellite, ids=[
       (1, "UHF Radio"),
       (3, "FC"),
       (4, "EPS"),
   ])

   eps_telemetry = Y.Container(
       system=satellite,
       name="eps_telemetry",
       base=csp.tm_container,
       condition=Y.all_of(
           Y.eq(csp.tm_src, "EPS"),
           Y.eq(csp.tm_dport, 7),
       ),
   )

As with CCSDS, commands derive from ``csp.tc_container``, assigning the
destination address and port per subsystem or service.

The returned handles are ordinary PyMDB objects and can be adjusted after
the call — for example setting ``csp.tc_src.default`` to the ground
station's own address, or filling in ``choices`` on the address fields
later, once the node list is assembled.
