import numpy as np
import pprint
import qcodes
from collections import OrderedDict
from qcodes.data.data_set import DataSet
from qcodes.plots.pyqtgraph import QtPlot
from .powerpoint import addPPTslide


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
    >>> addPPT_dataset(dataset, notes)
    """
    if len(dataset.arrays) < 2:
        raise IndexError('The dataset contains less than two data arrays')

    if customfig is None:

        if isinstance(paramname, str):
            if title is None:
                parameter_name = dataset.default_parameter_name(paramname=paramname)
                title = 'Parameter: %s' % parameter_name
            temp_fig = QtPlot(
                    dataset.default_parameter_array(paramname=paramname), show_window=False)
        else:
            if title is None:
                title = 'Parameter: %s' % (str(paramname),)
            for idx, parameter_name in enumerate(paramname):
                if idx == 0:
                    temp_fig = QtPlot(
                            dataset.default_parameter_array(paramname=parameter_name), show_window=False)
                else:
                    temp_fig.add(
                            dataset.default_parameter_array(paramname=parameter_name))

    else:
        temp_fig = customfig

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
    elif isinstance(notes, qcodes.Station):
        station = notes
        gates = getattr(station, 'gates', None)
        notes = reshape_metadata(station, printformat='s', add_scanjob=True)
        if extranotes is not None:
            notes = '\n' + extranotes + '\n' + notes
        if gates is not None:
            notes = 'gates: ' + str(gates.allvalues()) + '\n\n' + notes
    elif isinstance(notes, DataSet):
        notes = reshape_metadata(notes, printformat='s', add_gates=True)

    text = 'Dataset location: %s' % dataset.location

    ppt, slide = addPPTslide(title=title, fig=temp_fig, subtitle=text,
                             notes=notes, show=show, verbose=verbose,
                             **kwargs)
    return ppt, slide


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
