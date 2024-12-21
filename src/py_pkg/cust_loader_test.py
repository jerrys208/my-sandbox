import sys
from py_pkg.cust_loader import ZipFileFinder

sys.meta_path.insert(0, ZipFileFinder())

import my_module
my_module.hello()
