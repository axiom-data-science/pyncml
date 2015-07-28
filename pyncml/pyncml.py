#!python
# coding=utf-8

import os
import glob
import shutil
import netCDF4
import tempfile
import operator
import logging
import pyncml
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
                         Did you pass in a vali file string, xml string, or etree object?")

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


def scan(ncml, apply_to_members=None):
    if isinstance(ncml, str):
        root = etree.fromstring(ncml)
    elif etree.iselement(ncml):
        root = ncml
    else:
        root = etree.parse(ncml).getroot()

    if apply_to_members is not False:
        apply_to_members = True

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

    dataset_name      = None
    dataset_starting  = None
    dataset_ending    = None
    dataset_variables = []
    dataset_members   = []

    logger.info("Processing aggregation containing {!s} files".format(len(files)))
    for i, filepath in enumerate(files):
        logger.info("Processing member ({0}/{1}) - {2} ".format(i+1, len(files), filepath))
        nc = None
        try:
            if apply_to_members is True:
                # Apply NcML
                tmp_f, tmp_fp = tempfile.mkstemp(prefix="nc")
                os.close(tmp_f)
                nc = pyncml.apply(filepath, ncml, output_file=tmp_fp)
            else:
                nc = netCDF4.Dataset(filepath)

            if dataset_name is None:
                if 'name' in nc.ncattrs():
                    dataset_name = nc.name
                elif 'title' in nc.ncattrs():
                    dataset_name = nc.title
                else:
                    dataset_name = "Pyncml Dataset"

            timevar = nc.variables.get(timevar_name)
            if timevar is None:
                logger.error("Time variable '{0}' was not found in file '{1}'. Skipping.".format(timevar_name, filepath))
                continue

            # Start/Stop of NetCDF file
            starting  = netCDF4.num2date(np.min(timevar[:]), units=timevar.units)
            ending    = netCDF4.num2date(np.max(timevar[:]), units=timevar.units)
            variables = list(filter(None, [ nc.variables[v].standard_name if hasattr(nc.variables[v], 'standard_name') else None for v in nc.variables.keys() ]))

            dataset_variables = list(set(dataset_variables + variables))

            if starting.tzinfo is None:
                starting = starting.replace(tzinfo=pytz.utc)
            if ending.tzinfo is None:
                ending = ending.replace(tzinfo=pytz.utc)
            if dataset_starting is None or starting < dataset_starting:
                dataset_starting = starting
            if dataset_ending is None or ending > dataset_ending:
                dataset_ending = ending

            member = DotDict(path=filepath, standard_names=variables, starting=starting, ending=ending)
            dataset_members.append(member)
        except BaseException:
            logger.exception("Something went wrong with {0}".format(filepath))
            continue
        finally:
            nc.close()
            try:
                os.remove(tmp_fp)
            except (OSError, UnboundLocalError):
                pass

    dataset_members = sorted(dataset_members, key=operator.attrgetter('starting'))
    return DotDict(name=dataset_name,
                   timevar_name=timevar_name,
                   starting=dataset_starting,
                   ending=dataset_ending,
                   standard_names=dataset_variables,
                   members=dataset_members)
