Working with the dataset
========================

Creation of a dataset
---------------------
Datasets are created using the Measurement object (similar as in qcodes). This method can be used to construct your own dataset, but in most cases, it will be more convenient to generate the dataset using the predefined sweep functions. Example:
```python
from core_tools.sweeps.sweeps import do0D, do1D, do2D

gate = station.dacs.P1
v_start = 0
v_stop = 5
n_points = 100
delay = 0.001
do1D(gate, v_start, v_stop, n_points, delay, station.keithley.measure).run()
```

In some cases you might want to use the measurement object (e.g. to make your own sweep functions). An example of the code would look like:

```python
# register a measurement
from core_tools.data.lib.measurement import Measurement

experiment_name = 'name displayed in the database'
meas = Measurement(experiment_name)

#a1, a2 could be both dacs, m4 could be a keithley for example
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

Loading a dataset
-----------------

This can be done using two lines:

```python
# register a measurement
from core_tools.data.ds.data_set import load_by_id, load_by_uuid

ds = load_by_id(101)
ds = load_by_uuid(1603388322556642671)
```
Browsing data in the dataset
----------------------------

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
	* slicing e.g. m1.slice('x', 5) (take a slice of the fith element on the x axis) (alternative syntax[m1[5]], in this case, one dimension is remove, so y becomes x and you can call [m1[5].x to get the x axis of the graph).
	* averaging, same principle as slicing, expect that all elements on one axis are now averaged (e.g. m1.average(x))

Practical example:
```python

# get x, y, and z data:
x = ds.m1.x()
y = ds.m1.y()
z = ds.m1() #or if you like you can also call m1.z()

# get the fist slice on the x direction
x = ds.m1[0].x()
y = ds.m1[0] #or if you like you can also call m1.y()

# get the fist slice on the y direction
x = ds.m1[:,0].x()
y = ds.m1[:,0] #or if you like you can also call m1.y()

# average the y direction
x = ds.m1.average('y').x()
y = ds.m1.average('y') #or if you like you can also call m1.y()

# getting units and so on:
ds.m1.unit
ds.m1.label
ds.m1.name

ds.m1.x.unit
ds.m1.x.label
ds.m1.x.name

...
```