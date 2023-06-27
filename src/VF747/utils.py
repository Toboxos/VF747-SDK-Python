def byte(value):
    """
    Ensures value is always in the length of 1 byte
    """
    return value % 0x100


def bytes_to_hex_string(data):
    s = ""
    for b in data:
        s += "{:02x}".format(b)

    return s.upper()


def hex_string_to_bytes(s):
    data = bytearray()
    for i in range(0, len(s), 2):
        data += bytearray([int(s[i:i + 2], 16)])

    return data
