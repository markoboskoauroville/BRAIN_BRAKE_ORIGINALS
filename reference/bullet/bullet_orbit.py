"""STEP 94, BULLET TIME. A grey mannequin in the collapse pose, orbited 360 degrees in 15 degree steps.

    /Applications/Blender.app/Contents/MacOS/Blender --background --python bullet_orbit.py

Environment:
    BULLET_OUT     folder for the renders and the .blend      (default ./out)
    BULLET_SCALE   resolution percentage, 100 for the real thing (default 100)
    BULLET_ANGLES  comma list of angles to render, blank for all 24

The figure is a skin modifier mannequin: joints as vertices, limbs as edges, a radius per joint. It
never animates. Only the camera moves: it is a child of ORBIT_PIVOT at the sternum, and the pivot's
Z rotation is keyframed so frame N is angle (N-1)*15. To rerun at another step or height, change
the pivot keyframes or the camera's local position and render the range again.

Direction: 0 is the front right three quarter view of the reference. Each step moves the camera
toward HIS RIGHT flank, matching the three frames already generated (at 45 the number is edge on).
Coordinates: the figure faces +Y, his right is +X, up is +Z, metres.
"""
import bpy, os, math

OUT = os.path.abspath(os.environ.get('BULLET_OUT', 'out'))
SCALE = int(os.environ.get('BULLET_SCALE', '100'))
ANGLES = [int(a) for a in os.environ.get('BULLET_ANGLES', '').split(',') if a.strip()] or list(range(0, 360, 15))
os.makedirs(OUT, exist_ok=True)

# fresh scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

# ---------------------------------------------------------------- the pose
# name: (x, y, z), radius.  Falling backwards: torso tilted back toward -Y, legs sliding out to +Y.
J = {
    'pelvis':    ((0.00,  0.00, 0.72), 0.150),
    'spine':     ((0.00, -0.16, 0.98), 0.140),
    'chest':     ((0.00, -0.31, 1.20), 0.120),
    'neck':      ((0.00, -0.37, 1.28), 0.055),
    'head':      ((0.00, -0.44, 1.38), 0.120),
    'r_shoulder':((0.22, -0.30, 1.16), 0.075),
    'r_elbow':   ((0.26, -0.20, 0.88), 0.045),
    'r_wrist':   ((0.28, -0.10, 0.62), 0.035),
    'r_hand':    ((0.28, -0.06, 0.52), 0.045),
    'l_shoulder':((-0.22,-0.30, 1.16), 0.075),
    'l_elbow':   ((-0.27,-0.36, 0.90), 0.045),
    'l_wrist':   ((-0.28,-0.40, 0.64), 0.035),
    'l_hand':    ((-0.28,-0.42, 0.55), 0.045),
    'r_hip':     ((0.11,  0.00, 0.70), 0.100),
    'r_knee':    ((0.16,  0.32, 0.40), 0.065),
    'r_ankle':   ((0.19,  0.50, 0.08), 0.045),
    'r_toe':     ((0.20,  0.68, 0.04), 0.050),
    'l_hip':     ((-0.11, 0.00, 0.70), 0.100),
    'l_knee':    ((-0.15, 0.42, 0.38), 0.065),
    'l_ankle':   ((-0.17, 0.84, 0.07), 0.045),
    'l_toe':     ((-0.17, 1.02, 0.04), 0.050),
}
BONES = [
    ('pelvis','spine'), ('spine','chest'), ('chest','neck'), ('neck','head'),
    ('chest','r_shoulder'), ('r_shoulder','r_elbow'), ('r_elbow','r_wrist'), ('r_wrist','r_hand'),
    ('chest','l_shoulder'), ('l_shoulder','l_elbow'), ('l_elbow','l_wrist'), ('l_wrist','l_hand'),
    ('pelvis','r_hip'), ('r_hip','r_knee'), ('r_knee','r_ankle'), ('r_ankle','r_toe'),
    ('pelvis','l_hip'), ('l_hip','l_knee'), ('l_knee','l_ankle'), ('l_ankle','l_toe'),
]
names = list(J)
idx = {n: i for i, n in enumerate(names)}
mesh = bpy.data.meshes.new('RUNNER')
mesh.from_pydata([J[n][0] for n in names], [(idx[a], idx[b]) for a, b in BONES], [])
mesh.update()
fig = bpy.data.objects.new('RUNNER', mesh)
sc.collection.objects.link(fig)
bpy.context.view_layer.objects.active = fig
fig.select_set(True)

skin = fig.modifiers.new('Skin', 'SKIN')
skin.use_smooth_shade = True
for n in names:
    v = mesh.skin_vertices[0].data[idx[n]]
    r = J[n][1]
    v.radius = (r, r)
    v.use_root = (n == 'pelvis')
sub = fig.modifiers.new('Subdivision', 'SUBSURF')
sub.levels = 3
sub.render_levels = 3

# ---------------------------------------------------------------- camera rig
STERNUM = (0.0, -0.22, 1.08)
DIST, HEIGHT, LENS = 8.0, 0.95, 85   # long lens from far back: little perspective, the legs do not loom
SHIFT_Y = -0.09                  # frame lowered so the whole figure sits in it; the pivot stays fixed in frame
PHI0 = 55.0                      # degrees from +X toward +Y: front right three quarter

pivot = bpy.data.objects.new('ORBIT_PIVOT', None)
pivot.empty_display_type = 'PLAIN_AXES'
pivot.location = STERNUM
sc.collection.objects.link(pivot)

cam_data = bpy.data.cameras.new('ORBIT_CAMERA')
cam_data.lens = LENS
cam_data.sensor_fit = 'HORIZONTAL'
cam_data.sensor_width = 36
cam_data.shift_y = SHIFT_Y
cam = bpy.data.objects.new('ORBIT_CAMERA', cam_data)
sc.collection.objects.link(cam)
cam.parent = pivot
cam.location = (DIST, 0.0, HEIGHT - STERNUM[2])
track = cam.constraints.new('TRACK_TO')
track.target = pivot
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'
sc.camera = cam

sc.frame_start, sc.frame_end = 1, 24
for k in range(24):
    pivot.rotation_euler = (0, 0, math.radians(PHI0 - 15 * k))
    pivot.keyframe_insert('rotation_euler', frame=k + 1)
for fc in pivot.animation_data.action.fcurves if hasattr(pivot.animation_data.action, 'fcurves') else []:
    for kp in fc.keyframe_points:
        kp.interpolation = 'LINEAR'

# ---------------------------------------------------------------- flat grey render
sc.render.engine = 'BLENDER_WORKBENCH'
sh = sc.display.shading
sh.light = 'STUDIO'
sh.color_type = 'SINGLE'
sh.single_color = (0.50, 0.50, 0.50)
sh.show_shadows = False
sh.show_cavity = False
sh.show_object_outline = True
sh.show_specular_highlight = False
sc.display.render_aa = '16'
world = bpy.data.worlds.new('PAPER')
world.color = (0.92, 0.92, 0.92)
sc.world = world
sc.view_settings.view_transform = 'Standard'
sc.render.resolution_x, sc.render.resolution_y = 2752, 1536
sc.render.resolution_percentage = SCALE
sc.render.film_transparent = False
sc.render.image_settings.file_format = 'PNG'
sc.render.image_settings.color_mode = 'RGB'
sc.render.image_settings.compression = 50

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'BULLET_ORBIT.blend'))

for a in ANGLES:
    sc.frame_set(a // 15 + 1)
    sc.render.filepath = os.path.join(OUT, 'BULLET_%03d.png' % a)
    bpy.ops.render.render(write_still=True)
    print('RENDERED', sc.render.filepath)
print('BULLET_DONE', len(ANGLES))
