import sys
import importlib.util
import zipfile
import os

from importlib.abc import MetaPathFinder, SourceLoader
from importlib.machinery import ModuleSpec



class ZipFileLoader(SourceLoader):
    def __init__(self, fullname, path, zip_path):
        self.fullname = fullname
        self.path = path
        self.zip_path = zip_path

    def get_filename(self, fullname):
        return self.path

    def get_data(self, path):
        with zipfile.ZipFile(self.zip_path, 'r') as zf:
            with zf.open(self.path, 'r') as f:
                return f.read()

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        data = self.get_data(self.path)
        code = compile(data, self.path, 'exec', dont_inherit=True)
        exec(code, module.__dict__)


class ZipFileFinder(MetaPathFinder):
    """ meta path finder """

    def find_spec(self, fullname: str, path: str, target=None) -> (ModuleSpec | None):
        """ re-define search rule """
        print(f'[*] find_sepc: {fullname}, {path}, {target}')
        # define scope
        if not fullname.startswith('my_'):
            return None
        # load from custom source (e.g. zip)
        zip_filename = 'modules.zip'
        zip_filepath = os.path.join(os.path.dirname(__file__), zip_filename)
        if not os.path.exists(zip_filepath):
            print(f'[*] file not found: {zip_filepath}')
            return None

        try:
            with zipfile.ZipFile(zip_filepath, 'r') as zf:
                for filename in zf.namelist():
                    if filename.endswith('.py') and filename.replace('.py', '') == fullname:
                        return importlib.util.spec_from_loader(
                            fullname,
                            ZipFileLoader(fullname, filename, zip_filepath),
                            origin=zip_filepath + '!' + filename,
                            is_package=False
                        )
        except zipfile.BadZipFile:
          return None
        return None

# 建立一個包含模組的 zip 檔案
with zipfile.ZipFile('modules.zip', 'w') as zf:
    zf.writestr('my_module.py', 'def hello(): print("Hello from zip!")')

