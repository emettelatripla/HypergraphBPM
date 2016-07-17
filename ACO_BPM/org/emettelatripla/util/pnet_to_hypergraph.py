'''
Created on Jul 6, 201

Translates Petri net into Hypergraph
Works with PNML Petri nets extracted from ProM

@author: UNIST
'''
import logging
import xml.etree.ElementTree as ET
from halp.directed_hypergraph import DirectedHypergraph
from halp.utilities.directed_graph_transformations import to_networkx_digraph
import matplotlib.pyplot as plt
import networkx as nx
from org.emettelatripla.aco.ACO_util import *
from org.emettelatripla.util.util import *
from networkx.classes.digraph import DiGraph
from networkx.classes.digraph import Graph
from org.emettelatripla.util import util
from org.emettelatripla.util.graph_space_interface import upload_graphspace

#setup the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

file_name = "C://BPMNexamples/review.pnml"

tree = ET.parse(file_name)
pnet = tree.getroot()

print(pnet.tag)

# places = pnet.findall("./net/page/place")
# 
# for place in places:
#     logger.info("Found new place: "+str(place.attrib['id']))
#     
transitions = pnet.findall("./net/page/transition")
# 
for transition in transitions:
    name = transition.find("./name/text").text
    logger.info("Found new Transition: "+str(transition.attrib['id'])+" NAME: "+name)
     
# arcs = pnet.findall("./net/page/arc")
# 
# for arc in arcs:
#     id = str(arc.attrib['id'])
#     source = str(arc.attrib['source'])
#     target = str(arc.attrib['target'])
#     logger.info("Found new arc --- ID: "+id+" SOURCE: "+source+" TARGET: "+target)


    

# =====================
# Some useful functions to process pnml
# ====================

def get_element(id):
    return pnet.find("./net/page/*[@id='"+id+"']")

def get_places(pnet):
    return pnet.findall("./net/page/place")

def get_transitions(pnet):
    return pnet.findall("./net/page/transition")

def get_arcs(pnet):
    return pnet.findall("./net/page/arc")

def get_transition_name(t):
    return t.find("./name/text").text

def get_id(element):
    return element.attrib['id']

def get_arc_source(arc):
    return arc.attrib['source']

def get_arc_target(arc):
    return arc.attrib['target']

def get_incoming_arcs(element):
    t_id = get_id(element)
    inc_arcs = pnet.findall("./net/page/arc[@target='"+t_id+"']")
    return inc_arcs

def get_outgoing_arcs(element):
    t_id = get_id(element)
    inc_arcs = pnet.findall("./net/page/arc[@source='"+t_id+"']")
    return inc_arcs


#============================

#Main procedure to convert pnet in hypergraph
#This works only if there are no xor split/join in the Petri net!!!
def convert_pnet_to_hypergraph_andgatewayonly(pnet):
    hg = DirectedHypergraph()
    #scan all transitions and create hyperedges
    transitions = get_transitions(pnet)
    for transition in transitions:
        #get all incoming arcs, the source of these become the tail of hyperedge
        inc_arcs = get_incoming_arcs(transition)
        tail = []
        for inc_arc in inc_arcs:
            source = str(get_arc_source(inc_arc))
            tail.append(source)
        #get all outgoing arcs, the target of these become the head of the hyperedge
        out_arcs = get_outgoing_arcs(transition)
        head = []
        for out_arc in out_arcs:
            target = str(get_arc_target(out_arc))
            head.append(target)
        name = get_transition_name(transition)
        hg.add_hyperedge(tail, head, name = name, phero = 0.0, cost = 0.4, avail = 0.6, qual = 0.2, time = 0.99)
    #print the result before exit
    print_hg_std_out_only(hg)
    return hg

def convert_pnet_to_hypergraph(pnet):
    """ Convert a Petri net (in pnml format) into a hypergraph (Halp format) """
    hg = DirectedHypergraph()
    transitions = get_transitions(pnet)
    places = get_places(pnet)
    """STEP 1: Pre-process places to find xor places (splits and joints)
    If input/output of a transitions is 2 or more places, then mark those places as "X" and put in hypergraph"""
    for place in places:
        inc_arcs = get_incoming_arcs(place)
        out_arcs = get_outgoing_arcs(place)
        isSink = False
        isSource = False
        if len(inc_arcs) > 1:
            #create node for place in hypergraph
            node_id = get_id(place)
            #check if join is end event (sink)
            if (len(out_arcs) == 0):
                isSink = True
            logger.info("STEP 1 - Creating xor-join node -- {0}".format(node_id))
            hg.add_node(node_id, source = isSource, sink = isSink, type = 'xor-join')
            head = []
            head.append(node_id)
            isSink = False
            isSource = False
            #create node for all source of incoming arcs
            for arc in inc_arcs:
                node_id2 = get_id(get_element(get_arc_source(arc)))
                node_name = get_transition_name(get_element(get_arc_source(arc)))
                logger.info("STEP 1 - Creating transition node -- {0} -- {1}".format(node_id, node_name))
                hg.add_node(node_name, source = isSource, sink = isSink, type = 'transition', name = node_name)
                tail = []
                tail.append(node_name)
                #create hyperedge
                logger.info("STEP 1 - Creating hyperedge from {0} to {1}".format(str(tail), str(head)))
                hg.add_hyperedge(tail, head, name = " ", phero = 0.0, cost = 0.4, avail = 0.6, qual = 0.2, time = 0.99)
        if len(out_arcs) > 1:
            node_id = get_id(place)
            #create node for place in hypergraph (if it does not exist already)
            tail = []
            tail.append(node_id)
            if(not hg.has_node(node_id)):
                #check if source (start event)
                if (len(inc_arcs) == 0):
                    isSource = True
                logger.info("STEP 1 - Creating xor-split node -- {0}".format(node_id))
                hg.add_node(node_id, source = isSource, sink = isSink, type = 'xor-split')
                #create node for all targets of outgoing arcs
                isSink = False
                isSource = False
                for arc in out_arcs:
                    node_id2 = get_id(get_element(get_arc_target(arc)))
                    node_name = get_transition_name(get_element(get_arc_target(arc)))
                    if(not hg.has_node(node_id2)):
                        logger.info("STEP 1 - Creating transition node -- {0} -- {1}".format(node_id, node_name))
                        hg.add_node(node_name, source = isSource, sink = isSink, type = 'transition', name = node_name)
                    head = []
                    head.append(node_name)
                    #create hyperedge
                    logger.info("STEP 1 - Creating hyperedge from {0} to {1}".format(str(tail), str(head)))
                    hg.add_hyperedge(tail, head, name = " ", phero = 0.0, cost = 0.4, avail = 0.6, qual = 0.2, time = 0.99)
    """ STEP2 : Process each transition """
    for transition in transitions:
        logger.info("######## Processing transition {0}".format(get_transition_name(transition)))
        isSink = False
        isSource = False
        #check if transition is not a node in hg and add if needed
        if (not hg.has_node(get_transition_name(transition))):
            #check if transition is start
            inc_arcs = get_incoming_arcs(transition)
            for inc_arc in inc_arcs:
                source_place = get_element(get_arc_source(inc_arc))
                place_inc = get_incoming_arcs(source_place)
                if not place_inc:
                    isSource = True
            #check if trsnasition is end event
            out_arcs = get_outgoing_arcs(transition)
            for out_arc in out_arcs:
                sink_place = get_element(get_arc_target(out_arc))
                place_out = get_outgoing_arcs(sink_place)
                if not place_out:
                    isSink = True
            #create node in hypergraph
            logger.info("STEP 2 - Creating transition node")
            hg.add_node(get_transition_name(transition), source = isSource, sink = isSink, type = 'transition', name = get_transition_name(transition))
        #look BACKWARD 
        if not isSource:
            inc_arcs = get_incoming_arcs(transition)
            tail = []
            x_head = [get_transition_name(transition)]
            xplace_list = []
            otherp_list = []
            xplace_tail = []
            for inc_arc in inc_arcs:
                place = get_element(get_arc_source(inc_arc))
                #separate xor places from other forward places of this transition
                if(hg.has_node(get_id(place))):
                    xplace_list.append(place)
                    xplace_tail.append(get_id(place))
                else:
                    otherp_list.append(place)
                #create forward hyperedge to possibly multiple xor nodes
            he_from_xors_needed = False
            for place in xplace_tail:
                temp_tail = []
                temp_tail.append(place)
                if(not hg.has_hyperedge(temp_tail,x_head)):
                    he_from_xors_needed = True
            if(he_from_xors_needed):    
                logger.info("STEP 2 - Creating backward hyperedge to (multiple) xor - TAIL {0} -- HEAD {1} ".format(str(xplace_tail),str(x_head)))
                hg.add_hyperedge(xplace_tail, x_head, name = " ", phero = 0.0, cost = 0.4, avail = 0.6, qual = 0.2, time = 0.99)
                #create forward normal hyperdge
            tail = []
#             for place in otherp_list:
#                 inc_arcs_l2 = get_incoming_arcs(place)
#                 for inc_arc_l2 in inc_arcs_l2:
#                     trans2 = get_element(get_arc_source(inc_arc_l2))
#                     tail.append(get_transition_name(trans2))
#             if(tail):
#                 logger.info("STEP 2 - Creating real backward  hyperedge - TAIL {0} -- HEAD {1} ".format(str(tail),str(x_head)))
#                 hg.add_hyperedge(tail, x_head, name = " ", phero = 0.0, cost = 0.4, avail = 0.6, qual = 0.2, time = 0.99)
        #look FORWARD
        if not isSink:
            out_arcs = get_outgoing_arcs(transition)
            head = []
            x_tail = [get_transition_name(transition)]
            xplace_list = []
            otherp_list = []
            xplace_head = []
            for out_arc in out_arcs:
                place = get_element(get_arc_target(out_arc))
                #separate xor places from other forward places of this transition
                if(hg.has_node(get_id(place))):
                    xplace_list.append(place)
                    xplace_head.append(get_id(place))
                else:
                    otherp_list.append(place)
                #create forward hyperedge to possibly multiple xor nodes
            he_to_xors_needed = False
            for place in xplace_head:
                temp_head = []
                temp_head.append(place)
                if(not hg.has_hyperedge(x_tail,temp_head)):
                    he_to_xors_needed = True
            if(he_to_xors_needed):
                logger.info("STEP 2 - Creating forward hyperedge to (multiple) xor - TAIL {0} -- HEAD {1} ".format(str(x_tail),str(xplace_head)))
                hg.add_hyperedge(x_tail, xplace_head, name = " ", phero = 0.0, cost = 0.4, avail = 0.6, qual = 0.2, time = 0.99)
                #create forward normal hyperdge
            head = []
            for place in otherp_list:
                out_arcs_l2 = get_outgoing_arcs(place)
                for out_arc_l2 in out_arcs_l2:
                    trans2 = get_element(get_arc_target(out_arc_l2))
                    head.append(get_transition_name(trans2))
            if(head):
                logger.info("STEP 2 - Creating real forward  hyperedge - TAIL {0} -- HEAD {1} ".format(str(x_tail),str(head)))
                hg.add_hyperedge(x_tail, head, name = " ", phero = 0.0, cost = 0.4, avail = 0.6, qual = 0.2, time = 0.99)
    """ POST-PROCESSING of tau-split, tau-join nodes (in pnets created from inductive miner"""
    # tau-from-tree nodes don't have to be processed?
    # TO BE COMPLETED
    # TO BE COMPLETED
    return hg


hg = convert_pnet_to_hypergraph(pnet)
print_hg(hg, "hyp_file.txt")


#hg = convert_pnet_to_hypergraph_andgatewayonly(pnet)
#print_hg(hg, "hyp_file.txt")

#convert hypergaph to directed graph
#dg = DiGraph()
#dg = to_networkx_digraph(hg)
#draw diected graph
#nx.draw(dg)
#plt.show()

#Upload to graphspace (doesn't work, but it prints json that can be uploaded :)
#upload_graphspace("mcomuzzi@unist.ac.kr", "Uniqlo4321", "test", dg, "test001", "hyp_file.json")



