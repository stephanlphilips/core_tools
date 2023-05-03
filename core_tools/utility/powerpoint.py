import matplotlib
import qcodes
import tempfile
import logging
import numpy as np
import matplotlib.pyplot as plt
from collections import OrderedDict
from matplotlib.widgets import Button
from PyQt5 import QtGui, QtWidgets

logger = logging.getLogger(__name__)

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


def _convert_integer_to_rgb_color(value):
    red = value & 0xFF
    green = (value >> 8) & 0xFF
    blue = (value >> 16) & 0xFF
    return (red, green, blue)


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
        print(f' - Current color: {_convert_integer_to_rgb_color(fore_color.RGB)}')
        print(f' - Setting to {color} -> {ppt_color}')

    slide.FollowMasterBackground = 0
    fore_color.RGB = ppt_color


def _ppt_determine_image_position(ppt, figsize, fname, verbose=0):
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
            shape = cv2.imread(fname).shape
            imwh = shape[1], shape[0]
        except:
            imwh = None
        if imwh is not None:
            imratio = imwh[0] / imwh[1]
            slideratio = slidewh[0] / slidewh[1]
            if verbose > 1:
                print(f' image aspect ratio {imratio:.2f}, slide aspect ratio {slideratio:.2f}')
            if slideratio > imratio:
                # wide slide, so make the image width smaller
                if verbose:
                    print(f' adjust image width {width}->{height * imratio:.1f}')
                width = (height * imratio)
            else:
                # wide image, so make the image height smaller
                if verbose:
                    print(f' adjust image height {height}->{width / imratio:.1f}')
                height = (width / imratio)

        if verbose >= 2:
            print(f' slide size: {slidewh}')
        if verbose:
            print(f' image size: {width:.1f}, {height:.1f}')
    return left, top, width, height


def create_figure_ppt_callback(fig, title=None, notes=None, position=(0.9, 0.925, 0.075, 0.05)):
    """ Create a callback on a matplotlib figure to copy data to PowerPoint slide.

    The figure is copied to PowerPoint using @ref addPPTslide.

    Args:
        fig (int): handle to matplotlib window.
        title (None or str): title for the slide.
        notes (None or str): notes to add to the slide.
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
        print(f'creating PowerPoint slide for figure {fig}')
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
            print('Number of open PPTs: {Application.presentations.Count}.')

        try:
            ppt = Application.ActivePresentation
        except Exception:
            print('Could not open active Powerpoint presentation, opening blank presentation.')
            try:
                ppt = Application.Presentations.Add()
            except Exception:
                logger.warn('Could not make connection to Powerpoint presentation.')
                return None, None

        if show:
            Application.Visible = True  # shows what's happening, not required, but helpful for now

        if verbose >= 2:
            print('addPPTslide: presentation name: {ppt.Name}')

        ppLayoutTitleOnly = 11
        ppLayoutText = 2

        if txt is not None:
            if subtitle is None:
                logger.warn('please do not use the txt field any more')
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
            warning_message = f"Your presentation has more than {max_slides_count_warning} slides! " \
                "Please start a new measurement logbook."
            logger.warn(warning_message)
        if ppt.Slides.Count > max_slides_count:
            error_message = f"Your presentation has more than {max_slides_count} slides! " \
                "Please start a new measurement logbook."
            raise MemoryError(error_message)

        if verbose:
            print(f'addPPTslide: presentation name: {ppt.Name}, adding slide {ppt.Slides.count + 1}')

        slide = ppt.Slides.Add(ppt.Slides.Count + 1, ppLayout)

        if background_color is not None:
            set_ppt_slide_background(slide, background_color, verbose=verbose)

        if fig is None:
            mainbox = slide.shapes.Item(2)
            if maintext is None:
                raise TypeError('maintext argument is None')
            mainbox.TextFrame.TextRange.Text = maintext
        else:
            mainbox = None
            if maintext is not None:
                logger.warn('maintext not implemented when figure is set')

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
                    raise TypeError(f'figure is of an unknown type {type(fig)}')
            top = 120

            left, top, width, height = _ppt_determine_image_position(ppt, figsize, fname)

            if verbose >= 2:
                print(f'fname {fname}')
            slide.Shapes.AddPicture(FileName=fname, LinkToFile=False,
                                    SaveWithDocument=True, Left=left, Top=top, Width=width, Height=height)

        if subtitle is not None:
            # add subtitle
            subtitlebox = slide.Shapes.AddTextbox(
                1, Left=600, Top=120, Width=300, Height=300)
            subtitlebox.Name = 'subtitle box'
            subtitlebox.TextFrame.TextRange.Text = subtitle

        if notes is None:
            logger.warn('Please set notes for the powerpoint slide.')
        if isinstance(notes, qcodes.Station):
            station = notes
            gates = getattr(station, 'gates', None)
            notes = reshape_metadata_station(station)
            if extranotes is not None:
                notes = '\n' + extranotes + '\n' + notes
            if gates is not None:
                notes = 'gates: ' + str(gates.allvalues()) + '\n\n' + notes

        if notes is not None:
            if notes == '':
                notes = ' '
            slide.notespage.shapes.placeholders[
                2].textframe.textrange.insertafter(notes)

        if activate_slide:
            idx = int(slide.SlideIndex)
            if verbose >= 2:
                print(f'addPPTslide: goto slide {idx}' )
            Application.ActiveWindow.View.GotoSlide(idx)
        return ppt, slide


except ImportError:
    def addPPTslide(title=None, fig=None, txt=None, notes=None, figsize=None,
                    subtitle=None, maintext=None, show=False, verbose=1,
                    activate_slide=True, ppLayout=None, extranotes=None, background_color=None):
        ''' Dummy implementation '''
        logger.error('addPPTslide is not available on your system')


def reshape_metadata_station(station):
    '''Reshape the metadata of a qcodes station

    Arguments:
        station (qcodes.Station): a station of which the metadata will be reshaped.
    Returns:
        metadata (string): the reshaped metadata
    '''

    all_md = station.snapshot(update=False)['instruments']

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
                logger.error('failed on parameter %s / %s: %s' % (x, y, str(ex)))

    ss = ''
    for k in metadata:
        s = metadata[k]
        ss += '\n## %s:\n' % k
        for p in s:
            pp = s[p]
            ss += '%s: %s (%s)' % (pp['name'],
                                   pp.get('value', '?'), pp.get('unit', ''))
            ss += '\n'

    return ss
