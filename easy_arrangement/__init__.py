# SPDX-License-Identifier: GPL-3.0-or-later
# Easy Arrangement — Blender Extension
# Author: mlico
# Version: 0.1.6

import bpy
from mathutils import Vector, Euler
from math import radians, cos, sin

# ----------------------------
# Session-only cache (NOT saved to .blend file)
# ----------------------------
# Keyed by object name. Lives only in memory for the current Blender session.
# This replaces permanent custom properties on objects/scene, so no extra
# data is ever written into the user's .blend file.
_ea_cache = {
    "objects": {},   # { obj_name: {"loc": (x,y,z), "rot": (x,y,z), "arranged": bool} }
    "center":  None, # (x, y, z) or None
}

def _clear_cache():
    _ea_cache["objects"].clear()
    _ea_cache["center"] = None

# ----------------------------
# Utility
# ----------------------------
def object_length_along_axis(obj, axis_index):
    world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    projections = [corner[axis_index] for corner in world_corners]
    return max(projections) - min(projections)

def has_base_data(obj):
    return obj.name in _ea_cache["objects"]

def get_base_data(obj):
    return _ea_cache["objects"][obj.name]

def set_base_data(obj, loc, rot, arranged):
    _ea_cache["objects"][obj.name] = {
        "loc": tuple(loc),
        "rot": tuple(rot),
        "arranged": arranged,
    }

def is_arranged(obj):
    data = _ea_cache["objects"].get(obj.name)
    return bool(data and data.get("arranged", False))

# ----------------------------
# Core Arrangement
# ----------------------------
def apply_arrangement_from_base(context):
    scene = context.scene
    selected = context.selected_objects
    if len(selected) < 2:
        return

    for obj in selected:
        if not has_base_data(obj):
            return

    objs = list(selected)

    if scene.order_mode == 'ACTIVE':
        active = context.view_layer.objects.active
        if active in objs:
            objs.remove(active)
            objs.insert(0, active)
    elif scene.order_mode == 'NAME':
        objs.sort(key=lambda o: o.name.lower())

    if scene.arrangement_type in ['LINEAR', 'STAIR']:
        axis_map       = {'X': Vector((1,0,0)), 'Y': Vector((0,1,0)), 'Z': Vector((0,0,1))}
        axis_index_map = {'X': 0, 'Y': 1, 'Z': 2}

        axis_vector    = axis_map[scene.axis]
        step_vector    = axis_map[scene.step_axis]
        axis_index     = axis_index_map[scene.axis]

        lengths        = {obj: object_length_along_axis(obj, axis_index) for obj in objs}
        start_location = Vector(get_base_data(objs[0])["loc"])
        linear_offset  = 0.0

        for i, obj in enumerate(objs):
            base = get_base_data(obj)

            if i == 0:
                obj.location       = start_location
                obj.rotation_euler = Euler(base["rot"])
                _apply_rotation_offset(scene, obj)
                set_base_data(obj, base["loc"], base["rot"], True)
                continue

            prev = objs[i - 1]
            prev_base = get_base_data(prev)

            if scene.use_object_length:
                linear_offset += 0.5 * lengths[prev] + 0.5 * lengths[obj]

            linear_offset += scene.spacing
            new_location   = start_location + axis_vector * linear_offset

            if scene.arrangement_type == 'STAIR':
                new_location += step_vector * i * scene.step_height

            obj.location       = new_location
            obj.rotation_euler = Euler(base["rot"])
            _apply_rotation_offset(scene, obj)
            set_base_data(obj, base["loc"], base["rot"], True)

    elif scene.arrangement_type == 'CIRCULAR':
        if _ea_cache["center"] is not None:
            center = Vector(_ea_cache["center"])
        else:
            center = context.scene.cursor.location.copy()
            _ea_cache["center"] = tuple(center)

        num_objs = len(objs)

        if scene.circular_radius_mode == 'START_END':
            denom = max(1, num_objs - 1)
            radii = [
                scene.circular_start_radius +
                i * (scene.circular_end_radius - scene.circular_start_radius) / denom
                for i in range(num_objs)
            ]
        else:
            radii = [
                scene.circular_start_radius + i * scene.circular_increment_per_step
                for i in range(num_objs)
            ]

        if scene.circular_angle_mode == 'PER_OBJECT':
            angle_step = radians(scene.circular_angle_value)
        else:
            angle_step = radians(scene.circular_angle_value) / max(1, num_objs - 1)

        rot_mode = scene.circular_rotation_mode

        for idx, obj in enumerate(objs):
            base = get_base_data(obj)
            theta         = angle_step * idx
            r             = radii[idx]
            height_offset = scene.step_height * idx

            if scene.circular_axis == 'Z':
                offset = Vector((r * cos(theta), r * sin(theta), height_offset))
            elif scene.circular_axis == 'Y':
                offset = Vector((r * cos(theta), height_offset, r * sin(theta)))
            else:
                offset = Vector((height_offset, r * cos(theta), r * sin(theta)))

            obj.location = center + offset

            if rot_mode == 'AXIS':
                rot = list(base["rot"])
                axis_idx = {'Z': 2, 'Y': 1, 'X': 0}[scene.circular_axis]
                rot[axis_idx] += theta
                obj.rotation_euler = Euler(rot)
            elif rot_mode == 'CENTER':
                direction = center - obj.location
                if direction.length > 1e-6:
                    obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
                else:
                    obj.rotation_euler = Euler(base["rot"])
            else:
                obj.rotation_euler = Euler(base["rot"])

            _apply_rotation_offset(scene, obj)
            set_base_data(obj, base["loc"], base["rot"], True)

# ----------------------------
# Helper: Rotation Offset
# ----------------------------
def _apply_rotation_offset(scene, obj):
    if scene.rotation_offset_enabled:
        offset_euler = Euler((
            radians(scene.rotation_offset_x),
            radians(scene.rotation_offset_y),
            radians(scene.rotation_offset_z)
        ))
        obj.rotation_euler.rotate(offset_euler)

# ----------------------------
# Apply Operator
# ----------------------------
class OBJECT_OT_easy_arrangement_apply(bpy.types.Operator):
    bl_idname  = "object.easy_arrangement_apply"
    bl_label   = "Apply Arrangement"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected = context.selected_objects
        scene    = context.scene

        if len(selected) < 2:
            self.report({'WARNING'}, "Select at least two objects")
            return {'CANCELLED'}

        # Resolve circular center (kept in session cache, not on scene)
        if scene.arrangement_type == 'CIRCULAR':
            if scene.circular_center_mode == 'CURSOR':
                _ea_cache["center"] = tuple(context.scene.cursor.location)
            elif scene.circular_center_mode == 'ACTIVE':
                active = context.view_layer.objects.active
                if active:
                    _ea_cache["center"] = tuple(active.location)
                else:
                    self.report({'WARNING'}, "No active object for center")
                    _ea_cache["center"] = tuple(context.scene.cursor.location)
            elif scene.circular_center_mode == 'OBJECT':
                center_obj = scene.circular_center_object
                if center_obj:
                    _ea_cache["center"] = tuple(center_obj.location)
                else:
                    self.report({'WARNING'}, "Center Object not set — using 3D Cursor as fallback")
                    _ea_cache["center"] = tuple(context.scene.cursor.location)

        # Snapshot logic:
        # - If object is currently in an "arranged" state (placed by this tool
        #   and not moved manually since) -> restore true base, keep that base.
        # - Otherwise (manually moved, or first time) -> current position
        #   becomes the new base.
        for obj in selected:
            if is_arranged(obj):
                base = get_base_data(obj)
                obj.location       = Vector(base["loc"])
                obj.rotation_euler = Euler(base["rot"])

            set_base_data(obj, obj.location, obj.rotation_euler, False)

        apply_arrangement_from_base(context)
        self.report({'INFO'}, "Easy Arrangement applied")
        return {'FINISHED'}

# ----------------------------
# Reset Operator
# ----------------------------
class OBJECT_OT_easy_arrangement_reset(bpy.types.Operator):
    bl_idname  = "object.easy_arrangement_reset"
    bl_label   = "Reset Arrangement"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        reset_count = 0
        for obj in context.selected_objects:
            if has_base_data(obj):
                base = get_base_data(obj)
                obj.location       = Vector(base["loc"])
                obj.rotation_euler = Euler(base["rot"])
                set_base_data(obj, base["loc"], base["rot"], False)
                reset_count += 1

        if reset_count == 0:
            self.report({'WARNING'}, "No base data found — apply arrangement first")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Reset {reset_count} object(s) to base position")
        return {'FINISHED'}

# ----------------------------
# Panel
# ----------------------------
class VIEW3D_PT_easy_arrangement(bpy.types.Panel):
    bl_label       = "Easy Arrang v0.1.6"
    bl_idname      = "VIEW3D_PT_easy_arrangement"
    bl_space_type  = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category    = 'Easy Arrang'

    def draw(self, context):
        layout = self.layout
        scene  = context.scene

        # Status
        sel_count  = len(context.selected_objects)
        status_box = layout.box()
        row = status_box.row(align=True)
        if sel_count < 2:
            row.label(text=f"Select at least 2 objects  ({sel_count} selected)", icon='ERROR')
        else:
            row.label(text=f"{sel_count} objects selected", icon='CHECKMARK')

        # General
        box = layout.box()
        box.row(align=True).label(text="General", icon='SETTINGS')
        box.row(align=True).prop(scene, "ea_live_update", icon='FILE_REFRESH')
        box.row(align=True).label(text="Type:", icon='GRID')
        box.row(align=True).prop(scene, "arrangement_type", expand=True)
        row = box.row(align=True)
        row.label(text="Order:", icon='SORTALPHA')
        row.prop(scene, "order_mode", text="")

        # Linear / Stair
        if scene.arrangement_type in ['LINEAR', 'STAIR']:
            box  = layout.box()
            icon = 'SORTSIZE' if scene.arrangement_type == 'LINEAR' else 'ALIGN_TOP'
            text = "Linear Settings" if scene.arrangement_type == 'LINEAR' else "Stair Settings"
            box.row().label(text=text, icon=icon)

            row = box.row(align=True)
            row.label(text="Axis:", icon='AXIS_FRONT')
            row.prop(scene, "axis", expand=True)

            row = box.row(align=True)
            row.label(text="Spacing:", icon='ARROW_LEFTRIGHT')
            row.prop(scene, "spacing", text="")

            box.row(align=True).prop(scene, "use_object_length", icon='FULLSCREEN_ENTER')

            if scene.arrangement_type == 'STAIR':
                row = box.row(align=True)
                row.label(text="Step Axis:", icon='AXIS_TOP')
                row.prop(scene, "step_axis", expand=True)
                row = box.row(align=True)
                row.label(text="Step Height:", icon='SORT_DESC')
                row.prop(scene, "step_height", text="")

        # Circular
        if scene.arrangement_type == 'CIRCULAR':
            box = layout.box()
            box.row().label(text="Circular Settings", icon='FORCE_VORTEX')

            sub = box.box()
            row = sub.row(align=True)
            row.label(text="Center:", icon='PIVOT_CURSOR')
            row.prop(scene, "circular_center_mode", text="")
            if scene.circular_center_mode == 'OBJECT':
                row = sub.row(align=True)
                row.label(text="", icon='OBJECT_DATA')
                row.prop(scene, "circular_center_object", text="")

            sub = box.box()
            row = sub.row(align=True)
            row.label(text="Rot. Axis:", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            row.prop(scene, "circular_axis", expand=True)
            row = sub.row(align=True)
            row.label(text="Angle Mode:", icon='DRIVER_ROTATIONAL_DIFFERENCE')
            row.prop(scene, "circular_angle_mode", text="")
            row = sub.row(align=True)
            row.label(text="Angle (°):", icon='CURVE_PATH')
            row.prop(scene, "circular_angle_value", text="")

            sub = box.box()
            row = sub.row(align=True)
            row.label(text="Radius Mode:")
            row.prop(scene, "circular_radius_mode", text="")
            row = sub.row(align=True)
            row.label(text="Start R:", icon='SPHERECURVE')
            row.prop(scene, "circular_start_radius", text="")
            if scene.circular_radius_mode == 'START_END':
                row = sub.row(align=True)
                row.label(text="End R:", icon='SPHERECURVE')
                row.prop(scene, "circular_end_radius", text="")
            else:
                row = sub.row(align=True)
                row.label(text="Increment:", icon='ADD')
                row.prop(scene, "circular_increment_per_step", text="")

            row = box.row(align=True)
            row.label(text="Height Step:", icon='SORT_DESC')
            row.prop(scene, "step_height", text="")
            row = box.row(align=True)
            row.label(text="Rot. Mode:", icon='ORIENTATION_GIMBAL')
            row.prop(scene, "circular_rotation_mode", text="")

        # Rotation Offset
        box = layout.box()
        box.row(align=True).prop(scene, "rotation_offset_enabled",
                                  icon='DRIVER_ROTATIONAL_DIFFERENCE',
                                  text="Rotation Offset")
        if scene.rotation_offset_enabled:
            row = box.row(align=True)
            row.label(text="X:", icon='AXIS_FRONT')
            row.prop(scene, "rotation_offset_x", text="")
            row = box.row(align=True)
            row.label(text="Y:", icon='AXIS_SIDE')
            row.prop(scene, "rotation_offset_y", text="")
            row = box.row(align=True)
            row.label(text="Z:", icon='AXIS_TOP')
            row.prop(scene, "rotation_offset_z", text="")

        # Buttons
        layout.separator()
        row = layout.row(align=True)
        row.scale_y = 1.4
        row.operator("object.easy_arrangement_apply", icon='MOD_ARRAY', text="Apply")
        row.operator("object.easy_arrangement_reset", icon='LOOP_BACK', text="Reset")

# ----------------------------
# Scene Properties (UI state only — no per-object/scene permanent IDs)
# ----------------------------
def ea_update_live(self, context):
    if getattr(context.scene, "ea_live_update", False):
        apply_arrangement_from_base(context)

def register_props():
    S = bpy.types.Scene
    P = bpy.props

    S.ea_live_update              = P.BoolProperty(name="Live Update", default=True)
    S.arrangement_type            = P.EnumProperty(
        name="Arrangement Type",
        items=[('LINEAR','Linear',''),('STAIR','Stair',''),('CIRCULAR','Circular','')],
        default='LINEAR', update=ea_update_live)
    S.order_mode                  = P.EnumProperty(
        name="Order Mode",
        items=[('ACTIVE','Active First',''),('NAME','By Name','')],
        default='ACTIVE', update=ea_update_live)
    S.axis                        = P.EnumProperty(name="Axis",
        items=[('X','X',''),('Y','Y',''),('Z','Z','')], default='X', update=ea_update_live)
    S.step_axis                   = P.EnumProperty(name="Step Axis",
        items=[('X','X',''),('Y','Y',''),('Z','Z','')], default='Z', update=ea_update_live)
    S.spacing                     = P.FloatProperty(name="Spacing",     default=0.2,  update=ea_update_live)
    S.step_height                 = P.FloatProperty(name="Step Height",  default=1.0,  update=ea_update_live)
    S.use_object_length           = P.BoolProperty(name="Use Object Length", default=True, update=ea_update_live)
    S.circular_center_mode        = P.EnumProperty(name="Center Mode",
        items=[('CURSOR','3D Cursor',''),('ACTIVE','Active Object',''),('OBJECT','Selected Object','')],
        default='CURSOR', update=ea_update_live)
    S.circular_center_object      = P.PointerProperty(name="Center Object", type=bpy.types.Object)
    S.circular_axis               = P.EnumProperty(name="Rotation Axis",
        items=[('X','X',''),('Y','Y',''),('Z','Z','')], default='Z', update=ea_update_live)
    S.circular_angle_mode         = P.EnumProperty(name="Angle Mode",
        items=[('PER_OBJECT','Angle per Object',''),('TOTAL','Total Angle','')],
        default='PER_OBJECT', update=ea_update_live)
    S.circular_angle_value        = P.FloatProperty(name="Angle Value (deg)", default=30.0, update=ea_update_live)
    S.circular_radius_mode        = P.EnumProperty(name="Radius Mode",
        items=[('START_END','Start & End',''),('STEP','Increment per Step','')],
        default='START_END', update=ea_update_live)
    S.circular_start_radius       = P.FloatProperty(name="Start Radius",       default=2.0, update=ea_update_live)
    S.circular_end_radius         = P.FloatProperty(name="End Radius",         default=5.0, update=ea_update_live)
    S.circular_increment_per_step = P.FloatProperty(name="Increment per Step", default=0.5, update=ea_update_live)
    S.circular_rotation_mode      = P.EnumProperty(name="Rotation Mode",
        items=[('NONE','Default','No rotation'),
               ('AXIS','Rotate Along Axis','Rotate around circular axis'),
               ('CENTER','Rotate Toward Center','Rotate facing center')],
        default='NONE', update=ea_update_live)
    S.rotation_offset_enabled     = P.BoolProperty(name="Enable Rotation Offset", default=False, update=ea_update_live)
    S.rotation_offset_x           = P.FloatProperty(name="Offset X (deg)", default=0.0, update=ea_update_live)
    S.rotation_offset_y           = P.FloatProperty(name="Offset Y (deg)", default=0.0, update=ea_update_live)
    S.rotation_offset_z           = P.FloatProperty(name="Offset Z (deg)", default=0.0, update=ea_update_live)

def unregister_props():
    props = [
        "ea_live_update", "arrangement_type", "order_mode", "axis", "step_axis",
        "spacing", "step_height", "use_object_length",
        "circular_center_mode", "circular_center_object", "circular_axis",
        "circular_angle_mode", "circular_angle_value",
        "circular_radius_mode", "circular_start_radius", "circular_end_radius",
        "circular_increment_per_step", "circular_rotation_mode",
        "rotation_offset_enabled", "rotation_offset_x", "rotation_offset_y", "rotation_offset_z"
    ]
    for p in props:
        if hasattr(bpy.types.Scene, p):
            delattr(bpy.types.Scene, p)

# ----------------------------
# Handler: clear session cache when a new/different file is loaded
# ----------------------------
@bpy.app.handlers.persistent
def _ea_on_load(dummy):
    _clear_cache()

# ----------------------------
# Register / Unregister
# ----------------------------
classes = (
    OBJECT_OT_easy_arrangement_apply,
    OBJECT_OT_easy_arrangement_reset,
    VIEW3D_PT_easy_arrangement,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    register_props()
    if _ea_on_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_ea_on_load)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    unregister_props()
    if _ea_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_ea_on_load)
    _clear_cache()