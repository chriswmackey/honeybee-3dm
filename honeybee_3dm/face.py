"""Create Honeybee face objects(Face, Shade, Aperture, Door) from planar geometries
in a Rhino 3DM file."""

import warnings

# Importing core Honeybee & Ladybug Geometry dependencies
from honeybee.face import Face
from honeybee.shade import Shade
from honeybee.aperture import Aperture
from honeybee.door import Door
from honeybee.facetype import face_types
from honeybee.typing import clean_and_id_string, clean_string

# Importing dependencies from Honeybee-3dm package
from .togeometry import to_face3d
from .helper import filter_objects_by_layers


def import_faces(rhino3dm_file, tolerance=None):
    """Import Rhino planar geometry as Honeybee faces.

    This function looks up a rhino3dm file, converts the objects
    on the layer name "roof", "wall", "floor", "airwall", "shade", and  "aperture"
    to Honeybee objects, and writes them to a json file.

    Args:
        rhino3dm_file: A Rhino3DM file object.
        tolerance: A number for model tolerance. By default the tolerance is set to
            the ModelAbsoluteTolerance value in input 3DM file.

    Returns:
        A list of Honeybee faces.

    """
    hb_faces = []

    # TODO: Add an input to customize layer names
    # A Layer dictionary with layer name : (Honeybee face_type, Class) structure
    layer_to_hb_object = {
        'roof': (face_types.roof_ceiling, Face),
        'wall': (face_types.wall, Face),
        'floor': (face_types.floor, Face),
        'airwall': (face_types.air_boundary, Face),
        'shade': (None, Shade),
        'aperture': (None, Aperture),
        'door': (None, Door)
    }

    tolerance = tolerance or rhino3dm_file.Settings.ModelAbsoluteTolerance

    for layer in rhino3dm_file.Layers:
        if layer.Name not in layer_to_hb_object:
            warnings.warn(
                f'Object in layer "{layer.Name}" will be ignored during the process '
                'of importing faces.'
            )
            continue

    # get all the objects for valid layers
    layers = list(layer_to_hb_object.keys())
    objects_by_layer = filter_objects_by_layers(rhino3dm_file, layers)

    for layer, rhino_objects in zip(layers, objects_by_layer):

        hb_face_type, hb_face_module = layer_to_hb_object[layer]

        # for each rhino geometry gathered, Converting the Rhino3dm geometry
        # into a Ladybug Face3D objects
        for obj in rhino_objects:
            lb_faces = to_face3d(obj, tolerance=tolerance)
            name = obj.Attributes.Name
            for face_obj in lb_faces:
                # TODO: Double check with Chris if this naming works for energy models.
                # if name is assigned by user use the same name for all the sub faces
                # otherwise generate a randome name based on the layer name.
                obj_name = name or clean_and_id_string(layer)
                args = [clean_string(obj_name), face_obj]
                if hb_face_type:
                    args.append(hb_face_type)
                hb_face = hb_face_module(*args)
                hb_face.display_name = name

                hb_faces.append(hb_face)

    return hb_faces
