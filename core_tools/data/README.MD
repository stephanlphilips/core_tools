Spin Qubit dataset documentation
================================

This is a light weight dataset that has been made to support common spin qubit measurement practices.
The front end of the dataset has been made to resemble the qcodes dataset. The back-end uses a different database, which allows for non-local and fast storage/access of small and large measurements (>100Mb).


In this document the set up, creation, loading and browsing of dataset's is discussed.
# current status

* create postgres general measurement tables -> done
* set up measurement object similar to the one in qcodes -> done
* create a dataset -> done
* set up a buffer system that can write to the database -> done (~15 us needed per write operation (add_result call))
* add easy access operators to the dataset -> TODO
* loading a dataset -> TODO
* query tool for all the data -> TODO
* index database for fast searches + add keyword feature
* GUI to diplay data -> TODO 
* possible future concept :: push local to external database
# Set up
To set up the connection to the server, there are two options:
1. A PostgreSQL dataserver has been set up for the group where you are working in. Ask the server details to the server admin and you are good to go.
2. Install your own local PostgreSQL server.

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

# get the dataset
dataset = meas.dataset
```

# Loading a dataset
This can be done using two lines:

```python
# register a measurement
from core_tools.data.lib.SQL import data_mgr

ds = data_mgr.load_id(my_id)
```
# Browsing data in the dataset
To quickly see what is present in the dataset, can print it,
```python
print(ds)
```
This shows a output like:
```
dataset :: my_measurement_name

id = 1256
TrueID = 1225565471200

| idn   | label | unit  | size      |
------------------------------------- 
| m1    | 'I1'  | 'A'   | (100,100) |
|  x    | 'P1'  | 'mV'  | (100,)    |
|  y    | 'P2'  | 'mV'  | (100,)    |

| m2    | 'I2'  | 'A'   | (100)     |
|  x    | 'P1'  | 'mV'  | (100,)    |

database : vandersypen
set_up : XLD
project : 6dot
sample_name : SQ19
```

The contents can be browsed efficiently using the shorthand syntax.
* measurement parameters are denoted as m1, m2 (e.g. ds.m1, ds.m2). This will give you access to the data. If there are multiple setpoints, the data will be organized as m1a, m1b, ...
* setpoints can be called by calling m1.x, m1.y (or m1.x1, m1.x2 if there are multiple setpoints)
* measurement object have the options for data reduction (e.g. slicing and averaging)
⋅⋅* slicing e.g. m1.slice('x', 5) (take a slice of the fith element on the x axis) (alternative syntax[m1[5]], in this case, one dimension is remove, so y becomes x and you can call [m1[5].x to get the x axis of the graph).
..* averaging, same principle as slicing, expect that all elements on one axis are now averaged (e.g. m1.average(x))

Practical example:
```python

# get x, y, and z data:
x = ds.m1.x
y = ds.m1.y
z = ds.m1 #or if you like you can also call m1.z

# get the fist slice on the x direction
x = ds.m1[0].x
y = ds.m1[0] #or if you like you can also call m1.y

# get the fist slice on the y direction
x = ds.m1[:,0].x
y = ds.m1[:,0] #or if you like you can also call m1.y

# average the y direction
x = ds.m1.average('y').x
y = ds.m1.average('y') #or if you like you can also call m1.y

# getting units and so on:
ds.m1.unit
ds.m1.label
ds.m1.name

ds.m1.x.unit
ds.m1.x.label
ds.m1.x.name

...
```
# Browsing for data

