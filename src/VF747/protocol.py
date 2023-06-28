from .utils import *
from .exceptions import *

import logging
logger = logging.getLogger(__name__)


class Packet:
    def __init__(self, boot_code, command, data):
        """
        Creates a new packet
        :param boot_code: Boot code of the packet
        :param command: Command code
        :param data: packet data
        """

        self.boot_code = boot_code
        self.command = command
        self.packet_data = data

    def effective_length(self):
        """
        Returns the effective length of the packet content after the bootcode
        :return:
        """
        return 2 + len(self.packet_data)

    def checksum(self):
        """
        Computes the checksum of the packet data
        :return:
        """
        data = bytearray(
            [self.boot_code] + [self.effective_length()] + [self.command]
        ) + self.packet_data

        checksum = 0
        for i in range(len(data)):
            checksum = byte(checksum + data[i])

        checksum = byte((checksum ^ 0xFF) + 1)
        return checksum

    def __bytes__(self):
        return bytearray(
            [self.boot_code] + [self.effective_length()] + [self.command]
        ) + self.packet_data + bytearray([self.checksum()])

    def __str__(self):
        s = ""
        for c in self.__bytes__():
            s += f"{c:02x} "

        return s.strip()


class VF747Protocol:
    """
    Implementation of the protocol to communicate to the
    VF747 reader via serial connection.

    For tag operations currently only ISO18000-6C tags are
    supported.
    """

    # Memory banks
    MEM_PASSWORD = 0
    MEM_EPC = 1
    MEM_TID = 2
    MEM_USER = 3

    def __init__(self, connection):
        """
        Creates a new instance of the protocol for communicating
        over the given connection
        :param connection: Connection to communicate
        """
        self.connection = connection

    def send_command(self, command, param):
        """
        Sends a command packet over the connection
        :param command: Command code (1 byte)
        :param param: Command param (bytearray)
        :return:
        """

        packet = Packet(0x40, command, param)
        logger.debug(f"Write packet: {packet}")
        self.connection.write(bytes(packet))

    def read_return_packet(self):
        boot_code = self.connection.read(1)
        if boot_code != 0xF0 and boot_code != 0xF4:
            raise WrongBootCodeException()

        effective_length = self.connection.read(1)
        command = self.connection.read(1)
        data = self.connection.read(effective_length - 2)
        checksum = self.connection.read(1)
        packet = Packet(boot_code, command, data)
        logger.debug(f"Read packet: {packet}")

        if packet.checksum() != checksum:
            logger.warning("Received wrong checksum! Data may be inconsistent!")

        return packet

    def error_to_str(self, error_code):
        """
        Returns a readable representation for given error code
        """

        if error_code == 0x00:
            return "Command success or detect correct"
        elif error_code == 0x01:
            return "Anteanna connection fail"
        elif error_code == 0x02:
            return "Detect no tag"
        elif error_code == 0x03:
            return "illegal tag"
        elif error_code == 0x04:
            return "read/write power is inadequat"
        elif error_code == 0x05:
            return "write protection in this area"
        elif error_code == 0x06:
            return "checksum error"
        elif error_code == 0x07:
            return "paramter wrong"
        elif error_code == 0x08:
            return "nonexistent data rea"
        elif error_code == 0x09:
            return "wrong password"
        elif error_code == 0x0A:
            return "kill password cant be 0"
        elif error_code == 0x0B:
            return "when reader is in automode the command is illegal"
        elif error_code == 0x0C:
            return "Illegal user with unmatched password"
        elif error_code == 0x0D:
            return "RF interference from external"
        elif error_code == 0x0E:
            return "Read protection on tag"
        elif error_code == 0x1E:
            return "Invalid command, such as wrong parameter command"
        elif error_code == 0x1F:
            return "Unknown command"
        elif error_code == 0x20:
            return "Other error"
        else:
            return "Unknown error"

    def set_baud_rate(self, baudrate):
        """
        Sets the baudrate for communication on the reader
        :param baudrate: Legal baudrate
        :return:
        """
        param = 0x0
        if baudrate == 600:
            param = 0x0
        elif baudrate == 1200:
            param = 0x01
        elif baudrate == 2400:
            param = 0x02
        elif baudrate == 4800:
            param = 0x03
        elif baudrate == 9600:
            param = 0x04
        elif baudrate == 19200:
            param = 0x05
        elif baudrate == 38400:
            param = 0x06
        elif baudrate == 57600:
            param = 0x07
        elif baudrate == 115200:
            param = 0x08
        else:
            raise RuntimeError("Invalid baudrate")

        self.send_command(0x01, [param])
        packet = self.read_return_packet()

        if packet.command != 0x01:
            raise RuntimeError("Received wrong answer")

    def get_reader_version(self):
        """
        Gets the major and minor version of hardware and software
        :return: (major_hw, minor_hw), (major_sw, minor_sw)
        """
        self.send_command(0x02, [])
        packet = self.read_return_packet()

        if packet.command != 0x02:
            logger.warning("get_reader_version(): received invalid return command")

        if len(packet.packet_data) < 0x04:
            logger.error("get_reader_version(): packet data invalid")
            return

        major_version_hw = packet.packet_data[0]
        minor_version_hw = packet.packet_data[1]
        major_version_sw = packet.packet_data[2]
        minor_version_sw = packet.packet_data[3]
        return (major_version_hw, minor_version_hw), (major_version_sw, minor_version_sw)

    def set_relay(self, relay1: bool, relay2: bool):
        """
        Set the relay status for the reader
        :param relay1: status for relay 1
        :param relay2: status for relay 2
        :return:
        """

        param = int(relay1) + (int(relay2) << 2)

        self.send_command(0x03, [param])
        packet = self.read_return_packet()

        if packet.command != 0x03:
            raise RuntimeError("Set Relay command failed")

    def get_relay(self):
        """
        Gets the status of the relays
        :return: (relay1, relay2)
        """
        self.send_command(0x0B, [])
        packet = self.read_return_packet()

        if packet.command != 0x08:
            raise RuntimeError("Received wrong packet for answer")

        if len(packet.packet_data) < 1:
            raise RuntimeError("Return packet is invalid")

        relay1 = bool(packet.packet_data[0] & 0x01)
        relay2 = bool(packet.packet_data[0] & 0x02)

        return relay1, relay2

    def set_output_power(self, power):
        raise NotImplementedError()

    def set_frequency(self, frequency):
        raise NotImplementedError()

    def read_param(self):
        """
        Gets the current settings parameter from the reader
        :return:
        """
        self.send_command(0x06, [])
        packet = self.read_return_packet()

        if packet.command != 0x06:
            raise RuntimeError("Received invalid packet")

        if len(packet.packet_data) != 32:
            raise RuntimeError("Return packet has invalid data")

        return packet.packet_data

    def set_param(self, param):
        """
        Seths the new settings paramters for the reader
        :param param: settings (32 bytes array)
        :return:
        """
        self.send_command(0x09, param)
        packet = self.read_return_packet()

        if packet.command != 0x09:
            raise RuntimeError("Received invalid packet")

    def read_auto_param(self):
        raise NotImplementedError()

    def set_auto_param(self):
        raise NotImplementedError()

    def select_antenna(self, antenna):
        """
        Defines which antenna should be used to transmit/receive signal
        :param antenna: number of antenna (0-3)
        :return:
        """
        self.send_command(0x0A, [0x01 << antenna])
        packet = self.read_return_packet()

        if packet.command != 0x0A:
            raise RuntimeError("Received invalid packet")

    def restore_factory_settings(self):
        """
        Set back reader settings to factory settings
        :return:
        """
        self.send_command(0x0E, [])
        packet = self.read_return_packet()

        if packet.command != 0x0E:
            raise RuntimeError("Received invalid packet")

    def reboot(self):
        raise NotImplementedError()

    def set_auto_mode(self, status: bool):
        """
        Enables / Disabled auto mode
        :param status: true or false
        :return:
        """

        self.send_command(0x0F, [int(status)])
        packet = self.read_return_packet()

        if packet.command != 0x0F:
            raise RuntimeError("Received invalid packet")

    def clear_memory(self):
        """
        Remove the cache of tag data in the reader
        :return:
        """
        self.send_command(0x10, [])
        packet = self.read_return_packet()

        if packet.command != 0x10:
            raise RuntimeError("Received invalid packet")

    def set_reader_time(self, new_time):
        raise NotImplementedError()

    def get_reader_time(self):
        raise NotImplementedError()

    def set_report_filter(self):
        raise NotImplementedError()

    def get_report_filter(self):
        raise NotImplementedError()

    def set_reader_network_address(self):
        raise NotImplementedError()

    def get_reader_network_address(self):
        raise NotImplementedError()

    def set_reader_mac(self):
        raise NotImplementedError()

    def get_reader_mac(self):
        raise NotImplementedError()

    def report_now(self):
        raise NotImplementedError()

    def get_tag_info(self):
        raise NotImplementedError()

    def get_reader_id(self):
        raise NotImplementedError()

    def list_tag_id(self, memory_bank, mask_start, mask_size, mask):
        """
        This functions reads all tag IDs available in the radiation field of the antenna.

        It returns the total number of tags and a part of the tag IDs.
        If there are too many tags around not all tag IDs will be return by this function.
        The remaining tag IDs must be read from the memory.

        :param memory_bank:     The memory bank where the TAG_ID should be read from
        :param mask_start:      Offset in the memory bank in bits where the mask should be applied
        :param mask_size:       The size of the mask in bits for filtering
        :param mask:            The mask for filtering
        :return:                Tuple with total number of tags and partial list of tag ids
        """

        data = bytearray([memory_bank])  # Param 1: memory bank
        data += int.to_bytes(mask_start, length=2, byteorder="big")  # Param 2: start address of mask?
        data += bytearray([mask_size])  # Param 3: size of mask in bits
        data += mask  # Param 4: mask data bytes

        self.send_command(0xEE, data)
        packet = self.read_return_packet()

        if packet.command != 0xEE:
            raise RuntimeError("Received invalid return")

        num_tags_total = packet.packet_data[0]
        tags = []

        ptr = 1
        data = packet.packet_data
        while ptr < len(data):
            num_words = data[ptr]  # number of words for the next tag id
            start = ptr + 1  # next bytes is start
            end = ptr + 1 + 2 * num_words

            # Boundary check
            if end > len(data):
                break

            tag_id = bytes_to_hex_string(data[start:end])
            tags.append(tag_id)

            ptr = end  # move pointer to next id

        return num_tags_total, tags
