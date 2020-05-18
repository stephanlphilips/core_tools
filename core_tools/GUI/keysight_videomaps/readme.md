# Liveplotting for Keysight AWG

## Requirements
In order for this to work well, you need to have loaded a averaging module on the FPGA firmware of the digitzer. For the rest things should be rather straightforward.

## Example Keysight :
Simple example for booting up the LivePlotting GUI,
```python
from V2_software.LivePlotting.liveplotting import V2_liveplotting
from V2_software.drivers.M3102_firmware_loader import firmware_loader, M3102A_CLEAN, M3102A_AVG
from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib

# load the AWG library 
pulse, _ = return_pulse_lib(None, station.AWG1, station.AWG2, station.AWG3)
# make sure the right firmware is loaded
autoconfig_digitizer(M3102A_AVG)


V2_liveplotting(pulse, station.dig, "Keysight")
```
Now you should see something like:
![LivePlot 1D example](../img/videomode_example.PNG)

Some notes:
* 100us per point seems to be around the maximal average time that the FPGA seems the accept. Reason for this is unclear
* At the moment the number of points per scan is limited to 1000 points for 1D and 33x33 for 2D, this is a firmware limitation (Keysight is working on a fix for this)
* The biasT correction can be used to correct for the biasT's in case you want to take a charge stability diagram that takes longer than then RC time of the biasT's.
* Current overhead on the FPGA is ~2.1us per pixel you take. This value is fixed by the rearm time of the digitizer.
* The modulation tab is under development and should not be used at the moment.

## developer notes :
The software can also be run in a simulation mode,

```python
from V2_software.LivePlotting.data_getter.scan_generator_Virtual import construct_1D_scan_fast, construct_2D_scan_fast, fake_digitizer
from V2_software.pulse_lib_config.Init_pulse_lib import return_pulse_lib

# load a virtual version of the digitizer.
dig = fake_digitizer("fake_digitizer")

# load the AWG library (without loading the awg's) 
pulse, _ = return_pulse_lib()

V2_liveplotting(pulse,dig)
```

The structure of the code is as follows:
  * liveplotting.py : contains only the event handler for the GUI
  * GUI/ : Contains the user interface (generated from the UI file with pyuic5)
  * data_getter/ : contains the classes that are used to fetch data. If you want to add an additional support for different hardware, this is the place to do it.
  * plotter/ : contains the pyqtgraph items that plot stuff. This code is stand alond and can by tested by executing the single files.


So the main thing to add new hardware is, 
 1) make a data getter that has a similar format than the one given (e.g. one function that uploads, and a QCoDeS parameter for getting data)
 2) add the new classes to liveplotting.py (e.g. extend the 'scan_type' argument)
