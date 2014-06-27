#############################################################################################
# Available for use under the GNU GPL, version 2 (http://www.gnu.org/licenses/gpl-2.0.html) #
# Writer: Saeid Emami                                                                       #
#############################################################################################
 
"""
This script imports ANSYS cdb files to Blender.
 
The parsed commands are:
  N (node)
  EN (element)
  NBLOCK (node block)
  EBLOCK (element block)
  ET (element type definition)
  TYPE (element type selector)
  MAT (element material selector)
  REAL (element property selector)

Usage:
Execute this script from the "File->Import" menu and choose a cdb file to open.
"""


import bpy


def read3DMesh(cdbfilename):
    """
    Reads a 3D solid/shell mesh from an ANSYS cdb file.
    """
    global_et = {} # dictionary of element type no.: element type
    global_e = {} # dictionary of element no.: (element_mat, element_real, element_type, v1, v2, ..., vn)
    global_n = {} # dictionary of node no.: (x, y, z)

    current_element = 1 # ET comand requires current values for default element properties.
    current_mat = 1
    current_real = 1
    current_type = 1

    def parseCommand(first_line, filehandle):
        """
        Parses an ANSYS comamnd line and calls the appropriate function.
        """
        tokens = first_line.split(',')
        for i in range(len(tokens)):
            tokens[i] = tokens[i].strip().lower()

        command = tokens[0]
        if command == "n":
            readN(tokens)
        elif command == "en":
            readEN(tokens)
        elif command == "nblock":
            readNBLOCK(tokens, filehandle)
        elif command == "eblock":
            readEBLOCK(tokens, filehandle)
        elif command == "et":
            readET(tokens)
        elif command == "type":
            readTYPE(tokens)
        elif command == "mat":
            readMAT(tokens)
        elif command == "real":
            readREAL(tokens)

    def readN(tokens):
        """
        Reads an N command:
          N, R5.3, Type, NODE, SOLID, PARM, VAL1, VAL2, VAL3
            TYPE =
              LOC: VAL1, VAL2, VAL3 = X, Y, Z
              ANG: VAL1, VAL2, VAL3 = THXY, THYZ, THXZ
    
        It returns for NODE (node number) <= 0.
        Rotaions are ignored. Missing arguments are replaced with 0.
        SOLID (solid model reference key) is ignored. 
        PARM (line parameter value) is ignored.
        PARM and SOLID are not present for TYPE = ANG.
        """
        if len(tokens) < 4:
            return

        TYPE = tokens[2]
        if TYPE != "loc":
            return

        node_number = 0
        try:
            node_number = int(tokens[3])
        except:
            return
        if node_number <= 0:
            return

        x = y = z = 0
        try:
            x = float(tokens[6])
        except:
            pass
        try:
            y = float(tokens[7])
        except:
            pass
        try:
            z = float(tokens[8])
        except:
            pass
        global_n[node_number] = (x, y, z)

    def readEN(tokens):
        """
        Reads an EN command:
          EN, R5.5, Type, NUMN, I1, I2, I3, I4, I5, I6, I7, I8
            TYPE = 
              ATTR: I1, I2, ... = MAT,TYPE,REAL,SECNUM,ESYS,NUMELEM,SOLID,DEATH,EXCLUDE
              NODE: I1, I2, ... = node numbers
            NUMN: number of nodes

        Missing/invalid node numbers cause return.
        Missing/invalid attributes are replaced by current values.
        Out of attributes, only element number, type, material number and real constant are considered.
        """
        if len(tokens) < 4:
            return
        global current_element
        if tokens[2] == "attr":
            # It is assumed that missing/invalid arguments are replaced with default values.
            try:
                element_mat = int(tokens[4])
            except:
                element_mat = current_mat

            try:
                element_type = int(tokens[5])
            except:
                element_type = current_type

            try:
                element_real = int(tokens[6])
            except:
                element_real = current_real

            try:
                element_number = int(tokens[9])
                current_element = element_number
            except:
                element_number = current_element

            element_data = [element_mat, element_real, element_type]
            if (element_number in global_e) and len(global_e[element_number]) >= 3:
                element_data = list(global_e[current_element])
                element_data[0] = element_mat
                element_data[1] = element_real
                element_data[2] = element_type
            global_e[element_number] = tuple(element_data)

        elif tokens[2] == "node":
            element_data = [current_mat, current_real, current_type]
            if current_element in global_e:
                element_data = list(global_e[current_element])
            for i in range(len(tokens) - 4):
                try:
                    element_data.append(int(tokens[i + 4]))
                except:
                    return
            global_e[current_element] = tuple(element_data)     

    def detectFormat(line):
        """
        Generates a list of string formats from a format line:
          e.g. "(3i8,6e16.9)"-> (i, 8), (i, 8), (i, 8), (e, 16.9), (e, 16.9), ...
        """
        if len(line) < 3:
            return []
        r1 = line.find('(')
        r2 = line.rfind(')')
        if r2 < 0:
            r2 = len(line)
        line_split = line[r1 + 1 : r2].split(',')

        forms = []
        for raw_form in line_split:
            raw_count = ""; # "3" for format "3i8"
            str_type = ""; # "i" for format "3i8"
            raw_identifier1 = ""; # "8" for format "3i8"
            raw_identifier2 = ""; # ".9" for format "3e16.9"
            for c in raw_form:
                if len(str_type) == 0 and c.isdigit():
                    raw_count += c
                elif len(raw_identifier1) == 0 and not c.isdigit():
                    str_type += c
                elif len(raw_identifier2) == 0 and c!= '.':
                    raw_identifier1 += c
                else:
                    raw_identifier2 += c
            try:
                count = int(raw_count)
                identifier1 = int(raw_identifier1)
                identifier2 = 0
                if len(raw_identifier2) > 0:
                    identifier2 = int(raw_identifier2.strip('.'))
                for i in range(count):
                    forms.append((str_type, identifier1, identifier2))
            except:
                pass
        return forms

    def readNBLOCK(tokens, filehandle):
        """
        Reads a node block command:
          NBLOCK, Numfields, Solkey, NDmax, NDsel
          Format
          Node, Solkey, Lineocation, X, Y, Z, THXY, THYZ, THZX
          ...
          N command : final line
    
        Nodal rotations, solid key and other node properties are are ignored.
        Missing coordinates are replaced with 0.0.
        """
        forms = detectFormat(filehandle.readline())
        if len(forms) < 6:
            return
        start_x = forms[0][1] + forms[1][1] + forms[2][1]
        start_y = start_x + forms[3][1]
        start_z = start_y + forms[4][1]
        end_z = start_z + forms[5][1]

        while True:
            node_line = filehandle.readline()
            if (len(node_line) == 0) or (node_line.strip()[0].lower() == 'n'): # NBLOCK ends with a dummy N command.
                return
            #  Field 1 - Node number.
            #  Field 2 - The solid model entity (if any) in which the node exists (if SOLID key).
            #  Field 3 - The line location (if the node exists on a line and if SOLID key).
            #  Field 4 - 6 -The nodal coordinates.
            #  Field 7 - 9 -The rotation angles (ifNUMFIELD> 3).
            # last zero fields are removed (so, for example, if z = 0, only 5 fieds are present and so on.)
            try:
                node_number = int(node_line[0 : forms[0][1]])
            except:
                continue
            try:
                x = float(node_line[start_x : start_y])
            except:
                x = 0
            try:
                y = float(node_line[start_y : start_z])
            except:
                y = 0
            try:
                z = float(node_line[start_z : end_z])
            except:
                z = 0
            global_n[node_number] = (x, y, z)

    def readEBLOCK(tokens, filehandle): # TODO: Test a multi-line element, especially for non-solid elements.
        """
        Reads an element block command:
          EBLOCK, Num_fields, Solkey
          Format
        with Solkey == SOLID:
          Elem, Mat, Type, Real, SecID, ESYS, B/D flag, Solref, Shape flag, NNodes, X-key, ENUM, N1, N2, ..., N8
          N9, ....,N16 (optional)
          N17, ....,N20 (optional)
        without Solkey == SOLID:
          Elem, SecID, Real, Mat, ESYS, N1, N2, ..., N8
          N9, ....,N16 (optional)
          N17, ....,N20 (optional)
          ...
          -1 : final line

        Num_fields: number of items in the first line of a node definition.
        Reads a element block and populates global_e = dictionary of element no.: (element_mat, element_real, element_type, v1, v2, ..., vn)
        Num_fields determines the maximum number of fields in the first line of element definition.
        NOTE: Support for non-SOLID elements is shaky at best. Not sure how to capture multi-line nodes for these elements. 
        """
        if len(tokens) < 3:
            return

        Num_fields = 19
        try:
            Num_fields = int(tokens[1])
        except:
            return

        isSOLID = (tokens[2] == "solid")

        forms = detectFormat(filehandle.readline())
        if (isSOLID and len(forms) < 12) or (len(forms) < 6):
            return

        while True:
            element_line = filehandle.readline()
            if element_line.strip().startswith('-'): # An EBLOCK ends with a -1.
                break
            # The format with the SOLID keyword is:
            #  Field 1 -The material number.
            #  Field 2 -The element type number.
            #  Field 3 -The real constant number.
            #  Field 4 -The section ID attribute (beam section) number.
            #  Field 5 -The element coordinate system number.
            #  Field 6 -The birth/death flag.
            #  Field 7 -The solid model reference number.
            #  Field 8 -The element shape flag.
            #  Field 9 -The number of nodes defining this element if Solkey = SOLID; otherwise, Field 9 = 0.
            #  Field 10 -The exclude key (p-elements).
            #  Field 11 -The element number.
            #  Fields 12-19 -The node numbers. The next line will have the additional node numbers if there are more than eight.
            #
            # The format without the SOLID keyword is:
            #  Field 1 -The element number.
            #  Field 2 -The type of section ID.
            #  Field 3 -The real constant number.
            #  Field 4 -The material number.
            #  Field 5 -The element coordinate system number.
            #  Fields 6-15 -The node numbers. The next line will have the additional node numbers if there are more than ten.
            if isSOLID:
                fields = []
                start = 0
                for i in range(Num_fields):
                    try:
                        end = start + forms[i][1]
                        field = int(element_line[start : end])
                    except:
                       pass # Element fields can be less than Num_fields
                    fields.append(field)
                    start = end
    
                field_count = len(fields)
                if field_count < 8:
                    return # unexcpected number of fields
                while field_count < fields[8] + 11: # Keep reading lines until enough nodes are parsed.
                    element_line = filehandle.readline()
                    start = 0
                    while True:
                        try:
                            end = start + forms[field_count][1]
                            field = int(element_line[start : end])
                        except:
                            break
                        fields.append(field)
                        ++field_count

                element_mat, element_type, element_real = 1, 1, 1
                try:
                    element_mat, element_type, element_real = fields[0:3]
                    element_number = fields[10]
                    element_nodes = tuple(fields[11:])
                except:
                    return # unexcpected number of fields
            else: #not SOLID
                fields = []
                start = 0
                for i in range(Num_fields):
                    try:
                        end = start + forms[i][1]
                        field = int(element_line[start : end])
                    except:
                       return # unexcpected number of fields
                    fields.append(field)
                    start = end

                element_mat, element_type, element_real = 1, 1, 1
                try:
                    element_number, element_type, element_real, element_mat = fields[0:4]
                    element_nodes = tuple(fields[5:])
                except:
                    return # unexcpected number of fields

            element_data = [element_mat, element_real, element_type]
            element_data.extend(element_nodes)
            global_e[element_number] = tuple(element_data)     

    def readET(tokens):
        """
        Reads an ET command:
          ET, ITYPE, Ename, KOP1, ....

        ITYPE defaults to 1 + current maximum.
        Defines and an element type and selects it as the current type.
        """
        if len(tokens) < 3:
            return
        et_number = 1
        if tokens[1] == '': # The default et number is the maximum et number + 1
            max_et = 0
            if len(global_et) > 0:
                max_et = max(global_et)
            et_number = max_et + 1
        else:
            try:
                et_number = int(tokens[1])
                et_type = int(tokens[2])
            except:
                return

        global_et[et_number] = et_type
        global current_type
        current_type = et_number

    def readTYPE(tokens):
        """
        Reads a TYPE command:
          TYPE, ITYPE

        ITYPE defaults to 1.
        Selects an element type as current type.
        """
        try:
            global current_type
            current_type = int(tokens[1])
        except:
            pass

    def readMAT(tokens):
        """
        Reads a MAT command:
          MAT, mat

        mat defaults to 1.
        Selects an element material number as current material.
        """
        try:
            global current_mat
            current_mat = int(tokens[1])
        except:
            pass

    def readREAL(tokens):
        """
        Reads a REAL command:
          REAL, NSET

        NSET defaults to 1.
        Selects an element real constant set number as current real.
        """
        try:
            global current_real
            current_real = int(tokens[1])
        except:
            pass


    filehandle = open(cdbfilename, 'r')
    line = filehandle.readline()
    while line:
        parseCommand(line, filehandle)
        line = filehandle.readline()
    filehandle.close()

    return global_n, global_e, global_et



def get_faces(global_e, global_et, remove_duplicates=True):
    """
    Determines outer faces based on global_elements and global_et.
    Only for solid cells with positive volume is outside direction defined correctly.
    For other cases, remove_duplicates should be set to True to remove inside faces.. 
        
    Supported element types:
      Shell Elements
        SHELL28
        SHELL63
        SHELL93
        SHELL281
        SHELL152
    
      Solid Elements
        SOLID45
        SOLID92
        SOLID95
        SOLID185
        SOLID186
        SOLID187
    """

    counted_faces = {} # dictionary of (element_mat, element_real): dictionary of faces: count for all faces.
    outer_faces = {} # dictionary of (element_mat, element_real): set of outer faces.

    def order_face(f):
        """
        Returns an ordered permutation of f = (v1, v2, ..., vn) that starts with the lowest number.
        """
        if len(f) == 0:
            return []
        min_index = 0
        for i in range(len(f) - 1):
            if f[i + 1] < f[min_index]:
                min_index = i + 1
        ordered_face = []
        for i in range(len(f)):
            index = min_index + i
            if index >= len(f):
                index -= len(f)
            ordered_face.append(f[index])
        return tuple(ordered_face)

    def inverse_face(f):
        """
        Returns the opposite permutation for a face, so that f = (v1, v2, ..., vn) -> f(v1, vn, vn-1, ..., v2) 
        It keeps the first element as is and inverses the rest.
        """
        if len(f) == 0:
            return []
        inversed_face = [f[0]]
        for i in range(len(f) - 1):
            inversed_face.append(f[len(f) - i - 1])
        return tuple(inversed_face)

    def faces_on_8hexahedral(v1, v2, v3, v4, v5, v6, v7, v8):
        """
        Faces definitions for 8-node hexahedral cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v4, v3, v2))
        f2 = order_face((v1, v2, v6, v5))
        f3 = order_face((v2, v3, v7, v6))
        f4 = order_face((v3, v4, v8, v7))
        f5 = order_face((v4, v1, v5, v8)) 
        f6 = order_face((v5, v6, v7, v8))
        return (f1, f2, f3, f4, f5, f6)

    def faces_on_6wedge(v1, v2, v3, v4, v5, v6):
        """
        Faces definitions for 6-node wedge(prism) cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v3, v2))
        f2 = order_face((v1, v2, v5, v4))
        f3 = order_face((v2, v3, v6, v5))
        f5 = order_face((v3, v1, v4, v6))
        f6 = order_face((v4, v5, v6))
        return (f1, f2, f3, f5, f6)

    def faces_on_5pyramid(v1, v2, v3, v4, v5):
        """
        Faces definitions for 5-node pyramid cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v4, v3, v2))
        f2 = order_face((v1, v2, v5))
        f3 = order_face((v2, v3, v5))
        f4 = order_face((v3, v4, v5))
        f5 = order_face((v4, v1, v5)) 
        return (f1, f2, f3, f4, f5)

    def faces_on_4tetrahedral(v1, v2, v3, v4):
        """
        Faces definitions for 4-node tetrahedral cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v3, v2))
        f2 = order_face((v1, v2, v4))
        f3 = order_face((v2, v3, v4))
        f4 = order_face((v3, v1, v4))
        return (f1, f2, f3, f4)

    def faces_on_20hexahedral(v1, v2, v3, v4, v5, v6, v7, v8, v12, v23, v34, v14, v56, v67, v78, v58, v15, v26, v37, v48):
        """
        Faces definitions for 20-node hexahedral cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v14, v4, v34, v3, v23, v2, v12))
        f2 = order_face((v1, v12, v2, v26, v6, v56, v5, v15))
        f3 = order_face((v2, v23, v3, v37, v7, v67, v6, v26))
        f4 = order_face((v3, v34, v4, v48, v8, v78, v7, v37))
        f5 = order_face((v4, v14, v1, v15, v5, v58, v8, v48)) 
        f6 = order_face((v5, v56, v6, v67, v7, v78, v8, v58))
        return (f1, f2, f3, f4, f5, f6)

    def faces_on_15wedge(v1, v2, v3, v4, v5, v6, v12, v23, v13, v45, v56, v46, v14, v25, v36):
        """
        Faces definitions for 15-node wedge(prism) cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v13, v3, v32, v2, v21))
        f2 = order_face((v1, v12, v2, v25, v5, v54, v4, v41))
        f3 = order_face((v2, v23, v3, v36, v6, v56, v5, v25))
        f5 = order_face((v3, v13, v1, v14, v4, v46, v6, v36))
        f6 = order_face((v4, v45, v5, v56, v6, v46))
        return (f1, f2, f3, f5, f6)

    def faces_on_13pyramid(v1, v2, v3, v4, v5, v12, v23, v34, v14, v15, v25, v35, v45):
        """
        Faces definitions for 13-node pyramid cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v14, v4, v34, v3, v23, v2, v12))
        f2 = order_face((v1, v12, v2, v25, v5, v15))
        f3 = order_face((v2, v23, v3, v35, v5, v25))
        f4 = order_face((v3, v34, v4, v45, v5, v35))
        f5 = order_face((v4, v14, v1, v15, v5, v45)) 
        return (f1, f2, f3, f4, f5)

    def faces_on_10tetrahedral(v1, v2, v3, v4, v12, v23, v13, v14, v24, v34):
        """
        Faces definitions for 10-node tetrahedral cell based on ANSYS numbering convention.
        """
        f1 = order_face((v1, v13, v3, v23, v2, v12))
        f2 = order_face((v1, v12, v2, v24, v4, v14))
        f3 = order_face((v2, v23, v3, v34, v4, v24))
        f4 = order_face((v3, v13, v1, v14, v4, v34))
        return (f1, f2, f3, f4)

    def faces_on_4rectangle(v1, v2, v3, v4):
        """
        Faces definition for 4-node rectangle plane cell based on ANSYS numbering convention.
        """
        return (order_face((v1, v2, v3, v4)), )

    def faces_on_3triangle(v1, v2, v3):
        """
        Faces definition for 3-node triangle plane cell based on ANSYS numbering convention.
        """
        return (order_face((v1, v2, v3)), )

    def faces_on_8rectangle(v1, v2, v3, v4, v12, v23, v34, v14):
        """
        Faces definition for 8-node rectangle plane cell based on ANSYS numbering convention.
        """
        return (order_face((v1, v12, v2, v23, v3, v34, v4, v14)), )

    def faces_on_6triangle(v1, v12, v2, v23, v3, v13):
        """
        Faces definition for 6-node triangle plane cell based on ANSYS numbering convention.
        """
        return (order_face((v1, v12, v2, v23, v3, v13)), )

    def get_all_faces():
        """
        Determines all faces(counted_faces) based on element definition(global_e) and element type(global_e).
        """
        for e in global_e.values():
            try:
                etype = global_et[e[2]]
            except:
                continue
            faces = []
            if etype in (28, 63, 152): # Shell elements without midside node
                if len(e) < 7:
                    continue
                v1, v2, v3, v4 = e[3:7]
                if v3 == v4:
                    faces = faces_on_3triangle(v1, v2, v3)
                else:
                    faces = faces_on_4rectangle(v1, v2, v3, v4)

            elif etype in (93, 281): # Shell elements with midside node
                if len(e) < 11:
                    continue
                v1, v2, v3, v4, v12, v23, v34, v14 = e[3:11]
                if v3 == v4:
                    faces = faces_on_6triangle(v1, v12, v2, v23, v3, v13)
                else:
                    faces = faces_on_8rectangle(v1, v2, v3, v4, v12, v23, v34, v14)

            elif etype in (45, 185): # Solid elements without midside node
                if len(e) < 11:
                    continue
                v1, v2, v3, v4, v5, v6, v7, v8 = e[3:11]
                if v3 == v4 and v7 == v8:
                    faces = faces_on_6wedge(v1, v2, v3, v5, v6, v7)
                elif v5 == v6 and v5 == v7 and v5 == v8:
                    faces = faces_on_5pyramid(v1, v2, v3, v4, v5)
                elif v3 == v4 and v5 == v6 and v5 == v7 and v5 == v8:
                    faces = faces_on_4tetrahedral(v1, v2, v3, v5)
                else:
                    faces = faces_on_8hexahedral(v1, v2, v3, v4, v5, v6, v7, v8)

            elif etype in (95, 186): # Solid elements with midside node: 20-node structural solid
                if len(e) < 23:
                    continue
                v1, v2, v3, v4, v5, v6, v7, v8, v12, v23, v34, v14, v56, v67, v78, v58, v15, v26, v37, v48 = e[3:23]
                if v3 == v4 and v7 == v8:
                    faces_on_15wedge(v1, v2, v3, v5, v6, v7, v12, v23, v14, v56, v67, v58, v15, v26, v37)
                elif v5 == v6 and v5 == v7 and v5 == v8:
                    faces = faces_on_13pyramid(v1, v2, v3, v4, v5, v12, v23, v34, v14, v15, v26, v37, v48)
                elif v3 == v4 and v5 == v6 and v5 == v7 and v5 == v8:
                    faces = faces_on_10tetrahedral(v1, v2, v3, v5, v12, v23, v14, v15, v26, v37)
                else:
                    faces = faces_on_20hexahedral(v1, v2, v3, v4, v5, v6, v7, v8, v12, v23, v34, v14, v56, v67, v78, v58, v15, v26, v37, v48)

            elif etype in (92, 187): # Solid elements with midside node: 10-node structural solid tetrahedral
                if len(e) < 13:
                    continue
                v1, v2, v3, v4, v12, v23, v13, v14, v24, v34 = e[3:13]
                faces = faces_on_10tetrahedral(v1, v2, v3, v4, v12, v23, v13, v14, v24, v34)
            else:
                continue

            element_mat, element_real = e[0: 2]
            element_id = (element_mat, element_real)
            if element_id not in counted_faces:
                counted_faces[element_id] = {}

            for face in faces:
                face_count = counted_faces[element_id].get(face)
                if face_count is None:
                    face_count = 0
                face_count += 1
                counted_faces[element_id][face] = face_count

    def get_outer_faces(remove_duplicates):
        """
        Determines outer faces(outer_faces) from all defined faces (counted_faces).
        For well-defined cells (i.e. cells with positive volume), remove_duplicates can be set to False for better performance.
        """
        for element_id in counted_faces:
            outer_faces[element_id] = set()
            for f in counted_faces[element_id]:
                if (inverse_face(f) not in counted_faces[element_id]) and ((not remove_duplicates) or (counted_faces[element_id][f] == 1)):
                    outer_faces[element_id].add(f)


    get_all_faces()
    get_outer_faces(remove_duplicates)
    return outer_faces



def renumber(global_n, global_faces):
    """
    Reformates and renumbers nodes(from global_n) and faces(from global_faces) so that for each face_type = (material, real constant), node faces are compressed and start from 0.
    """
    verts = {} # dictionary of face_type:[(x, y, z), ...]; face_type = (material, real constant)
    faces = {} # dictionary of face_type:[(v1, v2, .., vn), ...]; face_type = (material, real constant)

    for face_type in global_faces:
        verts[face_type] = []
        faces[face_type] = []
        index_number = 0
        vert_coords = {}
        for f in global_faces[face_type]:
            face = []
            for v in f:
                coord = global_n[v]
                index = vert_coords.get(coord)
                if index is None:
                    index = vert_coords[coord] = index_number
                    index_number += 1
                    verts[face_type].append(coord)
                face.append(index)

            faces[face_type].append(tuple(face))

    return verts, faces



def readMesh(cdbfilename, objRootName, remove_duplicates):
    """
    Reads mesh from an ANSYS cdb file.
    For a cdb file, several objects for different defined pairs of material and real constant will be defined. 
    """
    n, e, et = read3DMesh(cdbfilename)
    f = get_faces(e, et, remove_duplicates)
    verts, faces = renumber(n, f)

    meshes = {}
    for face_type in faces:
        objName = objRootName + "_" + str(face_type[0]) + "_" +  str(face_type[1])
        mesh = bpy.data.meshes.new(objName)
        mesh.from_pydata(verts[face_type], [], faces[face_type])
        meshes[objName] = mesh

    return meshes



def addMeshObjs(meshes):
    """
    Create blender object from blender mesh and adding it to blender scene. 
    """
    scn = bpy.context.scene

    for o in scn.objects:
        o.select = False	

    for objname in meshes:
        meshes[objname].update()
        meshes[objname].validate()

        nobj = bpy.data.objects.new(objname, meshes[objname])
        scn.objects.link(nobj)
        nobj.select = True

        if scn.objects.active is None or scn.objects.active.mode == 'OBJECT':
            scn.objects.active = nobj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.normals_make_consistent(inside=False) # Slightly messy, but effective way to reorganize outside normals.
            bpy.ops.object.mode_set(mode='OBJECT')



def read(filepath, remove_duplicates=True):
    '''
    Converts the filename to a name.
    The ANSYS mesh is read and converted into diferent objects (based on material and real contant). The extracted name is used to name these objects.
    '''
    name = bpy.path.display_name_from_filepath(filepath)
    meshes = readMesh(filepath, name, remove_duplicates)
    addMeshObjs(meshes)


