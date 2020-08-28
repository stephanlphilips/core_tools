from setuptools import setup, find_packages
from setuptools.extension import Extension
from Cython.Build import cythonize
import numpy


packages = ["data"]



extensions = [
	Extension("data.lib.data_storage_class",
		include_dirs=[numpy.get_include(),"./data/libc", ".", './data/lib/'],
		sources=["data/lib/data_storage_class.pyx",
					"data/libc/utility.cpp",
					"data/libc/data_class.cpp",
					"data/libc/upload_mgr.cpp"], 
		language="c++",
		libraries=["mariadb","mysqlcppconn","stdc++"]
	  )
]



setup(name="new_dataset",
        version="0.1",
        packages = find_packages(),
        ext_modules = cythonize(extensions, language_level = "3")
        )