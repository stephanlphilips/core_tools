Project status
==============


The project is currently under beta, the following features have been added until now,

- create postgres general measurement tables
- set up measurement object similar to the one in qcodes
- create a dataset
- set up a buffer system that can write to the database (~15 us needed per write operation (add_result call))
- add easy access operators to the dataset
- loading a dataset
- query tool for all the data
- index database for fast searches + add keyword feature
- GUI to diplay data 

TODO : 
- pusher for local data to external database
- feature : add start and stop also to slicing (e.g. ds.m1[:, 5:10:20] --> slices dataset and its setpoints)
- autoconfigure db script for local configuration

small fixes todo list:
* incorporate metadata, tags
* boot-call : make already table with project and sample stuff