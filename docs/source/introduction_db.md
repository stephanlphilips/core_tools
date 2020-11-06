Introduction to the database set up
============================

In the background, a SQL server is used to store the data that is measured. The database of choise for this project is PostgreSQL.

To set up the connection to the SQL server, there are tree options:
1. Install your own [local PostgreSQL server](#setting-up-a-local-database). Save data only locally.
2. Use a [remote PostgreSQL server](#setting-up-a-remote-database). This is the **recommend** configuration for analysis computers.
3. It is also possible to [combine](#setting-up-a-remote-and-local-database) 1+2. In this case, the measurements are saved locally and synced in parallel to the server. This is the **recommend** option for measurement computers.


Setting up a local database
---------------------------

The instructions below are tested on windows. On Linux/Mac, the mindset is the same, but instructions might be slightly different.

Steps:
1. Download [PostgreSQL](https://www.postgresql.org/download/)
2. Go through the installer and install the database.
3. Launch the psql program and make a database user and a database (press enter until the shell asks for the password configured in the installation). Type the following commands:
    * CREATE USER myusername WITH PASSWORD 'mypasswd';
    * CREATE DATABASE 'mydbname';
    * GRANT ALL PRIVILEGES ON DATABASE 'mydbname' TO 'myusername';
 
In case you are running along with a server set up, it is recommended to have 'mydbname' to be the same as the one on the server.

In python you can run the following code to set up the database:
```python
from core_tools.data.SQL.connector import set_up_local_storage
set_up_local_storage("myusername", "mypasswd", "mydbname",
	"project_name", "set_up_name", "sample_name")
```
Arguments are:
* user (str) : name of the user to connect with (the the one just configured using psql)
* passwd (str) : password of the user
* dbname (str) : database to connect with (e.g. 'vandersypen_data')
* project (str) : project for which the data will be saved
* set_up (str) : set up at which the data has been measured
* sample (str) : sample name 


Setting up a remote database
---------------------------

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


Setting up a remote and local database
--------------------------------------

In this case you have to configure both the remote and local database at the same time
To acquire the log in information, check out the information on setting up the remote and local database.

After this, you can set up the python connection using:

```python
from core_tools.data.SQL.connector import set_up_local_and_remote_storage
set_up_local_and_remote_storage(server, port, 
                                    user_local, passwd_local, dbname_local,
                                    user_remote, passwd_remote, dbname_remote,
                                    project, set_up, sample)
```