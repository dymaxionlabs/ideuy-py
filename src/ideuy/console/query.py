# -*- coding: utf-8 -*-
"""
This script allows you to query the IDE UY catalog service.
It prints search results as JSON, which can then be passed to the
download script for downloading all files.

"""

import argparse
import logging
import sys
import json

from ideuy import __version__
from ideuy.download import download_all
from ideuy.query import query

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
        description="Search for products using the IDEuy Web Service",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('outfile',
                        nargs='?',
                        type=argparse.FileType('w'),
                        default=sys.stdout)

    parser.add_argument("-q", "--query", help="search by title")
    parser.add_argument("-a", "--aoi", help="path to AOI vector file")
    parser.add_argument("-c",
                        "--category",
                        nargs="+",
                        default=[],
                        help="filter by category")

    # parser.add_argument("-j",
    #                     "--num-jobs",
    #                     default=1,
    #                     type=int,
    #                     help="number of simultaneous download threads")

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

    products = query(query=args.query, aoi=args.aoi, categories=args.category)
    json.dump(products, args.outfile)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
