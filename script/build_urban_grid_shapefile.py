#!/usr/bin/env python3
"""
This internal script fixes the reference grid GeoJSON for the Urban ortoimage.
Each feature represents each image ("hoja") and has a 'data_path' property with
the path where the image is stored in the data repository at IDE.

The resulting GeoJSON is already included in the ideuy package.

Requirements:
- ideuy
- beautifulsoup4
- rasterio
- shapely
- tqdm

"""
import os
from urllib.parse import urlparse

import fiona
import requests
from bs4 import BeautifulSoup
from shapely.geometry import shape

from ideuy.download import BASE_HOST, DATA_PATH, download_grid

IMAGE_FORMAT_PATH = '02_RGBI_8bits'


def list_all_images():
    res = []
    for remesa in range(1, 11):
        # Build remesa URL for 02_Ortoimagenes, and download directory listing
        url = f'{BASE_HOST}{DATA_PATH}CU_Remesa_{remesa:0>2}/02_Ortoimagenes/'
        city_dirs = list_directory(url)
        for city_dir in city_dirs:
            # Build city URL
            city_url = f'{city_dir}{IMAGE_FORMAT_PATH}/'
            urls = list_directory(city_url)
            print(city_dir, len(urls))
            res.extend(urls)
    return res


def list_directory(url):
    res = requests.get(url)
    if not res.ok:
        raise RuntimeError(
            f'Failed to list files at {url}. Please retry later.')

    # Parse HTML response
    soup = BeautifulSoup(res.content, 'html.parser')

    # Gather all file links in directory listing
    files = []
    for row in soup.table.find_all('td'):
        for link in row.find_all('a'):
            files.append(link)

    # Ignore parent directory link
    files = [f for f in files if f.text != 'Parent Directory']

    # Build list of absolute URLs for each link
    return [f'{url}{f.get("href")}' for f in files]


def build_data_path_by_coord_dictionary(urls):
    res = {}
    for url in urls:
        path = urlparse(url).path
        data_path = path[path.index(DATA_PATH) +
                         len(DATA_PATH):path.index(IMAGE_FORMAT_PATH)]
        filename = path.split('/')[-1]
        parts = filename.split('_')
        coord = parts[0]
        res[coord] = data_path
    return res


def create_urban_grid_geojson(*, original_grid, image_urls, output_dir):
    # Build dict of (MGRS coord, image dirname)
    paths_by_coord = build_data_path_by_coord_dictionary(image_urls)

    # Create a new geojson with the same schema< CRS and features than the original,
    # but with an extra column 'data_path', using the recently built map.
    dst_path = os.path.join(output_dir, 'urban_grid.geojson')
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
                coord = feat['properties']['Nombre']
                feat['properties']['data_path'] = paths_by_coord[coord]
                dst.write(feat)

    return dst_path


def main():
    output_dir = './out/'

    # First, download original urban grid
    original_grid = download_grid('urban', output_dir=output_dir)

    # List directories recursively in data repository
    image_urls = list_all_images()

    # Create new urban grid using features from original one,
    # and listings from data repository
    new_grid = create_urban_grid_geojson(original_grid=original_grid,
                                         image_urls=image_urls,
                                         output_dir=output_dir)
    print("New urban grid shapefile written at:", new_grid)


if __name__ == '__main__':
    main()
