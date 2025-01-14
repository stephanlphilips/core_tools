import numpy as np


iq_mode2numpy = {
        'I': [('', np.real, 'mV')],
        'Q': [('', np.imag, 'mV')],
        'amplitude': [('', np.abs, 'mV')],
        'phase': [('', np.angle, 'rad')],
        'phase_deg': [('', lambda x: np.angle(x, deg=True), 'deg')],
        'I+Q': [('_I', np.real, 'mV'), ('_Q', np.imag, 'mV')],
        'amplitude+phase': [('_amp', np.abs, 'mV'), ('_phase', np.angle, 'rad')],
        'abs': [('', np.abs, 'mV')],
        'angle': [('', np.angle, 'rad')],
        'angle_deg': [('', lambda x: np.angle(x, deg=True), 'deg')],
        'abs+angle': [('_amp', np.abs, 'mV'), ('_phase', np.angle, 'rad')],
        }


# TODO: Add to pulse-lib
def get_channel_map(pulse, iq_mode: str | None, channels: list[str] | None = None):
    if iq_mode is None:
        iq_mode = 'I'
    iq_func = iq_mode2numpy[iq_mode]

    channel_map = {}
    for name, dig_ch in pulse.digitizer_channels.items():
        if channels and name not in channels:
            continue
        if dig_ch.iq_input or dig_ch.frequency or dig_ch.iq_out:
            # IQ data available
            for suffix, f, unit in iq_func:
                channel_map[name+suffix] = (name, f, unit)
        else:
            # Most likely already real data. Take real part to be sure.
            if iq_mode and iq_mode not in ['I', 'amplitude']:
                print(f"Warning iq_mode '{iq_mode}' has no effect on channel '{name}'")
            channel_map[name] = (name, np.real, 'mV')
    return channel_map


def get_channel_map_dig_4ch(iq_mode: str | None, channel_numbers: list[int] | None = None):
    # Old Keysight and Tektronix code.
    if iq_mode is None:
        iq_mode = 'I'
    iq_func = iq_mode2numpy[iq_mode]

    if not channel_numbers:
        channel_numbers = range(1, 5)
    channels = [(f'ch{i}', i) for i in channel_numbers]

    channel_map = {}
    for name, channel_num in channels:
        for suffix, f, unit in iq_func:
            channel_map[name+suffix] = (channel_num, f, unit)

    return channel_map


def add_channel_map_units(channel_map):
    return {key: _add_unit(*args) for key, args in channel_map.items()}


def _add_unit(channel, func, unit='mV'):
    return channel, func, unit
