import serial


class SerialConnection:
    """
    A serial connection over RS232
    """

    def __init__(self, port, baud_rate):
        self.serial_connection = serial.Serial(port, baud_rate)

    def write(self, data):
        self.serial_connection.write(data)

    def read(self, size):
        return self.serial_connection.read(size)


class MockupConnection:
    """
    A mockup connection not sending any data
    """

    def write(self, data):
        pass

    def read(self, size):
        pass
