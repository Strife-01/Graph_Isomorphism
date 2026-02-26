"""
Includes functions for reading and writing graphs, in a very simple readable format.
"""
import sys
import colorsys
import xml.etree.ElementTree as ET
from typing import IO, Tuple, List, Union, Any
from collections import defaultdict
from graph import Graph, Edge


# GraphML settings
COLORBLIND_MODE = False  # Start with variations in value and saturation rather than hue
TYPE_TO_STRING = {str: 'string', int: 'int', bool: 'bool', float: 'float'}
DEFAULT_ATTRIBUTES_GRAPHML = {'node': {'color': 'light gray', 'label': str, 'size': 30}, 'edge': {'color': 'black'}}

# Dot settings
NUM_COLORS = 12  # Make combinations of fillcolor and edgecolor in order to get more distinct nodes
USE_GRAPHML_COLORS = False  # Overwrite the .dot file color scheme by the graphML color scheme.
DEFAULT_ATTRIBUTES_DOT = {'node': {'penwidth': 1 if USE_GRAPHML_COLORS else 4, 'label': str, 'color': str, 'width': .5,
                                   'height': .5, 'margin': .05, 'style': 'filled', 'colorscheme': 'paired12'},
                          'edge': {'penwidth': 2}}


def num_to_color(n: int) -> str:
    """
    Converts natural numbers to colors such that numbers that are close together map to distinguishable colors.
    :param n: Natural number
    :return: Color in hex format as a string
    """
    n = int(n)
    sv_combs = [(0.8, 1), (0.2, 1), (0.8, 0.7)]

    if COLORBLIND_MODE:
        s, v = sv_combs[n % len(sv_combs)]
        hue_6 = (n//len(sv_combs)) % 6
    else:
        hue_6 = n % 6
        s, v = sv_combs[(n//6) % len(sv_combs)]

    n //= 6 * len(sv_combs)

    hue_rem = bin(n)[:1:-1]
    hue_frac = int(hue_rem, 2) / (1 << len(hue_rem))
    h = 1 - (hue_6 + hue_frac) / 6

    (r, g, b) = colorsys.hsv_to_rgb(h, s, v)
    (r, g, b) = (round(255*r), round(255*g), round(255*b))

    return f'#{r:02x}{g:02x}{b:02x}'


def read_line(f: IO[str]) -> str:
    """
    Read a single non-comment line from a file
    :param f: The file
    :return: The line
    """
    line = f.readline()

    while len(line) > 0 and line[0] == '#':
        line = f.readline()

    return line


def read_graph(graphclass, f: IO[str]) -> Tuple[Graph, bool]:
    """
    Read a graph from a file
    :param graphclass: The class of the graph
    :param f: The file
    :return: The graph
    """
    while True:
        try:
            line = read_line(f)
            n = int(line)
            graph = graphclass(directed=False, n=n)
            break
        except ValueError:
            pass

    line = read_line(f)
    edges = []

    try:
        while True:
            comma = line.find(',')
            if ':' in line:
                colon = line.find(':')
                edges.append((int(line[:comma]), int(line[comma + 1:colon]), int(line[colon + 1:])))
            else:
                edges.append((int(line[:comma]), int(line[comma + 1:]), None))
            line = read_line(f)
    except:
        pass

    indexed_nodes = list(graph.vertices)

    for edge in edges:
        graph += Edge(indexed_nodes[edge[0]], indexed_nodes[edge[1]], edge[2])

    if line and line[0] == '-':
        return graph, True
    else:
        return graph, False


def read_graph_list(graph_class, f: IO[str]) -> List[Graph]:
    """
    Read a list of graphs from a file
    :param graph_class: The graph class
    :param f: The file
    :return: A list of graphs
    """
    graphs = []
    cont = True

    while cont:
        graph, cont = read_graph(graph_class, f)
        graphs.append(graph)

    return graphs


def load_graph(f: IO[str], graph_class=Graph, read_list: bool = False) -> Union[List[Graph], Graph]:
    """
    Load a graph from a file
    :param f: The file
    :param graph_class: Class of the graph. You may subclass the default graph class and add your own here.
    :param read_list: Specifies whether to read a list of graphs from the file, or just a single graph.
    :return: The graph, or a list of graphs.
    """
    if read_list:
        graph_list = read_graph_list(graph_class, f)
        return graph_list
    else:
        graph, _ = read_graph(graph_class, f)
        return graph


def input_graph(graph_class=Graph, read_list: bool = False) -> Union[Tuple[List[Graph], List[str]], Graph]:
    """
    Load a graph from sys.stdin
    :param graph_class: The class of the graph. You may subclass the default graph class and add your own here.
    :param read_list: Specifies whether to read a list of graphs from the file, or just a single graph.
    :return: The graph, or a list of graphs.
    """
    return load_graph(f=sys.stdin, graph_class=graph_class, read_list=read_list)


def write_line(f: IO[str], line: str):
    """
    Write a line to a file
    :param f: The file
    :param line: The line
    """
    f.write(line + '\n')


def write_graph_list(graph_list: List[Graph], f: IO[str]):
    """
    Write a graph list to a file.
    :param graph_list: List of graphs
    :param f: The file
    """
    for i, g in enumerate(graph_list):
        n = len(g)
        write_line(f, '# Number of vertices:')
        write_line(f, str(n))

        # Give the vertices (temporary) labels from 0 to n-1:
        label = {}
        for vertex_index, vertex in enumerate(g):
            label[vertex] = vertex_index

        write_line(f, '# Edge list:')

        for e in g.edges:
            if e.weight:
                write_line(f, str(label[e.tail]) + ',' + str(label[e.head]) + ':' + str(e.weight))
            else:
                write_line(f, str(label[e.tail]) + ',' + str(label[e.head]))

        if i + 1 < len(graph_list):
            write_line(f, '--- Next graph:')


def save_graph(graph_list: Union[Graph, List[Graph]], f: IO[str]):
    """
    Write a graph, or a list of graphs to a file.
    :param graph_list: The graph, or a list of graphs.
    :param f: The file
    """
    if type(graph_list) is list:
        write_graph_list(graph_list, f)
    else:
        write_graph_list([graph_list], f)


def print_graph(graph_list: Union[Graph, List[Graph]]):
    """
    Print a graph, or a list of graphs to sys.stdout
    :param graph_list: The graph, or list of graphs.
    """
    if type(graph_list) is list:
        write_graph_list(graph_list, sys.stdout)
    else:
        write_graph_list([graph_list], sys.stdout)


def get_attribute_value(attribute: str, obj, dict_or_default_or_type):
    """
    Helper function for the write_graphml and write_dot functions. Tries to determine whether obj has a given attribute.
    :param attribute:
    :param obj:
    :param dict_or_default_or_type:
    :return:
    """
    if isinstance(dict_or_default_or_type, dict):
        if obj in dict_or_default_or_type:
            return dict_or_default_or_type[obj]
        else:
            return None
    elif hasattr(obj, attribute):
        return getattr(obj, attribute)
    elif type(dict_or_default_or_type) is type:
        return None
    return dict_or_default_or_type


def write_graphml(graph: Graph, f: IO[str], node_attributes: dict[str, Any] = None,
                  edge_attributes: dict[str, Any] = None):
    """
    Writes a graph to a .graphML file. Look at the documentation of write_visualization for more information.

    :param graph: The graph
    :param f: The file
    :param node_attributes: Optional node attributes to write to the file
    :param edge_attributes: Optional edge attributes to write to the file
    """

    if node_attributes is None:
        node_attributes = {}
    else:
        node_attributes = node_attributes.copy()
    if edge_attributes is None:
        edge_attributes = {}
    else:
        edge_attributes = edge_attributes.copy()

    for attribute, default in DEFAULT_ATTRIBUTES_GRAPHML['node'].items():
        if attribute not in node_attributes:
            node_attributes[attribute] = default

    for attribute, default in DEFAULT_ATTRIBUTES_GRAPHML['edge'].items():
        if attribute not in edge_attributes:
            edge_attributes[attribute] = default

    root = ET.Element('graphML')

    object_attribute_to_key = defaultdict(lambda: 'd'+str(len(object_attribute_to_key)))

    for object_type, object_attributes in [('node', node_attributes), ('edge', edge_attributes)]:
        for attribute in object_attributes:
            if attribute == 'color' and object_type == 'node':
                attribute_type = str
            elif isinstance(object_attributes[attribute], dict):
                attribute_type = type(next(iter(object_attributes[attribute].values())))
            elif type(object_attributes[attribute]) is type:
                attribute_type = object_attributes[attribute]
            else:
                attribute_type = type(object_attributes[attribute])

            if not any(isinstance(attribute, t) for t in TYPE_TO_STRING):
                raise ValueError(f"Attributes may only have type int, bool, str or float, not {type(attribute_type)}")

            ET.SubElement(root, 'key', {'id': object_attribute_to_key[(object_type, attribute)],
                                        'for': object_type,
                                        'attr.name': attribute,
                                        'attr.type': TYPE_TO_STRING[attribute_type]})

    edgedefault = 'directed' if graph.directed else 'undirected'
    graph_obj = ET.SubElement(root, 'graph', {'id': str(id(graph)), 'edgedefault': edgedefault})

    for v in graph:
        node = ET.SubElement(graph_obj, 'node', {'id': str(id(v))})

        for attribute in node_attributes:
            value = get_attribute_value(attribute, v, node_attributes[attribute])
            if value is None:
                continue
            if attribute == 'color' and isinstance(value, int):
                value = num_to_color(value)

            nc = ET.SubElement(node, 'data', {'key': object_attribute_to_key[('node', attribute)]})
            nc.text = str(value)

    for e in graph.edges:
        edge = ET.SubElement(graph_obj, 'edge', {'source': str(id(e.tail)), 'target': str(id(e.head))})

        for attribute in edge_attributes:
            value = get_attribute_value(attribute, e, edge_attributes[attribute])
            if value is None:
                continue

            nc = ET.SubElement(edge, 'data', {'key': object_attribute_to_key[('edge', attribute)]})
            nc.text = str(value)

    ET.indent(root)
    s = ET.tostring(root, encoding='unicode')
    f.write(s)


def write_dot(graph: Graph, f: IO[str], node_attributes: dict[str, Any] = None,
              edge_attributes: dict[str, Any] = None):
    """
    Writes a graph to a .dot file. Look at the documentation of write_visualization for more information.

    :param graph: The graph
    :param f: The file
    :param node_attributes: Optional node attributes to write to the file
    :param edge_attributes: Optional edge attributes to write to the file
    """

    if node_attributes is None:
        node_attributes = {}
    else:
        node_attributes = node_attributes.copy()
    if edge_attributes is None:
        edge_attributes = {}
    else:
        edge_attributes = edge_attributes.copy()

    for attribute, default in DEFAULT_ATTRIBUTES_DOT['node'].items():
        if attribute not in node_attributes:
            node_attributes[attribute] = default

    for attribute, default in DEFAULT_ATTRIBUTES_DOT['edge'].items():
        if attribute not in edge_attributes:
            edge_attributes[attribute] = default

    if graph.directed:
        f.write('digraph G {\n')
        edge_symbol = ' -> '
    else:
        f.write('graph G {\n')
        edge_symbol = ' -- '

    f.write('node [')

    for attribute, default in DEFAULT_ATTRIBUTES_DOT['node'].items():
        if not isinstance(default, dict) and not type(default) is type:
            if isinstance(default, str):
                f.write(f'{attribute}="{default}",')
            else:
                f.write(f'{attribute}={str(default)},')

    f.write(']\nedge [')
    for attribute, default in DEFAULT_ATTRIBUTES_DOT['edge'].items():
        if not isinstance(default, dict) and not type(default) is type:
            if isinstance(default, str):
                f.write(f'{attribute}="{default}",')
            else:
                f.write(f'{attribute}={str(default)},')

    f.write(']\n')

    v_to_name = defaultdict(lambda: len(v_to_name))

    for v in graph:
        f.write(f'{v_to_name[v]} [')
        for attribute in node_attributes:
            value = get_attribute_value(attribute, v, node_attributes[attribute])
            if value is None or value is node_attributes[attribute]:
                continue
            if attribute == 'color' and isinstance(value, int):
                if USE_GRAPHML_COLORS:
                    f.write(f'fillcolor="{num_to_color(value)}",')
                    continue
                if value > NUM_COLORS:
                    fillcolor = (value // NUM_COLORS) % NUM_COLORS + 1
                    f.write(f'fillcolor={str(fillcolor)},')
                value = value % NUM_COLORS + 1
            if isinstance(value, str):
                f.write(f'{attribute}="{value}",')
            else:
                f.write(f'{attribute}={value},')
        f.write(']\n')

    f.write('\n')

    for e in graph.edges:
        f.write(f'{v_to_name[e.tail]} {edge_symbol} {v_to_name[e.head]} [')
        for attribute in edge_attributes:
            value = get_attribute_value(attribute, e, edge_attributes[attribute])
            if value is None or value is edge_attributes[attribute]:
                continue
            if isinstance(value, str):
                f.write(f'{attribute}="{value}",')
            else:
                f.write(f'{attribute}={value},')

        f.write(']\n')

    f.write('}')


def write_visualization(graph: Graph, f: IO[str], node_attributes: dict[str, Any] = None,
                        edge_attributes: dict[str, Any] = None):
    """
    Writes a graph to the given file in .graphML or .dot format, matching the extension of the file.
    Optional attributes for the nodes and edges can be given in node_attributes and edge_attributes.

    Attributes can be given as a dict that maps vertices or edges to their corresponding values. Alternatively, it is
    possible to give a default value or type and look for the attributes by name in the vertex and edge objects.

    Example for node_attributes:

    node_attributes = {'color': {<v_1> : 1, <v_2> : 2, <v_4>: 1, ...}, # Only vertices in the dictionary get a value
                       'size': 30,  # Look for <v>.size, otherwise write a default value of 30
                       'weight': int  # Look for <v>.weight, otherwise do not write a value
                       }

    Depending on the file format, some attributes will be written by default from the DEFAULT_ATTRIBUTES_ constant.
    A list of attributes that might be used by .dot viewers can be found at https://graphviz.org/doc/info/attrs.html
    Gephi only uses the following graphML attributes by default for the visualization: 'label', 'color',
    'weight' (edges only) and 'x', 'y', 'z', 'size' for nodes only. Gephi cannot read the .dot files.

    :param graph: The graph
    :param f: The file
    :param node_attributes: Optional node attributes to write to the file
    :param edge_attributes: Optional edge attributes to write to the file
    """
    if f.name.endswith('.dot'):
        write_dot(graph, f, node_attributes, edge_attributes)
    elif f.name.endswith('.graphML'):
        write_graphml(graph, f, node_attributes, edge_attributes)
    else:
        raise ValueError(f"Writing visualizations is only supported for file extensions '.dot' and '.graphML', "
                         f"so {f.name} is invalid filename.")


if __name__ == "__main__":
    with open('examplegraph.gr') as file:
        G = load_graph(file, Graph)
        print(G)
