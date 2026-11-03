"""Tiny software z-buffer renderer (orthographic, Lambert shading) -> PNG.
Used to produce renders/*.png without an OpenGL context.
Usage as module: render(meshes_with_colors, out_png, view=(azim_deg, elev_deg))
"""
import numpy as np
from PIL import Image, ImageDraw


def _rot(azim, elev):
    a, e = np.radians(azim), np.radians(elev)
    # camera looks along -d; d = direction from target to camera
    d = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    up = np.array([0, 0, 1.0])
    r = np.cross(up, d); r /= np.linalg.norm(r)
    u = np.cross(d, r)
    return np.stack([r, u, d])  # rows: screen x, screen y, depth (towards camera)


def render(items, out_png, view=(-60, 30), size=(1200, 900), title=None, margin=40, bg=(250, 250, 248)):
    """items: list of (trimesh.Trimesh, rgb tuple 0-255)."""
    R = _rot(*view)
    allv = np.vstack([m.vertices for m, _ in items])
    P = allv @ R.T
    lo, hi = P[:, :2].min(0), P[:, :2].max(0)
    W, H = size
    s = min((W - 2 * margin) / max(hi[0] - lo[0], 1e-6), (H - 2 * margin - (30 if title else 0)) / max(hi[1] - lo[1], 1e-6))
    off = np.array([(W - s * (hi[0] - lo[0])) / 2, (H - s * (hi[1] - lo[1])) / 2 + (15 if title else 0)])
    zbuf = np.full((H, W), -np.inf)
    img = np.zeros((H, W, 3)); img[:] = np.array(bg) / 255.0
    light = np.array([0.35, -0.25, 0.9]); light /= np.linalg.norm(light)
    light_cam = R @ light
    for m, col in items:
        col = np.array(col) / 255.0
        V = m.vertices @ R.T
        sx = (V[:, 0] - lo[0]) * s + off[0]
        sy = H - ((V[:, 1] - lo[1]) * s + off[1])
        sz = V[:, 2]
        F = m.faces
        N = m.face_normals @ R.T
        shade = 0.30 + 0.70 * np.clip(np.abs(N @ light_cam), 0, 1)
        shade = np.where(N[:, 2] < 0, shade * 0.8, shade)
        for fi in range(len(F)):
            i0, i1, i2 = F[fi]
            x = np.array([sx[i0], sx[i1], sx[i2]]); y = np.array([sy[i0], sy[i1], sy[i2]]); z = np.array([sz[i0], sz[i1], sz[i2]])
            xmin, xmax = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), W - 1))
            ymin, ymax = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), H - 1))
            if xmax < xmin or ymax < ymin:
                continue
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-12:
                continue
            gx, gy = np.meshgrid(np.arange(xmin, xmax + 1) + 0.5, np.arange(ymin, ymax + 1) + 0.5)
            w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not inside.any():
                continue
            zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
            sub = zbuf[ymin:ymax + 1, xmin:xmax + 1]
            upd = inside & (zz > sub)
            if upd.any():
                sub[upd] = zz[upd]
                img[ymin:ymax + 1, xmin:xmax + 1][upd] = col * shade[fi]
    # edge enhancement from depth discontinuities
    zb = zbuf.copy(); fin = np.isfinite(zb); zb[~fin] = zb[fin].min() - 50 if fin.any() else 0
    gx = np.abs(np.diff(zb, axis=1, prepend=zb[:, :1])); gy = np.abs(np.diff(zb, axis=0, prepend=zb[:1, :]))
    edge = (np.maximum(gx, gy) > 1.0)
    img[edge] *= 0.35
    im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
    if title:
        ImageDraw.Draw(im).text((12, 8), title, fill=(20, 20, 20))
    im.save(out_png)
    return out_png


if __name__ == '__main__':
    import sys, trimesh
    out = sys.argv[1]; az = float(sys.argv[2]); el = float(sys.argv[3])
    items = [(trimesh.load(f), (90, 120, 200)) for f in sys.argv[4:]]
    render(items, out, view=(az, el), title=' '.join(a.split('/')[-1] for a in sys.argv[4:]) + f'  az={az} el={el}')
