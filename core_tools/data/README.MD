Spin Qubit dataset documentation
================================

This is a light weight dataset that has been made to support common spin qubit measurement practices.
The front end of the dataset has been made to resemble the qcodes dataset. The back-end uses a different database, which allows for non-local and fast storage/access of small and large measurements (>100Mb).


In this document the set up, creation, loading and browsing of dataset's is discussed.
# current status

- [x] create postgres general measurement tables
- [x] set up measurement object similar to the one in qcodes
- [x] create a dataset
- [x] set up a buffer system that can write to the database (~15 us needed per write operation (add_result call))
- [x] add easy access operators to the dataset
- [x] loading a dataset
- [x] query tool for all the data
- [x] index database for fast searches + add keyword feature
- [x] GUI to diplay data 
- [ ] pusher for local data to external database
- [ ] feature : add start and stop also to slicing (e.g. ds.m1[:, 5:10:20] --> slices dataset and its setpoints)
- [ ] autoconfigure db script for local configuration

small fixes todo list:
* incorporate metadata, tags and take snapshot
* add the total size
* boot-call : make already table with project and sample stuff

# Set up
To set up the connection to the server, there are two options:
1. Install your own local PostgreSQL server. Save data only locally.
2. Use a remote PostgreSQL server. This is the **recommend** configuration for analysis computers.
3. It is also possible to combine 1+2. In this case, the measurements are saved locally and synced in parallel to the server. This is the **recommend** option for measurement computers.

## Option 1
The instructions below are tested on windows. On Linux/Mac, the mindset is the same, but instructions might be slightly different.

Steps:
1. Download [PostgreSQL](https://www.postgresql.org/download/)
2. Go through the installer and install the database.
3. Launch the psql program and make a database user and a database (press enter until the shell asks for the password configured in the installation). Type the following commands:
    * CREATE USER myusername WITH PASSWORD 'mypasswd';
    * CREATE DATABASE 'mydbname';
    * GRANT ALL PRIVILEGES ON DATABASE 'mydbname' TO 'myusername';
 
In case you are running along with a server set up, it is recommended to have 'mydbname' to be the same as the one on the server.

In python you can run:
```python
from core_tools.data.SQL.connector import set_up_local_storage
set_up_local_storage("myusername", "mypasswd", "mydbname", "project_name", "set_up_name", "sample_name")
```
Arguments are:
* user (str) : name of the user to connect with (the the one just configured using psql)
* passwd (str) : password of the user
* dbname (str) : database to connect with (e.g. 'vandersypen_data')
* project (str) : project for which the data will be saved
* set_up (str) : set up at which the data has been measured
* sample (str) : sample name 

## Option 2
In this case we will be connecting with a remote server. This can be set up using the following code:

```python
from core_tools.data.SQL.connector import set_up_remote_storage
set_up_remote_storage(server, port, user, passwd, dbname, project, set_up, sample)
```
The arguments are:
* server (str) : server that is used for storage, e.g. "spin_data.tudelft.nl" for global storage
* port (int) : port number to connect through, the default it 5421
* user (str) : name of the user to connect with
* passwd (str) : password of the user
* dbname (str) : database to connect with (e.g. 'vandersypen_data')
* project (str) : project for which the data will be saved
* set_up (str) : set up at which the data has been measured
* sample (str) : sample name 

Note that the admin of the server has to provide you with login credentials for the storage. 
### admin set up.
Example for a linux server running ubuntu.

Install postgres:
```bash
sudo apt install postgresql
```

Set up the datasbase, in your shell swich to the postgres user and run psql, e.g.,
```bash
sudo apt install postgresql
```
```bash
psql
```

Now, make the databases and users,

Then set up a database and related users:
```SQL
CREATE USER myusername WITH PASSWORD 'mypasswd';
CREATE DATABASE 'mydbname';
GRANT ALL PRIVILEGES ON DATABASE 'mydbname' TO 'myusername';
```

The default install of postgress does not allow external connections. We can adjest this by typing
```bash
sudo vim /etc/postgresql/12/main/postgresql.conf
```
and adding the following line:
```
listen_addresses = '*'
```
This means the postgress process will listen to all incomming requests from any ip.
Now, let's also tell postgress that users are allowed to authenticate, change the following config file,
```bash
sudo vim /etc/postgresql/12/main/pg_hba.conf
```
and add the following line,
```
host    all     all     0.0.0.0/0               md5
```
Now restart the postgres services to apply the changes, 
```bash
sudo systemctl restart postgresql.service 
```
Note : also make sure port 5432 is open, e.g.:
```bash
sudo ufw allow 5432
```
TODO :: add certificates to ensure no random people can login with passwords found on github (currentl protectected using VLAN's).

## Option 3
In this case configure both option 1 and 2 at the same time, this can be done using:

```python
from core_tools.data.SQL.connector import set_up_local_and_remote_storage
set_up_local_and_remote_storage(server, port, 
                                    user_local, passwd_local, dbname_local,
                                    user_remote, passwd_remote, dbname_remote,
                                    project, set_up, sample)
```

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
from core_tools.data.ds.data_set import load_by_id, load_by_uuid

ds = load_by_id(101)
ds = load_by_uuid(1603388322556642671)
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
# Browsing for data



# Developer information

## Database structure

The user has two configurations to operate in, 
* local database
* local database + server side database (network connection needed)

The serverside configuration offers the advantage that you can access the data of your experiments from any device. The serverside is combined with a local database, in order to be able to keep operating when the network is down.

When operating only locally, no features are lost. Mainly you don't have back up and you can't access the data with a device that is not your measurement computer.

To accommodate a structure that can dynamically switch between both modes, the following tables are made :

### Client side
* global_measurement_overview : contains all the local measurements performed. Used for queries when the server is unavailable (e.g. no network).
* projects_set_up_sample table : local table containing all the data of the current sample being measured. This tables are kept on the system, even if you switch sample (the data linking to it might be removed if you set a storage limit (only data that has been moved to the server))
* project_set_up_sample overview : simple table summarizing all the projects_set_up_sample on the client side
* projects_set_up_sample_id tables : tables containing the raw data of all the local experiments

### Server side
* global_measurement_overview : same as for client side, only much bigger (this will have consequences, see further)
* projects_set_up_sample : synced version of the client side (see conflicts section for more information on how conflicts between two set ups measuring on the same sample at the same time are handled.) 
* project_set_up_sample overview : simple table summarizing all the projects_set_up_sample on the server side
* projects_set_up_sample_id tables : tables containing the raw data of all experiments.

Ensure scalability: fast searches. In order to sort through less data in searches, additional tables are build, containing views of the global_measurement_overview table (note that this are physical tables and not views).
* project table
* set_up table
* project_set_up table
* project_set_up_sample table

General question:
* should the measured data be in a different schema?

### Conflict resolution
When looking a this scheme there is one error that can be made and is irritating to solve. Two systems are writing to the same table locally, both tables get out of sync --> measurement ID's of one of the two systems have to be adjusted in order for the tables to be able to merge.

## Storage information

### Measurement identification
For identifying measurements two types of identifiers are generated:
* exp id
* uuid

#### exp id
This is a id that is associated with the measurement project, set up and sample. This id always starts from 1 and counts up as you make more measurements on your sample and is unique in this space. Once you switch the sample, the counter resets, and will start back from 1.

The exp id is designed to be used when you want to quickly access data of a single of single sample.

#### uuid
This is a 64bit identifier that is designed to be unique among all measurements in the database. The goal of the ID is to have a relatively easily type-able id that can be used over all the measurements.

The unique ID's are generated by concatenating the current time (epoch time in ms) + ~ the last 27 bits of your mac address. This results in a 15 digit number which should be unique for every measurement

### raw data storage in the database
The raw data of the measurements is stored in so called large objects (postgres type). This are large binary object that are directly saved to your harddrive (much like your files on your computer). A pointer to the location of these files is kept in the database.

When the dataset is constructed a buffer (large object), is made for each setpoint and measured variable. When performing a measurement, the buffers are filled in the RAM. To enable real time plotting, these buffers are synchronized every 200ms to the local database. Only the data that has been modified in the buffer will be written. The same counts for the read buffer.
The synchronization to the server is slower to ensure low overhead. This is typically done every few seconds (= slower online liveplotting).

The size of a dataset can be arbitrary, where the main limitation is the amount of RAM in the measurement computer and the amount of hard disk space available.

## Managing space on measurements computers
The software can make an estimation of the amount of data that has been written to the hard disk of the measurement computer. Since it is recommended to use SSD's for fast performance, the space might be limited. Therefore the user has the option to set a soft limit on the amount of space that can be used to save data.

The software will regularly check the amount of data that has been used. When this goes over the limit, it will trash the oldest datasets that are present on the system. Only datasets that are synchronized to the server can be trashed.
When asking for the data of the removed measurements, a call will be made to the server instead of the computer.

By default no limit is applied.
