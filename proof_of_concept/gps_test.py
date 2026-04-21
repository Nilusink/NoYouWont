import gpsd

gpsd.connect()
print(gpsd.device())

while True:
    packet = gpsd.get_current()
    print(packet.lat, packet.lon, packet.mode)

    if packet.mode:
        print(packet.speed(), packet.speed_vertical())
