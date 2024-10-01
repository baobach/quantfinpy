"""
Quantfinpy is a toolbox adapted from the book Advances in Financial Machine Learning.

This package contains functions in the book that help you implement the ideas and code snippets without worrying about structure your code.
This package is for acamedmic purpose only. Not meant for live trading or active portfolio management.
"""

import quantfinpy.data_structure as data_structure
import quantfinpy.filters.filters as filters
import quantfinpy.labeling as labeling
import quantfinpy.util as util
import quantfinpy.dataset as dataset

# read version from installed package
from importlib.metadata import version

__version__ = version("quantfinpy")
