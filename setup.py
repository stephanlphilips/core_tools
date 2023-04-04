from setuptools import setup, find_packages

setup(name="core_tools",
    version="1.4.20",
    packages = find_packages(),
    python_requires=">=3.7",
    install_requires=[
          'pyqt5',
          'pyqtgraph >= 0.12.4',
          'si-prefix', 'matplotlib', 'psycopg2',
          'xarray',
          'qcodes',
          'pulse_lib',
          'numpy >= 1.20',
      ],
    package_data={
        "": ["*.qml"],
    },
    )
