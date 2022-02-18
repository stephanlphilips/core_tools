from setuptools import setup, find_packages
from setuptools.extension import Extension

setup(name="core_tools",
	version="1.0",
	packages = find_packages(),
	install_requires=[
          'pyqtgraph==0.12.3',
          'si-prefix==1.2.2',
          'matplotlib==3.5.1',
          'psycopg2==2.9.3',
          'h5py==3.6.0',
          'qcodes==0.32.0',
          'pyqt5==5.15.6',
          'lmfit==1.0.3',
          'qutip==4.6.3'
      ],
	)