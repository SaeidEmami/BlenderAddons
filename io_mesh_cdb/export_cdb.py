#############################################################################################
# Available for use under the GNU GPL, version 2 (http://www.gnu.org/licenses/gpl-2.0.html) #
# Writer: Saeid Emami                                                                       #
#############################################################################################

"""
This script exports a Mesh to a ANSYS cdb file format.
 
It exports faces as shell elements. The nodes and elements are written in an NBLOCK and EBLOCK respectively.

Depending on the number of nodes on a face, the following shell types are generated:
  SHELL63 (planes with no misdie nodes)
  SHELL93 (planes with misdie nodes)

Usage:
Execute this script from the "File->Export" menu and choose a cdb file to open.
"""

import bpy

def processSelectedObjs(apply_modifiers=True, scale=1.0):
    """
    Extracts nodal numbers and face vertices for selected objects.
    Returned vertex numbers are globally numbered starting from 0.
    """
    from mathutils import Matrix

    scene = bpy.context.scene

    scale_Matrix = Matrix.Scale(scale, 4)
    nodal_offset = 1 # Nodes are numbered from 1.
    global_nodes = {} # dictionary of node number: coordinate
    global_faces = [] # list of list of tuple of node numbers
    for obj in bpy.context.selected_objects:
        if obj.type != 'MESH':
            try:
                me = obj.to_mesh(scene, apply_modifiers, "PREVIEW")
            except:
                me = None
            is_tmp_mesh = True
        else:
            me = obj.data
            is_tmp_mesh = False

        if me is not None:
            matrix = scale_Matrix * obj.matrix_world.copy()

            for i, v in enumerate(me.vertices):
                global_nodes[nodal_offset + i] = tuple(matrix * v.co)

            mesh_faces = []
            for face in me.polygons:
                global_f = []
                for v in face.vertices:
                    global_f.append(nodal_offset + v)
                mesh_faces.append(tuple(global_f))
            global_faces.append(mesh_faces)

            nodal_offset += len(me.vertices)

            if is_tmp_mesh:
                bpy.data.meshes.remove(me)

    return global_nodes, global_faces



def write(cdbfilepath, apply_modifiers=True, scale=1.0, initial_mat=1, increment_mat=False, initial_real=1, increment_real=False):
    """
    Writes a shell mesh to an ANSYS cdb file.
    """
    four_noded_shell = (1, 63)
    eight_noded_shell = (2, 93)

    def writeHeader(fhandle):
        """
        Writes ANSYS header commands.
        """
        fhandle.write("/PREP7\n/TITLE,\n")

    def writeET(fhandle):
        """
        Writes an ET command.
        """
        fhandle.write("ET,%i,%i\nET,%i,%i\n" % (four_noded_shell[0], four_noded_shell[1], eight_noded_shell[0], eight_noded_shell[1]))

    def writeNBLOCK(fhandle, nodes):
        """
        Writes a node block command.
        """
        fhandle.write("NBLOCK,6,SOLID\n(3i8,6g16.9)\n")
        for node in n:
            fhandle.write("%8i%8i%8i%16.9g%16.9g%16.9g\n" % (node, 0, 0, n[node][0], n[node][1], n[node][2]))
        fhandle.write("N,R5.3,LOC,-1,\n")

    def writeEBLOCK(fhandle, faces, init_mat=1, inc_mat=False, init_real=1, inc_real=False): #TODO: Test elements with midside node.
        """
        Writes a element block command.
        """
        face_count = 0
        for face_list in faces:
            face_count += len(face_list)
        fhandle.write("EBLOCK,19,SOLID," + str(face_count) + "\n(19i8)\n")

        element_number = 1
        element_mat = init_mat
        element_real = init_real
        for face_list in faces:
            for face in face_list:
                if len(face) == 4:
                    element_type = four_noded_shell[0]
                    nodes = face
                elif len(face) == 8:
                    element_type = eight_noded_shell[0]
                    nodes = face
                elif len(face) == 3:
                    element_type = four_noded_shell[0]
                    nodes = (face[0], face[1], face[2], face[2])
                elif len(face) == 6:
                    element_type = eight_noded_shell[0]
                    nodes = (face[0], face[2], face[4], face[4], face[1], face[3], face[4], face[5])
                else:
                    continue
                fhandle.write("%8i%8i%8i%8i%8i%8i%8i%8i%8i%8i%8i%8i%8i%8i%8i" % (element_mat, element_type, element_real, 1, 0, 0, 0, 0,
                                 len(nodes), 0, element_number, nodes[0], nodes[1], nodes[2], nodes[3]))
                if len(nodes) > 4:
                    fhandle.write("%8i%8i%8i%8i\n" % (nodes[4], nodes[5], nodes[6], nodes[7]))
                else:
                    fhandle.write("\n")
                element_number += 1

            if inc_mat:
                element_mat += 1
            if inc_real:
                element_real += 1

        fhandle.write("-1,\n")


    def writeFINISH(fhandle):
        """
        Writes a FINISH command.
        """
        line = "FINISH\n"
        fhandle.write(line)


    n, f = processSelectedObjs(apply_modifiers, scale)

    filehandle = open(cdbfilepath, 'w')
    writeHeader(filehandle)
    writeET(filehandle)
    writeNBLOCK(filehandle, n)
    writeEBLOCK(filehandle, f, initial_mat, increment_mat, initial_real, increment_real)
    writeFINISH(filehandle)
    filehandle.close()

