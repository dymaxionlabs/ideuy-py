#!/usr/bin/env python3
"""
This internal script fixes creates a reference grid GeoJSON for the Urban ortoimage.
Each feature represents each image ("hoja") and has a 'data_path' property with
the path where the image is stored in the data repository at IDE.

The resulting shapefile is already included in the ideuy package.

Requirements:
- ideuy
- beautifulsoup4
- rasterio
- shapely
- tqdm

"""
import os
from glob import glob

import rasterio
import requests
from bs4 import BeautifulSoup
from shapely.geometry import box
from shapely.ops import transform
from tqdm import tqdm

from ideuy.download import BASE_HOST, DATA_PATH, download_all, download_grid
from ideuy.vector import (flip, get_vector_bounds_and_crs, reproject_shape,
                          write_geojson)


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


def create_urban_grid_geojson(output_dir):
    features = []
    remesa_dirs = sorted(glob(os.path.join(output_dir, DATA_PATH[1:], '*')))

    print("Building grid features...")
    for remesa_dir in remesa_dirs:
        remesa = remesa_dir.split('/')[-1]
        city_dirs = sorted(glob(os.path.join(remesa_dir, '*', '*')))

        for city_dir in city_dirs:
            city_id = city_dir.split('/')[-1].split('_')[-1]
            images = sorted(glob(os.path.join(city_dir, '*', '*.jpg')))

            for image in tqdm(images):
                with rasterio.open(image) as src:
                    minx, miny, maxx, maxy = src.bounds
                bbox = box(minx, miny, maxx, maxy)
                bbox = reproject_shape(bbox, 'epsg:5382', 'epsg:4326')
                bbox = transform(flip, bbox)
                name, _ = os.path.splitext(os.path.basename(image))
                mgrs_coord = name.split('_')[0]

                image_dirname = os.path.dirname(image)
                data_path = image_dirname[image_dirname.index(DATA_PATH) +
                                          len(DATA_PATH):image_dirname.
                                          index('03_RGB_8bits')]

                feature = {
                    'properties': {
                        'id': name,
                        'remesa': remesa,
                        'city_id': city_id,
                        'mgrs_coord': mgrs_coord,
                        'data_path': data_path
                    }
                }
                features.append((feature, bbox))

    dst = os.path.join(output_dir, 'urban_grid.geojson')
    return write_geojson(features, dst)


def main():
    output_dir = './out/'
    num_jobs = 4

    # First, download original urban grid
    download_grid('urban', output_dir=output_dir)

    # For each remesa, list directories:
    image_urls = []
    for remesa in range(1, 11):
        # Build remesa URL for 02_Ortoimagenes, and download directory listing
        url = f'{BASE_HOST}{DATA_PATH}CU_Remesa_{remesa:0>2}/02_Ortoimagenes/'
        city_dirs = list_directory(url)

        for city_dir in city_dirs:
            # Build city URL for 03_RGB_8bits (JPG files)
            city_url = f'{city_dir}03_RGB_8bits/'
            urls = list_directory(city_url)
            print(city_dir, len(urls))
            image_urls.extend(urls)

    # Download at most 16kb of each image, we only want to know the image size
    # Also, keep original dir structure.
    download_all(image_urls,
                 num_jobs=num_jobs,
                 output_dir=output_dir,
                 flatten=False,
                 file_size=16 * 1024)

    path = create_urban_grid_geojson(output_dir)
    print("New urban grid shapefile written at:", path)


if __name__ == '__main__':
    main()
