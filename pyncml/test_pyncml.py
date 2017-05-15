import os

import unittest
from datetime import datetime

import pytz
import pyncml
from pyncml import etree

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class PyncmlFileLoadTests(unittest.TestCase):

    def setUp(self):
        netcdf  = os.path.join(os.path.dirname(__file__), 'resources', "test.nc")
        out     = os.path.join(os.path.dirname(__file__), 'resources', "test_file.nc")
        ncml    = etree.parse(os.path.join(os.path.dirname(__file__), 'resources', "test.ncml")).getroot()
        self.nc = pyncml.apply(netcdf, ncml, output_file=out)

    def tearDown(self):
        self.nc.close()

    def test_global_attribute_add(self):
        self.assertEquals(self.nc.new_attribute, 'works')

    def test_global_attribute_rename(self):
        with self.assertRaises(AttributeError):
            self.nc.history
        self.assertEquals(self.nc.new_history, 'Direct read of GRIB-1 into NetCDF-Java 4 API')

    def test_global_attribute_delete(self):
        with self.assertRaises(AttributeError):
            self.nc.source

    def test_rename_and_edit_value(self):
        with self.assertRaises(AttributeError):
            self.nc.getncattr('file_format')
        self.assertEquals(self.nc.new_file_format, 'New Format')

    def test_dimension_rename(self):
        self.assertFalse('x' in self.nc.dimensions)
        self.assertTrue('new_x_dim' in self.nc.dimensions)

    def test_variable_rename(self):
        self.assertFalse('u_component_wind_true_direction_all_geometries' in self.nc.variables)
        self.assertTrue('u' in self.nc.variables)

    def test_variable_attribute_add(self):
        self.assertEquals(self.nc.variables['time'].standard_name, 'time')

    def test_variable_attribute_rename(self):
        with self.assertRaises(AttributeError):
            self.nc.variables['x'].grid_spacing
        self.assertEquals(self.nc.variables['x'].grid_cell_spacing, '4.0 km')

    def test_variable_attribute_delete(self):
        with self.assertRaises(AttributeError):
            self.nc.variables['u'].units


class PyncmlStringLoadTests(unittest.TestCase):
    def test_with_string(self):
        netcdf  = os.path.join(os.path.dirname(__file__), 'resources', "test.nc")
        out     = os.path.join(os.path.dirname(__file__), 'resources', "test_string.nc")
        ncml    = """<?xml version="1.0" encoding="UTF-8"?>
        <netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2">
            <attribute name="new_attribute" value="works" />
            <attribute name="new_history" orgName="history" />
            <attribute name="new_file_format" orgName="file_format" value="New Format" />
            <remove name="source" type="attribute" />
        </netcdf>
        """
        self.nc = pyncml.apply(netcdf, ncml, output_file=out)
        self.assertEquals(self.nc.new_attribute, 'works')


class PyncmlObjectLoadTests(unittest.TestCase):
    def test_with_string(self):
        netcdf  = os.path.join(os.path.dirname(__file__), 'resources', "test.nc")
        out     = os.path.join(os.path.dirname(__file__), 'resources', "test_object.nc")
        ncml    = etree.fromstring("""<?xml version="1.0" encoding="UTF-8"?>
        <netcdf xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2">
            <attribute name="new_attribute" value="works" />
            <attribute name="new_history" orgName="history" />
            <attribute name="new_file_format" orgName="file_format" value="New Format" />
            <remove name="source" type="attribute" />
        </netcdf>
        """)
        self.nc = pyncml.apply(netcdf, ncml, output_file=out)
        self.assertEquals(self.nc.new_attribute, 'works')


class PyncmlFilePathLoadTests(unittest.TestCase):
    def test_with_string(self):
        netcdf  = os.path.join(os.path.dirname(__file__), 'resources', "test.nc")
        out     = os.path.join(os.path.dirname(__file__), 'resources', "test_object.nc")
        ncml    = os.path.join(os.path.dirname(__file__), 'resources', "test.ncml")
        self.nc = pyncml.apply(netcdf, ncml, output_file=out)
        self.assertEquals(self.nc.new_attribute, 'works')


class PyncmlScanTests(unittest.TestCase):
    def test_scan(self):
        ncml = etree.parse(os.path.join(os.path.dirname(__file__), 'resources', "test.ncml")).getroot()
        aggregation = pyncml.scan(ncml)
        self.assertEquals(len(aggregation.members), 14)
        self.assertEquals(aggregation.starting, datetime(2014, 6, 20, 0, 0, tzinfo=pytz.utc))
        self.assertEquals(aggregation.ending, datetime(2014, 7, 19, 23, 0, tzinfo=pytz.utc))
