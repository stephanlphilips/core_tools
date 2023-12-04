from typing import List, Optional
import numpy as np


iq_mode2numpy = {
        'I': np.real,
        'Q': np.imag,
        'amplitude': np.abs,
        'phase': np.angle,
        'phase_deg': lambda x:np.angle(x, deg=True),
        'I+Q': [('_I', np.real), ('_Q', np.imag)],
        'amplitude+phase': [('_amp', np.abs), ('_phase', np.angle)],
        'abs': np.abs,
        'angle': np.angle,
        'angle_deg': lambda x:np.angle(x, deg=True),
        'abs+angle': [('_amp', np.abs), ('_phase', np.angle)],
        }


# TODO: Add to pulse-lib
def get_channel_map(pulse, iq_mode: str, channels: Optional[List[str]] = None):
    if iq_mode is None:
        iq_func = np.real
    else:
        iq_func = iq_mode2numpy[iq_mode]

    channel_map = {}
    for name, dig_ch in pulse.digitizer_channels.items():
        if channels and name not in channels:
             continue
        if dig_ch.iq_input or dig_ch.frequency or dig_ch.iq_out:
            # IQ data available
            if isinstance(iq_func, list):
                for suffix, f in iq_func:
                    channel_map[name+suffix] = (name, f)
            else:
                channel_map[name] = (name, iq_func)
        else:
            # Most likely already real data. Take real part to be sure.
            if iq_mode and iq_mode not in ['I', 'amplitude']:
                print(f"Warning iq_mode '{iq_mode}' has no effect on channel '{name}'")
            channel_map[name] = (name, np.real)
    return channel_map


def get_channel_map_dig_4ch(iq_mode: str, channel_numbers: Optional[List[int]] = None):
    # Old Keysight and Tektronix code.
    if iq_mode is None:
        iq_func = np.real
    else:
        iq_func = iq_mode2numpy[iq_mode]

    if not channel_numbers:
        channel_numbers = range(1,5)
    channels = [(f'ch{i}', i) for i in channel_numbers]

    channel_map = {}
    for name, channel in channels:
        if isinstance(iq_func, list):
            for suffix, f in iq_func:
                channel_map[name+suffix] = (channel, f)
        else:
            channel_map[name] = (channel, iq_func)

    return channel_map
