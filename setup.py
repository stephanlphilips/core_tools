from setuptools import setup, find_packages

setup(name="core_tools",
	version="1.2.0",
	packages = find_packages(),
    python_requires=">=3.7",
	install_requires=[
          'quantify_core','pyqtgraph','si-prefix', 'matplotlib', 'psycopg2',
          'pulse_lib',
      ],
	)
