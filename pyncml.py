#!python
# coding=utf-8

__version__ = "0.0.1"

import shutil
import netCDF4
import logging
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


def apply(input_file, ncml, output_file=None):
    if isinstance(ncml, (str, unicode,)):
        root = etree.fromstring(ncml)
    elif etree.iselement(ncml):
        root = ncml
    else:
        root = etree.parse(ncml).getroot()

    if output_file is None:
        # In place changes
        nc = netCDF4.Dataset(input_file, 'a')
    else:
        # New file
        shutil.copy(input_file, output_file)
        nc = netCDF4.Dataset(output_file, 'a')

    ncml_namespace = 'http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2'

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
