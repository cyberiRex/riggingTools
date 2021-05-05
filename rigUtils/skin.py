import maya.api.OpenMaya as oM
import maya.api.OpenMayaAnim as oMa
import maya.cmds as mc
from contextlib import contextmanager
import os
import json
import sys

# todo: reduce data file size by removing 0 weights and recreating them in setWeights process


def export_skin(path=None, node=None):
    """
    Exports skin data
    :param path: full path of json file
    :param node: skinned node name
    :return:
    """
    data_dict = None
    if not node:
        node = mc.ls(sl=True)[0]

    if not mc.ls(node):
        mc.warning("'{}' skipped. Cannot be found in the scene".format(node))
    else:
        # If layered system is used and orig shape has connections
        orig_connections = __check_orig_connections(node=node)
        if orig_connections:
            with disconnect_attributes_context(connections=orig_connections):
                data_dict = __get_data(node=node)
        else:
            data_dict = __get_data(node=node)
        if data_dict:
            __save_data(data_dict=data_dict, path=path)


def import_skin(path=None):
    """
    Exports skin data
    :param path: full path of json file
    :return:
    """
    data_dict = __load_data(path=path)
    node = __get_object_name(data_dict)
    if not mc.ls(node):
        mc.warning("'{}' skipped. Cannot be found in the scene".format(node))
    else:
        __set_data(data_dict=data_dict)


def __set_data(data_dict=None):
    compressed = False
    skin_cluster = None
    if data_dict["skin_data_format"] == "compressed":
        compressed = True

    object_name = __get_object_name(data_dict)
    shape = __get_skin_cluster_data(object_name)[1].name()
    # Check vertex num
    object_vertex_num = mc.polyEvaluate(shape, vertex=True)

    if compressed:
        imported_obj_vertex_num = data_dict["vertex_count"]
    else:
        imported_obj_vertex_num = len(data_dict["blend_weights"])
    if not imported_obj_vertex_num == object_vertex_num:
        mc.warning("Vertex does not match on {}".format(object_name))

    if __get_skin_cluster_data(object_name)[0]:
        skin_cluster = __get_skin_cluster_data(object_name)[0].name()
    else:
        joints = data_dict["influences"]
        try:
            skin_cluster_name = data_dict["skin_cluster_name"]
            skin_cluster = mc.skinCluster(joints, object_name,
                                          toSelectedBones=True,
                                          normalizeWeights=1,
                                          name=skin_cluster_name,
                                          )
        except Exception as e:
            missing_joints = list()
            for i in joints:
                if not mc.ls(i):
                    missing_joints.append(i)
            if missing_joints:
                mc.warning("Missing joints{} for {} {}".format(missing_joints, object_name, e))
    if skin_cluster:
        # If layered system is used and orig shape has connections
        orig_connections = __check_orig_connections(object_name)
        if orig_connections:
            with disconnect_attributes_context(connections=orig_connections):
                __set_skin_cluster_data(data_dict)
        else:
            __set_skin_cluster_data(data_dict)
        sys.stdout.write("Imported skin data for {}".format(object_name))


def __set_skin_cluster_data(data_dict=None):
    """
    Sets weights and attributes on skim cluster node
    :param data_dict: data dictionary
    :return:
    """
    node_name = __get_object_name(data_dict)

    skin = __get_skin_cluster_data(node_name)[0]
    dag_path = __get_dag_path(node_name)
    components = __get_components(__get_shape_objects(node_name))
    indices = oM.MIntArray(range(len(data_dict["influences"])))
    weights = oM.MDoubleArray(data_dict["weights"])
    blend_weights = oM.MDoubleArray(data_dict["blend_weights"])

    use_components = data_dict["use_components"]
    skinning_method = data_dict["skinning_method"]
    dqs_support_non_rigid = data_dict["dqs_support_non_rigid"]
    deform_user_normals = data_dict["deform_user_normals"]
    component_tag = data_dict["component_tag"]

    mc.setAttr("{0}.{1}".format(skin.name(), "skinningMethod"), skinning_method)
    mc.setAttr("{0}.{1}".format(skin.name(), "deformUserNormals"), deform_user_normals)
    mc.setAttr("{0}.{1}".format(skin.name(), "useComponents"), use_components)
    mc.setAttr("{0}.{1}".format(skin.name(), "dqsSupportNonRigid"), dqs_support_non_rigid)
    if mc.objExists("{0}.{1}".format(skin.name(), "input[0].componentTagExpression")):
        mc.setAttr("{0}.{1}".format(skin.name(), "input[0].componentTagExpression"), component_tag, type="string")

    skin.setWeights(dag_path, components, indices, weights)
    if blend_weights:
        skin.setBlendWeights(dag_path, components, blend_weights)


def __get_data(node=None):
    """
    Collects needed data and creates data_dict dictionary
    :param node: skinned object name
    :return:
    """
    data_dict = None
    skin_fn = __get_skin_cluster_data(node)[0]
    shape = __get_skin_cluster_data(node)[1]
    skinning_method = __get_skin_cluster_data(node)[2]
    use_components = __get_skin_cluster_data(node)[3]
    deform_user_normals = __get_skin_cluster_data(node)[4]
    support_non_rigid_transformations = __get_skin_cluster_data(node)[5]
    component_tag = __get_skin_cluster_data(node)[6]

    if not skin_fn:
        mc.warning("{} object does not has skin cluster".format(node))
    else:
        source_mesh_dp = __get_dag_path(str(shape.fullPathName()))
        components = __get_components(shape)

        weights, influence_count = skin_fn.getWeights(source_mesh_dp, components)
        blend_weights = skin_fn.getBlendWeights(source_mesh_dp, components)
        joint_names = [x.fullPathName().rpartition("|")[2] for x in skin_fn.influenceObjects()]
        component_count = 0
        name_space = node.rpartition(":")[0]
        if name_space:
            name = node.rpartition(":")[2]
        else:
            name = node
        data_dict = {
            "skin_data_format": "compressed",
            "name_space": name_space,
            "weights": [],
            "object_name": name,
            "blend_weights": [],
            "vertex_count": 0,
            "influences": [],
            "component_tag": component_tag,
            "skin_cluster_name": "{}_SKN".format(node.rpartition(":")[2]),
            "use_components": use_components,
            "deform_user_normals": deform_user_normals,
            "skinning_method": skinning_method,
            "dqs_support_non_rigid": support_non_rigid_transformations

        }

        # todo: add nurbs surface and curve support
        if shape.type() == 267:
            component_count = shape.numCVs
        if shape.type() == 296:
            component_count = shape.numVertices

        data_dict["weights"] = [x for x in weights]
        # Check i blend weights are not 0
        blend_weights = [x for x in blend_weights]
        if not all(x == 0.0 for x in blend_weights):
            data_dict["blend_weights"] = blend_weights
        data_dict["vertex_count"] = component_count
        data_dict["influences"] = joint_names

    return data_dict


def __save_data(data_dict=None, path=None):
    """
    Saves data to file
    :param data_dict: Dictionary with skin data
    :param path: Path to save json file
    :return:
    """

    __save_json(path=path, save_dict=data_dict)
    sys.stdout.write("Saving file '{0}'".format(path))


def __load_data(path=None):
    data_dict = __load_json(path)
    if data_dict:
        sys.stdout.write("Loading skin data file '{0}'".format(os.path.basename(path)))
    return data_dict


def __get_shape_objects(node=None):
    """
    Gets shape nodes
    :param node: transform name
    :return: shape FN
    """
    shape = None
    # Get transforms and shapes of selected objects in the scene
    mesh_item = oM.MGlobal.getSelectionListByName(node)
    transform = mesh_item.getDagPath(0)
    shape_type = mc.nodeType(mc.listRelatives(node, children=True)[0])
    if shape_type == "mesh":
        shape = oM.MFnMesh(transform)
    if shape_type == "nurbsCurve":
        shape = oM.MFnNurbsCurve(transform)
        sys.stdout.write("Nurbs cure are not supported yet. Skipping")
        return
    if shape_type == "nurbsSurface":
        shape = oM.MFnNurbsSurface(transform)
        sys.stdout.write("Nurbs surfaces are not supported yet. Skipping")
        return

    return shape


def __get_dag_path(object_name=None):
    """
    This function returns full dag path of the object
    :param object_name: name of object
    :return: full dag path
    """
    obj = oM.MGlobal.getSelectionListByName(object_name)
    return obj.getDagPath(0)


def __get_components(shape_object=None):
    """
    This function returns vertex component data
    :param shape_object: poly shapes Fn
    :return: mesh component data
    """
    # todo: add nurbs surface and curve support
    current_components = oM.MFnSingleIndexedComponent()
    components_object = current_components.create(oM.MFn.kMeshVertComponent)
    if shape_object.type() == 296:
        current_components.setCompleteData(shape_object.numVertices)
    if shape_object.type() == 267:
        current_components.setCompleteData(shape_object.numCVs)
    return components_object


def __get_skin_cluster_data(node=None):
    """
    Get Skin cluster info
    :param node: object name
    :return: skin FN objects and skinCluster attributes
    """

    skinning_method = None
    use_components = None
    deform_user_normals = None
    skin_fn = None
    component_tag = None
    support_non_rigid_transformations = None
    shape_fn = __get_shape_objects(node)

    m_selection_list = oM.MSelectionList()
    m_selection_list.add(shape_fn.fullPathName())
    shape_object = m_selection_list.getDependNode(0)
    dg_iterator = oM.MItDependencyGraph(shape_object,
                                        oM.MItDependencyGraph.kDownstream,
                                        oM.MItDependencyGraph.kPlugLevel)
    while not dg_iterator.isDone():
        current_item = dg_iterator.currentNode()
        if current_item.hasFn(oM.MFn.kSkinClusterFilter):
            skin_fn = oMa.MFnSkinCluster(current_item)
            # In case of multi deformers on mesh, check if skin cluster's output geometry.
            geometry_mo_array = skin_fn.getOutputGeometry()
            for i in geometry_mo_array:
                mdp_node = oM.MDagPath()
                if str(mdp_node.getAPathTo(i)) == str(shape_fn.name()):
                    skinning_method = mc.getAttr(skin_fn.name() + '.skinningMethod')
                    use_components = mc.getAttr(skin_fn.name() + '.useComponents')
                    deform_user_normals = mc.getAttr(skin_fn.name() + '.deformUserNormals')
                    support_non_rigid_transformations = mc.getAttr(skin_fn.name() + '.dqsSupportNonRigid')
                    if mc.objExists(skin_fn.name() + ".input[0].componentTagExpression"):
                        component_tag = mc.getAttr(skin_fn.name() + ".input[0].componentTagExpression")
                    break
        dg_iterator.next()

    return [skin_fn, shape_fn, skinning_method, use_components, deform_user_normals,
            support_non_rigid_transformations, component_tag]


def __get_no_intermediate_shape(node=None):
    """
    Gets mesh shape that is not intermediateObject
    :param node: mesh transform name
    :return: shape name
    """
    children = mc.listRelatives(node, children=True)
    if children:
        for i in children:
            if mc.nodeType(i) == "mesh":
                if not mc.getAttr(i + ".intermediateObject"):
                    return i


def __get_object_name(data_dict=None):
    """
    Get object name based on namespace
    :param data_dict: skin data dictionary
    :return: name of the skinned object
    """
    name_space = data_dict["name_space"]
    if name_space:
        node_name = "{}:{}".format(name_space, data_dict["object_name"])
    else:
        node_name = data_dict["object_name"]

    return node_name


def __check_orig_connections(node=None):
    """
    If layered skin is used in workflow.
    Check if orig node has inMesh connection
    :param node: mesh transform name
    :return:
    """
    connections = None
    relatives = mc.listRelatives(node, children=True)
    if relatives:
        originals = [x for x in relatives if mc.getAttr("{}.{}".format(x, "intermediateObject"))]
        for i in originals:
            relation = mc.listConnections("{}.{}".format(i, "worldMesh[0]"), connections=True)
            if relation and mc.nodeType(relation[1]) == "groupParts":
                connections = mc.listConnections("{}.{}".format(i, "inMesh"), connections=True, destination=True,
                                                 plugs=True)

    return connections


def __load_json(path):
    with open(path) as json_file:
        data = json.load(json_file)
    return data


def __save_json(path, save_dict):
    with open(path, "w") as json_file:
        json.dump(save_dict, json_file, indent=4)


@contextmanager
def disconnect_attributes_context(connections=None):
    disconnect_attribute(connections=connections)
    yield
    connect_attribute(connections=connections)


def disconnect_attribute(connections=None):
    mc.disconnectAttr(connections[1], connections[0])
    return True


def connect_attribute(connections=None):
    mc.connectAttr(connections[1], connections[0])
    return True
