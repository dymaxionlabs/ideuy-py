import json
import logging
import os
import tempfile
from functools import partial

import fiona
import pkg_resources
import pyproj
from shapely.geometry import box, mapping, shape
from shapely.ops import transform, unary_union

from ideuy.download import download_grid

_logger = logging.getLogger(__name__)

DATA_DIR = pkg_resources.resource_filename('ideuy', 'data')
URBAN_GRID_PATH = os.path.join(DATA_DIR, 'urban_grid.geojson')
NATIONAL_GRID_PATH = os.path.join(DATA_DIR, 'national_grid.geojson')

GRIDS_BY_TYPE = {'urban': URBAN_GRID_PATH, 'national': NATIONAL_GRID_PATH}


def get_vector_bounds_and_crs(vector):
    with fiona.open(vector) as src:
        return box(*src.bounds), src.crs['init']


def reproject_shape(shp, from_crs, to_crs):
    project = partial(pyproj.transform, pyproj.Proj(from_crs),
                      pyproj.Proj(to_crs))
    return transform(project, shp)


def flip(x, y):
    """Flips the x and y coordinate values"""
    return y, x


def filter_by_aoi(aoi_vector, *, output, type_id, grid_vector):
    """
    Filter a grid vector using polygons from the AOI vector,
    and create a filtered grid GeoJSON as output.

    """
    if not grid_vector:
        grid_vector = GRIDS_BY_TYPE[type_id]

    # Open aoi_vector, union all polygons into a single AOI polygon
    with fiona.open(aoi_vector) as src:
        aoi_polys = [shape(f['geometry']) for f in src]
        aoi_polys = [shp for shp in aoi_polys if shp.is_valid]
        aoi_crs = src.crs

    # Union over all AOI shapes to form a single AOI multipolygon,
    # in case there are many.
    aoi_poly = unary_union(aoi_polys)

    # For each feature in grid vector, filter those polygons that
    # intersect with AOI
    with fiona.open(grid_vector) as src:
        if aoi_crs != src.crs:
            raise RuntimeError("AOI vector has different CRS than grid. "
                               "Please make sure it is EPSG:5381.")

        with fiona.open(output,
                        'w',
                        driver='GeoJSON',
                        crs=src.crs,
                        schema=src.schema) as dst:
            for feat in src:
                shp = shape(feat['geometry'])
                if shp.intersects(aoi_poly):
                    dst.write(feat)
