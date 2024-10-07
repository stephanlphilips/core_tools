from setuptools import setup, find_packages

setup(name="core_tools",
    version="1.4.67",
    packages = find_packages(),
    python_requires=">=3.10",
    install_requires=[
          'pyqt5 >= 5.15.1',
          'pyqtgraph >= 0.13',
          'matplotlib',
          'psycopg2; platform_system != "Darwin"',
          'psycopg2-binary; platform_system == "Darwin"',
          'xarray',
          'h5netcdf',
          'qcodes',
          'numpy >= 1.24, < 2.0',
          'ruamel-yaml',
          # 'pulse_lib',
      ],
    package_data={
        "core_tools": ["py.typed"],
        "": ["*.qml", "*.png"],
    },
    )
