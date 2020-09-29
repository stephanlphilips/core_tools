Spin Qubit dataset documentation
================================

This a light weight dataset that has been made to support common spin qubit measurement practices.
The front end of the dataset has been made to resemble the qcodes dataset. The back-end uses a different database, which allows for non-local and fast storage of larger measurements (>100Mb).


In this document the set up, creation, loading and browsing of dataset's is discussed.

# Set up
The set up the connection to the server there are two options:
1. A PostgreSQL dataserver has been set up of the group where you are working in. Ask the server details to the server admin and you should be good to go.
2. Install your local PostgreSQL server.

## Option 1 (recommended)
Run the following code in your python console:

```python
from core_tools.data.SQL.connector import set_up_data_storage
set_up_data_storage(server, port, user, passwd, dbname, project, set_up, sample)
```
The arguments are:
* server (str) : server that is used for storage, e.g. "localhost" for local or "spin_data.tudelft.nl" for global storage
* port (int) : port number to connect through, the default it 5421
* user (str) : name of the user to connect with
* passwd (str) : password of the user
* dbname (str) : database to connect with (e.g. 'vandersypen_data')
* project (str) : project for which the data will be saved
* set_up (str) : set up at which the data has been measured
* sample (str) : sample name 

## Option 2
These instructions are only valid for windows (for Linux and OS X things should be very straightforward).

Steps:
1. Download [PostgreSQL](https://www.postgresql.org/download/)
2. Go through the installer and install the database
3. Launch the psql program and make a database user and a database
... type the following commands:
... * createuser myusername
... * ALTER ...
... * createdb mydbname

You should be ready to go now and be able to use the database.
In python you can run:
```python
from core_tools.data.SQL.connector import set_up_data_storage
set_up_data_storage("localhost", 5432, "myusername", "mypasswd", "mydbname", "project_name", "set_up_name", "sample_name")
```
The datastorage has now been set up.

# Creation of a dataset
Datasets are created using the Measurement object (similar as in qcodes). This method can be used to construct your own dataset, but in most cases, it will be more convenient to generate the dataset using the predefined sweep functions.
```python
from core_tools.sweeps.sweeps import do0D, do1D, do2D

gate = station.dacs.P1
v_start = 0
v_stop = 5
n_points = 100
delay = 0.001
do1D(gate, v_start, v_stop, n_points, delay, station.keithley.measure).run()
```

In case you want to use the measurement object, an example of the code would look like:

```python
# register a measurement
from core_tools.data.lib.measurement import Measurement

experiment_name = 'name displayed in the database'
meas = Measurement(experiment_name)

# there will be two variable that will be swept (e.g. x, y), with 50 points on each axis
meas.register_set_parameter(a1, 50)
meas.register_set_parameter(a2, 50)

# we will be measuring 1 parameter that depends both on the value of a1 and a2
meas.register_get_parameter(m4, a1, a2)

# generate the dataset in the context manager
with meas as ds:
	# do sweep on two axises
    for i in range(50):
    	# set variable 1
    	a1(i)
    	for j in range(50):
    		# set variable 2
    		a2(j)
    		# measure + write the results
    		meas.add_result( (a1, a1.get()), (a2, a2.get()), (m4, m4.get()))
```


