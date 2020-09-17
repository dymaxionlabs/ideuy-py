import logging
import os
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from urllib.request import urlopen

import fiona
import requests
from tqdm import tqdm

BASE_URL = 'https://visualizador.ide.uy/descargas/datos/'
DEFAULT_CRS = 'epsg:4326'

GRID_SHP_EXTS = ['cpg', 'dbf', 'prj', 'shp', 'shx']
GRID_PATHS_BY_TYPE = {
    'national': 'Grillas/Nacional/Articulacion_Ortoimagenes_Nacional',
    'urban': 'Grillas/Urbana/Articulacion_Ortoimagenes_Urbana',
}
TYPE_DIR = {
    'national': 'CN_Remesa_{remesa_id:0>2}',
    'urban': 'CU_Remesa_{remesa_id:0>2}'
}
PRODUCT_PATHS_BY_TYPE = {
    'rgbi_16bit':
    ['01_RGBI_16bits/{hoja_id}_RGBI_16_Remesa_{remesa_id:0>2}.tif'],
    'rgbi_8bit': ['02_RGBI_8bits/{hoja_id}_RGBI_8_Remesa_{remesa_id:0>2}.tif'],
    'rgb_8bit': [
        '03_RGB_8bits/{hoja_id}_RGB_8_Remesa_{remesa_id:0>2}' + f'.{ext}'
        for ext in ('jpg', 'jgw')
    ]
}
IMAGE_URL = BASE_URL + "{type_dir}/02_Ortoimagenes/{product_path}"

_logger = logging.getLogger(__name__)


def download_all(products, num_jobs=1, *, output_dir):
    products = add_extra_files(products)
    with ThreadPool(num_jobs) as pool:
        worker = partial(download_from_url, output_dir=output_dir)
        file_urls = [file['url'] for p in products for file in p['__files']]
        with tqdm(total=len(file_urls)) as pbar:
            for _ in enumerate(pool.imap_unordered(worker, file_urls)):
                pbar.update()


def add_extra_files(products):
    for product in products:
        new_files = []
        for file in product['__files']:
            # Workaround: add JGW file if link is a JPG:
            if file['id'].endswith('.jpg'):
                new_id = file['id'].replace('.jpg', '.jgw')
                new_url = file['url'].replace('.jpg', '.jgw')
                new_files.append(
                    dict(id=new_id, name=file['name'], url=new_url))
        product['__files'] = new_files
    return products


def download_image(*, output_dir, type_id, product_type_id, remesa_id,
                   hoja_id):
    if type_id not in ('national', 'urban'):
        raise RuntimeError(
            "Invalid type_id. Should be either 'national' or 'urban'")

    if type_id == 'urban':
        raise RuntimeError("Sorry, 'urban' type is still not supported.")

    product_paths = PRODUCT_PATHS_BY_TYPE[product_type_id]

    res = []
    for product_path in product_paths:
        t = TYPE_DIR[type_id].format(remesa_id=remesa_id)
        p = product_path.format(remesa_id=remesa_id, hoja_id=hoja_id)
        url = IMAGE_URL.format(type_dir=t, product_path=p)
        output_path = download_from_url(url, output_dir)
        res.append(output_path)
    return res


def download_feature_image(feat, *, output_dir, type_id, product_type_id):
    remesa_id = int(feat['properties']['Remesa'])
    hoja_id = feat['properties']['Nombre']
    download_image(output_dir=output_dir,
                   type_id=type_id,
                   product_type_id=product_type_id,
                   remesa_id=remesa_id,
                   hoja_id=hoja_id)


def download_images_from_grid_vector(grid_vector,
                                     num_jobs=1,
                                     *,
                                     output_dir,
                                     type_id,
                                     product_type_id):
    with fiona.open(grid_vector) as src:
        features = list(src)

    with ThreadPool(num_jobs) as pool:
        worker = partial(download_feature_image,
                         output_dir=output_dir,
                         type_id=type_id,
                         product_type_id=product_type_id)
        with tqdm(total=len(features)) as pbar:
            for _ in enumerate(pool.imap_unordered(worker, features)):
                pbar.update()


def download_grid(type_id, *, output_dir):
    if type_id not in GRID_PATHS_BY_TYPE.keys():
        raise RuntimeError("type_id is invalid")
    base_url = BASE_URL + GRID_PATHS_BY_TYPE[type_id]
    res = None
    for ext in GRID_SHP_EXTS:
        url = f'{base_url}.{ext}'
        output_path, _ = download_from_url(url, output_dir)
        if ext == 'shp':
            res = output_path
    return res


def download_from_url(url, output_dir):
    """
    Download from a URL

    @param: url to download file
    @param: dst place to put the file
    """
    _logger.info(f"Download {url} to {output_dir}")
    filename = url.split('/')[-1]
    dst = Path(output_dir) / filename

    file_size = int(urlopen(url).info().get('Content-Length', -1))
    if os.path.exists(dst):
        first_byte = os.path.getsize(dst)
    else:
        first_byte = 0
    if first_byte >= file_size:
        return file_size
    header = {"Range": "bytes=%s-%s" % (first_byte, file_size)}
    pbar = tqdm(total=file_size,
                initial=first_byte,
                unit='B',
                unit_scale=True,
                desc=url.split('/')[-1])
    req = requests.get(url, headers=header, stream=True)
    os.makedirs(output_dir, exist_ok=True)
    with open(dst, 'ab') as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                pbar.update(1024)
    pbar.close()

    return dst, file_size
