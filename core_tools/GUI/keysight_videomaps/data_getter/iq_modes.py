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
