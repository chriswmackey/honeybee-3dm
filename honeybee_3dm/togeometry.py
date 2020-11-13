"""Functions to create Ladybug objects from Rhino3dm objects."""

# The Rhino3dm library provides the ability to access content of a Rhino3dm
# file from outside of Rhino
import warnings
import rhino3dm

# Importing Ladybug geometry dependencies
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.line import LineSegment3D
from ladybug_geometry.geometry3d.polyline import Polyline3D


def to_point3d(point):
    """Create a Ladybug Point3D object from a rhino3dm point.

    Args:
        point: A rhino3dm point.

    Returns:
        A Ladybug Point3D object.
    """
    return Point3D(point.X, point.Y, point.Z)


def to_vector3d(vector):
    """Create a Ladybug Vector3D from a rhino3dm Vector3d.

    Args:
        vector: A rhino3dm vector3d.

    Returns:
         A Ladybug Vector3D object.
    """
    return Vector3D(vector.X, vector.Y, vector.Z)


def remove_dup_vertices(vertices, tolerance=0.001):
    """Remove vertices from an array of Point3Ds that are equal within the tolerance.

    Args:
        vertices: A list of Ladybug Point3D objects.

    Returns:
         A list of Ladybug Point3D objects with duplicate points removed.

    """
    return [pt for i, pt in enumerate(vertices)
            if not pt.is_equivalent(vertices[i - 1], tolerance)]


def mesh_to_face3d(mesh):
    """Create a Ladybug Face3D object out of a rhino3dm Mesh.

    Args:
        mesh: A rhino3dm mesh geometry.

    Returns:
        A list of Ladybug Face3D objects.
    """

    faces = []
    pts = [to_point3d(mesh.Vertices[i]) for i in range(len(mesh.Vertices))]

    for j in range(len(mesh.Faces)):
        face = mesh.Faces[j]
        if len(face) == 4:
            all_verts = (pts[face[0]], pts[face[1]],
                         pts[face[2]], pts[face[3]])
        else:
            all_verts = (pts[face[0]], pts[face[1]], pts[face[2]])

        faces.append(Face3D(all_verts))

    return faces


def brep_to_face3d(brep):
    """Create a Ladybug Face3D object from a rhino3dm Brep.

    Args:
        brep: A rhino3dm Brep.

    Returns:
        A list of Ladybug Face3D objects.
    """
    faces = []
    for i in range(len(brep.Faces)):
        mesh = brep.Faces[i].GetMesh(rhino3dm.MeshType.Any)
        faces.extend(mesh_to_face3d(mesh))

    return faces


def brep2d_to_face3d(brep, tolerance):
    """Create a Ladybug Face3D object from a rhino3dm Brep.

    This function is used in translating rhino3dm planar Brep to Ladybug Face3D objects.

    Args:
        brep: A rhino3dm Brep.

    Returns:
        A list of Ladybug Face3D objects.
    """
    faces = []
    try:
        # * Check 01 - If any of the edge is an arc
        lines = []
        not_line = 0
        for i in range(len(brep.Edges)):
            if brep.Edges[i].IsLinear(tolerance) == False:
                not_line += 1
        # If there's an arc in one of the edges, mesh it
        if not_line > 0:
            print("The surface has curved edges. It will be meshed")
            faces.extend(brep_to_face3d(brep))
        else:
            # Create Ladybug lines from start and end points of edges
            for i in range(len(brep.Edges)):
                start_pt = to_point3d(brep.Edges[i].PointAtStart)
                end_pt = to_point3d(brep.Edges[i].PointAtEnd)
                line = LineSegment3D.from_end_points(start_pt, end_pt)
                lines.append(line)

            # Create Ladybug Polylines from the lines
            polylines = Polyline3D.join_segments(lines, tolerance)
            # Sort the Ladybug Polylines based on length
            # The longest polyline belongs to the boundary of the face
            # The rest of the polylines belong to the holes in the face
            sorted_polylines = sorted(polylines, key=lambda polyline: polyline.length)
            # The first polyline in the list shall always be the polyline for
            # the boundary
            sorted_polylines.reverse()

            # Getting all vertices of the face
            mesh = brep.Faces[0].GetMesh(rhino3dm.MeshType.Any)
            mesh_pts = [to_point3d(mesh.Vertices[i])
                        for i in range(len(mesh.Vertices))]

            # In the list of the Polylines, if there's only one polyline then
            # the face has no holes
            if len(sorted_polylines) == 1:
                if len(mesh_pts) == 4 or len(mesh_pts) == 3:
                    faces.extend(mesh_to_face3d(mesh))
                else:
                    boundary_pts = remove_dup_vertices(
                        sorted_polylines[0].vertices)
                    lb_face = Face3D(boundary=boundary_pts)
                    faces.append(lb_face)

            # In the list of the Polylines, if there's more than one polyline then
            # the face has hole / holes
            elif len(sorted_polylines) > 1:
                boundary_pts = remove_dup_vertices(sorted_polylines[0].vertices)
                hole_pts = [remove_dup_vertices(polyline.vertices)
                            for polyline in sorted_polylines[1:]]
                # Merging lists of hole_pts
                total_hole_pts = [
                    pts for pts_lst in hole_pts for pts in pts_lst]
                hole_pts_on_boundary = [
                    pts for pts in total_hole_pts if pts in boundary_pts]
                # * Check 02 - If any of the hole is touching the boundary of the face
                # then mesh it
                if len(hole_pts_on_boundary) > 0:
                    print(
                        "The surface has holes that touch the boundary. \
                            It will be meshed")
                    faces.extend(brep_to_face3d(brep))
                else:
                    lb_face = Face3D(boundary=boundary_pts, holes=hole_pts)
                    faces.append(lb_face)
    # If any of the above fails, mesh it
    except Exception as e:
        print(str(e) + "Face creation failed, this face will be meshed")
        faces.extend(brep_to_face3d(brep))

    return faces


def solid_to_face3d(brep):
    """Create a Ladybug Face3D object from a rhino3dm Brep.

    This function is used in translating rhino3dm solid volumes to Ladybug Face3D
    objects.

    Args:
        brep: A rhino3dm Brep.

    Returns:
        A list of Ladybug Face3D objects.
    """
    faces = []
    for i in range(len(brep.Faces)):
        mesh = brep.Faces[i].GetMesh(rhino3dm.MeshType.Any)
        faces.extend(mesh_to_face3d(mesh))

    return faces


def extrusion_to_face3d(extrusion):
    """Create a Ladybug Face3D object from a rhino3dm Extrusion.

    Args:
        brep: A rhino3dm Extrusion.

    Returns:
        A list of Ladybug Face3D objects.
    """
    faces = []
    mesh = extrusion.GetMesh(rhino3dm.MeshType.Any)
    faces.extend(mesh_to_face3d(mesh))

    return faces


def to_face3d(obj, *, tolerance, raise_exception=True):
    """Convert Rhino objects to Ladybug Face3D objects.

    Supported object types are Brep, Extrusion and Meshes. If raise_exception is set to
    True this method will raise a ValueError for unsupported object types.

    Args:
        obj: A Rhino object.
        tolerance: A number for tolerance value. Tolerance will only be used for
            converting mesh geometries.
        raise_exception: A Boolean to raise an exception for unsupported object types.
            default is True.

    Returns:
        A list of Ladybug Face3D.

    Raises:
        ValueError if object type is not supported and raise_exception is set to True.

    """
    rh_geo = obj.Geometry

    if rh_geo.ObjectType == rhino3dm.ObjectType.Brep:
        if rh_geo.IsSolid:
            lb_face = solid_to_face3d(rh_geo)
        else:
            lb_face = brep2d_to_face3d(rh_geo, tolerance)

    elif rh_geo.ObjectType == rhino3dm.ObjectType.Extrusion:
        lb_face = extrusion_to_face3d(rh_geo)

    elif rh_geo.ObjectType == rhino3dm.ObjectType.Mesh:
        lb_face = mesh_to_face3d(rh_geo)
    else:
        if raise_exception:
            raise ValueError(f'Unsupported object type: {rh_geo.ObjectType}')
        warnings.warn(f'Unsupported object type: {rh_geo.ObjectType}')
        lb_face = []

    return lb_face
