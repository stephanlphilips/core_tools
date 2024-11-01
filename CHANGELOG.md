# Changelog
All notable changes to core_tools will be documented in this file.

## \[1.5.3] - 2024-10-30

- Fixed slow database connection setup

## \[1.5.2] - 2024-10-21

- Support dark style GUI.
- Updates for qcodes 0.49

## \[1.5.1] - 2024-10-14

- Fixed type annotation on VideoMode
- Changes for new Keysight HVI2/PTSE release

## \[1.5.0] - 2024-10-07

- "Official" release of new Video Mode.
- Fixed Video Mode bugs of 1.4.67

## \[1.4.67] - 2024-10-07

- Refactored Video Mode for new features
- Added Favorites to Video Mode
- Added automatic recompile in Video Mode if pulse-lib settings change.
- Added extra title text to Video Mode
- Performance improvement setting virtual gates

## \[1.4.66] - 2024-09-30

- Reverted to old logic for Keysight for using digitizer channels from pulse_lib: use digitizer if specified.

## \[1.4.65] - 2024-09-30

- Fixed construct_1D_fast_scan and construct_2D_fast_scan (after v1.4.63 refactoring)

## \[1.4.64] - 2024-09-26

- Fix Set DC voltages in Video Mode (broken in v1.4.63)

## \[1.4.63] - 2024-09-25

- Refactored VideoMode to allow simple external scan generator.
- Fixed database locking due to synchronization manager

## \[1.4.62] - 2024-09-19

- Performance improvement ParameterViewer.
- Improved Scan and combi_parameter for better reset.

## \[1.4.61] - 2024-09-17

- Fix pulse_gates in VideoMode

## \[1.4.60] - 2024-09-13

- Added download_hdf5, download_hdf5_parallel for sQDL.
- Huge performance improvement virtual gate matrix GUI.

## \[1.4.59] - 2024-09-09

- Added sqdl_query, sqdl_logout, load_uuids_parallel

## \[1.4.58] - 2024-09-02

- Improved error message in case COM port number change is likely cause of error.
- Set proper GUI window titles.
- Fixed Mac OS installation.
- Added scan arguments to fast-scan parameter snapshots.
- Added scan arguments to video mode snapshot.
- Video Mode improvements:
  - Fixed saving of wrong data when switching tabs before pressing Save.
  - Added shortcut keys F5, Esc, Ctrl+S, Ctrl+C, Ctrl+P.
  - Increased number of pulse gates and made it configurable.
  - Added noise filter in 2D (Gaussian low pass).
  - Added static methods liveplotting.stop_all and liveplotting.is_any_running
  - Automatic stop of other running video mode gui.
  - Added icons on buttons.
- Reduced amount of logging on info level.
- HVI2 (Keysight): Fixed error with multiple digitizers and not all channels active

## \[1.4.57] - 2024-08-13

- Fixed race conditions with db synchronization.
- Added get_idn to D5a.

## \[1.4.56] - 2024-08-07

- Fixed disabling digitizer sequencer functionality in Keysight_QS
- Automatically remove log-files older than "max_age" days (default: 90)

## \[1.4.55] - 2024-07-22

- Fixed databrowser QML.
- minor fixes and cleanup.
- Added QT-Dataset Browser (qt-dataviewer >= v0.3.0)

## \[1.4.54] - 2024-06-14

- Fixed refresh of DataBrowser GUI.

## \[1.4.53] - 2024-06-03

- Fixed unit radians for phase in video mode.
- Fixed GUI for changes in latest matplotlib release.

## \[1.4.52] - 2024-04-29

- Fixed RF generators with Keysight_QS video mode

## \[1.4.51] - 2024-04-29

- Added resume after break to Scan.
- Virtual Matrix Editor: Show matrix determinant and show matrix elements in bold and red when out of range
- Parameter Viewer: Show virtual gate values in red and disable editing when value out of range due to matrix
- Fixed bug in Scan of v1.4.49

## \[1.4.50] - 2024-04-19

- Fixed measurement parameters in dataset.

## \[1.4.49] - 2024-04-19

- Added Section to Scan to make a sequence of sweeps in a scan.
- Fixed order of measurement parameters in dataset.
- Fixed old dataviewer after removing si_prefix package.

## \[1.4.48] - 2024-04-16

- Added close to dataset to release file objects.

## \[1.4.47] - 2024-04-10

- Added value_after to sweep in Scan to set the value of the inner loop before the next step of the outer loop.
- Removed dependency on package si_prefix
- Minor correction for DC compensation on 2D scans.

## \[1.4.46] - 2024-03-28

- Significantly improved performance of gates.snapshot and parameter viewer.

## \[1.4.45] - 2024-03-21

- M3202A improved logging for long measurements
- Avoid unnecessary HVI script regeneration when number waveforms changes

## \[1.4.44] - 2024-02-08

- Update for qt-dataviewer v0.3.0

## \[1.4.43] - 2024-01-30

- Fixed PostgreSQL data limit: 1GB per field.

## \[1.4.42] - 2024-01-29

- Compress snapshot in HDF5 files.
- Added 'application' to xarray / HDF5 file.
- Added query for new measurements.

## \[1.4.41] - 2024-01-18

- Fixed backward compatibility for old data viewer.

## \[1.4.40] - 2024-01-18

- Added new qt_dataviewer to plot datasets.

## \[1.4.39] - 2024-01-12

- Added SQL_database_manager.disconnect() to change database connection.

## \[1.4.38] - 2024-01-10

- Video mode: disabled auto SI prefix to avoid 'mmV'.
- Improved dataset name checking.
- Fixed warning "<gate> corrected from -0.00 to 0.00".
- Added argument snapshot_extra to Scan.

## \[1.4.37] - 2023-12-21

- Change segment HVI variables to sequence.schedule_params (preparation pulse-lib v1.8)
- Fixed sample/project/setup name validation. Allow 0-9_ as first character.

## \[1.4.36] - 2023-12-11

- Added data_writer() to create and store a dataset from arrays
- Added validation of dataset name, parameter name, project name, setup name, sample name
- Added checks on parameter data size in dataset
- Added Keysight AWG oscillator control to HVI and video mode.
- Video mode for Keysight uses pulse-lib digitizer channel configuration if digitizer is None in liveplotting()
- Video mode now determines required AWG driver from pulse-lib configuration.
- Added pre-pulses to Qblox video mode.

## \[1.4.35] - 2023-11-13

- Fixed database synchronization. Fields 'completed', 'data_size' and 'stop_time' were often missed in sync.
- Robust write of HDF5 data file and overwrite existing file.

## \[1.4.34] - 2023-10-31

- Moved QT5 initialization check to application start. Automatically start QT5 thread when using IPython outside Spyder.
- Fixed plotting of arbitrary dataset when there are no datasets in selection.
- Improved logging and exception handling during measurement.

## \[1.4.33] - 2023-10-19

- Parameter viewer virtual gate limits set to +/- 9999.99 mV
- Parameter viewer print warning if gate voltage is corrected by GUI limits
- Use digitizer average output scaling to better use digital range (requires keysight-fpga v1.1+)
- Avoid partially written hdf5 files

## \[1.4.32] - 2023-08-29

- Made VideoMode more robust on acquisition errors.

## \[1.4.31] - 2023-08-29

- Fixed `add_derived_param()` of digitizer_param_m4i
- Fixed IQ demodulation to M4i VideoMode

## \[1.4.30] - 2023-08-28

- Added IQ demodulation to digitizer_param_m4i and removed link to instrument
- Added IQ demodulation to M4i VideoMode

## \[1.4.29] - 2023-06-20

- Fixed exception thrown when starting video mode without passing default settings.
- Fixed axis of 2D plot for incomplete dataset of scan from high to low values.

## \[1.4.28] - 2023-05-26

- Keep order of keywords of dataset.

## \[1.4.27] - 2023-05-17

- Added `starred` to loaded dataset.
- Databrowser: Fixed live plotting
- Databrowser: Added 'Close all plots' button

## \[1.4.26] - 2023-05-08

- VideoMode: added pulsed offsets to settings argument and metadata.
- Fixed M3102A for configuration of time-traces.
- Better exception handling in measurement loops.

## \[1.4.25] - 2023-05-03

- Moved qcodes dataset dependent code to powerpoint_qcodes.py
- Added Enum type annotation to script runner functions.

## \[1.4.24] - 2023-05-02

- VideoMode: Added stop() to liveplotting to stop video mode 1D and 2D.
- Removed unneeded qcodes.data import

## \[1.4.23] - 2023-04-28

- VideoMode: Fixed scale when starting averaging.
- VideoMode: Keep buffered data when changing the number of averages.
- VideoMode: Changing sweep direction in 1D now keeps correct x-values in chart.
- VideoMode: Set DC voltages in 1D.
- VideoMode: Added copy to clipboard.
- VideoMode: Added maximum voltage swing to settings.
- VideoMode: Fixed background filter setting when uploading waveforms.
- Databrowser: Added dataset info to window title and panel.
- Databrowser: Fixed presentation of 0D data, a scalar.
- Databrowser: Filter on name, keywords and starred.

## \[1.4.22] - 2023-04-25

- Fixed dataset - xarray conversion and storage of HDF5 files.

## \[1.4.21] - 2023-04-19

- Added SequenceFunction to Scan to execute a function after setting
  a sweep index in a pulse-lib sequence.

## \[1.4.20] - 2023-04-04

- Improved ScriptRunner
- Enabled compression on HDF5 files
- Fixed axis is data browser for small relative scale.

## \[1.4.19] - 2023-03-02

- Fixed VideoMode DC voltage missing gates
- Fixed data browser hangup after setting unknown sample or project

## \[1.4.18] - 2023-03-01

- VideoMode added 'Set DC voltage' to 2D
- VideoMode added cross in 2D
- VideoMode added color bar in 2D
- VideoMode added background filter in 2D
- VideoMode added 2D plot coordinates in status bar
- VideoMode added 'gates' to PPT notes
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
