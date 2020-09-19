# -*- coding: utf-8 -*-
"""
This is a skeleton file that can serve as a starting point for a Python
console script. To run this script uncomment the following lines in the
[options.entry_points] section in setup.cfg:

    console_scripts =
         fibonacci = ideuy.skeleton:run

Then run `python setup.py install` which will install the command `fibonacci`
inside your current environment.
Besides console scripts, the header (i.e. until _logger...) of this file can
also be used as template for Python modules.

Note: This skeleton file can be safely removed if not needed!
"""

import argparse
import logging
import sys

from ideuy import __version__
from ideuy.download import download_images_from_grid_vector

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

    parser.add_argument("grid_vector", help="path to grid vector")

    parser.add_argument("-t",
                        "--type",
                        default="national",
                        choices=["national", "urban"],
                        help="type of grid")
    parser.add_argument("-p",
                        "--product-type",
                        default="rgb_8bit",
                        choices=["rgbi_16bit", "rgbi_8bit", "rgb_8bit"],
                        help="product type")
    parser.add_argument("-o", "--output-dir", default=".", help="output dir")
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

    download_images_from_grid_vector(grid_vector=args.grid_vector,
                                     output_dir=args.output_dir,
                                     type_id=args.type,
                                     product_type_id=args.product_type,
                                     num_jobs=args.num_jobs)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
