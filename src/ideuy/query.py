import json
import logging
from fnmatch import fnmatch
from itertools import zip_longest, islice

import requests
from shapely.ops import transform

from ideuy.vector import get_vector_bounds_and_crs, reproject_shape, flip

HOSTNAME = "https://visualizador.ide.uy"
SERVICE_PATH = "/geonetwork/srv/eng/q"
SERVICE_URL = f"{HOSTNAME}{SERVICE_PATH}"
MAX_PAGE_SIZE = 100
DEFAULT_CRS = 'epsg:4326'
DEFAULT_PARAMS = {
    "_content_type": "json",
    "bucket": "s101",
    "fast": "index",
    "resultType": "details",
    "sortBy": "relevance"
}

_logger = logging.getLogger(__name__)


def query(query=None, aoi=None, limit=None, categories=[], file_filters=[]):
    if not categories:
        categories = []

    params = {**DEFAULT_PARAMS, 'facet.q': '&'.join(categories)}

    if query:
        params['title'] = f'{query}*'

    if aoi:
        # TODO: Query for each feature geometry bounds in AOI file...
        bounds, crs = get_vector_bounds_and_crs(aoi)

        if crs != DEFAULT_CRS:
            # If crs is not the default one, reproject
            bounds = reproject_shape(bounds, crs, DEFAULT_CRS)

        # Flip (latitude,longitude) because the web service expects it the other way...
        bounds = transform(flip, bounds)
        params['geometry'] = bounds.wkt

    gen = query_all_pages(params)
    if limit:
        gen = islice(gen, limit)
    products = build_products(gen)

    return products


def build_products(raw_products):
    res = []
    for result in raw_products:
        files = []
        # Build list of downloadable files in product
        links = result['link']
        # Make sure links is a list (e.g. when there is only 1 link)
        if not isinstance(links, list):
            links = [links]
        for link in links:
            parts = link.split("|")
            link_id, name, url = parts[0], parts[1], parts[2]
            # Replace file:// URL for current https static assets URL
            if url.startswith('file://'):
                url = url.replace("file:///opt/", f"{HOSTNAME}/")
                files.append(dict(id=link_id, name=name, url=url))
        res.append(dict(**result, __files=files))
    return res


def filter_products_by_files(products, file_filters=[]):
    res = []
    for product in products:
        files = []
        # For each file filter, add filtered files to new files list
        for filt in file_filters:
            key, pattern = filt.split('/')
            files.extend(
                [f for f in product['__files'] if fnmatch(f[key], pattern)])
        # Only return product if it has any file, after filtering
        if files:
            product['__files'] = files
            res.append(product)
    return res


def grouper(iterable, n, fillvalue=None):
    "Collect data into fixed-length chunks or blocks"
    # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return zip_longest(*args, fillvalue=fillvalue)


def query_all_pages(params):
    """Generates results for all pages"""
    i = 1
    while True:
        page_params = {**params, 'from': i, 'to': (i + MAX_PAGE_SIZE - 1)}
        _logger.info(f"Query: {page_params}")
        res = requests.get(SERVICE_URL, params=page_params)
        if not res.ok:
            raise RuntimeError(
                "Status code: {res.status_code}. Response: {res.content}")

        body = json.loads(res.content)
        metadata = body.get('metadata', [])

        # Make sure metadata is a list (e.g. when there is only 1 result)
        if not isinstance(metadata, list):
            metadata = [metadata]

        for row in metadata:
            yield row

        # If page results count is less than max page size,
        # this is the last page, so return:
        if len(metadata) < MAX_PAGE_SIZE:
            return
        # Otherwise, increment item_from and item_to to query next page
        i += MAX_PAGE_SIZE
