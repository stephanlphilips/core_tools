Example configuration
=====================

In the [example folder](https://github.com/stephanlphilips/core_tools/tree/master/examples/data) you can find example scripts to easily get you started.

There are tree scripts,
- The code in the measurement script is meant to be running in the main python session where you do the measurments.
- The code in the databrowser is meant to be used a seperate python instance (e.g. launch from a .bat script)
- The code in back-up is also meast to be used in a seperate python instance. Note that this scrip can only be ran if you set up a local and a remote server.

Making a .bat script
--------------------

This is very simple, e.g. make a text file on you desktop with extention
```
filename.bat
```

In the file, write:
```
python C:\"name to my"\folder\file.py
```
Note that in case of spaces, you need to put quotation marks.