#!/usr/bin/env py.test

import os

import numpy as np
from numpy.testing import assert_allclose
from astropy.coordinates import SkyCoord

import sfdmap

# -----------------------------------------------------------------------------
# Test coordinate conversions

import os


datapath = os.path.join(os.path.dirname(__file__), "testdata")
TOL = 0.0001  # tolerance in arcseconds

# Angular separation between two points (angles in radians)
#
#   The angular separation is calculated using the Vincenty formula [1]_,
#   which is slighly more complex and computationally expensive than
#   some alternatives, but is stable at at all distances, including the
#   poles and antipodes.
#
#   [1] http://en.wikipedia.org/wiki/Great-circle_distance
def angsep(lon1, lat1, lon2, lat2):

    sdlon = np.sin(lon2 - lon1)
    cdlon = np.cos(lon2 - lon1)
    slat1 = np.sin(lat1)
    slat2 = np.sin(lat2)
    clat1 = np.cos(lat1)
    clat2 = np.cos(lat2)

    num1 = clat2 * sdlon
    num2 = clat1 * slat2 - slat1 * clat2 * cdlon
    denom = slat1 * slat2 + clat1 * clat2 * cdlon

    return np.arctan2(np.sqrt(num1*num1 + num2*num2), denom)


def rad2arcsec(r):
    return 3600. * np.rad2deg(r)

# input coordinates
fname = os.path.join(datapath, "input_coords.csv")
lat_in, lon_in = np.loadtxt(fname, skiprows=1, delimiter=',', unpack=True)


def run_sys(insys, f):
    lat_out, lon_out = f(lat_in, lon_in)

    # Read in reference answers.
    fname = os.path.join(datapath, "{}_to_gal.csv".format(insys))
    lat_ref, lon_ref = np.loadtxt(fname, skiprows=1, delimiter=',', unpack=True)
    
    # compare
    sep = angsep(lat_out, lon_out, lat_ref, lon_ref)
    maxsep = rad2arcsec(sep.max())
    #meansep = rad2arcsec(sep.mean())
    #minsep = rad2arcsec(sep.min())
    #print("{:8s} --> galactic : max={:6.4f}\"  mean={:6.4f}\"  min={:6.4f}\""
    #      .format(insys, maxsep, meansep, minsep))
    assert maxsep < TOL


def test_icrs():
    run_sys("icrs", sfdmap._icrs_to_gal)


def test_fk5j2000():
    run_sys("fk5j2000", sfdmap._fk5j2000_to_gal)


def test_icrs_scalar():
    """Test that the coordinate conversion function works with scalars"""
    
    # function that takes arrays and returns arrays, calls the coordinate
    # conversions using scalars.
    def f(lat, lon):
        lat_out = np.empty_like(lat)
        lon_out = np.empty_like(lon)
        for i in range(len(lat)):
            lat_out[i], lon_out[i] = sfdmap._icrs_to_gal(lat[i], lon[i])

        return lat_out, lon_out

    run_sys("icrs", f)


def test_bilinear_interpolate():
    f = sfdmap._bilinear_interpolate
    data = np.array([[  0.,   1.,   2.,   3.,   4.],
                     [  5.,   6.,   7.,   8.,   9.],
                     [ 10.,  11.,  12.,  13.,  14.]])

    # interpolate between [0, 1, 5, 6]
    y =   [0.5, 0.5, 2.9]
    x =   [0.5, -0.1, 2.9]
    ans = [3.0, 2.5, 12.9]
    assert_allclose(f(data, y, x), ans)

    # works on scalars?
    assert_allclose(f(data, 0.5, 0.5), 3.0)


def test_single():
    # value from http://irsa.ipac.caltech.edu/applications/DUST/
    # with input "204.0 -30.0 J2000"
    true_ebv = 0.0477

    # Use interpolate=False to match IRSA value
    ebv = sfdmap.ebv(204.0, -30.0, interpolate=False)
    assert_allclose(ebv, true_ebv, rtol=0.01)

def test_skycoord():
    import fitsio
    from astropy.io.fits import getdata

    # test with different fits readers
    for f in (fitsio.read, getdata):
        sfdmap.getdata = f
    
        coords = SkyCoord(204.0, -30.0, frame='icrs', unit='deg')

        # value from http://irsa.ipac.caltech.edu/applications/DUST/
        # with input "204.0 -30.0 J2000"
        true_ebv = 0.0477

        ebv = sfdmap.ebv(coords, interpolate=False)
        assert_allclose(ebv, true_ebv, rtol=0.01)
