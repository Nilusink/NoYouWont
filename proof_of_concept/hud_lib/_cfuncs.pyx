# cython: boundscheck=False, wraparound=False, cdivision=True
cimport cython
from libc.math cimport sqrt, atan2, cos, sin, pi, asin



cdef float R = 6371000  # Earth radius in meters
cdef float DTR = pi / 180
cdef float RTD = 180 / pi


cpdef tuple latlon_to_meters(
        double lat1,
        double lon1,
        double lat2,
        double lon2
):
    """Returns approximate x, y in meters from point1 to point2"""
    cdef float dx = (lon2 - lon1) * cos(lat1*DTR) * (2 * pi * R / 360)
    cdef float dy = (lat2 - lat1) * (2 * pi * R / 360)
    return dx, dy


cpdef void latlon_to_meters_batch(
        double[:] lat1, double[:] lon1,
        double[:] lat2, double[:] lon2,
        double[:, :] out  # shape (N, 2), out[i,0]=dx, out[i,1]=dy
):
    """
    Converts arrays of coordinates to dx, dy in meters
    lat1, lon1: reference points
    lat2, lon2: target points
    out: preallocated array of shape (N, 2)
    """
    cdef Py_ssize_t i, n = lat1.shape[0]
    cdef double cos_lat
    for i in range(n):
        cos_lat = cos(lat1[i]*DTR)
        out[i,0] = (lon2[i] - lon1[i]) * cos_lat * (2 * pi * R / 360)  # dx
        out[i,1] = (lat2[i] - lat1[i]) * (2 * pi * R / 360)            # dy


cpdef tuple meters_to_pixels(
        double dx,
        double dy,
        double cx,
        double cy,
        double radius,
        int screen_size
):
    cdef float scale = screen_size / (2 * radius)  # pixels per meter
    cdef float px = screen_size / 2 + (dx + cx) * scale   # center at middle
    cdef float py = screen_size / 2 - (dy + cy) * scale   # invert y to have north up
    return px, py


cpdef void meters_to_pixels_batch(
        double[:, :] meters,  # shape (N, 2), meters[i,0]=dx, meters[i,1]=dy
        double cx, double cy,
        double radius,
        int screen_size,
        double[:, :] out      # shape (N, 2), out[i,0]=px, out[i,1]=py
):
    """
    Converts arrays of dx/dy to pixel coordinates
    """
    cdef Py_ssize_t i, n = meters.shape[0]
    cdef double scale = screen_size / (2 * radius)
    for i in range(n):
        out[i,0] = screen_size/2 + (meters[i,0] + cx) * scale
        out[i,1] = screen_size/2 - (meters[i,1] + cy) * scale  # north up


cpdef tuple offset_center(
        double lat,
        double lon,
        double rotation,
        double radius
):
    """
        Offset a lat/lon by `radius` meters in direction `rotation` (degrees).

        lat, lon: degrees
        rotation: degrees (0 = north, 90 = east)
        radius: meters
        """
    cdef float lat1 = lat * DTR
    cdef float lon1 = lon * DTR

    # Convert your rotation → geographic bearing
    cdef float bearing = (pi / 2) - rotation

    cdef float d = radius / R

    cdef float lat2 = asin(
        sin(lat1) * cos(d) +
        cos(lat1) * sin(d) * cos(bearing)
    )

    cdef float lon2 = lon1 + atan2(
        sin(bearing) * sin(d) * cos(lat1),
        cos(d) - sin(lat1) * sin(lat2)
    )

    return lat2 * RTD, lon2 * RTD


cpdef float get_radius(double speed):
    cdef radius = (speed / 3.6) * 60
    if radius > 50:
        return radius

    return 50


cpdef float get_detail(double radius):
    return 20 * ((500/radius) ** 1.285)