"""STEP 94, BULLET_000 only. The collapse pose solved ON the drawing.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python bullet_pose.py

Environment:
    BULLET_OUT     folder for the render and the .blend     (default ./out)
    BULLET_REF     the drawing, 2752x1536                     (default collapse.png beside this file)
    BULLET_ANGLES  angles to render, default 0 only. The other 23 wait for Marko.

Every joint has a target in the drawing's own pixels (JOINTS below, measured on a grid over
BB_C_1/1-6-COLLAPSE-v1.png). The camera is fixed first. Each joint is then placed on the ray through
its pixel, at the depth where the bone reaches its anatomical length (or where the foot meets the
ground), so the silhouette lands on the drawn one by construction and the depth stays plausible.
The drawing is loaded as the camera background so the blend opens with the figure on top of it.

Coordinates: figure faces roughly +Y, camera at its front right, up +Z, metres.
"""
import bpy, os, math
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(os.environ.get('BULLET_OUT', 'out'))
REF = os.environ.get('BULLET_REF', os.path.join(HERE, 'collapse.png'))
ANGLES = [int(a) for a in os.environ.get('BULLET_ANGLES', '0').split(',') if a.strip()]
os.makedirs(OUT, exist_ok=True)
W, H = 2752, 1536

# -------------------------------------------------- targets in the drawing, pixels, y down
# name: (px, py, radius_m, solve, hint)   solve: 'root' | ('len', parent, metres) | ('ground', z)
# hint: +1 take the root nearer the camera, -1 the further one
JOINTS = {
    'pelvis':     (1370,  890, 0.150, 'root', 0),
    'waist':      (1290,  760, 0.135, ('len', 'pelvis', 0.16), -1),
    'chest':      (1175,  500, 0.140, ('len', 'waist', 0.32), -1),
    'neck':       (1140,  375, 0.060, ('len', 'chest', 0.13), -1),
    'head':       (1085,  262, 0.110, ('len', 'neck', 0.17), -1),
    'crown':      (1020,  185, 0.100, ('len', 'head', 0.09), -1),
    'r_shoulder': (1045,  475, 0.062, ('len', 'chest', 0.20), +1),
    'l_shoulder': (1320,  430, 0.075, ('len', 'chest', 0.20), -1),
    'r_elbow':    (1010,  775, 0.042, ('len', 'r_shoulder', 0.32), +1),
    'r_wrist':    (1085, 1085, 0.032, ('len', 'r_elbow', 0.30), +1),
    'r_hand':     (1160, 1190, 0.035, ('len', 'r_wrist', 0.15), +1),
    'l_elbow':    (1360,  720, 0.045, ('len', 'l_shoulder', 0.32), -1),
    'l_wrist':    (1400,  940, 0.035, ('len', 'l_elbow', 0.29), -1),
    'l_hand':     (1410, 1040, 0.040, ('len', 'l_wrist', 0.15), -1),
    'r_hip':      (1300,  935, 0.110, ('len', 'pelvis', 0.11), +1),
    'l_hip':      (1480,  905, 0.110, ('len', 'pelvis', 0.11), -1),
    'r_knee':     (1435, 1105, 0.082, ('len', 'r_hip', 0.44), +1),
    'r_ankle':    (1560, 1265, 0.048, ('len', 'r_knee', 0.43), +1),
    'r_toe':      (1680, 1305, 0.050, ('len', 'r_ankle', 0.25), +1),
    'l_knee':     (1650, 1080, 0.078, ('len', 'l_hip', 0.44), -1),
    'l_ankle':    (1835, 1285, 0.048, ('len', 'l_knee', 0.43), -1),
    'l_toe':      (1935, 1335, 0.050, ('len', 'l_ankle', 0.25), -1),
}
BONES = [('pelvis','waist'),('waist','chest'),('chest','neck'),('neck','head'),('head','crown'),
         ('chest','r_shoulder'),('r_shoulder','r_elbow'),('r_elbow','r_wrist'),('r_wrist','r_hand'),
         ('chest','l_shoulder'),('l_shoulder','l_elbow'),('l_elbow','l_wrist'),('l_wrist','l_hand'),
         ('pelvis','r_hip'),('r_hip','r_knee'),('r_knee','r_ankle'),('r_ankle','r_toe'),
         ('pelvis','l_hip'),('l_hip','l_knee'),('l_knee','l_ankle'),('l_ankle','l_toe')]

# -------------------------------------------------- scene and camera, fixed first
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H

DIST, HEIGHT, LENS, PHI = 8.0, 0.95, 85.0, 45.0
ROOT = 6.7                      # depth of the pelvis on its ray: sets the figure's scale against the drawing
AIM = Vector((0.0, 0.0, 0.85))
cam_data = bpy.data.cameras.new('ORBIT_CAMERA')
cam_data.lens, cam_data.sensor_fit, cam_data.sensor_width = LENS, 'HORIZONTAL', 36.0
cam = bpy.data.objects.new('ORBIT_CAMERA', cam_data)
sc.collection.objects.link(cam)
cam.location = Vector((DIST * math.cos(math.radians(PHI)), DIST * math.sin(math.radians(PHI)), HEIGHT))
cam.rotation_euler = (AIM - cam.location).to_track_quat('-Z', 'Y').to_euler()
sc.camera = cam
bpy.context.view_layer.update()

def ray(px, py):
    """Camera origin and unit direction through a drawing pixel."""
    fx = LENS / 36.0 * W                         # focal length in pixels, horizontal sensor fit
    d_cam = Vector(((px - W / 2) / fx, -(py - H / 2) / fx, -1.0))
    d = (cam.matrix_world.to_3x3() @ d_cam).normalized()
    return cam.matrix_world.translation.copy(), d

P = {}
report = []
for name, (px, py, r, solve, hint) in JOINTS.items():
    o, d = ray(px, py)
    if solve == 'root':
        P[name] = o + d * ROOT
    elif solve[0] == 'ground':
        t = (solve[1] - o.z) / d.z
        P[name] = o + d * t
    else:
        parent, L = P[solve[1]], solve[2]
        oc = o - parent
        b = 2 * d.dot(oc); c = oc.dot(oc) - L * L
        disc = b * b - 4 * c
        if disc < 0:
            t = -b / 2                            # closest approach, bone comes out short
            P[name] = o + d * t
            report.append('SHORT %s: drawn longer than %.2f m by %.3f' % (name, L, ((o + d * t) - parent).length - L))
        else:
            roots = sorted([(-b - math.sqrt(disc)) / 2, (-b + math.sqrt(disc)) / 2])
            t = roots[0] if hint >= 0 else roots[1]
            P[name] = o + d * t
for a, b in BONES:
    report.append('%-22s %.2f m' % (a + '>' + b, (P[b] - P[a]).length))
print('JOINTS ' + ' | '.join('%s=(%.2f,%.2f,%.2f)' % (n, *P[n]) for n in ('pelvis', 'chest', 'head', 'r_hand', 'r_ankle', 'l_ankle')))
print('BONES ' + ' | '.join(report))

# -------------------------------------------------- the figure
names = list(JOINTS); idx = {n: i for i, n in enumerate(names)}
mesh = bpy.data.meshes.new('RUNNER')
mesh.from_pydata([P[n] for n in names], [(idx[a], idx[b]) for a, b in BONES], [])
mesh.update()
fig = bpy.data.objects.new('RUNNER', mesh); sc.collection.objects.link(fig)
bpy.context.view_layer.objects.active = fig; fig.select_set(True)
skin = fig.modifiers.new('Skin', 'SKIN'); skin.use_smooth_shade = True
for n in names:
    v = mesh.skin_vertices[0].data[idx[n]]; r = JOINTS[n][2]
    v.radius = (r, r); v.use_root = (n == 'pelvis')
sub = fig.modifiers.new('Subdivision', 'SUBSURF'); sub.levels = sub.render_levels = 3

# -------------------------------------------------- orbit rig around the sternum, frame 1 = this camera
pivot = bpy.data.objects.new('ORBIT_PIVOT', None); pivot.empty_display_type = 'PLAIN_AXES'
pivot.location = P['chest'].copy(); sc.collection.objects.link(pivot)
bpy.context.view_layer.update()
world_mat = cam.matrix_world.copy()
cam.parent = pivot
cam.matrix_parent_inverse.identity()
cam.matrix_world = world_mat
sc.frame_start, sc.frame_end = 1, 24
for k in range(24):
    pivot.rotation_euler = (0, 0, math.radians(-15 * k))
    pivot.keyframe_insert('rotation_euler', frame=k + 1)
if pivot.animation_data and pivot.animation_data.action and hasattr(pivot.animation_data.action, 'fcurves'):
    for fc in pivot.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'

# the drawing behind the camera view, so the blend opens posed on top of it
if os.path.exists(REF):
    img = bpy.data.images.load(REF)
    cam_data.show_background_images = True
    bg = cam_data.background_images.new(); bg.image = img; bg.alpha = 0.6; bg.display_depth = 'BACK'

# -------------------------------------------------- flat grey render
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light, sh.color_type, sh.single_color = 'STUDIO', 'SINGLE', (0.50, 0.50, 0.50)
sh.show_shadows = sh.show_cavity = sh.show_specular_highlight = False
sh.show_object_outline = True
sc.display.render_aa = '16'
world = bpy.data.worlds.new('PAPER'); world.color = (0.92, 0.92, 0.92); sc.world = world
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format, sc.render.image_settings.color_mode = 'PNG', 'RGB'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'BULLET_ORBIT.blend'))
for a in ANGLES:
    sc.frame_set(a // 15 + 1)
    sc.render.filepath = os.path.join(OUT, 'BULLET_%03d.png' % a)
    bpy.ops.render.render(write_still=True)
print('BULLET_DONE', len(ANGLES))
