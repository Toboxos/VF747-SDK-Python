This python module is an implementation of the serial communication protocol
for the VF747 RFID reader.

# Usage
```python
from VF747.connections import SerialConnection
from VF747.protocol import VF747Protocol

conn = SerialConnection("/dev/ttyUSB0", 115200)
reader = VF747Protocol(conn)

num_tags, tags = reader.list_tag_id()
```

# Install
````python setup.py install````