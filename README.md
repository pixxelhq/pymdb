# Yamcs PyMDB

```
pip install yamcs-pymdb
```

Use this Python library to generate XTCE XML files for use with [Yamcs Mission Control](https://yamcs.org):

```python
import yamcs.pymdb as Y

spacecraft = Y.System("Spacecraft")

param1 = Y.IntegerParameter(
    system=spacecraft,
    name="param1",
    signed=False,
    encoding=Y.uint8_t,
)

param2 = Y.EnumeratedParameter(
    system=spacecraft,
    name="param2",
    choices=[
        (0, "SUCCESS"),
        (-1, "ERROR"),
    ],
    encoding=Y.int8_t,
)

# Emit an XML that conforms to XTCE
print(spacecraft.dumps())
```

## Using a local checkout as a dependency

Other projects (e.g. [Hermes](../hermes)) may depend on this package via a
local path instead of the PyPI release, useful for developing against
unreleased changes. Reference it in the consuming project's
`requirements.txt` as:

```text
yamcs-pymdb @ file:///absolute/path/to/pymdb
```

To pick up edits without reinstalling after every change, install it in
editable mode inside the consuming project's environment instead:

```bash
pip install -e /absolute/path/to/pymdb
```

## License

LGPL-3.0. See [LICENSE](https://github.com/yamcs/pymdb/blob/master/LICENSE)

### Aggregate-local array lengths (Pixxel extension)

Use `AggregateMemberValue("member_name")` for an array length read from an
integer member of the enclosing aggregate. XML exports now put
`AncillaryData name="Yamcs:AggregateMember"` on `ArrayParameterType`, before
`DimensionList`, with the member name as the entry's text.

The older `yamcs:aggregateMember` attribute and Yamcs's
`XtceStaxReader.isAggregateMemberReference()` compatibility reader are scheduled
for deprecation soon. Legacy imports remain supported; no deprecation release
or removal date has been set. Regenerate existing XML with the updated PyMDB
to migrate to ancillary data. The `AggregateMemberValue` Python API remains
supported and is not being deprecated. See [the parameter guide](docs/parameters.rst)
for details.
