#!/usr/bin/env python3
"""
This internal script adds the 'data_path' property to the original National
grid shapefile.  Each feature represents each image ("hoja") and has a
'data_path' property with the path where the image is stored in the data
repository at IDE.

The resulting shapefile is already included in the ideuy package.

"""
import os

import fiona

from ideuy.download import BASE_HOST, DATA_PATH, download_grid


def create_national_grid_geojson(*, original_grid, output_dir):
    # Create a new geojson with the same schema< CRS and features than the original,
    # but with an extra column 'data_path', using the recently built map.
    dst_path = os.path.join(output_dir, 'national_grid.geojson')
    with fiona.open(original_grid) as src:
        schema = src.schema.copy()
        schema['properties']['data_path'] = 'str:180'

        with fiona.open(dst_path,
                        'w',
                        driver='GeoJSON',
                        crs=src.crs,
                        schema=src.schema) as dst:
            for feat in src:
                feat = feat.copy()
                remesa = feat['properties']['Remesa']
                data_path = f'CN_Remesa_{remesa:0>2}/02_Ortoimagenes/'
                feat['properties']['data_path'] = data_path
                dst.write(feat)

    return dst_path


def main():
    output_dir = './out/'

    # First, download original urban grid
    original_grid = download_grid('national', output_dir=output_dir)

    # Create new urban grid using features from original one,
    # and listings from data repository
    new_grid = create_national_grid_geojson(original_grid=original_grid,
                                            output_dir=output_dir)
    print("New national grid shapefile written at:", new_grid)


if __name__ == '__main__':
    main()
