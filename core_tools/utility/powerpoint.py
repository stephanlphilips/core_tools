import sys
import os
import numpy as np
import pprint
import matplotlib
import logging
import qcodes
import warnings
import functools
import pickle
import inspect
import tempfile
from itertools import chain
import scipy.ndimage as ndimage
from functools import wraps
import datetime
import subprocess
import time
import importlib
import platform
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

# explicit import
from qcodes.plots.qcmatplotlib import MatPlot
try:
    from qcodes.plots.pyqtgraph import QtPlot
except:
    pass

# do NOT load any other qtt submodules here

try:
    import qtpy.QtGui as QtGui
    import qtpy.QtCore as QtCore
    import qtpy.QtWidgets as QtWidgets
except:
    pass


def _convert_rgb_color_to_integer(rgb_color):
    if not isinstance(rgb_color, tuple) or not all(isinstance(i, int) for i in rgb_color):
        raise ValueError('Color should be an RGB integer tuple.')

    if len(rgb_color) != 3:
        raise ValueError('Color should be an RGB integer tuple with three items.')

    if any(i < 0 or i > 255 for i in rgb_color):
        raise ValueError('Color should be an RGB tuple in the range 0 to 255.')

    red = rgb_color[0]
    green = rgb_color[1] << 8
    blue = rgb_color[2] << 16
    return int(red + green + blue)

def set_ppt_slide_background(slide, color, verbose=0):
    """ Sets the background color of PPT slide.

    Args:
        slide (object): PowerPoint COM object for slide.
        color (tuple): tuple with RGB color specification.
    """
    fore_color = slide.Background.Fill.ForeColor
    ppt_color = _convert_rgb_color_to_integer(color)
    if verbose > 1:
        print('Setting PPT slide background color:')
        print(' - Current color: {0}'.format(_covert_integer_to_rgb_color(fore_color.RGB)))
        print(' - Setting to {0} -> {1}'.format(color, ppt_color))

    slide.FollowMasterBackground = 0
    fore_color.RGB = ppt_color

# %%


def _ppt_determine_image_position(ppt, figsize, fname, verbose=1):
    top = 120

    if figsize is not None:
        left = (ppt.PageSetup.SlideWidth - figsize[0]) / 2
        width = figsize[0]
        height = figsize[1]
    else:
        slidewh = [ppt.PageSetup.SlideWidth, ppt.PageSetup.SlideHeight]
        width = 16 * ((slidewh[0] * .75) // 16)
        height = 16 * (((slidewh[1] - 120) * .9) // 16)
        height = min(height, 350)
        left = (slidewh[0] - width) / 2

        try:
            import cv2
            imwh = cv2.imread(fname).shape[1], cv2.imread(fname).shape[0]
        except:
            imwh = None
        if imwh is not None:
            imratio = imwh[0] / imwh[1]
            slideratio = slidewh[0] / slidewh[1]
            if verbose >= 1:
                print(' image aspect ratio %.2f, slide aspect ratio %.2f' % (imratio, slideratio))
            if slideratio > imratio:
                # wide slide, so make the image width smaller
                print('adjust width %d->%d' % (width, height * imratio))
                width = height * imratio
            else:
                # wide image, so make the image height smaller
                print('adjust height %d->%d' % (height, width / imratio))
                height = int(width / imratio)

        if verbose:
            print('slide width height: %s' % (slidewh,))
            print('image width height: %d, %d' % (width, height))
    return left, top, width, height


def create_figure_ppt_callback(fig, title=None, notes=None, position=(0.9, 0.925, 0.075, 0.05)):
    """ Create a callback on a matplotlib figure to copy data to PowerPoint slide.

    The figure is copied to PowerPoint using @ref addPPTslide.

    Args:
        fig (int): handle to matplotlib window.
        title (None or str): title for the slide.
        notes (None or str or DataSet): notes to add to the slide.
        position (list): position specified as fraction left, right, width, height.

    Example:
        >>> plt.figure(10)
        >>> plt.plot(np.arange(100), np.random.rand(100), 'o', label='input data')
        >>> create_figure_ppt_callback(10, 'test')
        >>> plt.show()
    """
    plt.figure(fig)
    ax = plt.gca()
    ppt_axis = plt.axes(position)
    ppt_button = Button(ppt_axis, 'ppt')
    ppt_axis._button = ppt_button
    ppt_axis.set_alpha(.5)
    plt.sca(ax)

    def figure_ppt_callback(event):
        print('creating PowerPoint slide for figure %d' % fig)
        ppt_axis.set_visible(False)
        addPPTslide(fig=fig, title=title, notes=notes)
        ppt_axis.set_visible(True)

    ppt_button.on_clicked(figure_ppt_callback)


try:
    import win32com
    import win32com.client

    def addPPTslide(title=None, fig=None, txt=None, notes=None, figsize=None,
                    subtitle=None, maintext=None, show=False, verbose=1,
                    activate_slide=True, ppLayout=None, extranotes=None, background_color=None):
        """ Add slide to current active Powerpoint presentation

        Arguments:
            title (str): title added to slide
            fig (matplotlib.figure.Figure or qcodes.plots.pyqtgraph.QtPlot or integer): 
                figure added to slide
            subtitle (str): text added to slide as subtitle
            maintext (str): text in textbox added to slide
            notes (str or QCoDeS station): notes added to slide
            figsize (list): size (width,height) of figurebox to add to powerpoint
            show (boolean): shows the powerpoint application
            verbose (int): print additional information
            background_color (None or tuple): background color for the slide
        Returns:
            ppt: PowerPoint presentation
            slide: PowerPoint slide

        The interface to Powerpoint used is described here:
            https://msdn.microsoft.com/en-us/library/office/ff743968.aspx

        Example:
            >>> title = 'An example title'
            >>> fig = plt.figure(10)
            >>> txt = 'Some comments on the figure'
            >>> notes = 'some additional information' 
            >>> addPPTslide(title,fig, subtitle = txt,notes = notes)
        """
        Application = win32com.client.Dispatch("PowerPoint.Application")

        if verbose >= 2:
            print('Number of open PPTs: %d.' % Application.presentations.Count)

        try:
            ppt = Application.ActivePresentation
        except Exception:
            print('Could not open active Powerpoint presentation, opening blank presentation.')
            try:
                ppt = Application.Presentations.Add()
            except Exception as ex:
                warnings.warn('Could not make connection to Powerpoint presentation.')
                return None, None

        if show:
            Application.Visible = True  # shows what's happening, not required, but helpful for now

        if verbose >= 2:
            print('addPPTslide: presentation name: %s' % ppt.Name)

        ppLayoutTitleOnly = 11
        ppLayoutText = 2

        if txt is not None:
            if subtitle is None:
                warnings.warn('please do not use the txt field any more')
                subtitle = txt
            else:
                raise ValueError('please do not use the txt field any more')

            txt = None

        if fig is None:
            # no figure, text box over entire page
            if ppLayout is None:
                ppLayout = ppLayoutText
        else:
            # we have a figure, assume textbox is for dataset name only
            ppLayout = ppLayoutTitleOnly

        max_slides_count_warning = 750
        max_slides_count = 950
        if ppt.Slides.Count > max_slides_count_warning:
            warning_message = "Your presentation has more than {} slides! \
                Please start a new measurement logbook.".format(max_slides_count_warning)
            warnings.warn(warning_message)
        if ppt.Slides.Count > max_slides_count:
            error_message = "Your presentation has more than {} slides! \
                Please start a new measurement logbook.".format(max_slides_count)
            raise MemoryError(error_message)

        if verbose:
            print('addPPTslide: presentation name: %s, adding slide %d' %
                  (ppt.Name, ppt.Slides.count + 1))

        slide = ppt.Slides.Add(ppt.Slides.Count + 1, ppLayout)

        if background_color is not None:
            set_ppt_slide_background(slide, background_color, verbose=verbose)

        if fig is None:
            titlebox = slide.shapes.Item(1)
            mainbox = slide.shapes.Item(2)
            if maintext is None:
                raise TypeError('maintext argument is None')
            mainbox.TextFrame.TextRange.Text = maintext
        else:
            titlebox = slide.shapes.Item(1)
            mainbox = None
            if maintext is not None:
                warnings.warn('maintext not implemented when figure is set')

        if title is not None:
            slide.shapes.title.textframe.textrange.text = title
        else:
            slide.shapes.title.textframe.textrange.text = 'QCoDeS measurement'

        if fig is not None:
            fname = tempfile.mktemp(prefix='qcodesimageitem', suffix='.png')
            if isinstance(fig, matplotlib.figure.Figure):
                fig.savefig(fname)
            elif isinstance(fig, int):
                fig = plt.figure(fig)
                fig.savefig(fname)
            elif isinstance(fig, QtWidgets.QWidget):
                # generic method
                figtemp = fig.plotwin.grab()
                figtemp.save(fname)
            elif isinstance(fig, QtWidgets.QWidget):
                try:
                    figtemp = QtGui.QPixmap.grabWidget(fig)
                except:
                    # new Qt style
                    figtemp = fig.grab()
                figtemp.save(fname)
            elif isinstance(fig, qcodes.plots.pyqtgraph.QtPlot):
                fig.save(fname)
            else:
                if verbose:
                    raise TypeError('figure is of an unknown type %s' % (type(fig), ))
            top = 120

            left, top, width, height = _ppt_determine_image_position(ppt, figsize, fname, verbose=1)

            if verbose >= 2:
                print('fname %s' % fname)
            slide.Shapes.AddPicture(FileName=fname, LinkToFile=False,
                                    SaveWithDocument=True, Left=left, Top=top, Width=width, Height=height)

        if subtitle is not None:
            # add subtitle
            subtitlebox = slide.Shapes.AddTextbox(
                1, Left=600, Top=120, Width=300, Height=300)
            subtitlebox.Name = 'subtitle box'
            subtitlebox.TextFrame.TextRange.Text = subtitle

        if notes is None:
            warnings.warn(
                'please set notes for the powerpoint slide. e.g. use the station or reshape_metadata')

        if isinstance(notes, qcodes.Station):
            station = notes
            gates = getattr(station, 'gates', None)
            notes = reshape_metadata(station, printformat='s', add_scanjob=True)
            if extranotes is not None:
                notes = '\n' + extranotes + '\n' + notes
            if gates is not None:
                notes = 'gates: ' + str(gates.allvalues()) + '\n\n' + notes
        if isinstance(notes, qcodes.DataSet):
            notes = reshape_metadata(notes, printformat='s', add_gates=True)

        if notes is not None:
            if notes == '':
                notes = ' '
            slide.notespage.shapes.placeholders[
                2].textframe.textrange.insertafter(notes)

        if activate_slide:
            idx = int(slide.SlideIndex)
            if verbose >= 2:
                print('addPPTslide: goto slide %d' % idx)
            Application.ActiveWindow.View.GotoSlide(idx)
        return ppt, slide

    def addPPT_dataset(dataset, title=None, notes=None,
                       show=False, verbose=1, paramname='measured',
                       printformat='fancy', customfig=None, extranotes=None, **kwargs):
        """ Add slide based on dataset to current active Powerpoint presentation

        Args:
            dataset (DataSet): data and metadata from DataSet added to slide
            customfig (QtPlot): custom QtPlot object to be added to
                                slide (for dataviewer)
            notes (string): notes added to slide
            show (boolean): shows the powerpoint application
            verbose (int): print additional information
            paramname (None or str): passed to dataset.default_parameter_array
            printformat (string): 'fancy' for nice formatting or 'dict'
                                  for easy copy to python
        Returns:
            ppt: PowerPoint presentation
            slide: PowerPoint slide

        Example
        -------
        >>> notes = 'some additional information'
        >>> addPPT_dataset(dataset,notes)
        """
        if len(dataset.arrays) < 2:
            raise IndexError('The dataset contains less than two data arrays')

        if customfig is None:

            if isinstance(paramname, str):
                if title is None:
                    parameter_name = dataset.default_parameter_name(paramname=paramname)
                    title = 'Parameter: %s' % parameter_name
                temp_fig = QtPlot(dataset.default_parameter_array(
                    paramname=paramname), show_window=False)
            else:
                if title is None:
                    title = 'Parameter: %s' % (str(paramname),)
                for idx, parameter_name in enumerate(paramname):
                    if idx == 0:
                        temp_fig = QtPlot(dataset.default_parameter_array(
                            paramname=parameter_name), show_window=False)
                    else:
                        temp_fig.add(dataset.default_parameter_array(
                            paramname=parameter_name))

        else:
            temp_fig = customfig

        text = 'Dataset location: %s' % dataset.location
        if notes is None:
            try:
                metastring = reshape_metadata(dataset,
                                              printformat=printformat)
            except Exception as ex:
                metastring = 'Could not read metadata: %s' % str(ex)
            notes = 'Dataset %s metadata:\n\n%s' % (dataset.location,
                                                    metastring)
            scanjob = dataset.metadata.get('scanjob', None)
            if scanjob is not None:
                s = pprint.pformat(scanjob)
                notes = 'scanjob: ' + str(s) + '\n\n' + notes

            gatevalues = dataset.metadata.get('allgatevalues', None)
            if gatevalues is not None:
                notes = 'gates: ' + str(gatevalues) + '\n\n' + notes

        ppt, slide = addPPTslide(title=title, fig=temp_fig, subtitle=text,
                                 notes=notes, show=show, verbose=verbose,
                                 extranotes=extranotes,
                                 **kwargs)
        return ppt, slide

except ImportError:
    def addPPTslide(title=None, fig=None, txt=None, notes=None, figsize=None,
                    subtitle=None, maintext=None, show=False, verbose=1,
                    activate_slide=True, ppLayout=None, extranotes=None, background_color=None):
        ''' Dummy implementation '''
        warnings.warn('addPPTslide is not available on your system')

    def addPPT_dataset(dataset, title=None, notes=None,
                       show=False, verbose=1, paramname='measured',
                       printformat='fancy', customfig=None, extranotes=None, **kwargs):
        """ Dummy implementation """
        warnings.warn('addPPT_dataset is not available on your system')

# %%
from collections import OrderedDict


def reshape_metadata(dataset, printformat='dict', add_scanjob=True, add_gates=True, verbose=0):
    '''Reshape the metadata of a DataSet

    Arguments:
        dataset (DataSet or qcodes.Station): a dataset of which the metadata 
                                             will be reshaped.
        printformat (str): can be 'dict' or 'txt','fancy' (text format)
        add_scanjob (bool): If True, then add the scanjob at the beginning of the notes
        add_gates (bool): If True, then add the scanjob at the beginning of the notes
    Returns:
        metadata (string): the reshaped metadata
    '''

    if isinstance(dataset, qcodes.Station):
        station = dataset
        all_md = station.snapshot(update=False)['instruments']
        header = None
    else:
        if not 'station' in dataset.metadata:
            return 'dataset %s: no metadata available' % (str(dataset.location), )

        tmp = dataset.metadata.get('station', None)
        if tmp is None:
            all_md = {}
        else:
            all_md = tmp['instruments']

        header = 'dataset: %s' % dataset.location

        if hasattr(dataset.io, 'base_location'):
            header += ' (base %s)' % dataset.io.base_location

    if add_gates:
        gate_values = dataset.metadata.get('allgatevalues', None)

        if gate_values is not None:
            gate_values = dict([(key, np.around(value, 3)) for key, value in gate_values.items()])
            header += '\ngates: ' + str(gate_values) + '\n'

    scanjob = dataset.metadata.get('scanjob', None)
    if scanjob is not None and add_scanjob:
        s = pprint.pformat(scanjob)
        header += '\n\nscanjob: ' + str(s) + '\n'

    metadata = OrderedDict()
    # make sure the gates instrument is in front
    all_md_keys = sorted(sorted(all_md), key=lambda x: x ==
                         'gate s',  reverse=True)
    for x in all_md_keys:
        metadata[x] = OrderedDict()
        if 'IDN' in all_md[x]['parameters']:
            metadata[x]['IDN'] = dict({'name': 'IDN', 'value': all_md[
                                      x]['parameters']['IDN']['value']})
            metadata[x]['IDN']['unit'] = ''
        for y in sorted(all_md[x]['parameters'].keys()):
            try:
                if y != 'IDN':
                    metadata[x][y] = OrderedDict()
                    param_md = all_md[x]['parameters'][y]
                    metadata[x][y]['name'] = y
                    if isinstance(param_md['value'], (float, np.float64)):
                        metadata[x][y]['value'] = float(
                            format(param_md['value'], '.3f'))
                    else:
                        metadata[x][y]['value'] = str(param_md['value'])
                    metadata[x][y]['unit'] = param_md.get('unit', None)
                    metadata[x][y]['label'] = param_md.get('label', None)
            except KeyError as ex:
                if verbose:
                    print('failed on parameter %s / %s: %s' % (x, y, str(ex)))

    if printformat == 'dict':
        ss = str(metadata).replace('(', '').replace(
            ')', '').replace('OrderedDict', '')
    else:  # 'txt' or 'fancy'
        ss = ''
        for k in metadata:
            if verbose:
                print('--- %s' % k)
            s = metadata[k]
            ss += '\n## %s:\n' % k
            for p in s:
                pp = s[p]
                if verbose:
                    print('  --- %s: %s' % (p, pp.get('value', '??')))
                ss += '%s: %s (%s)' % (pp['name'],
                                       pp.get('value', '?'), pp.get('unit', ''))
                ss += '\n'

    if header is not None:
        ss = header + '\n\n' + ss
    return ss
