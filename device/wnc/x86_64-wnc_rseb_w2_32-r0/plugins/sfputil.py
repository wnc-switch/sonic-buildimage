#! /usr/bin/python
#
# Platform-specific SFP transceiver interface for SONiC
#

try:
    import time
    from sonic_sfp.sfputilbase import SfpUtilBase
    import sys
    sys.path.append('/usr/lib/python2.7/dist-packages/sonic_sfp/')
except ImportError, e:
    raise ImportError("%s - required module not found" % str(e))


class SfpUtil(SfpUtilBase):
    """Platform-specific SfpUtil class"""

    @property
    def port_start(self):
        return self._port_start

    @property
    def port_end(self):
        return self._port_end

    @property
    def qsfp_ports(self):
        return range(self._port_end + 1)

    @property
    def port_to_eeprom_mapping(self):
        return self._port_to_eeprom_mapping

    def __init__(self):
        self._port_start = 0
        self._port_end = 31
        self._port_to_eeprom_mapping = {}
        self._port_to_presence_mapping = {}
        self._port_to_low_power_mapping = {}
        self._port_to_reset_mapping = {}
        eeprom_path = "/sys/class/i2c-adapter/i2c-{0}/{0}-0050/eeprom"
        mux_start_channel = (18, 26, 34, 42, 50, 58)
        sfp_path = "/sys/class/gpio/gpio{0}/value"
        gpio_start_pin = (489, 465, 441, 417, 393, 369)

        port_num = 0
        for start_port_channel in mux_start_channel:
            end_port_channel = start_port_channel + 6
            for x in range(start_port_channel, end_port_channel):
                self._port_to_eeprom_mapping[port_num] = eeprom_path.format(x)
                port_num += 1
                if port_num > self.port_end:
                    break

        port_num = 0
        for start_pin in gpio_start_pin:
            list_gpio = [start_pin + x*4 for x in range(6)]
            for x in list_gpio:
                self._port_to_presence_mapping[port_num] = sfp_path.format(x)
                self._port_to_low_power_mapping[port_num] = sfp_path.format(x+1)
                self._port_to_reset_mapping[port_num] = sfp_path.format(x+2)
                port_num += 1
                if port_num > self.port_end:
                    break

        SfpUtilBase.__init__(self)

    def get_presence(self, port_num):
        if port_num < self.port_start or port_num > self.port_end:
            return False

        with open(self._port_to_presence_mapping[port_num], "rb") as reg_file:
            reg_value = int(reg_file.readline().rstrip())
            if reg_value == 0:
                return True
            else:
                return False

    def get_low_power_mode(self, port_num):
        if port_num < self.port_start or port_num > self.port_end:
            return False

        with open(self._port_to_low_power_mapping[port_num], "rb") as reg_file:
            reg_value = int(reg_file.readline().rstrip())
            if reg_value == 1:
                return True
            else:
                return False

    def set_low_power_mode(self, port_num, lpmode):
        if port_num < self.port_start or port_num > self.port_end:
            return False

        with open(self._port_to_low_power_mapping[port_num], "r+") as reg_file:
            reg_file.seek(0)
            reg_file.write(str(int(lpmode)))

        return True

    def reset(self, port_num):
        if port_num < self.port_start or port_num > self.port_end:
            return False

        with open(self._port_to_reset_mapping[port_num], "r+") as reg_file:
            reg_file.seek(0)
            reg_file.write(str("0"))
            time.sleep(1)
            reg_file.seek(0)
            reg_file.write(str("1"))

        return True

    def get_transceiver_change_event(self):
        """
        TODO: This function need to be implemented
        when decide to support monitoring SFP(Xcvrd)
        on this platform.
        """
        raise NotImplementedError
