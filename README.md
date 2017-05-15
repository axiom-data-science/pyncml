# pyncml  [![Build Status](https://travis-ci.org/axiom-data-science/pyncml.svg?branch=master)](https://travis-ci.org/axiom-data-science/pyncml)

#### A simple python library to apply NcML logic to NetCDF files


## Installation

##### Stable

```bash
$ pip install pyncml
# or
$ conda install -c conda-forge pyncml
```


##### Development

    pip install git+https://github.com/axiom-data-science/pyncml.git


## Supported

*  Adding things
    *  Attributes: `<attribute name="some_new_attribute" type="string" value="some_standard_name" />`

*  Renaming things
    *  Variables: `<variable name="new_var" orgName="old_var" />`
    *  Attributes: `<attribute name="new_attr" orgName="old_attr" />`
    *  Dimensions: `<dimension name="new_dim" orgName="old_dim" />`

*  Removing things
    *  Variables: `<remove name="some_variable" type="variable" />`
    *  Attributes: `<remove name="some_variable" type="variable" />`

*  Aggregating things
    *  Scans: `<scan location="some_directory/foo/bar/" suffix=".nc" subdirs="true" />`

## Not supported

*  Adding variables (could be implemented in the future)
*  Groups (could be implemented in the future)
*  Setting actual data values on variables (could be implemented in the future)
*  Creating a file from scratch (could be implemented in the future)
*  Removing Dimensions (not implemented in the C library)
*  Aggregation scans that utilize the `dateFormatMark` attribute (most likely will never be implemented)

## Usage

### Apply

The `apply` function takes in a path to the `input_file` NetCDF file, an `ncml` object (string, file path, or python etree `Element` object), and an optional `output_file`.  **If an output_file is not specified, the `input_file` will be edited in place**.  The object returned from the `apply` function is a netcdf4-python object, ready to be used.

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
```

### Scan

The `scan` function takes in a path to an `ncml` object (string, file path, or python etree `Element` object).

##### Results

The object returned from the `scan` function is a metadata object describing the scan aggregation **it is not a netcdf4-python object of the aggregation**.  You can create a `netcdf4-python` object from the scan aggregation (example below).

```python
ncml   = '/some/file/path/foo.ncml'
import pyncml
agg = pyncml.scan(ncml=ncml)

print(agg.starting)
2014-06-20 00:00:00+00:00

print(agg.ending)
2014-07-19 23:00:00+00:00

print(agg.timevar_name)
u'time'

print(agg.standard_names)
[
  u'time',
  u'projection_y_coordinate',
  u'projection_x_coordinate',
  u'eastward_wind_velocity'
]

print(agg.members)  # These are already sorted by the 'starting' date
[
  {
    'title':          'hello'  # Pulled from the global attraibutes 'name' or 'title'
    'starting':       datetime.datetime(2014, 6, 20, 0, 0, tzinfo=<UTC>),
    'ending':         datetime.datetime(2014, 6, 20, 0, 0, tzinfo=<UTC>),
    'path':           '/path/to/aggregation/defined/in/ncml/first_member.nc'
    'standard_names': [u'time',
                       u'projection_y_coordinate',
                       u'projection_x_coordinate',
                       u'eastward_wind_velocity'],
  },
  {
    'title':          'hello'  # Pulled from the global attraibutes 'name' or 'title'
    'starting':       datetime.datetime(2014, 6, 20, 1, 0, tzinfo=<UTC>),
    'ending':         datetime.datetime(2014, 6, 20, 1, 0, tzinfo=<UTC>),
    'path':           '/path/to/aggregation/defined/in/ncml/second_member.nc'
    'standard_names': [u'time',
                       u'projection_y_coordinate',
                       u'projection_x_coordinate',
                       u'eastward_wind_velocity'],
  },
  ...
]
```

##### Applying metadata

By default only the `scan` object in the `ncml` is used... meaning any attribute changes specified in the `ncml` **will not** be applied to individual members of the aggregation before computing the scan aggregation. If you would like each individual file to have the `ncml` applied to it (using the `apply` method documented above), set the `apply_to_members=True`. This will take longer because it is actually saving a new file with any applied `ncml` and then computing the metadata.

```python
ncml   = '/some/file/path/foo.ncml'
import pyncml
agg = pyncml.scan(ncml=ncml, apply_to_members=True)
```

##### CPUs

`scan` will utilize all cores minus 1 (`multiprocessing.cpu_count() - 1`). If you want to configure this setting use the `cpu_count=x` parameter to `scan`.

```python
ncml   = '/some/file/path/foo.ncml'
import pyncml
agg = pyncml.scan(ncml=ncml, cpu_count=2)
```



##### Creating `netcdf4-python` Aggregation object

<sup>**Note: This will not work with aggregations whose members overlap in time!**</sup>

```python
ncml   = '/some/file/path/foo.ncml'
import pyncml
agg = pyncml.scan(ncml=ncml)
files = [ f.path for f in agg.members ]
agg = netCDF4.MFDataset(files)
time = agg.variables.get(agg.timevar_name)

print(time)
<class 'netCDF4._Variable'>
float64 time('time',)
    long_name: date time
    units: hours since 1970-01-01 00:00:00
    _CoordinateAxisType: Time
unlimited dimensions = ('time',)
current size = (14,)

print(time[:])
[ 389784.  389785.  389786.  389787.  389788.  389789.  389790.  389791.
  389792.  389793.  390500.  390501.  390502.  390503.]

print(netCDF4.num2date(time[:], units=time.units))
[datetime.datetime(2014, 6, 20, 0, 0)
 datetime.datetime(2014, 6, 20, 1, 0)
 datetime.datetime(2014, 6, 20, 2, 0)
 datetime.datetime(2014, 6, 20, 3, 0)
 datetime.datetime(2014, 6, 20, 4, 0)
 datetime.datetime(2014, 6, 20, 5, 0)
 datetime.datetime(2014, 6, 20, 6, 0)
 datetime.datetime(2014, 6, 20, 7, 0)
 datetime.datetime(2014, 6, 20, 8, 0)
 datetime.datetime(2014, 6, 20, 9, 0)
 datetime.datetime(2014, 7, 19, 20, 0)
 datetime.datetime(2014, 7, 19, 21, 0)
 datetime.datetime(2014, 7, 19, 22, 0)
 datetime.datetime(2014, 7, 19, 23, 0)]
```
