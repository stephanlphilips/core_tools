Spin Qubit dataset documentation
================================

This is a light weight dataset that has been made to support common spin qubit measurement practices.
The front end of the dataset has been made to resemble the qcodes dataset. The back-end uses a different database, which allows for non-local and fast storage/access of small and large measurements (>100Mb).

user docs [at](https://core-tools.readthedocs.io/en/latest/):


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
