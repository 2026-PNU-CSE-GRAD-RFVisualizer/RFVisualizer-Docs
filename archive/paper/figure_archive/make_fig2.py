"""Fig. 2 (a) PGSR mesh and (b) proxy shell from the same camera. Run with the `sionna` conda env.

Inputs (made once with the `pgsr` env, plyfile/trimesh):
  pgsr_f32.ply  = proxy_mesh/complex_envelope/pgsr_mesh_metric.ply with uchar red/green/blue
                  rewritten as float r/g/b in [0, 1] (mitsuba reads these as vertex_color)
  proxy.ply     = proxy_mesh/complex_envelope/room_envelope_metric.obj exported to PLY
Outputs fig2a_tex.png / fig2b_proxy.png; fig2-a_v3.png is fig2a_tex.png with callouts added by hand.
Unused variant: fig2a_tex_band.png (pgsr_tex_band.ply, 0-3 m out-of-band tint).
"""
import numpy as np, mitsuba as mi, matplotlib.pyplot as plt
mi.set_variant('cuda_ad_rgb')
T = np.array([22.5, 10.5, 0.8])
elev, azim, dist = np.radians(42), np.radians(-58), 66.0
eye = T + dist*np.array([np.cos(elev)*np.cos(azim), np.cos(elev)*np.sin(azim), np.sin(elev)])
def render(mesh, refl, face_normals=False):
    s = mi.load_dict({'type': 'scene', 'integrator': {'type': 'path', 'max_depth': 3},
        'sensor': {'type': 'perspective', 'fov': 42,
                   'to_world': mi.ScalarTransform4f().look_at(origin=eye.tolist(), target=T.tolist(), up=[0, 0, 1]),
                   'film': {'type': 'hdrfilm', 'width': 1600, 'height': 1000, 'rfilter': {'type': 'gaussian'}},
                   'sampler': {'type': 'independent', 'sample_count': 128}},
        'env': {'type': 'constant', 'radiance': {'type': 'rgb', 'value': 0.8}},
        'sun': {'type': 'directional', 'direction': [0.4, 0.6, -1.0], 'irradiance': {'type': 'rgb', 'value': 1.0}},
        'mesh': {'type': 'ply', 'filename': mesh, 'face_normals': face_normals,
                 'bsdf': {'type': 'twosided', 'bsdf': {'type': 'diffuse', 'reflectance': refl}}}})
    return np.clip(np.array(mi.util.convert_to_bitmap(mi.render(s))), 0, 255)
vc = {'type': 'mesh_attribute', 'name': 'vertex_color'}
imgs = {'fig2a_tex.png': render('pgsr_f32.ply', vc),
        'fig2a_tex_band.png': render('pgsr_tex_band.ply', vc),
        'fig2b_proxy.png': render('proxy.ply', {'type': 'rgb', 'value': [0.62, 0.66, 0.72]}, face_normals=True)}
mask = np.zeros(next(iter(imgs.values())).shape[:2], bool)
for im in imgs.values():
    mask |= np.abs(im.astype(int) - im[0, 0].astype(int)).sum(2) > 12
ys, xs = np.where(mask); pad = 12
y0, y1, x0, x1 = max(ys.min()-pad, 0), ys.max()+pad, max(xs.min()-pad, 0), xs.max()+pad
for name, im in imgs.items():
    plt.imsave(name, im[y0:y1, x0:x1].astype(np.uint8)); print('wrote', name)
