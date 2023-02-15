import qcodes as qc

from .config import get_configuration

# global references to GUIs to avoid garbage collection
_pv_qt = None
_pv_qml =  None
_vmg_qt = None
_vmg_qml = None
_script_runner = None

def start_parameter_viewer(keysight_rf=None):
    from core_tools.GUI.param_viewer.param_viewer_GUI_main import param_viewer

    global _pv_qt
    gates = _get_gates()
    cfg = get_configuration()
    _pv_qt = param_viewer(
            gates,
            max_diff=cfg.get('max_diff'),
            keysight_rf=keysight_rf,
            locked = cfg.get('parameter_viewer.lock', False))
    _set_window(_pv_qt, cfg, 'parameter_viewer')
    return _pv_qt


def start_parameter_viewer_qml():
    from core_tools.GUI.parameter_viewer_qml.param_viewer import param_viewer

    global _pv_qml
    gates = _get_gates()
    cfg = get_configuration()
    allow_mouse_wheel_updates = cfg.get('parameter_viewer_qml.allow_mouse_wheel_updates', True)
    _pv_qml = param_viewer(gates, allow_mouse_wheel_updates)
    _set_window_qml(_pv_qml, cfg, 'parameter_viewer_qml')
    return _pv_qml


def start_virtual_matrix_gui(pulse):
    from core_tools.GUI.virt_gate_matrix.virt_gate_matrix_main import virt_gate_matrix_GUI

    global _vmg_qt
    gates = _get_gates()
    cfg = get_configuration()
    _vmg_qt = virt_gate_matrix_GUI(gates, pulse,
                               coloring=cfg.get('virtual_matrix_gui.coloring', True))
    _set_window(_vmg_qt, cfg, 'virtual_matrix_gui')
    return _vmg_qt


def start_virtual_matrix_gui_qml():
    from core_tools.GUI.virt_gate_matrix_qml.gui_controller import virt_gate_matrix_GUI

    global _vmg_qml
    cfg = get_configuration()
    _vmg_qml = virt_gate_matrix_GUI(invert=cfg.get('virtual_matrix_gui_qml.invert_matrix', True))
    _set_window_qml(_vmg_qml, cfg, 'virtual_matrix_gui_qml')
    return _vmg_qml

def start_script_runner():
    from core_tools.GUI.script_runner.script_runner_main import ScriptRunner

    global _script_runner
    cfg = get_configuration()
    _script_runner = ScriptRunner()
    _set_window(_script_runner, cfg, 'script_runner')
    return _script_runner

def _get_station():
    return qc.Station.default

def _get_gates():
    try:
        return _get_station().gates
    except AttributeError:
        raise AttributeError('gates not added to station')

def _set_window(window, cfg, cfg_key):
    try:
        location = cfg[f'{cfg_key}.location']
        window.move(location[0], location[1])
    except KeyError:
        pass
    try:
        size = cfg[f'{cfg_key}.size']
        window.resize(size[0], size[1])
    except KeyError:
        pass

def _set_window_qml(window, cfg, cfg_key):
    try:
        location = cfg[f'{cfg_key}.location']
        window.win.setPosition(location[0], location[1])
    except KeyError:
        pass
    try:
        size = cfg[f'{cfg_key}.size']
        window.win.setWidth(size[0])
        window.win.setHeight(size[1])
    except KeyError:
        pass

