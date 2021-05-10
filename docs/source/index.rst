.. CoreTools documentation master file, created by
   sphinx-quickstart on Wed Nov  4 09:33:07 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Core tools documentation
========================

Setting up gates and virtual gates
----------------------------------

.. toctree::
   :maxdepth: 2

   generating_hardware
   GUI_for_gates
   loading_virt_gates


Spin Qubit dataset documentation
--------------------------------

This is a light weight dataset that has been made to support common spin qubit measurement practices.
The front end of the dataset has been made to resemble the qcodes dataset. The back-end uses a different database, which allows for non-local and fast storage/access of small and large measurements (>100Mb).

In the table below you find the instructions to use the dataset.

.. toctree::
   :maxdepth: 2

   introduction_db
   working_with_datasets
   starting_up_the_GUI
   dev_information
   examples
   project_status


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
