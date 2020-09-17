# ideuy

Python package for downloading images from IDEuy

## Install

Create a virtual environment and install with pip in development mode, for
example:

```
virtualenv -p python3 .venv/
source .venv/bin/activate
pip install -e .
```

## Usage

### Available CLI scripts

* `ideuy_download_grid`: Downloads a grid (national or urban) shapefile
* `ideuy_filter`: Filters a grid shapefile with another AOI shapefile
* `ideuy_download_images`: Downloads orthoimages based on a grid shapefile
