# -*- coding: utf-8 -*-
"""
This script downloads files from a JSON of products

"""

import argparse
import json
import logging
import sys

from ideuy import __version__
from ideuy.download import download_all_products
from ideuy.query import filter_products_by_files

__author__ = "Damián Silvani"
__copyright__ = "Damián Silvani"
__license__ = "mit"

_logger = logging.getLogger(__name__)


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """
    parser = argparse.ArgumentParser(
        description="Downloads image products from IDEuy",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('infile',
                        nargs='?',
                        type=argparse.FileType('r'),
                        default=sys.stdin)
    parser.add_argument("-o", "--output-dir", default=".", help="output dir")

    # Filters
    parser.add_argument("--files",
                        nargs="+",
                        default=[],
                        help="filter files in product")

    parser.add_argument("-j",
                        "--num-jobs",
                        default=1,
                        type=int,
                        help="number of simultaneous download threads")

    parser.add_argument("--version",
                        action="version",
                        version="ideuy {ver}".format(ver=__version__))
    parser.add_argument("-v",
                        "--verbose",
                        dest="loglevel",
                        help="set loglevel to INFO",
                        action="store_const",
                        const=logging.INFO)
    parser.add_argument("-vv",
                        "--very-verbose",
                        dest="loglevel",
                        help="set loglevel to DEBUG",
                        action="store_const",
                        const=logging.DEBUG)

    return parser.parse_args(args)


def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel,
                        stream=sys.stdout,
                        format=logformat,
                        datefmt="%Y-%m-%d %H:%M:%S")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """
    args = parse_args(args)
    setup_logging(args.loglevel)

    products = json.load(args.infile)
    products = filter_products_by_files(products,
                                        file_filters=args.file_filters)
    download_all_products(products,
                          output_dir=args.output_dir,
                          num_jobs=args.num_jobs)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
