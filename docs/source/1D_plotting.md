1D plotting
===========

This manual gives as short introduction to the classes that are constructed to make easy paper ready figures.
For both one and two dimensional figures there are two settings classes that will determine how the plot will look.
* The layout class : determines how many figures will be in one panel
* The settings class : determines the settings of lines/points in the graph (e.g. colors, labels, line thicknesses, ...)

The plots are rendered in SVG format. This is a well supported and modern format that should work in most illustration programs (e.g. Adobe Illustrator).

Creating a simple 1D plot
-------------------------

A very simple 1D plot can be created by :

```python
from COLORS import MATERIAL_COLOR, Red

# Load a 1D plot with default layout and settings
a = plot_data_1D()
# Load in the first plot in the layout some setting 
a[0].set_labels('x_label', 'y_label')
a[0].add_data(np.linspace(10,50,200), np.sin(np.linspace(10,50,200)))
a[0].add_data(np.linspace(10,50,200), np.sin(np.linspace(10,50,200)+1))

# a.save_svg('./test.svg')
a.plot() # plot in a python terminal for quick inspection 
```

We can further customize the plots by 