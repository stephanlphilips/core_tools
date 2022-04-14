# Changelog
All notable changes to core_tools will be documented in this file.

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
