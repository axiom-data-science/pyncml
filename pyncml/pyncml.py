#!python
# coding=utf-8

import os
import glob
import shutil
import netCDF4
import logging
import tempfile
import operator
import itertools

import multiprocessing as mp

import pytz
import numpy as np
logger = logging.getLogger("pyncml")
logger.addHandler(logging.NullHandler())

try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    raise RuntimeError('You need either lxml or ElementTree')

ncml_namespace = 'http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2'


class DotDict(object):
    def __init__(self, *args, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        import pprint
        return pprint.pformat(vars(self), indent=2)


def apply(input_file, ncml, output_file=None):
    if isinstance(ncml, str) and os.path.isfile(ncml):
        root = etree.parse(ncml).getroot()
    elif isinstance(ncml, str):
        root = etree.fromstring(ncml)
    elif etree.iselement(ncml):
        root = ncml
    else:
        raise ValueError("Could not parse ncml. \
                         Did you pass in a valid file path, xml string, or etree Element object?")

    if output_file is None:
        # In place changes
        nc = netCDF4.Dataset(input_file, 'a')
    else:
        # New file
        shutil.copy(input_file, output_file)
        nc = netCDF4.Dataset(output_file, 'a')

    # Variables
    for v in root.findall('{%s}variable' % ncml_namespace):

        var_name = v.attrib.get("name")
        if var_name is None:
            logger.error("No 'name' attribute supplied on the <variable /> tag.  Skipping.")
            continue

        # First, rename variable
        old_var_name = v.attrib.get("orgName")
        if old_var_name is not None and var_name is not None:
            logger.debug("Renaming variable from '{0}' to '{1}'".format(old_var_name, var_name))
            nc.renameVariable(old_var_name, var_name)

        ncvar = nc.variables.get(var_name)
        if ncvar is None:
            logger.error("Variabe {0} not found in NetCDF file.  Skipping.".format(var_name))
            continue

        # Add/Remove attributes
        for a in v.findall('{%s}attribute' % ncml_namespace):
            process_attribute_tag(ncvar, a)

        # Removals
        for r in v.findall('{%s}remove' % ncml_namespace):
            if r.attrib.get("type") == "attribute":
                logger.debug("Removing attribute '{0}' from variable '{1}'".format(r.attrib.get("name"), var_name))
                ncvar.delncattr(r.attrib.get("name"))

    # Global attributes
    for a in root.findall('{%s}attribute' % ncml_namespace):
        process_attribute_tag(nc, a)

    # Dimensions
    for d in root.findall('{%s}dimension' % ncml_namespace):
        dim_name = d.attrib.get('name')
        old_dim_name = d.attrib.get('orgName')
        if old_dim_name is not None:
            logger.debug("Renaming dimension from '{0}'' to '{1}''".format(old_dim_name, dim_name))
            nc.renameDimension(old_dim_name, dim_name)

    # Global removals
    for r in root.findall('{%s}remove' % ncml_namespace):
        if r.attrib.get("type") == "attribute":
            logger.debug("Removing global attribute '{0}'".format(r.attrib.get('name')))
            nc.delncattr(r.attrib.get("name"))

    nc.sync()
    return nc


def process_attribute_tag(target, a):
    attr_name  = a.attrib.get("name")
    if attr_name is None:
        logger.error("No 'name' attribute supplied on the <attribute /> tag.  Skipping.")
        return

    tipe  = a.attrib.get("type")
    value = a.attrib.get("value")

    # First, reaname attribute
    old_attr_name = a.attrib.get('orgName')
    if old_attr_name is not None:
        logger.debug("Renaming attribute from '{0}'' to '{1}''".format(old_attr_name, attr_name))
        target.setncattr(attr_name, target.getncattr(old_attr_name))
        target.delncattr(old_attr_name)

    if value is not None:
        if tipe is not None:
            if tipe.lower() in ['float', 'double']:
                value = float(value)
            elif tipe.lower() in ['int', 'long', 'short']:
                value = int(value)
        logger.debug("Setting attribute '{0}' to '{1!s}''".format(attr_name, value))
        target.setncattr(attr_name, value)


def scan(ncml, apply_to_members=False, cpu_count=None):

    cpu_count = cpu_count or max(mp.cpu_count() - 1, 1)

    if isinstance(ncml, str) and os.path.isfile(ncml):
        root = etree.parse(ncml).getroot()
    elif isinstance(ncml, str):
        root = etree.fromstring(ncml)
    elif etree.iselement(ncml):
        root = ncml
    else:
        raise ValueError("Could not parse ncml. \
                         Did you pass in a valid file path, xml string, or etree Element object?")

    agg = root.find('{%s}aggregation' % ncml_namespace)
    if agg is None:
        logger.debug("No <aggregation /> element found")
        return dict()
    timevar_name = agg.attrib.get("dimName")

    scan = agg.find('{%s}scan' % ncml_namespace)
    if scan is None:
        logger.debug("No <scan /> element found")
        return dict()

    location = os.path.abspath(scan.attrib.get('location'))
    if os.path.isfile(location):
        files = [os.path.abspath(location)]
    else:
        suffix   = scan.attrib.get('suffix')
        subdirs  = scan.attrib.get('subdirs')
        files = []
        if subdirs.lower() == "true":
            files = glob.glob(os.path.join(location, "**", "*{0}".format(suffix)))
        files += glob.glob(os.path.join(location, "*{0}".format(suffix)))
    files = [ os.path.abspath(x) for x in files ]

    # Start threading
    num_files = len(files)
    logger.info("Processing aggregation containing {!s} files".format(num_files))

    pool = mp.Pool(cpu_count)
    results = []
    for i, filepath in enumerate(files):
        r = pool.apply_async(scan_file, (etree.tostring(ncml), filepath, apply_to_members, timevar_name, i + 1, num_files))
        results.append(r)

    dataset_members = []
    for r in results:
        dataset_members.append(r.get())

    pool.close()
    pool.join()

    # Generate collection stats
    dataset_members = filter(None, dataset_members)  # Remove None responses
    logger.info("Generating collection stats...")
    dataset_members = sorted(dataset_members, key=operator.attrgetter('starting'))
    if not dataset_members:
        return DotDict(timevar_name=timevar_name,
                       starting=None,
                       ending=None,
                       standard_names=None,
                       members=[])
    dataset_starting = min([ x.starting for x in dataset_members ])
    dataset_ending = max([ x.ending for x in dataset_members ])
    dataset_variables = itertools.chain.from_iterable([ m.standard_names for m in dataset_members ])
    dataset_variables = list(set(dataset_variables))

    return DotDict(timevar_name=timevar_name,
                   starting=dataset_starting,
                   ending=dataset_ending,
                   standard_names=dataset_variables,
                   members=dataset_members)


def scan_file(ncml, filepath, apply_to_members, timevar_name, num, total_num):
    logger.info("Processing member ({0}/{1}) - {2} ".format(num, total_num, filepath))

    ncml = etree.fromstring(ncml)
    nc = None
    try:
        if apply_to_members is True:
            # Apply NcML
            tmp_f, tmp_fp = tempfile.mkstemp(prefix="nc")
            os.close(tmp_f)
            nc = apply(filepath, ncml, output_file=tmp_fp)
        else:
            nc = netCDF4.Dataset(filepath)

        title = "Pyncml Dataset"
        if 'name' in nc.ncattrs():
            title = nc.name
        elif 'title' in nc.ncattrs():
            title = nc.title

        timevar = nc.variables.get(timevar_name)
        if timevar is None:
            logger.error("Time variable '{0}' was not found in file '{1}'. Skipping.".format(timevar_name, filepath))
            return None

        # Start/Stop of NetCDF file
        starting  = netCDF4.num2date(np.min(timevar[:]),
                                     units=timevar.units,
                                     calendar=getattr(timevar, 'calendar', 'standard'))
        ending    = netCDF4.num2date(np.max(timevar[:]),
                                     units=timevar.units,
                                     calendar=getattr(timevar, 'calendar', 'standard'))
        variables = list(
            filter(
                None,
                [ nc.variables[v].standard_name if hasattr(nc.variables[v], 'standard_name') else None for v in nc.variables.keys() ]
            )
        )

        if starting.tzinfo is None:
            starting = starting.replace(tzinfo=pytz.utc)
        if ending.tzinfo is None:
            ending = ending.replace(tzinfo=pytz.utc)

        return DotDict(path=filepath, standard_names=variables, title=title, starting=starting, ending=ending)
    except BaseException:
        logger.exception("Something went wrong with {0}".format(filepath))
        return None
    finally:
        nc.close()
        try:
            os.remove(tmp_fp)
        except (OSError, UnboundLocalError):
            pass
