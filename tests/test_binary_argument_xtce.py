import unittest
import xml.etree.ElementTree as ET

import yamcs.pymdb as Y


XTCE = {"x": "http://www.omg.org/spec/XTCE/20180204"}


class BinaryArgumentXtceTest(unittest.TestCase):
    def test_embedded_tc_is_opt_in_for_binary_arguments(self):
        system = Y.System("Commands")
        Y.Command(
            system,
            "send",
            arguments=[
                Y.BinaryArgument("packet", embedded_tc=True),
                Y.BinaryArgument("payload"),
            ],
        )
        root = ET.fromstring(system.dumps())
        marked_types = root.findall(
            './/x:BinaryArgumentType/x:AncillaryDataSet/'
            'x:AncillaryData[@name="Yamcs:EmbeddedTc"]/../..',
            XTCE,
        )
        self.assertEqual([element.get("name") for element in marked_types], ["send__packet"])

    def test_embedded_tc_member_keeps_metadata_on_the_member(self):
        system = Y.System("Commands")
        scheduled = Y.AggregateArgument(
            "scheduled",
            members=[
                Y.BinaryMember(
                    "packet",
                    embedded_tc=True,
                    min_length=11,
                    max_length=256,
                    extra={"owner": "scheduler"},
                ),
            ],
        )
        Y.Command(system, "insert", arguments=[scheduled])
        root = ET.fromstring(system.dumps())

        member = root.find('.//x:Member[@name="packet"]', XTCE)
        packet_type = root.find(
            f'.//x:BinaryArgumentType[@name="{member.get("typeRef")}"]', XTCE
        )
        self.assertEqual(
            [(item.get("name"), item.text) for item in member.findall(
                "x:AncillaryDataSet/x:AncillaryData", XTCE
            )],
            [("owner", "scheduler")],
        )
        self.assertEqual(
            [(item.get("name"), item.text) for item in packet_type.findall(
                "x:AncillaryDataSet/x:AncillaryData", XTCE
            )],
            [("Yamcs", "minLength=11"), ("Yamcs", "maxLength=256"), ("Yamcs:EmbeddedTc", None)],
        )
