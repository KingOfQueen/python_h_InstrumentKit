#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Provides support for the SRS DG645 digital delay generator.
"""

# IMPORTS #####################################################################

from enum import IntEnum

from instruments.abstract_instruments.comm import GPIBCommunicator
from instruments.generic_scpi import SCPIInstrument
import instruments.units as u
from instruments.util_fns import assume_units, ProxyList

# CLASSES #####################################################################


class _SRSDG645Channel:

    """
    Class representing a sensor attached to the SRS DG645.

    .. warning:: This class should NOT be manually created by the user. It is
        designed to be initialized by the `SRSDG645` class.
    """

    def __init__(self, ddg, chan):
        if not isinstance(ddg, SRSDG645):
            raise TypeError("Don't do that.")

        if isinstance(chan, SRSDG645.Channels):
            self._chan = chan.value
        else:
            self._chan = chan

        self._ddg = ddg

    # PROPERTIES #

    @property
    def idx(self):
        """
        Gets the channel identifier number as used for communication

        :return: The communication identification number for the specified
            channel
        :rtype: `int`
        """
        return self._chan

    @property
    def delay(self):
        """
        Gets/sets the delay of this channel.
        Formatted as a two-tuple of the reference and the delay time.
        For example, ``(SRSDG645.Channels.A, u.Quantity(10, "ps"))``
        indicates a delay of 10 picoseconds from delay channel A.

        :units: Assume seconds if no units given.
        """
        resp = self._ddg.query("DLAY?{}".format(int(self._chan))).split(",")
        return SRSDG645.Channels(int(resp[0])), u.Quantity(float(resp[1]), "s")

    @delay.setter
    def delay(self, newval):
        newval = (newval[0], assume_units(newval[1], u.s))
        self._ddg.sendcmd("DLAY {},{},{}".format(
            int(self._chan),
            int(newval[0].idx),
            newval[1].rescale("s").magnitude
        ))


class SRSDG645(SCPIInstrument):

    """
    Communicates with a Stanford Research Systems DG645 digital delay generator,
    using the SCPI commands documented in the `user's guide`_.

    Example usage:

    >>> import instruments as ik
    >>> import instruments.units as u
    >>> srs = ik.srs.SRSDG645.open_gpibusb('/dev/ttyUSB0', 1)
    >>> srs.channel["B"].delay = (srs.channel["A"], u.Quantity(10, 'ns'))
    >>> srs.output["AB"].level_amplitude = u.Quantity(4.0, "V")

    .. _user's guide: http://www.thinksrs.com/downloads/PDFs/Manuals/DG645m.pdf
    """

    def __init__(self, filelike):
        super(SRSDG645, self).__init__(filelike)

        # This instrument requires stripping two characters.
        if isinstance(filelike, GPIBCommunicator):
            filelike.strip = 2

    # ENUMS #

    class LevelPolarity(IntEnum):

        """
        Polarities for output levels.
        """
        positive = 1
        negative = 0

    class Outputs(IntEnum):

        """
        Enumeration of valid outputs from the DDG.
        """
        T0 = 0
        AB = 1
        CD = 2
        EF = 3
        GH = 4

    class Channels(IntEnum):

        """
        Enumeration of valid delay channels for the DDG.
        """
        T0 = 0
        T1 = 1
        A = 2
        B = 3
        C = 4
        D = 5
        E = 6
        F = 7
        G = 8
        H = 9

    class DisplayMode(IntEnum):

        """
        Enumeration of possible modes for the physical front-panel display.
        """
        trigger_rate = 0
        trigger_threshold = 1
        trigger_single_shot = 2
        trigger_line = 3
        adv_triggering_enable = 4
        trigger_holdoff = 5
        prescale_config = 6
        burst_mode = 7
        burst_delay = 8
        burst_count = 9
        burst_period = 10
        channel_delay = 11
        channel_levels = 12
        channel_polarity = 13
        burst_T0_config = 14

    class TriggerSource(IntEnum):

        """
        Enumeration of the different allowed trigger sources and modes.
        """
        internal = 0
        external_rising = 1
        external_falling = 2
        ss_external_rising = 3
        ss_external_falling = 4
        single_shot = 5
        line = 6

    # INNER CLASSES #

    class Output:

        """
        An output from the DDG.
        """

        def __init__(self, parent, idx):
            self._parent = parent
            self._idx = int(idx)

        @property
        def polarity(self):
            """
            Polarity of this output.

            :type: :class:`SRSDG645.LevelPolarity`
            """
            return self._parent.LevelPolarity(
                int(self._parent.query("LPOL? {}".format(self._idx)))
            )

        @polarity.setter
        def polarity(self, newval):
            if not isinstance(newval, self._parent.LevelPolarity):
                raise TypeError("Mode must be specified as a "
                                "SRSDG645.LevelPolarity value, got {} "
                                "instead.".format(type(newval)))
            self._parent.sendcmd("LPOL {},{}".format(
                self._idx, int(newval.value)
            ))

        @property
        def level_amplitude(self):
            """
            Amplitude (in voltage) of the output level for this output.

            :type: `float` or :class:`~quantities.Quantity`
            :units: As specified, or :math:`\\text{V}` by default.
            """
            return u.Quantity(
                float(self._parent.query('LAMP? {}'.format(self._idx))),
                'V'
            )

        @level_amplitude.setter
        def level_amplitude(self, newval):
            newval = assume_units(newval, 'V').magnitude
            self._parent.sendcmd("LAMP {},{}".format(self._idx, newval))

        @property
        def level_offset(self):
            """
            Amplitude offset (in voltage) of the output level for this output.

            :type: `float` or :class:`~quantities.Quantity`
            :units: As specified, or :math:`\\text{V}` by default.
            """
            return u.Quantity(
                float(self._parent.query('LOFF? {}'.format(self._idx))),
                'V'
            )

        @level_offset.setter
        def level_offset(self, newval):
            newval = assume_units(newval, 'V').magnitude
            self._parent.sendcmd("LOFF {},{}".format(self._idx, newval))

    # PROPERTIES #

    @property
    def channel(self):
        """
        Gets a specific channel object.

        The desired channel is accessed by passing an EnumValue from
        `~SRSDG645.Channels`. For example, to access channel A:

        >>> import instruments as ik
        >>> inst = ik.srs.SRSDG645.open_gpibusb('/dev/ttyUSB0', 1)
        >>> inst.channel[inst.Channels.A]

        See the example in `SRSDG645` for a more complete example.

        :rtype: `_SRSDG645Channel`
        """
        return ProxyList(self, _SRSDG645Channel, SRSDG645.Channels)

    @property
    def output(self):
        """
        Gets the specified output port.

        :type: :class:`SRSDG645.Output`
        """
        return ProxyList(self, self.Output, self.Outputs)

    @property
    def display(self):
        """
        Gets/sets the front-panel display mode for the connected DDG.
        The mode is a tuple of the display mode and the channel.

        :type: `tuple` of an `SRSDG645.DisplayMode` and an `SRSDG645.Channels`
        """
        disp_mode, chan = map(int, self.query("DISP?").split(","))
        return SRSDG645.DisplayMode(disp_mode), SRSDG645.Channels(chan)

    @display.setter
    def display(self, newval):
        # TODO: check types here.
        self.sendcmd("DISP {0},{1}".format(*map(int, newval)))

    @property
    def enable_adv_triggering(self):
        """
        Gets/sets whether advanced triggering is enabled.

        :type: `bool`
        """
        return bool(int(self.query("ADVT?")))

    @enable_adv_triggering.setter
    def enable_adv_triggering(self, newval):
        self.sendcmd("ADVT {}".format(1 if newval else 0))

    @property
    def trigger_rate(self):
        """
        Gets/sets the rate of the internal trigger.

        :type: `~quantities.Quantity` or `float`
        :units: As passed or Hz if not specified.
        """
        return u.Quantity(float(self.query("TRAT?")), u.Hz)

    @trigger_rate.setter
    def trigger_rate(self, newval):
        newval = assume_units(newval, u.Hz)
        self.sendcmd("TRAT {}".format(newval.rescale(u.Hz).magnitude))

    @property
    def trigger_source(self):
        """
        Gets/sets the source for the trigger.

        :type: :class:`SRSDG645.TriggerSource`
        """
        return SRSDG645.TriggerSource(int(self.query("TSRC?")))

    @trigger_source.setter
    def trigger_source(self, newval):
        self.sendcmd("TSRC {}".format(int(newval)))

    @property
    def holdoff(self):
        """
        Gets/sets the trigger holdoff time.

        :type: `~quantities.Quantity` or `float`
        :units: As passed, or s if not specified.
        """
        return u.Quantity(float(self.query("HOLD?")), u.s)

    @holdoff.setter
    def holdoff(self, newval):
        newval = assume_units(newval, u.s)
        self.sendcmd("HOLD {}".format(newval.rescale(u.s).magnitude))

    @property
    def enable_burst_mode(self):
        """
        Gets/sets whether burst mode is enabled.

        :type: `bool`
        """
        return bool(int(self.query("BURM?")))

    @enable_burst_mode.setter
    def enable_burst_mode(self, newval):
        self.sendcmd("BURM {}".format(1 if newval else 0))

    @property
    def enable_burst_t0_first(self):
        """
        Gets/sets whether T0 output in burst mode is on first. If
        enabled, the T0 output is enabled for first delay cycle of the
        burst only. If disabled, the T0 output is enabled for all delay
        cycles of the burst.

        :type: `bool`
        """
        return bool(int(self.query("BURT?")))

    @enable_burst_t0_first.setter
    def enable_burst_t0_first(self, newval):
        self.sendcmd("BURT {}".format(1 if newval else 0))

    @property
    def burst_count(self):
        """
        Gets/sets the burst count. When burst mode is enabled, the
        DG645 outputs burst count delay cycles per trigger.
        Valid numbers for burst count are between 1 and 2**32 - 1
        """
        return int(self.query("BURC?"))

    @burst_count.setter
    def burst_count(self, newval):
        self.sendcmd("BURC {}".format(int(newval)))

    @property
    def burst_period(self):
        """
        Gets/sets the burst period. The burst period sets the time
        between delay cycles during a burst. The burst period may
        range from 100 ns to 2000 – 10 ns in 10 ns steps.

        :units: Assume seconds if no units given.
        """
        return u.Quantity(float(self.query("BURP?")), u.s)

    @burst_period.setter
    def burst_period(self, newval):
        newval = assume_units(newval, u.s)
        self.sendcmd("BURP {}".format(newval.rescale(u.s).magnitude))

    @property
    def burst_delay(self):
        """
        Gets/sets the burst delay. When burst mode is enabled the DG645
        delays the first burst pulse relative to the trigger by the
        burst delay. The burst delay may range from 0 ps to < 2000 s
        with a resolution of 5 ps.

        :units: Assume seconds if no units given.
        """
        return u.Quantity(float(self.query("BURD?")), u.s)

    @burst_delay.setter
    def burst_delay(self, newval):
        newval = assume_units(newval, u.s)
        self.sendcmd("BURD {}".format(newval.rescale(u.s).magnitude))
