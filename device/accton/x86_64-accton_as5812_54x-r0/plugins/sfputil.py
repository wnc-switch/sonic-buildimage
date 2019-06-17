# sfputil.py
#
# Platform-specific SFP transceiver interface for SONiC
#
try:
    import time
    import os
    import pickle
    from ctypes import create_string_buffer
    from sonic_sfp.sfputilbase import SfpUtilBase
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))


class SfpUtil(SfpUtilBase):
    """Platform-specific SfpUtil class"""

    PORT_START = 1
    PORT_END = 72
    PORTS_IN_BLOCK = 72
    QSFP_PORT_START = 48
    QSFP_PORT_END = 72

    BASE_VAL_PATH = "/sys/class/i2c-adapter/i2c-{0}/{1}-0050/"
    BASE_OOM_PATH = "/sys/bus/i2c/devices/{0}-0050/"
    BASE_CPLD2_PATH = "/sys/bus/i2c/devices/{0}-0061/"
    BASE_CPLD3_PATH = "/sys/bus/i2c/devices/{0}-0062/"
    I2C_BUS_ORDER = -1

    #The sidebands of QSFP is different. 
    #present is in-order. 
    #But lp_mode and reset are not. 	
    qsfp_sb_map = [1, 3, 5, 2, 4, 6]

    _port_to_is_present = {}
    _port_to_lp_mode = {}

    _port_to_eeprom_mapping = {}
    _port_to_i2c_mapping = {
            1: [1, 2],
            2: [2, 3],
            3: [3, 4],
            4: [4, 5],
            5: [5, 6],
            6: [6, 7],
            7: [7, 8],
            8: [8, 9],
            9: [9, 10],
           10: [10, 11],
           11: [11, 12],
           12: [12, 13],
           13: [13, 14],
           14: [14, 15],
           15: [15, 16],
           16: [16, 17],
           17: [17, 18],
           18: [18, 19],
           19: [19, 20],
           20: [20, 21],
           21: [21, 22],
           22: [22, 23],
           23: [23, 24],
           24: [24, 25],
           25: [25, 26],
           26: [26, 27],
           27: [27, 28],
           28: [28, 29],
           29: [29, 30],
           30: [30, 31],
           31: [31, 32],
           32: [32, 33],
           33: [33, 34],
           34: [34, 35],
           35: [35, 36],
           36: [36, 37],
           37: [37, 38],
           38: [38, 39],
           39: [39, 40],
           40: [40, 41],
           41: [41, 42],
           42: [42, 43],
           43: [43, 44],
           44: [44, 45],
           45: [45, 46],
           46: [46, 47],
           47: [47, 48],
           48: [48, 49],
           49: [49, 50],#QSFP49
           50: [49, 50],
           51: [49, 50],
           52: [49, 50],
           53: [50, 52],#QSFP50
           54: [50, 52],
           55: [50, 52],
           56: [50, 52],
           57: [51, 54],#QSFP51
           58: [51, 54],
           59: [51, 54],
           60: [51, 54],
           61: [52, 51],#QSFP52
           62: [52, 51],
           63: [52, 51],
           64: [52, 51],
           65: [53, 53],#QSFP53
           66: [53, 53],
           67: [53, 53],
           68: [53, 53],
           69: [54, 55],#QSFP54
           70: [54, 55],
           71: [54, 55],
           72: [54, 55],
           }

    @property
    def port_start(self):
        return self.PORT_START

    @property
    def port_end(self):
        return self.PORT_END

    @property
    def qsfp_port_start(self):
        return self.QSFP_PORT_START

    @property
    def qsfp_port_end(self):
        return self.QSFP_PORT_END
    
    @property
    def qsfp_ports(self):
        return range(self.QSFP_PORT_START, self.PORTS_IN_BLOCK + 1)

    @property
    def port_to_eeprom_mapping(self):
        return self._port_to_eeprom_mapping

    def __init__(self):
        eeprom_path = self.BASE_OOM_PATH + "eeprom"

        for x in range(self.port_start, self.port_end+1):
            self.port_to_eeprom_mapping[x] = eeprom_path.format(
                self._port_to_i2c_mapping[x][1]
                )

        SfpUtilBase.__init__(self)

    #Two i2c buses might get flipped order, check them both.
    def update_i2c_order(self):
        if os.path.exists("/tmp/accton_util.p"):
            self.I2C_BUS_ORDER = pickle.load(open("/tmp/accton_util.p", "rb"))
        else:
            if self.I2C_BUS_ORDER < 0:
                eeprom_path = "/sys/bus/i2c/devices/1-0057/eeprom"
                if os.path.exists(eeprom_path):
                    self.I2C_BUS_ORDER = 0
                eeprom_path = "/sys/bus/i2c/devices/0-0057/eeprom"
                if os.path.exists(eeprom_path):
                    self.I2C_BUS_ORDER = 1
        return self.I2C_BUS_ORDER 

    def get_presence(self, port_num):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

        order = self.update_i2c_order()
        if port_num <= 24:
            present_path = self.BASE_CPLD2_PATH.format(order)         
        else:
            present_path = self.BASE_CPLD3_PATH.format(order)
        
        present_path = present_path + "module_present_" + str(self._port_to_i2c_mapping[port_num][0])            
        self.__port_to_is_present = present_path

        try:
            val_file = open(self.__port_to_is_present)
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)          
            return False

        content = val_file.readline().rstrip()
        val_file.close()

        # content is a string, either "0" or "1"
        if content == "1":
            return True

        return False

    def qsfp_sb_remap(self, port_num):
        qsfp_start = self.qsfp_port_start
        qsfp_index = self._port_to_i2c_mapping[port_num][0] - qsfp_start
        qsfp_index = self.qsfp_sb_map[qsfp_index-1]
        return qsfp_start+qsfp_index

    def get_low_power_mode_cpld(self, port_num):
        if port_num < self.qsfp_port_start or port_num > self.qsfp_port_end:
            return False
        
        order = self.update_i2c_order()
        lp_mode_path = self.BASE_CPLD3_PATH.format(order)
        lp_mode_path = lp_mode_path + "module_lp_mode_" 
        q = self.qsfp_sb_remap(port_num)
        lp_mode_path = lp_mode_path + str(q)
        
        try:
            val_file = open(lp_mode_path)
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)          
            return False

        content = val_file.readline().rstrip()
        val_file.close()

        # content is a string, either "0" or "1"
        if content == "1":
            return True

        return False

    def get_low_power_mode(self, port_num):
        if port_num < self.qsfp_port_start or port_num > self.qsfp_port_end:
            return False
        
        if not self.get_presence(port_num):
            return self.get_low_power_mode_cpld(port_num)

        try:
            eeprom = None

            eeprom = open(self.port_to_eeprom_mapping[port_num], "rb")
            eeprom.seek(93)
            lpmode = ord(eeprom.read(1))

            if not (lpmode & 0x1): # 'Power override' bit is 0
                return self.get_low_power_mode_cpld(port_num)
            else:
                if ((lpmode & 0x2) == 0x2):
                    return True # Low Power Mode if "Power set" bit is 1
                else:
                    return False # High Power Mode if "Power set" bit is 0
        except IOError as err:
            print "Error: unable to open file: %s" % str(err)
            return False
        finally:
            if eeprom is not None:
                eeprom.close()
                time.sleep(0.01)

    def set_low_power_mode(self, port_num, lpmode):
        if port_num < self.qsfp_port_start or port_num > self.qsfp_port_end:
            return False

        try:
            eeprom = None

            if not self.get_presence(port_num):
                return False # Port is not present, unable to set the eeprom

            # Fill in write buffer
            regval = 0x3 if lpmode else 0x1 # 0x3:Low Power Mode, 0x1:High Power Mode
            buffer = create_string_buffer(1)
            buffer[0] = chr(regval)

            # Write to eeprom
            eeprom = open(self.port_to_eeprom_mapping[port_num], "r+b")
            eeprom.seek(93)
            eeprom.write(buffer[0])
            return True
        except IOError as err:
            print "Error: unable to open file: %s" % str(err)
            return False
        finally:
            if eeprom is not None:
                eeprom.close()
                time.sleep(0.01)

    def reset(self, port_num):
        if port_num < self.qsfp_port_start or port_num > self.qsfp_port_end:
            return False
         
        order = self.update_i2c_order()
        lp_mode_path = self.BASE_CPLD3_PATH.format(order)
        mod_rst_path = lp_mode_path + "module_reset_" 
        q = self.qsfp_sb_remap(port_num)
        mod_rst_path = mod_rst_path + str(q)
        
        try:
            reg_file = open(mod_rst_path, 'r+')
        except IOError as e:
            print "Error: unable to open file: %s" % str(e)          
            return False

        #toggle reset
        reg_file.seek(0)
        reg_file.write('0')
        time.sleep(1)
        reg_file.seek(0)
        reg_file.write('1')
        reg_file.close()
        return True
        
    def get_transceiver_change_event(self):
        """
        TODO: This function need to be implemented
        when decide to support monitoring SFP(Xcvrd)
        on this platform.
        """
        raise NotImplementedError

