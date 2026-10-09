import yamcs.pymdb as Y
from yamcs.pymdb import pus

spacecraft = Y.System(
    "RVM",
    extra={"apids": '{"Time": "0", "PUS": "1"}'},
)
pus_header = pus.add_pus_header(
    spacecraft,
    cuctime_fields=pus.CucTime(epoch=Y.Epoch.UNIX, pfield=46),
)

with open("pus.xml", "wt") as f:
    spacecraft.dump(f)
