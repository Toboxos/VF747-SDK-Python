from distutils.core import setup

setup(
    name="VF747-SDK-Python",
    version="0.1",
    description="Implementation of the serial protocol for the VF747 RFID reader",
    author="Tobias Bungard",
    author_email="tobi-bungard@t-online.de",
    url="https://github.com/Toboxos/VF747-SDK-Python",
    packages=["VF747"],
    install_requires=["pyserial==3.5"],
    python_requires='>=3.6',
)
