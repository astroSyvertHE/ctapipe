"""This module defines the important coordinate systems to be used in
reconstruction with the CTA pipeline and the transformations between
this different systems. Frames and transformations are defined using
the astropy.coordinates framework. This module defines transformations
for ground based cartesian and planar systems.

For examples on usage see examples/coordinate_transformations.py

This code is based on the coordinate transformations performed in the
read_hess code

TODO:

- Tests Tests Tests!
"""

import astropy.units as u
import numpy as np
from astropy.coordinates import (BaseCoordinateFrame,
                                 CartesianRepresentation,
                                 FunctionTransform)

try:
    # FrameAttribute was renamed Attribute in astropy 2.0
    # TODO: should really use subclasses like QuantityAttribute
    from astropy.coordinates import FrameAttribute as Attribute
except:
    from astropy.coordinates import Attribute


from astropy.coordinates import frame_transform_graph
from numpy import cos, sin
from ..coordinates.representation import PlanarRepresentation

__all__ = [
    'GroundFrame',
    'TiltedGroundFrame',
    'project_to_ground'
]


class GroundFrame(BaseCoordinateFrame):
    """Ground coordinate frame.  The ground coordinate frame is a simple
    cartesian frame describing the 3 dimensional position of objects
    compared to the array ground level in relation to the nomial
    centre of the array.  Typically this frame will be used for
    describing the position on telescopes and equipment

    Frame attributes: None

    """
    default_representation = CartesianRepresentation
    # Pointing direction of the tilted system (alt,az),
    # could be the telescope pointing direction or the reconstructed shower
    # direction
    pointing_direction = Attribute(default=None)


class TiltedGroundFrame(BaseCoordinateFrame):
    """Tilted ground coordinate frame.  The tilted ground coordinate frame
    is a cartesian system describing the 2 dimensional projected
    positions of objects in a tilted plane described by
    pointing_direction Typically this frame will be used for the
    reconstruction of the shower core position

    Frame attributes:
    
    * ``pointing_direction``
        Alt,Az direction of the tilted reference plane

    """
    default_representation = PlanarRepresentation
    # Pointing direction of the tilted system (alt,az),
    # could be the telescope pointing direction or the reconstructed shower
    # direction
    pointing_direction = Attribute(default=None)

# Transformations defined below this point


def get_shower_trans_matrix(azimuth, altitude):
    """Get Transformation matrix for conversion from the ground system to
    the Tilted system and back again (This function is directly lifted
    from read_hess, probably could be streamlined using python
    functionality)

    Parameters
    ----------
    azimuth: float
        Azimuth angle of the tilted system used
    altitude: float
        Altitude angle of the tilted system used

    Returns
    -------
    trans: 3x3 ndarray transformation matrix
    """

    cos_z = sin(altitude)
    sin_z = cos(altitude)
    cos_az = cos(azimuth)
    sin_az = sin(azimuth)

    trans = np.zeros([3, 3])
    trans[0][0] = cos_z * cos_az
    trans[1][0] = sin_az
    trans[2][0] = sin_z * cos_az

    trans[0][1] = -cos_z * sin_az
    trans[1][1] = cos_az
    trans[2][1] = -sin_z * sin_az

    trans[0][2] = -sin_z
    trans[1][2] = 0.
    trans[2][2] = cos_z

    return trans


@frame_transform_graph.transform(FunctionTransform, GroundFrame,
                                 TiltedGroundFrame)
def ground_to_tilted(ground_coord, tilted_coord):
    """
    Transformation from ground system to tilted ground system

    Parameters
    ----------
    ground_coord: `astropy.coordinates.SkyCoord`
        GroundFrame system
    tilted_coord: `astropy.coordinates.SkyCoord`
        TiltedGroundFrame system

    Returns
    -------
    TiltedGroundFrame coordinates
    """
    x_grd = ground_coord.cartesian.x
    y_grd = ground_coord.cartesian.y
    z_grd = ground_coord.cartesian.z

    altitude, azimuth = tilted_coord.pointing_direction.alt, tilted_coord.pointing_direction.az
    altitude = altitude.to(u.rad)
    azimuth = azimuth.to(u.rad)
    trans = get_shower_trans_matrix(azimuth, altitude)

    x_tilt = trans[0][0] * x_grd + trans[0][1] * y_grd + trans[0][2] * z_grd
    y_tilt = trans[1][0] * x_grd + trans[1][1] * y_grd + trans[1][2] * z_grd

    representation = PlanarRepresentation(x_tilt, y_tilt)

    return tilted_coord.realize_frame(representation)


@frame_transform_graph.transform(FunctionTransform, TiltedGroundFrame,
                                 GroundFrame)
def tilted_to_ground(tilted_coord, ground_coord):
    """
    Transformation from tilted ground system to  ground system

    Parameters
    ----------
    tilted_coord: `astropy.coordinates.SkyCoord`
        TiltedGroundFrame system
    ground_coord: `astropy.coordinates.SkyCoord`
        GroundFrame system

    Returns
    -------
    GroundFrame coordinates
    """
    x_tilt = tilted_coord.x
    y_tilt = tilted_coord.y

    altitude, azimuth = tilted_coord.pointing_direction.alt, tilted_coord.pointing_direction.az
    altitude = altitude.to(u.rad)
    azimuth = azimuth.to(u.rad)

    trans = get_shower_trans_matrix(azimuth, altitude)

    x_grd = trans[0][0] * x_tilt + trans[1][0] * y_tilt
    y_grd = trans[0][1] * x_tilt + trans[1][1] * y_tilt
    z_grd = trans[0][2] * x_tilt + trans[1][2] * y_tilt

    representation = CartesianRepresentation(x_grd, y_grd, z_grd)

    grd = ground_coord.realize_frame(representation)
    return grd


def project_to_ground(tilt_system):
    """Project position in the tilted system onto the ground. This is
    needed as the standard transformation will return the 3d position
    of the tilted frame. This projection may ultimately be the
    standard use case so may be implemented in the tilted to ground
    transformation

    Parameters
    ----------
    tilt_system: `astropy.coordinates.SkyCoord`
        coorinate in the the tilted ground system

    Returns
    -------
    Projection of tilted system onto the ground (GroundSystem)

    """
    ground_system = tilt_system.transform_to(GroundFrame)

    unit = ground_system.x.unit
    x_initial = ground_system.x.value
    y_initial = ground_system.y.value
    z_initial = ground_system.z.value

    trans = get_shower_trans_matrix(tilt_system.pointing_direction.az,
                                    tilt_system.pointing_direction.alt)

    x_projected = x_initial - trans[2][0] * z_initial / trans[2][2]
    y_projected = y_initial - trans[2][1] * z_initial / trans[2][2]

    return GroundFrame(x=x_projected * unit, y=y_projected * unit, z=0 * unit)
