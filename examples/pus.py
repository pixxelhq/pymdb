import yamcs.pymdb as Y
from yamcs.pymdb import pus

spacecraft = Y.System("RVM")
pus_header = pus.add_pus_header(spacecraft)

with open("pus.xml", "wt") as f:
    spacecraft.dump(f)
