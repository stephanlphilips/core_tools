from setuptools import setup, find_packages

setup(name="core_tools",
    version="1.4.54",
    packages = find_packages(),
    python_requires=">=3.7",
    install_requires=[
          'pyqt5',
          'pyqtgraph >= 0.12.4',
          'matplotlib', 'psycopg2',
          'xarray',
          'qcodes',
          'pulse_lib',
          'numpy >= 1.20',
      ],
    package_data={
        "core_tools": ["py.typed"],
        "": ["*.qml"],
    },
    )
