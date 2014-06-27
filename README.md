# io_mesh_cdb

This Blender addon allows import and export of ANSYS cdb files containing geometry data to and from Blender.


## Importing

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


## Exporting

Faces are exported as shell elements. The nodes and elements are written in an NBLOCK and EBLOCK.

Depending on the number of nodes on a face, the following shell types are generated:
  SHELL63 (planes with no misdie nodes)
  SHELL93 (planes with misdie nodes)

Usage:
Execute this script from the "File->Export" menu and choose a cdb file to open.

