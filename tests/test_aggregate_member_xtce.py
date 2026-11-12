import shutil
import subprocess
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import yamcs.pymdb as Y


class AggregateMemberXtceTest(unittest.TestCase):
    def make_system(self):
        system = Y.System("CountedArrays")
        Y.AggregateParameter(
            system=system,
            name="report",
            members=[
                Y.IntegerMember("outer_count", signed=False, encoding=Y.uint8_t),
                Y.ArrayMember(
                    "groups",
                    length=Y.AggregateMemberValue("outer_count"),
                    data_type=Y.AggregateDataType(members=[
                        Y.IntegerMember("inner_count", signed=False, encoding=Y.uint8_t),
                        Y.ArrayMember(
                            "samples",
                            length=Y.AggregateMemberValue("inner_count"),
                            data_type=Y.IntegerDataType(signed=False, encoding=Y.uint16_t),
                        ),
                    ]),
                ),
            ],
        )
        Y.ArrayParameter(
            system=system,
            name="ordinary",
            length=Y.ParameterValue("/CountedArrays/count"),
            data_type=Y.IntegerDataType(signed=False, encoding=Y.uint8_t),
        )
        return system

    def test_nested_arrays_use_type_ancillary_data(self):
        xml = self.make_system().dumps()
        root = ET.fromstring(xml)
        ns = {"x": root.tag.split("}")[0][1:]}
        arrays = root.findall(".//x:ArrayParameterType", ns)
        marked = {}
        for array in arrays:
            marker = array.find("x:AncillaryDataSet/x:AncillaryData[@name='Yamcs:AggregateMember']", ns)
            if marker is not None:
                marked[marker.text] = array
                ref = array.find(".//x:ParameterInstanceRef", ns)
                self.assertEqual(ref.attrib, {"parameterRef": marker.text})
                self.assertEqual(list(array)[0].tag.split("}")[1], "AncillaryDataSet")
        self.assertEqual(set(marked), {"inner_count", "outer_count"})
        ordinary = next(a for a in arrays if a.attrib["name"] == "ordinary")
        self.assertIsNone(ordinary.find("x:AncillaryDataSet", ns))
        self.assertNotIn("aggregateMember=", xml)
        self.assertNotIn("http://yamcs.org/schema/xtce", xml)

    @unittest.skipUnless(shutil.which("xmllint"), "xmllint is required for XSD validation")
    def test_generated_xml_validates_with_xtce_schemas(self):
        for version in ("1.2", "1.3"):
            with self.subTest(version=version):
                xml = self.make_system().dumps(format=f"xtce-{version}")
                schema = Path(__file__).parents[1] / "schema" / f"SpaceSystemV{version}.xsd"
                result = subprocess.run(
                    ["xmllint", "--noout", "--schema", str(schema), "-"],
                    input=xml, text=True, capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
