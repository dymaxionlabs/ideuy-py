import json
import logging
import tempfile
from functools import partial

import fiona
import pyproj
from shapely.geometry import box, mapping, shape
from shapely.ops import transform, unary_union

from ideuy.download import download_grid

_logger = logging.getLogger(__name__)


def get_vector_bounds_and_crs(vector):
    with fiona.open(vector) as src:
        return box(*src.bounds), src.crs['init']


def reproject_shape(shp, from_crs, to_crs):
    project = partial(pyproj.transform, pyproj.Proj(from_crs),
                      pyproj.Proj(to_crs))
    return transform(project, shp)


def write_geojson(features, output_path):
    with open(output_path, "w") as f:
        d = {"type": "FeatureCollection", "features": []}
        for feat, shp in features:
            feature = {
                "type": "Feature",
                "geometry": mapping(shp),
                "properties": feat['properties'],
            }
            d["features"].append(feature)
        f.write(json.dumps(d))
    return output_path


def filter_by_aoi(aoi_vector, *, output, type_id, grid_vector):
    """
    Filter a grid vector using polygons from the AOI vector,
    and create a filtered grid GeoJSON as output.

    """
    grid_tempdir = None
    if not grid_vector:
        # Use type to download grid vector first
        grid_tempdir = tempfile.TemporaryDirectory()
        _logger.info("Download grid for type '%s' to %s", type_id,
                     grid_tempdir.name)
        grid_vector = download_grid(type_id, output_dir=grid_tempdir.name)

    # Open grid vector and filter those polygons that touch AOI
    with fiona.open(grid_vector) as src:
        grid_features = [(f, shape(f['geometry'])) for f in src]
        grid_crs = src.crs
    _logger.info("Grid cells: %d", len(grid_features))

    # Open aoi_vector, union all polygons into a single AOI polygon
    with fiona.open(aoi_vector) as src:
        aoi_polys = [shape(f['geometry']) for f in src]
        aoi_polys = [shp for shp in aoi_polys if shp.is_valid]
        aoi_crs = src.crs

    # Union over all AOI shapes to form a single AOI multipolygon,
    # in case there are many.
    aoi_poly = unary_union(aoi_polys)

    # TODO Reproject aoi_poly to grid vector CRS (usually epsg:5381)
    if aoi_crs != grid_crs:
        _logger.info("Reproject AOI polygon from CRS %s to CRS %s", aoi_crs,
                     grid_crs)
        aoi_poly = reproject_shape(aoi_poly, aoi_crs, grid_crs)

    filtered_features = [(f, s) for f, s in grid_features
                         if s.intersects(aoi_poly)]
    _logger.info("Filtered grid cells: %d", len(filtered_features))

    # Generate GeoJSON
    _logger.info("Write filtered grid GeoJSON to %s", output)
    write_geojson(filtered_features, output)

    # Delete temporary grid vector directory (if it was created previously)
    if grid_tempdir:
        grid_tempdir.cleanup()