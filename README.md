# pyncml

#### A simple python library to apply NcML logic to NetCDF files


## Installation

##### Stable

    pip install pyncml

##### Development

    pip install git+https://github.com/kwilcox/pyncml.git

## Supported

  *  Adding things
    * Attributes: `<attribute name="some_new_attribute" type="string" value="some_standard_name" />`

  * Renaming things
    *  Variables: `<variable name="new_var" orgName="old_var" />`
    *  Attributes: `<attribute name="new_attr" orgName="old_attr" />`
    *  Dimensions: `<dimension name="new_dim" orgName="old_dim" />`

  * Removing things
    * Variables: `<remove name="some_variable" type="variable" />`
    * Attributes: `<remove name="some_variable" type="variable" />`

## Not supported

  *  Adding variables (could be implemented in the future)
  *  Groups (could be implemented in the future)
  *  Setting actual data values on variables (could be implemented in the future)
  *  Creating a file from scratch (could be implemented in the future)
  *  Removing Dimensions (not implemented in the C library)
  *  Any type of aggregation (will never be implemented)

## Usage

The `apply` function takes in a path to the `input_file` NetCDF file, an `ncml` object (string, file path, or python etree object), and an optional `output_file`.  **If an output_file is not specified, the `input_file` will be edited in place**.  The object returned from the `apply` function is a netcdf4-python object, ready to be used.

Any `location` attributes in the NcML are **ignored** and the NcML is applied against the file specified as the `input_file`.


##### Editing a file in place
```python
netcdf = '/some/file/path/in.nc'
ncml   = '/some/file/path/foo.ncml'
import pyncml
nc = pyncml.apply(input_file=netcdf, ncml=ncml)
```

##### Using an NcML file
```python
netcdf = '/some/file/path/in.nc'
out    = '/some/file/path/out.nc'
ncml   = '/some/file/path/foo.ncml'
import pyncml
nc = pyncml.apply(input_file=netcdf, ncml=ncml, output_file=out)
```

##### Using an NcML string
```python
netcdf = '/some/file/path/in.nc'
out    = '/some/file/path/out.nc'
ncml   = """<?xml version="1.0" encoding="UTF-8"?>
         <netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2">
             <attribute name="new_attribute" value="works" />
             <attribute name="new_history" orgName="history" />
             <attribute name="new_file_format" orgName="file_format" value="New Format" />
             <remove name="source" type="attribute" />
         </netcdf>
         """
import pyncml
nc = pyncml.apply(input_file=netcdf, ncml=ncml, output_file=out)
```

##### Using an `etree` object
```python
import pyncml
netcdf = '/some/file/path/in.nc'
out    = '/some/file/path/out.nc'
ncml   = pyncml.etree.fromstring("""<?xml version="1.0" encoding="UTF-8"?>
         <netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2">
             <attribute name="new_attribute" value="works" />
         </netcdf>
         """)
nc = pyncml.apply(input_file=netcdf, ncml=ncml, output_file=out)
