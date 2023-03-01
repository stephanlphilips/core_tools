# Changelog
All notable changes to core_tools will be documented in this file.

## \[1.4.18] - 2023-03-01

- Limit dataset size to 20e6 values per parameter.


## \[1.4.17] - 2023-02-15

- Added DC gain to gates
- Added set_timeout to Keysight digitizer driver M3201A
- Added ScriptRunner GUI
- Replaced logging by logging.getLogger(__name__)
- Changed included KeysightSD1 package to coexist with official Keysight package

## \[1.4.16] - 2023-02-01

- Added HVI2 Continuous mode

## \[1.4.15] - 2023-01-23

- Added var_mgr.get_values_at(time)
- Added iq_mode 'amplitude+phase' to VideoMode
- Reduced load on database server by databrowser

## \[1.4.14] - 2023-01-19

- Fixed bug in VideoMode for Qblox
- Added save_csv(dataset)

## \[1.4.13] - 2023-01-16

- Add QML files to setup
- Improved HVI2; fixed a case where digitizer did not return data.
- Added method force_daq_configuration() to Keysight digitizer to resolve 'no data' state.
- Show UUID in 3 parts separated by '_' in data browser

## \[1.4.12] - 2022-12-22

- Fixed db_sync script

## \[1.4.11] - 2022-12-01

- Fixed data loading from HDF5 and conversion xarray dataset to core-tools dataset.
- ds2xarray: corrected conversion of datasets with dimensions with same name, but different coordinates.
- Fixed memory leakage in job_mgmt.
- Maintain insertion order in job queue for jobs with equal priority.
- Full implementation of new Scan class

## \[1.4.10] - 2022-11-24

- Fixed corrupt charts and weird font sizes when using Windows display scaling.

## \[1.4.9] - 2022-11-22

- Added 'I+Q' and 'abs+angle' to iq_mode options of video mode
- Fixed Q, amp and angle output in VideoMode

## \[1.4.8] - 2022-11-21

- Improved performance of measurement for measurements > 30 s.
- Added first version of new Scan class.

## \[1.4.7] - 2022-11-18

- Fixed import of NumpyJSONEncoder for new qcodes versions
- Improved error handling during measurement
- Fixed VideoMode and DataBrowser 2D plots for pyqtgraph 0.13+
- Lowered VideoMode refresh rate to better support remote connections
- Added option silent to measurement and scan_generic
- Keyboard interrupt in measurement now aborts running script (So you don't have to hit Ctrl-C 50 times..)
- Added get_idn to Instruments gates, hardware, M3102A.
- Fixed resetting histogram
- Added option to disable live plotting of data browser at startup
- Data browser live plotting now only checks for updates on selected project, setup and sample.

## \[1.4.6] - 2022-10-17
- Improved logfile format
- Requires numpy >= 1.20
- Fixed load_by_uuid without database
- Show histogram checkbox for datasets >= 2D

## \[1.4.5] - 2022-10-07
- Fixed problem with QML GUI logging and some Spyder versions.
- Added get_history to VarMgr.
- Improved handing of database error messages

## \[1.4.4] - 2022-09-26
### Fixed
- VarMgr: Reconnect to database after exception

## \[1.4.3] - 2022-09-23
### Fixed
- Log QML GUI errors and warnings (databrowser, ...)
- Fixed ds2xarray for datasets with dimensions > 3

## \[1.4.2] - 2022-09-19
### Fixed
- Windows specific calls in app_launcher.

## \[1.4.1] - 2022-09-19
### Fixed
- missing __init__.py

## \[1.4.0] - 2022-09-19
### Added
- Added selection of project, set-up and sample at data_browser startup.
- Added rebuild_sample_info() to SQL_sync_manager.
- Added locked option to parameter viewer startup.
- Added HDF5 export and re-import for data publication.
- Added configuration using YAML file
- Added simple startup of GUIs
- Added examples/demo_station

### Changed
- Changed database scheme !! Data written by v1.4+ can only be read by v1.4+ !!
- Improved error handling in data browser.
- Do not accept 'any' as name for project, set-up, or sample in measurement.
- Synchronize sample info to server.
- Changed layout of data-browser.

### Fixed
- import of PyQt5

## \[1.3.1] - 2022-07-25
### Changed
- Updates for pulselib 1.5 with configuration of Keysight digitizer

## \[1.3.0] - 2022-05-20
### Changed
- VideoMode / liveplotting now uses DataSaver to store data
  NOTE: call liveplotting.set_data_saver(QCodesDataSaver()) to enable saving to qcodes dataset

### Fixed
- Use acquisition_delay_ns for qblox VideoMode


## \[1.2.0] - 2022-04-14
### Fixed
- Added qt_utils.qt_init() for reliable startup of GUI
- Added Qblox Pulsar support in Video Mode
- Improved setup and release

## \[1.1.2] - 2022-04-04
### Fixed
- M3102A driver fixed initialization

## \[1.1.1] - 2022-03-31
### Fixed
- DataBrowser updated for pyqtgraph > 0.11
- DataBrowser fixed exceptions with slow connection to database

## \[1.1.0] - 2022-02-24
### Added
- Automatically reconnect to database server when connection was lost/closed.
- Refactored virtual matrix
    - Added normalization
    - Added stacked matrices (virtual gates of virtual gates)
- load_gate_voltages from snapshot
- Improved parameter viewer Qt GUI
    - Added "Lock parameter viewer"
    - Added max diff
    - Restore values in GUI when locked or boundary exceeded
- Improved virtual matrix Qt GUI
    - Added coloring of virtual matrix in GUI

### Changed
- Keysight M3102A driver independent control of V-max, coupling and impedance per channel.

### Removed
- Digitizer V-max has been removed from 1D and 2D fast scans. It should be configured directly on digitizer.
- Keysight SD1 2.x is no longer supported

### Fixed
- gates class: restore all gates when boundary of one gate exceeded when setting a real or virtual gate.

## \[1.0.0] - 2022-01-18
First labeled release. Start of dev branch and change logging.
