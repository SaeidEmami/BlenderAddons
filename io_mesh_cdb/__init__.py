#############################################################################################
# Available for use under the GNU GPL, version 2 (http://www.gnu.org/licenses/gpl-2.0.html) #
# Writer: Saeid Emami                                                                       #
#############################################################################################


bl_info = {
    "name": "CDB format",
    "author": "Saeid Emami",
    "version": (0, 1),
    "blender": (2, 70, 0),
    "location": "File > Import-Export > ANSYS (.cdb) ",
    "description": "Import-Export CDB Files",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"}


"""
Imports ANSYS cdb files.
 
The parsed commands are:
  N (node)
  EN (element)
  NBLOCK (node block)
  EBLOCK (element block)
  ET (element type definition)
  TYPE (element type selector)
  MAT (element material selector)
  REAL (element property selector)

Supported element types:
  Shell Elements
    SHELL28, SHELL63, SHELL93, SHELL281
    
  Solid Elements
    SOLID45, SOLID92, SOLID95, SOLID185, SOLID186, SOLID187

Usage:
Execute this script from the "File->Import" menu and choose a cdb file to open.
"""

if "bpy" in locals():
    import imp
    if "import_cdb" in locals():
        imp.reload(import_cdb)
    if "export_cdb" in locals():
        imp.reload(export_cdb)
else:
    import bpy

import os
from bpy.props import StringProperty, BoolProperty, CollectionProperty, FloatProperty, IntProperty
from bpy_extras.io_utils import ImportHelper, ExportHelper


class CDBImporter(bpy.types.Operator, ImportHelper):
    """
    Loads ANSYS cdb mesh data
    """
    bl_idname = "import_mesh.cdb"
    bl_label = "Import CDB"
    bl_options = {"UNDO"}

    filename_ext = ".cdb"
    files = CollectionProperty(name="File Path", type=bpy.types.OperatorFileListElement)
    directory = StringProperty(subtype="DIR_PATH")
    filepath = StringProperty(subtype="FILE_PATH")
    filter_glob = StringProperty(default="*.cdb", options={"HIDDEN"})

    remove_duplicates = BoolProperty(name="Remove Duplicate Surfaces", 
                                     description="Remove duplicate faces.\n"
                                                 "Turn off to improve performance when the orgignal mesh is well-defined.",
                                     default=True)

    def execute(self, context):
        from . import import_cdb

        paths = [os.path.join(self.directory, name.name) for name in self.files]
        if not paths:
            paths.append(self.filepath)

        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode="OBJECT")

        if bpy.ops.object.select_all.poll():
            bpy.ops.object.select_all(action="DESELECT")

        for path in paths:
            import_cdb.read(path, self.remove_duplicates)

        return {"FINISHED"}



class CDBExporter(bpy.types.Operator, ExportHelper):
    """
    Saves ANSYS cdb shell planar mesh data
    """
    bl_idname = "export_mesh.cdb"
    bl_label = "Export CDB"

    filename_ext = ".cdb"
    filter_glob = StringProperty(default="*.cdb", options={"HIDDEN"})
    filepath = StringProperty(subtype="FILE_PATH")

    apply_modifiers = BoolProperty(name="Apply Modifiers", description="Apply the modifiers before saving", default=True)

    global_scale = FloatProperty(name="Scale", min=0.0001, max=100000.0, default=1.0)

    mat_init = IntProperty(name="Initial Material Number", min=1, max=10000, default=1, description="Initial material number for exported mesh.")
    mat_inc = BoolProperty(name="Incremenet Material Number", description="Increment material number for each mesh.", default=False)

    real_init = IntProperty(name="Initial Real Constant Number", min=1, max=10000, default=1, description="Initial real constant number for exported mesh.")
    real_inc = BoolProperty(name="Incremenet Real Constant Number", description="Increment real constant number for each mesh.", default=False)

    def execute(self, context):
        from . import export_cdb

        export_cdb.write(self.filepath, self.apply_modifiers, self.global_scale, self.mat_init, self.mat_inc, self.real_init, self.real_inc)

        return {"FINISHED"}



def menu_import(self, context):
    self.layout.operator(CDBImporter.bl_idname, text="CDB (.cdb)")



def menu_export(self, context):
    self.layout.operator(CDBExporter.bl_idname, text="CDB (.cdb)")



def register():
    bpy.utils.register_module(__name__)

    bpy.types.INFO_MT_file_import.append(menu_import)
    bpy.types.INFO_MT_file_export.append(menu_export)



def unregister():
    bpy.utils.unregister_module(__name__)

    bpy.types.INFO_MT_file_import.remove(menu_import)
    bpy.types.INFO_MT_file_export.remove(menu_export)



if __name__ == "__main__":
    register()

