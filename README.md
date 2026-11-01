# TDMSlite

TDMSlite is a lightweight python package to write to and read from National Instruments TDMS files with no external dependencies. TDMSlite is available under an MIT license and was originally written by Aidan Benjamin.

### Usage 

TDMSlite is zero-dependency and allows for platform-agnostic read interface with NI's open standard. Write capability is planned. TDMSlite is hosted on PyPi:
```cmd
pip install tdmslite
```

The core object is `TDMSDocument`, which can be created using a binary stream or with an in-place method (`.from_file`).

```python
import tdmslite, pathlib

path = pathlib.Path("tdms_example.tdms")

document = tdmslite.TDMSDocument.from_file(path)
group = document['group name']
channel = group.channels['channel name']
raw_data = channel.data # easy!
```

### Limitations

While TDMS is an open standard, it is strangely not opinionated and allows nonstandard formats like 80-bit floats and fixed point numbers. These types are largely relics of old hardware or byproducts of FPGAs (which cannot write fixed point numbers to the filetype regardless...), but are seldom supported by third parties or NI's own extensions. 

TDMSlite aims to mostly support these niche features. Floating point numbers are all coerced into vanilla python floats, and any integer (aside from a boolean) is coerced into a python integer. Strings and booleans are preserved as independant data types, and complex casting automatically occurs where applicable. 

Data storage is done on a per-channel basis. If a channel's data cannot be embedded in an instance of Python's `array.array`, a costly list is necessary. Very large datasets full of strings will take signficantly more memory than the equivalent space on disk in the TDMS file by virtue of Python's lists and strings. The price we pay for convenience!

### References
 - [128-bit floating point numbers](https://en.wikipedia.org/wiki/Quadruple-precision_floating-point_format)
 - [80-bit floating point numbers](https://en.wikipedia.org/wiki/Extended_precision)
 - [Fixed point numbers](https://en.wikipedia.org/wiki/Fixed-point_arithmetic) (wikipedia)
 - [Fixed point numbers](https://www.ni.com/docs/en-US/bundle/labview/page/fixed-point-numbers.html) (NI)
 - [TDMS Versions](https://www.ni.com/docs/en-US/bundle/labview/page/file-format-versions.html)
 - [TDMS Standard](https://www.ni.com/en/support/documentation/supplemental/07/tdms-file-format-internal-structure.html)
 - [NI Type Descriptors](https://www.ni.com/docs/en-US/bundle/labview/page/type-descriptors.html)
