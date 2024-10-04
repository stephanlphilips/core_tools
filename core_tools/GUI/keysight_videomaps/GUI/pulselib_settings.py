import logging

from pulse_lib.base_pulse import pulselib


logger = logging.getLogger(__name__)


class PulselibSettings:
    def __init__(self, pulse_lib: pulselib):
        self._pulse_lib = pulse_lib
        self._attenuations: dict[str, any] = None
        self._v_gate_projection: dict[str, any] = None

        # TODO change this check in a required update to 1.7.31+
        if hasattr(pulselib, "get_virtual_gate_projection"):
            self._check_pulselib = True
        else:
            logger.error("Upgrade to pulse-lib 1.7.31+ for automatic reload "
                         "after virtual gate change")
            self._check_pulselib = False

    def store(self):
        if not self._check_pulselib:
            return
        attenuations = self._pulse_lib.get_channel_attenuations()
        self._attenuations = attenuations.copy()
        v_gate_projection = self._pulse_lib.get_virtual_gate_projection()
        self._v_gate_projection = v_gate_projection.copy()

    def has_changes(self):
        if not self._check_pulselib:
            return False
        attenuations = self._pulse_lib.get_channel_attenuations()
        v_gate_projection = self._pulse_lib.get_virtual_gate_projection()
        return (
            self._attenuations != attenuations
            or self._v_gate_projection != v_gate_projection
            )

