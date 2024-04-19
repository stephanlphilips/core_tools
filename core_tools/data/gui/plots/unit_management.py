from pyqtgraph.functions import siScale


_si_prefixes = {
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "" : 1,
    "m": 1e-3,
    "u": 1e-6,
    "\u03BC": 1e-6,  # mu
    "n": 1e-9,
    "p": 1e-12,
    "f": 1e-15,
    }
_si_units = ["s", "Hz", "A", "V", "Ohm", "\u03A9", "H", "T"]

_auto_si_units = {
    prefix+unit: scale
    for prefix, scale in _si_prefixes.items()
    for unit in _si_units
    }


def fix_units(unit):
    try:
        scale = _auto_si_units[unit]
        return unit[1:], scale
    except KeyError:
        return unit, 1.0

def format_value_and_unit(value, unit, precision=1):
    d = precision
    if unit in [None, '', '#']:
        return f"{value:#.{d}g}"
    try:
        scale = _auto_si_units[unit]
        value *= scale
        unit = unit[1:]
        prefixscale, prefix = siScale(value)
        value = value * prefixscale
        unit = prefix+unit
    except KeyError:
        pass
    return f"{value:#.{d}g} {unit}"


def format_unit(unit):
    return fix_units(unit)[0]


def return_unit_scaler(unit):
    return fix_units(unit)[1]


