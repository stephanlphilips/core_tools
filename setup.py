from setuptools import setup, find_packages

setup(name="core_tools",
	version="1.3.1",
	packages = find_packages(),
    python_requires=">=3.7",
	install_requires=[
          'pyqtgraph','si-prefix', 'matplotlib', 'psycopg2',
          'pulse_lib',
      ],
	)
