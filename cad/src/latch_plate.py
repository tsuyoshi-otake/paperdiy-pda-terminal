"""The snap's flex zone as a Kirchhoff plate (Morley triangles, scikit-fem): the lid's front wall between the parting
(free edge) and the ceiling, clamped at the ceiling and at the end walls, thinned from inside over the flex zone (45 deg
chamfers back to the full wall). A unit outward force spread over the lip's width, acting at the bump (below the free
edge), gives the stiffness at the bump and the surface strain per newton everywhere.

The ceiling and the end walls are taken as rigid, so the real wall is somewhat softer than this (lower forces, lower
strain)."""
import numpy as np
from skfem import Basis, BilinearForm, ElementTriMorley, FacetBasis, LinearForm, MeshTri, asm, condense, solve
from skfem.helpers import dd, ddot, dot, eye, grad, trace

E_PLA, NU_PLA = 3500.0, 0.35


def wall_plate(z_bot, z_top, x_end, t_wall, zone, lip, below, hx=1.0, hz=0.5):
    """zone = (x0, x1, t, top): thinned to t over x0..x1, up to `top` below z_top; lip = (x0, x1) carrying the load,
    `below` under the free edge. Returns (stiffness N/mm, strain per N, (x, z, thickness) where it peaks)."""
    x0, x1, tf, top = zone
    xs = np.unique(np.concatenate([np.arange(-x_end, x_end + 1e-9, hx), np.arange(x0 - 3.0, x1 + 3.0 + 1e-9, hx / 2)]))
    xs = xs[np.abs(xs) <= x_end]
    zs = np.append(np.arange(z_bot, z_top - hz / 2, hz), z_top)
    m = MeshTri.init_tensor(xs, zs)
    zr = z_top - top

    def thick(x, z):
        d = np.maximum(np.maximum(np.maximum(x0 - x, x - x1), 0.0), np.maximum(z - zr, 0.0))
        return tf + (t_wall - tf) * np.minimum(d / (t_wall - tf), 1.0)      # 45 deg: 1 mm of wall per mm

    def C(T):
        return E_PLA / (1 + NU_PLA) * (T + NU_PLA / (1 - NU_PLA) * eye(trace(T), 2))

    @BilinearForm
    def a(u, v, w):
        return thick(w.x[0], w.x[1]) ** 3 / 12.0 * ddot(C(dd(u)), dd(v))

    e = ElementTriMorley()
    ib = Basis(m, e)
    K = asm(a, ib)
    clamped = m.facets_satisfying(lambda x: (np.abs(x[1] - z_top) < 1e-6) | (np.abs(np.abs(x[0]) - x_end) < 1e-6))
    q = 1.0 / (lip[1] - lip[0])

    @LinearForm
    def load(v, w):        # force at the bump = force + moment at the edge (w + below * dw/dn)
        return q * (v + below * dot(grad(v), w.n))

    edge = m.facets_satisfying(lambda x: (np.abs(x[1] - z_bot) < 1e-6) & (x[0] > lip[0] - 1e-6) & (x[0] < lip[1] + 1e-6))
    f = asm(load, FacetBasis(m, e, facets=edge))
    u = solve(*condense(K, f, D=ib.get_dofs(clamped).all()))
    h = ib.interpolate(u).hess
    X = ib.global_coordinates()
    d = thick(X[0], X[1])
    mean, dev = (h[0][0] + h[1][1]) / 2, np.sqrt(((h[0][0] - h[1][1]) / 2) ** 2 + h[0][1] ** 2)
    eps = d / 2 * np.maximum(np.abs(mean + dev), np.abs(mean - dev))
    i = np.unravel_index(np.argmax(eps), eps.shape)
    return 1.0 / float(f @ u), float(eps[i]), (float(X[0][i]), float(X[1][i]), float(d[i]))


def wall_compliance(z_bot, z_top, x_end, t_wall, zone, cases, hx=1.0, hz=0.5):
    """The same plate under several load cases. cases = [[(x0, x1, below), ...], ...]: in each case a unit outward force
    is shared by its spans in proportion to their widths, acting `below` under the free edge. Returns the matrix C,
    C[i][j] = outward displacement at case i's points (mm) per newton of case j."""
    x0, x1, tf, top = zone
    xs = np.unique(np.concatenate([np.arange(-x_end, x_end + 1e-9, hx), np.arange(x0 - 3.0, x1 + 3.0 + 1e-9, hx / 2)]))
    xs = xs[np.abs(xs) <= x_end]
    zs = np.append(np.arange(z_bot, z_top - hz / 2, hz), z_top)
    m = MeshTri.init_tensor(xs, zs)
    zr = z_top - top

    def thick(x, z):
        d = np.maximum(np.maximum(np.maximum(x0 - x, x - x1), 0.0), np.maximum(z - zr, 0.0))
        return tf + (t_wall - tf) * np.minimum(d / (t_wall - tf), 1.0)

    def C(T):
        return E_PLA / (1 + NU_PLA) * (T + NU_PLA / (1 - NU_PLA) * eye(trace(T), 2))

    @BilinearForm
    def a(u, v, w):
        return thick(w.x[0], w.x[1]) ** 3 / 12.0 * ddot(C(dd(u)), dd(v))

    e = ElementTriMorley()
    ib = Basis(m, e)
    K = asm(a, ib)
    clamped = m.facets_satisfying(lambda x: (np.abs(x[1] - z_top) < 1e-6) | (np.abs(np.abs(x[0]) - x_end) < 1e-6))
    D = ib.get_dofs(clamped).all()
    fs = []
    for spans in cases:
        total = sum(b - a_ for a_, b, _ in spans)
        f = 0.0
        for sx0, sx1, below in spans:
            @LinearForm
            def load(v, w, below=below):
                return (v + below * dot(grad(v), w.n)) / total

            edge = m.facets_satisfying(lambda x, sx0=sx0, sx1=sx1: (np.abs(x[1] - z_bot) < 1e-6) & (x[0] > sx0 - 1e-6)
                                       & (x[0] < sx1 + 1e-6))
            f = f + asm(load, FacetBasis(m, e, facets=edge))
        fs.append(f)
    us = [solve(*condense(K, f, D=D)) for f in fs]
    return np.array([[float(fi @ uj) for uj in us] for fi in fs])
