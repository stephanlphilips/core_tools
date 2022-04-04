from setuptools import setup, find_packages

setup(name="core_tools",
	version="1.1.2",
	packages = find_packages(),
	install_requires=[
          'pyqtgraph','si-prefix', 'matplotlib', 'psycopg2 '
      ],
	)
