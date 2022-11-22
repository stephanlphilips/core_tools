from setuptools import setup, find_packages

setup(name="core_tools",
	version="1.4.9",
	packages = find_packages(),
    python_requires=">=3.7",
	install_requires=[
          'pyqt5', 'pyqtgraph',
          'si-prefix', 'matplotlib', 'psycopg2',
          'xarray',
          'qcodes',
          'pulse_lib',
          'numpy >= 1.20',
      ],
	)
