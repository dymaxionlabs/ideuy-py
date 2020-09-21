import logging
import os
from functools import partial
from multiprocessing.pool import ThreadPool
from urllib.parse import urlparse
from urllib.request import urlopen

import fiona
import requests
from tqdm import tqdm

BASE_HOST = 'https://visualizador.ide.uy'
DATA_PATH = '/descargas/datos/'
DEFAULT_CRS = 'epsg:4326'

# deprecated: move to script/build_*
GRID_SHP_EXTS = ['cpg', 'dbf', 'prj', 'shp', 'shx']
GRID_PATHS_BY_TYPE = {
    'national': 'Grillas/Nacional/Articulacion_Ortoimagenes_Nacional',
    'urban': 'Grillas/Urbana/Articulacion_Ortoimagenes_Urbana',
}

DIRS_BY_FORMAT = {
    'rgbi_16bit': '01_RGBI_16bits',
    'rgbi_8bit': '02_RGBI_8bits',
    'rgb_8bit': '03_RGB_8bits'
}
FORMAT_PART_BY_FORMAT = {
    'rgbi_16bit': 'RGBI_16',
    'rgbi_8bit': 'RGBI_16',
    'rgb_8bit': 'RGB_8'
}
FILE_ID_BY_TYPE = {
    'national': '{coord}_{format}_Remesa_{remesa_id:0>2}',
    'urban': '{coord}_{format}_Remesa_{remesa_id:0>2}_{city_id}'
}
EXTS_BY_FORMAT = {
    'rgbi_16bit': ['tif'],
    'rgbi_8bit': ['tif'],
    'rgb_8bit': ['jpg', 'jgw']
}

# deprecated
IMAGE_URL = f'{BASE_HOST}{DATA_PATH}' '{type_dir}/02_Ortoimagenes/{product_path}'

_logger = logging.getLogger(__name__)


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


def download_feature_image(feat, *, output_dir, type_id, product_type_id):
    props = feat['properties']
    coord = props['Nombre']
    data_path = props['data_path']
    download_image(output_dir=output_dir,
                   type_id=type_id,
                   product_type_id=product_type_id,
                   data_path=data_path,
                   coord=coord)


def download_image(dry_run=False,
                   *,
                   output_dir,
                   type_id,
                   product_type_id,
                   data_path,
                   coord):
    if type_id not in ('national', 'urban'):
        raise RuntimeError(
            "Invalid type_id. Should be either 'national' or 'urban'")

    format_part = FORMAT_PART_BY_FORMAT[product_type_id]
    remesa_id = int(data_path.split('/')[0].split('_')[2])  # e.g CU_Remesa_03/...
    if type_id == 'natioanl':
        name = FILE_ID_BY_TYPE[type_id].format(coord=coord,
                                               format=format_part,
                                               remesa_id=remesa_id)
    else:
        city_id = [p for p in data_path.split('/') if p][-1].split('_')[-1]
        name = FILE_ID_BY_TYPE[type_id].format(coord=coord,
                                               format=format_part,
                                               remesa_id=remesa_id,
                                               city_id=city_id)
    exts = EXTS_BY_FORMAT[product_type_id]
    filenames = [f'{name}.{ext}' for ext in exts]

    product_type_dir = DIRS_BY_FORMAT[product_type_id]
    urls = [
        f'{BASE_HOST}{DATA_PATH}{data_path}{product_type_dir}/{filename}'
        for filename in filenames
    ]

    # Workaround: for some reason, CU_Remesa_10 contains JPG2000 files, which
    # have extensions .jp2/.j2w instead of .jpg/.jgw
    if type_id == 'urban' and remesa_id == 10:
        urls = [
            url.replace('.jpg', '.jp2').replace('.jgw', '.j2w') for url in urls
        ]

    res = []
    for url in urls:
        res.append(download_from_url(url, output_dir))
    return res


def download_all(urls,
                 num_jobs=1,
                 file_size=None,
                 flatten=True,
                 *,
                 output_dir):
    with ThreadPool(num_jobs) as pool:
        worker = partial(download_from_url,
                         output_dir=output_dir,
                         flatten=flatten,
                         file_size=file_size)
        with tqdm(total=len(urls)) as pbar:
            for _ in enumerate(pool.imap_unordered(worker, urls)):
                pbar.update()


# deprecated: move to script/build_*
def download_grid(type_id, *, output_dir):
    if type_id not in GRID_PATHS_BY_TYPE.keys():
        raise RuntimeError("type_id is invalid")
    base_url = f'{BASE_HOST}{DATA_PATH}{GRID_PATHS_BY_TYPE[type_id]}'
    res = None
    for ext in GRID_SHP_EXTS:
        url = f'{base_url}.{ext}'
        output_path, _ = download_from_url(url, output_dir)
        if ext == 'shp':
            res = output_path
    return res


def download_from_url(url, output_dir, file_size=None, flatten=True):
    """
    Download from a URL

    @param: url to download file
    @param: output_dir place to put the file
    @param: file_size specify the output file size, only downloads up to this point
    @param: flatten: keep original dir structure in URL or not
    """
    _logger.info(f"Download {url} to {output_dir}")

    # Extract path from url (without the leading slash)
    path = urlparse(url).path[1:]
    if flatten:
        filename = path.split("/")[-1]
        dst = os.path.join(output_dir, filename)
    else:
        dst = os.path.join(output_dir, path)

    real_file_size = int(urlopen(url).info().get('Content-Length', -1))
    if not file_size or file_size > real_file_size:
        file_size = real_file_size

    if os.path.exists(dst):
        first_byte = os.path.getsize(dst)
    else:
        first_byte = 0
    if first_byte >= file_size:
        return dst, file_size
    header = {"Range": "bytes=%s-%s" % (first_byte, file_size)}
    pbar = tqdm(total=file_size,
                initial=first_byte,
                unit='B',
                unit_scale=True,
                desc=url.split('/')[-1])
    req = requests.get(url, headers=header, stream=True)

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, 'ab') as f:
        for chunk in req.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                pbar.update(1024)
    pbar.close()

    return dst, file_size
