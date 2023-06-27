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

