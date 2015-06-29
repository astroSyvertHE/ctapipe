# Licensed under a 3-clause BSD style license - see LICENSE.rst
"""Hillas shower parametrization.

TODO:
-----

*Should have a separate function to c


"""
import numpy as np

__all__ = ['hillas_parameters','hillas_parameters_2']


def hillas_parameters(x, y, s):
    """Compute Hillas parameters for a given shower image.

    Reference: Appendix of the Whipple Crab paper Weekes et al. (1998)
    http://adsabs.harvard.edu/abs/1989ApJ...342..379W
    (corrected for some obvious typos)

    Parameters
    ----------
    x : array_like
        Pixel x-coordinate
    y : array_like
        Pixel y-coordinate
    s : array_like
        Pixel value

    Returns
    -------
    hillas_parameters : dict
        Dictionary of Hillas parameters
    """
    x = np.asanyarray(x, dtype=np.float64)
    y = np.asanyarray(y, dtype=np.float64)
    s = np.asanyarray(s, dtype=np.float64)
    assert x.shape == s.shape
    assert y.shape == s.shape

    # Compute image moments
    _s = np.sum(s)
    m_x = np.sum(s * x) / _s
    m_y = np.sum(s * y) / _s
    m_xx = np.sum(s * x * x) / _s  # note: typo in paper
    m_yy = np.sum(s * y * y) / _s
    m_xy = np.sum(s * x * y) / _s  # note: typo in paper

    # Compute major axis line representation y = a * x + b
    S_xx = m_xx - m_x * m_x
    S_yy = m_yy - m_y * m_y
    S_xy = m_xy - m_x * m_y
    d = S_yy - S_xx
    temp = d * d + 4 * S_xy * S_xy
    a = (d + np.sqrt(temp)) / (2 * S_xy)
    b = m_y - a * m_x

    # Compute Hillas parameters
    width_2 = (S_yy + a * a * S_xx - 2 * a * S_xy) / (1 + a * a)
    width = np.sqrt(width_2)
    length_2 = (S_xx + a * a * S_yy + 2 * a * S_xy) / (1 + a * a)
    length = np.sqrt(length_2)
    miss = np.abs(b / (1 + a * a))
    r = np.sqrt(m_x * m_x + m_y * m_y)

    # Compute azwidth by transforming to (p, q) coordinates
    sin_theta = m_y / r
    cos_theta = m_x / r
    q = (m_x - x) * sin_theta + (y - m_y) * cos_theta
    m_q = np.sum(s * q) / _s
    m_qq = np.sum(s * q * q) / _s
    azwidth_2 = m_qq - m_q * m_q
    azwidth = np.sqrt(azwidth_2)

    # Return relevant parameters in a dict
    p = dict()
    p['x'] = m_x
    p['y'] = m_y
    p['a'] = a
    p['b'] = b
    p['width'] = width
    p['length'] = length
    p['miss'] = miss
    p['r'] = r
    p['azwidth'] = azwidth
    return p


def hillas_parameters_2(pix_x, pix_y, image):
    """ Alternate implementation of Hillas parameters """
    pix_x = np.asanyarray(pix_x, dtype=np.float64)
    pix_y = np.asanyarray(pix_y, dtype=np.float64)
    image = np.asanyarray(image, dtype=np.float64)
    assert pix_x.shape == image.shape
    assert pix_y.shape == image.shape

    # Compute image moments (done in a bit faster way, but putting all
    # into one 2D array, where each row will be summed to calculate a
    # moment) However, this doesn't avoid a temporary created for the
    # 2D array 

    size = image.sum()
    momdata = np.row_stack([pix_x,
                            pix_y,
                            pix_x * pix_x,
                            pix_y * pix_y,
                            pix_x * pix_y]) * image
    
    moms = momdata.sum(axis=1) / size

    # calculate variances

    vx2 = moms[2] - moms[0] ** 2
    vy2 = moms[3] - moms[1] ** 2
    vxy = moms[4] - moms[0] * moms[1]

    # common factors:

    dd = vy2 - vx2
    zz = np.sqrt(dd ** 2 + 4.0 * vxy ** 2)

    # miss

    uu = 1.0 + dd / zz
    vv = 2.0 - uu
    miss = np.sqrt((uu * moms[0] ** 2 + vv * moms[1] ** 2) / 2.0
                   - moms[0] * moms[1] * 2.0 * vxy / zz)

    # parameters

    width = np.sqrt(vx2 + vy2 - zz)
    length = np.sqrt(vx2 + vy2 + zz)
    distance = np.hypot(moms[0], moms[1])
    azwidth = np.sqrt(moms[2] + moms[3] - zz)

    # angles

    tanpsi_numer = (dd + zz) * moms[1] + 2.0 * vxy * moms[0]
    tanpsi_denom = (2 * vxy * moms[1]) - (dd - zz) * moms[0]
    psi = np.pi/2.0 + np.arctan2(tanpsi_numer, tanpsi_denom)
    alpha = np.arcsin(miss / distance)
    phi = np.arctan2(moms[1], moms[0])

    return dict(size=size, cx=moms[0], cy=moms[1], length=length, width=width,
                distance = distance, azwidth=azwidth, psi=psi, phi=phi,
                alpha=alpha)
