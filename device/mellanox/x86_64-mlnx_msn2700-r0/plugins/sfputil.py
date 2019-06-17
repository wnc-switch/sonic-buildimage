# sfputil.py
#
# Platform-specific SFP transceiver interface for SONiC
#

try:
    import time
    import subprocess
    from sonic_sfp.sfputilbase import *
except ImportError as e:
    raise ImportError("%s - required module not found" % str(e))

# parameters for DB connection 
REDIS_HOSTNAME = "localhost"
REDIS_PORT = 6379
REDIS_TIMEOUT_USECS = 0

# parameters for SFP presence
SFP_STATUS_INSERTED = '1'

GET_HWSKU_CMD = "sonic-cfggen -d -v DEVICE_METADATA.localhost.hwsku"

# Ethernet<n> <=> sfp<n+SFP_PORT_NAME_OFFSET>
SFP_PORT_NAME_OFFSET = 1
SFP_PORT_NAME_CONVENTION = "sfp{}"

# magic code defnition for port number, qsfp port position of each hwsku
# port_position_tuple = (PORT_START, QSFP_PORT_START, PORT_END, PORT_IN_BLOCK, EEPROM_OFFSET)
hwsku_dict = {'ACS-MSN2700': 0, "LS-SN2700":0, 'ACS-MSN2740': 0, 'ACS-MSN2100': 1, 'ACS-MSN2410': 2, 'ACS-MSN2010': 3, 'ACS-MSN3700': 0, 'ACS-MSN3700C': 0, 'Mellanox-SN2700': 0, 'Mellanox-SN2700-D48C8': 0}
port_position_tuple_list = [(0, 0, 31, 32, 1), (0, 0, 15, 16, 1), (0, 48, 55, 56, 1),(0, 18, 21, 22, 1)]

class SfpUtil(SfpUtilBase):
    """Platform-specific SfpUtil class"""
    PORT_START = 0
    QSFP_PORT_START = 0
    PORT_END = 0
    PORTS_IN_BLOCK = 0
    EEPROM_OFFSET = 0

    db_sel = None
    db_sel_timeout = None
    db_sel_object = None
    db_sel_tbl = None
    state_db = None
    sfpd_status_tbl = None

    @property
    def port_start(self):
        return self.PORT_START

    @property
    def port_end(self):
        return self.PORT_END

    @property
    def qsfp_ports(self):
        return range(self.QSFP_PORT_START, self.PORTS_IN_BLOCK + 1)

    @property
    def port_to_eeprom_mapping(self):
        print "dependency on sysfs has been removed"
        raise Exception() 

    def get_port_position_tuple_by_sku_name(self):
        p = subprocess.Popen(GET_HWSKU_CMD, shell=True, stdout=subprocess.PIPE)
        out, err = p.communicate()
        position_tuple = port_position_tuple_list[hwsku_dict[out.rstrip('\n')]]
        return position_tuple

    def __init__(self):
        port_position_tuple = self.get_port_position_tuple_by_sku_name()
        self.PORT_START = port_position_tuple[0]
        self.QSFP_PORT_START = port_position_tuple[1]
        self.PORT_END = port_position_tuple[2]
        self.PORTS_IN_BLOCK = port_position_tuple[3]
        self.EEPROM_OFFSET = port_position_tuple[4]

        SfpUtilBase.__init__(self)

    def get_presence(self, port_num):
        presence = False

        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return presence

        port_num += SFP_PORT_NAME_OFFSET
        sfpname = SFP_PORT_NAME_CONVENTION.format(port_num)

        ethtool_cmd = "ethtool -m {} 2>/dev/null".format(sfpname)
        try:
            proc = subprocess.Popen(ethtool_cmd, stdout=subprocess.PIPE, shell=True, stderr=subprocess.STDOUT)
            stdout = proc.communicate()[0]
            proc.wait()
            result = stdout.rstrip('\n')
            if result != '':
                presence = True

        except OSError, e:
            return presence

        return presence

    def get_low_power_mode(self, port_num):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

        lpm_cmd = "docker exec syncd python /usr/share/sonic/platform/plugins/sfplpmget.py {}".format(port_num)

        try:
            output = subprocess.check_output(lpm_cmd, shell=True)
            if 'LPM ON' in output:
                return True
        except subprocess.CalledProcessError as e:
            print "Error! Unable to get LPM for {}, rc = {}, err msg: {}".format(port_num, e.returncode, e.output)
            return False

        return False

    def set_low_power_mode(self, port_num, lpmode):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

        curr_lpmode = self.get_low_power_mode(port_num)
        if curr_lpmode == lpmode:
            return True

        # Compose LPM command
        lpm = 'on' if lpmode else 'off'
        lpm_cmd = "docker exec syncd python /usr/share/sonic/platform/plugins/sfplpmset.py {} {}".format(port_num, lpm)

        # Set LPM
        try:
            subprocess.check_output(lpm_cmd, shell=True)
        except subprocess.CalledProcessError as e:
            print "Error! Unable to set LPM for {}, rc = {}, err msg: {}".format(port_num, e.returncode, e.output)
            return False

        return True

    def reset(self, port_num):
        # Check for invalid port_num
        if port_num < self.port_start or port_num > self.port_end:
            return False

        lpm_cmd = "docker exec syncd python /usr/share/sonic/platform/plugins/sfpreset.py {}".format(port_num)

        try:
            subprocess.check_output(lpm_cmd, shell=True)
            return True
        except subprocess.CalledProcessError as e:
            print "Error! Unable to set LPM for {}, rc = {}, err msg: {}".format(port_num, e.returncode, e.output)
            return False

        return False

    def get_transceiver_change_event(self, timeout=0):
        phy_port_dict = {}
        status = True

        if self.db_sel == None:
            from swsscommon import swsscommon
            self.state_db = swsscommon.DBConnector(swsscommon.STATE_DB,
                                             REDIS_HOSTNAME,
                                             REDIS_PORT,
                                             REDIS_TIMEOUT_USECS)

            # Subscribe to state table for SFP change notifications
            self.db_sel = swsscommon.Select()
            self.db_sel_tbl = swsscommon.NotificationConsumer(self.state_db, 'TRANSCEIVER_NOTIFY')
            self.db_sel.addSelectable(self.db_sel_tbl)
            self.db_sel_timeout = swsscommon.Select.TIMEOUT
            self.db_sel_object = swsscommon.Select.OBJECT
            self.sfpd_status_tbl = swsscommon.Table(self.state_db, 'MLNX_SFPD_TASK')

        # Check the liveness of mlnx-sfpd, if it failed, return false
        keys = self.sfpd_status_tbl.getKeys()
        if 'LIVENESS' not in keys:
            return False, phy_port_dict

        if timeout:
            (state, c) = self.db_sel.select(timeout)
        else:
            (state, c) = self.db_sel.select()

        if state == self.db_sel_timeout:
            status = True
        elif state != self.db_sel_object:
            status = False
        else:
            (key, op, fvp) = self.db_sel_tbl.pop()
            phy_port_dict[key] = op

        return status, phy_port_dict

    def _read_eeprom_specific_bytes(self, sysfsfile_eeprom, offset, num_bytes):
        print("_read_eeprom_specific_bytes should not be called since the sysfs it dependents on will no longer exist.")
        print("_read_eeprom_specific_bytes_via_ethtool should be called instead")
        raise Exception()

    # Read out any bytes from any offset
    def _read_eeprom_specific_bytes_via_ethtool(self, port_num, offset, num_bytes):
        port_num += SFP_PORT_NAME_OFFSET
        sfpname = SFP_PORT_NAME_CONVENTION.format(port_num)

        eeprom_raw = []
        ethtool_cmd = "ethtool -m {} hex on offset {} length {}".format(sfpname, offset, num_bytes)
        try:
            output = subprocess.check_output(ethtool_cmd, shell=True)
            output_lines = output.splitlines()
            first_line_raw = output_lines[0]
            if "Offset" in first_line_raw:
                for line in output_lines[2:]:
                    line_split = line.split()
                    eeprom_raw = eeprom_raw + line_split[1:]
        except subprocess.CalledProcessError as e:
            return None

        return eeprom_raw

    # Read eeprom
    def _read_eeprom_devid(self, port_num, devid, offset, num_bytes = 512):
        if port_num in self.osfp_ports:
            pass
        elif port_num in self.qsfp_ports:
            pass
        elif (self.DOM_EEPROM_ADDR == devid):
                offset += 256

        eeprom_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, offset, num_bytes)

        return eeprom_raw

    # Read out SFP type, vendor name, PN, REV, SN from eeprom.
    def get_transceiver_info_dict(self, port_num):
        transceiver_info_dict = {}
        compliance_code_dict = {}

        # ToDo: OSFP tranceiver info parsing not fully supported.
        # in inf8628.py lack of some memory map definition
        # will be implemented when the inf8628 memory map ready
        if port_num in self.osfp_ports:
            offset = 0
            vendor_rev_width = XCVR_HW_REV_WIDTH_OSFP

            sfpi_obj = inf8628InterfaceId()
            if sfpi_obj is None:
                print("Error: sfp_object open failed")
                return None

            sfp_type_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + OSFP_TYPE_OFFSET), XCVR_TYPE_WIDTH)
            if sfp_type_raw is not None:
                sfp_type_data = sfpi_obj.parse_sfp_type(sfp_type_raw, 0)
            else:
                return None

            sfp_vendor_name_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + OSFP_VENDOR_NAME_OFFSET), XCVR_VENDOR_NAME_WIDTH)
            if sfp_vendor_name_raw is not None:
                sfp_vendor_name_data = sfpi_obj.parse_vendor_name(sfp_vendor_name_raw, 0)
            else:
                return None

            sfp_vendor_pn_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + OSFP_VENDOR_PN_OFFSET), XCVR_VENDOR_PN_WIDTH)
            if sfp_vendor_pn_raw is not None:
                sfp_vendor_pn_data = sfpi_obj.parse_vendor_pn(sfp_vendor_pn_raw, 0)
            else:
                return None

            sfp_vendor_rev_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + OSFP_HW_REV_OFFSET), vendor_rev_width)
            if sfp_vendor_rev_raw is not None:
                sfp_vendor_rev_data = sfpi_obj.parse_vendor_rev(sfp_vendor_rev_raw, 0)
            else:
                return None

            sfp_vendor_sn_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + OSFP_VENDOR_SN_OFFSET), XCVR_VENDOR_SN_WIDTH)
            if sfp_vendor_sn_raw is not None:
                sfp_vendor_sn_data = sfpi_obj.parse_vendor_sn(sfp_vendor_sn_raw, 0)
            else:
                return None

            transceiver_info_dict['type'] = sfp_type_data['data']['type']['value']
            transceiver_info_dict['manufacturename'] = sfp_vendor_name_data['data']['Vendor Name']['value']
            transceiver_info_dict['modelname'] = sfp_vendor_pn_data['data']['Vendor PN']['value']
            transceiver_info_dict['hardwarerev'] = sfp_vendor_rev_data['data']['Vendor Rev']['value']
            transceiver_info_dict['serialnum'] = sfp_vendor_sn_data['data']['Vendor SN']['value']
            # Below part is added to avoid fail the xcvrd, shall be implemented later
            transceiver_info_dict['vendor_oui'] = 'N/A'
            transceiver_info_dict['vendor_date'] = 'N/A'
            transceiver_info_dict['Connector'] = 'N/A'
            transceiver_info_dict['encoding'] = 'N/A'
            transceiver_info_dict['ext_identifier'] = 'N/A'
            transceiver_info_dict['ext_rateselect_compliance'] = 'N/A'
            transceiver_info_dict['cable_type'] = 'N/A'
            transceiver_info_dict['cable_length'] = 'N/A'
            transceiver_info_dict['specification_compliance'] = 'N/A'
            transceiver_info_dict['nominal_bit_rate'] = 'N/A'

        else:
            if port_num in self.qsfp_ports:
                offset = 128
                vendor_rev_width = XCVR_HW_REV_WIDTH_QSFP
                cable_length_width = XCVR_CABLE_LENGTH_WIDTH_QSFP
                interface_info_bulk_width = XCVR_INTFACE_BULK_WIDTH_QSFP
                sfp_type = 'QSFP'

                sfpi_obj = sff8436InterfaceId()
                if sfpi_obj is None:
                    print("Error: sfp_object open failed")
                    return None

            else:
                offset = 0
                vendor_rev_width = XCVR_HW_REV_WIDTH_SFP
                cable_length_width = XCVR_CABLE_LENGTH_WIDTH_SFP
                interface_info_bulk_width = XCVR_INTFACE_BULK_WIDTH_SFP
                sfp_type = 'SFP'

                sfpi_obj = sff8472InterfaceId()
                if sfpi_obj is None:
                    print("Error: sfp_object open failed")
                    return None

            sfp_interface_bulk_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + XCVR_INTFACE_BULK_OFFSET), interface_info_bulk_width)
            if sfp_interface_bulk_raw is not None:
                sfp_interface_bulk_data = sfpi_obj.parse_sfp_info_bulk(sfp_interface_bulk_raw, 0)
            else:
                return None

            sfp_vendor_name_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + XCVR_VENDOR_NAME_OFFSET), XCVR_VENDOR_NAME_WIDTH)
            if sfp_vendor_name_raw is not None:
                sfp_vendor_name_data = sfpi_obj.parse_vendor_name(sfp_vendor_name_raw, 0)
            else:
                return None

            sfp_vendor_pn_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + XCVR_VENDOR_PN_OFFSET), XCVR_VENDOR_PN_WIDTH)
            if sfp_vendor_pn_raw is not None:
                sfp_vendor_pn_data = sfpi_obj.parse_vendor_pn(sfp_vendor_pn_raw, 0)
            else:
                return None

            sfp_vendor_rev_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + XCVR_HW_REV_OFFSET), vendor_rev_width)
            if sfp_vendor_rev_raw is not None:
                sfp_vendor_rev_data = sfpi_obj.parse_vendor_rev(sfp_vendor_rev_raw, 0)
            else:
                return None

            sfp_vendor_sn_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + XCVR_VENDOR_SN_OFFSET), XCVR_VENDOR_SN_WIDTH)
            if sfp_vendor_sn_raw is not None:
                sfp_vendor_sn_data = sfpi_obj.parse_vendor_sn(sfp_vendor_sn_raw, 0)
            else:
                return None

            sfp_vendor_oui_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + XCVR_VENDOR_OUI_OFFSET), XCVR_VENDOR_OUI_WIDTH)
            if sfp_vendor_oui_raw is not None:
                sfp_vendor_oui_data = sfpi_obj.parse_vendor_oui(sfp_vendor_oui_raw, 0)
            else:
                return None

            sfp_vendor_date_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + XCVR_VENDOR_DATE_OFFSET), XCVR_VENDOR_DATE_WIDTH)
            if sfp_vendor_date_raw is not None:
                sfp_vendor_date_data = sfpi_obj.parse_vendor_date(sfp_vendor_date_raw, 0)
            else:
                return None

            transceiver_info_dict['type'] = sfp_interface_bulk_data['data']['type']['value']
            transceiver_info_dict['manufacturename'] = sfp_vendor_name_data['data']['Vendor Name']['value']
            transceiver_info_dict['modelname'] = sfp_vendor_pn_data['data']['Vendor PN']['value']
            transceiver_info_dict['hardwarerev'] = sfp_vendor_rev_data['data']['Vendor Rev']['value']
            transceiver_info_dict['serialnum'] = sfp_vendor_sn_data['data']['Vendor SN']['value']
            transceiver_info_dict['vendor_oui'] = sfp_vendor_oui_data['data']['Vendor OUI']['value']
            transceiver_info_dict['vendor_date'] = sfp_vendor_date_data['data']['VendorDataCode(YYYY-MM-DD Lot)']['value']
            transceiver_info_dict['Connector'] = sfp_interface_bulk_data['data']['Connector']['value']
            transceiver_info_dict['encoding'] = sfp_interface_bulk_data['data']['EncodingCodes']['value']
            transceiver_info_dict['ext_identifier'] = sfp_interface_bulk_data['data']['Extended Identifier']['value']
            transceiver_info_dict['ext_rateselect_compliance'] = sfp_interface_bulk_data['data']['RateIdentifier']['value']
            if sfp_type == 'QSFP':
                for key in qsfp_cable_length_tup:
                    if key in sfp_interface_bulk_data['data']:
                        transceiver_info_dict['cable_type'] = key
                        transceiver_info_dict['cable_length'] = str(sfp_interface_bulk_data['data'][key]['value'])

                for key in qsfp_compliance_code_tup:
                    if key in sfp_interface_bulk_data['data']['Specification compliance']['value']:
                        compliance_code_dict[key] = sfp_interface_bulk_data['data']['Specification compliance']['value'][key]['value']
                transceiver_info_dict['specification_compliance'] = str(compliance_code_dict)
                
                transceiver_info_dict['nominal_bit_rate'] = str(sfp_interface_bulk_data['data']['Nominal Bit Rate(100Mbs)']['value'])
            else:
                for key in sfp_cable_length_tup:
                    if key in sfp_interface_bulk_data['data']:
                        transceiver_info_dict['cable_type'] = key
                        transceiver_info_dict['cable_length'] = str(sfp_interface_bulk_data['data'][key]['value'])

                for key in sfp_compliance_code_tup:
                    if key in sfp_interface_bulk_data['data']['Specification compliance']['value']:
                        compliance_code_dict[key] = sfp_interface_bulk_data['data']['Specification compliance']['value'][key]['value']
                transceiver_info_dict['specification_compliance'] = str(compliance_code_dict)

                transceiver_info_dict['nominal_bit_rate'] = str(sfp_interface_bulk_data['data']['NominalSignallingRate(UnitsOf100Mbd)']['value'])

        return transceiver_info_dict

    def get_transceiver_dom_info_dict(self, port_num):
        transceiver_dom_info_dict = {}

        # Below part is added to avoid failing xcvrd
        # Currently, the way in which dom data is read has been changed from
        # using sysfs to using ethtool.
        # The ethtool returns None for ports without dom support, resulting in 
        # None being returned. However, this fails xcvrd to add the 
        # TRANSCEIVER_DOM_SENSOR table entry of associated port to CONFIG_DB
        # and then causes SNMP fail.
        # To address this issue a default dict is initialized with all data set to
        # 'N/A' and is returned is the above case.
        # BTW, in the original implementation which sysfs is used to read dom data,
        # even though non-None data is returned for ports without dom support, 
        # it does not contain valid data. This can result in wrong data in 
        # TRANSCEIVER_DOM_SENSOR table.
        transceiver_dom_info_dict['temperature'] = 'N/A'
        transceiver_dom_info_dict['voltage'] = 'N/A'
        transceiver_dom_info_dict['rx1power'] = 'N/A'
        transceiver_dom_info_dict['rx2power'] = 'N/A'
        transceiver_dom_info_dict['rx3power'] = 'N/A'
        transceiver_dom_info_dict['rx4power'] = 'N/A'
        transceiver_dom_info_dict['tx1bias'] = 'N/A'
        transceiver_dom_info_dict['tx2bias'] = 'N/A'
        transceiver_dom_info_dict['tx3bias'] = 'N/A'
        transceiver_dom_info_dict['tx4bias'] = 'N/A'
        transceiver_dom_info_dict['tx1power'] = 'N/A'
        transceiver_dom_info_dict['tx2power'] = 'N/A'
        transceiver_dom_info_dict['tx3power'] = 'N/A'
        transceiver_dom_info_dict['tx4power'] = 'N/A'

        if port_num in self.osfp_ports:
            pass
        elif port_num in self.qsfp_ports:
            offset = 0
            offset_xcvr = 128

            sfpd_obj = sff8436Dom()
            if sfpd_obj is None:
                return None

            sfpi_obj = sff8436InterfaceId()
            if sfpi_obj is None:
                return None


            # QSFP capability byte parse, through this byte can know whether it support tx_power or not.
            # TODO: in the future when decided to migrate to support SFF-8636 instead of SFF-8436,
            # need to add more code for determining the capability and version compliance
            # in SFF-8636 dom capability definitions evolving with the versions.
            qsfp_dom_capability_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset_xcvr + XCVR_DOM_CAPABILITY_OFFSET), XCVR_DOM_CAPABILITY_WIDTH)
            if qsfp_dom_capability_raw is not None:
                qspf_dom_capability_data = sfpi_obj.parse_qsfp_dom_capability(qsfp_dom_capability_raw, 0)
            else:
                return transceiver_dom_info_dict

            dom_temperature_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + QSFP_TEMPE_OFFSET), QSFP_TEMPE_WIDTH)
            if dom_temperature_raw is not None:
                dom_temperature_data = sfpd_obj.parse_temperature(dom_temperature_raw, 0)
            else:
                return transceiver_dom_info_dict

            dom_voltage_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + QSFP_VLOT_OFFSET), QSFP_VOLT_WIDTH)
            if dom_voltage_raw is not None:
                dom_voltage_data = sfpd_obj.parse_voltage(dom_voltage_raw, 0)
            else:
                return transceiver_dom_info_dict

            qsfp_dom_rev_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + QSFP_DOM_REV_OFFSET), QSFP_DOM_REV_WIDTH)
            if qsfp_dom_rev_raw is not None:
                qsfp_dom_rev_data = sfpd_obj.parse_sfp_dom_rev(qsfp_dom_rev_raw, 0)
            else:
                return transceiver_dom_info_dict

            transceiver_dom_info_dict['temperature'] = dom_temperature_data['data']['Temperature']['value']
            transceiver_dom_info_dict['voltage'] = dom_voltage_data['data']['Vcc']['value']

            # The tx_power monitoring is only available on QSFP which compliant with SFF-8636
            # and claimed that it support tx_power with one indicator bit.
            dom_channel_monitor_data = {}
            qsfp_dom_rev = qsfp_dom_rev_data['data']['dom_rev']['value']
            qsfp_tx_power_support = qspf_dom_capability_data['data']['Tx_power_support']['value']
            if (qsfp_dom_rev[0:8] != 'SFF-8636' or (qsfp_dom_rev[0:8] == 'SFF-8636' and qsfp_tx_power_support != 'on')):
                dom_channel_monitor_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + QSFP_CHANNL_MON_OFFSET), QSFP_CHANNL_MON_WIDTH)
                if dom_channel_monitor_raw is not None:
                    dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params(dom_channel_monitor_raw, 0)
                else:
                    return transceiver_dom_info_dict
            else:
                dom_channel_monitor_raw = self._read_eeprom_specific_bytes_via_ethtool(port_num, (offset + QSFP_CHANNL_MON_OFFSET), QSFP_CHANNL_MON_WITH_TX_POWER_WIDTH)
                if dom_channel_monitor_raw is not None:
                    dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params_with_tx_power(dom_channel_monitor_raw, 0)
                else:
                    return transceiver_dom_info_dict

                transceiver_dom_info_dict['tx1power'] = dom_channel_monitor_data['data']['TX1Power']['value']
                transceiver_dom_info_dict['tx2power'] = dom_channel_monitor_data['data']['TX2Power']['value']
                transceiver_dom_info_dict['tx3power'] = dom_channel_monitor_data['data']['TX3Power']['value']
                transceiver_dom_info_dict['tx4power'] = dom_channel_monitor_data['data']['TX4Power']['value']

            transceiver_dom_info_dict['temperature'] = dom_temperature_data['data']['Temperature']['value']
            transceiver_dom_info_dict['voltage'] = dom_voltage_data['data']['Vcc']['value']
            transceiver_dom_info_dict['rx1power'] = dom_channel_monitor_data['data']['RX1Power']['value']
            transceiver_dom_info_dict['rx2power'] = dom_channel_monitor_data['data']['RX2Power']['value']
            transceiver_dom_info_dict['rx3power'] = dom_channel_monitor_data['data']['RX3Power']['value']
            transceiver_dom_info_dict['rx4power'] = dom_channel_monitor_data['data']['RX4Power']['value']
            transceiver_dom_info_dict['tx1bias'] = dom_channel_monitor_data['data']['TX1Bias']['value']
            transceiver_dom_info_dict['tx2bias'] = dom_channel_monitor_data['data']['TX2Bias']['value']
            transceiver_dom_info_dict['tx3bias'] = dom_channel_monitor_data['data']['TX3Bias']['value']
            transceiver_dom_info_dict['tx4bias'] = dom_channel_monitor_data['data']['TX4Bias']['value']

        else:
            offset = 256

            eeprom_raw = ['0'] * 256
            eeprom_raw[92:92+16] = self._read_eeprom_specific_bytes_via_ethtool(port_num, 92, 16)
            sfp_obj = sff8472InterfaceId()
            calibration_type = sfp_obj._get_calibration_type(eeprom_raw)

            eeprom_domraw = self._read_eeprom_specific_bytes_via_ethtool(port_num, offset, 256)
            if eeprom_domraw is None:
                return transceiver_dom_info_dict

            sfpd_obj = sff8472Dom(None, calibration_type)
            if sfpd_obj is None:
                print "no sff8472Dom"
                return None

            dom_temperature_raw = eeprom_domraw[SFP_TEMPE_OFFSET:SFP_TEMPE_OFFSET+SFP_TEMPE_WIDTH]
            dom_temperature_data = sfpd_obj.parse_temperature(dom_temperature_raw, 0)

            dom_voltage_raw = eeprom_domraw[SFP_VLOT_OFFSET:SFP_VLOT_OFFSET+SFP_VOLT_WIDTH]
            dom_voltage_data = sfpd_obj.parse_voltage(dom_voltage_raw, 0)

            dom_channel_monitor_raw = eeprom_domraw[SFP_CHANNL_MON_OFFSET:SFP_CHANNL_MON_OFFSET+SFP_CHANNL_MON_WIDTH]
            dom_channel_monitor_data = sfpd_obj.parse_channel_monitor_params(dom_channel_monitor_raw, 0)

            transceiver_dom_info_dict['temperature'] = dom_temperature_data['data']['Temperature']['value']
            transceiver_dom_info_dict['voltage'] = dom_voltage_data['data']['Vcc']['value']
            transceiver_dom_info_dict['rx1power'] = dom_channel_monitor_data['data']['RXPower']['value']
            transceiver_dom_info_dict['tx1bias'] = dom_channel_monitor_data['data']['TXBias']['value']
            transceiver_dom_info_dict['tx1power'] = dom_channel_monitor_data['data']['TXPower']['value']

        return transceiver_dom_info_dict
