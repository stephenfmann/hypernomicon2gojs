# -*- coding: utf-8 -*-

import os
import logging
import json
import argparse
import copy
import webbrowser
from bs4 import BeautifulSoup as bs

## HTML Template filepath
## New HTML files will be copied from this one.
HTML_TEMPLATE = 'blockEditorTemplate.html'

## Configure display format
POSITION_FIGURE = "CreateRequest"

## Position IDs need to be distinct from arugment IDs.
## Offset argument IDs by this number.
## Should be robust unless you have more than this number of positions.
ARGUMENT_OFFSET = 10000
ARGUMENT_FIGURE = "RoundedRectangle" # default shape for argument nodes

def run(args):
    """
    The main run method.
    Convert Hypernomicon XML to GoJS JSON.

    Parameters
    ----------
    args : dict
        Input arguments. See arg parser declarations for details.

    Returns
    -------
    None.

    """
    
    ## Create log
    logging.Logger("Hypernomicon2GoJS")
    
    ## Parse the input
    try:
        nodes,links = parse_xml(args)
    except ValueError:
        logging.error("An error occurred while attempting to parse XML files.")
        return
    
    ## Create JSON
    json_object = create_json(nodes,links)
    
    ## Determine the true JSON filename.
    json_fpath = get_json_filepath(args)
    
    ## Fix the locations of known nodes and links
    json_object = fix_locations(json_object,json_fpath)
    
    ## Dump JSON
    output_json(json_object,json_fpath)
    
    ## Output HTML
    output_html(json_object,args['html'])
    
    ## Launch browser
    if args['launch']:launch_html(args['html'])
    

def parse_xml(args):
    """
    Get basic info on nodes and links from XML file.

    Parameters
    ----------
    fpath_xml : string
        Filepath location of XML file.

    Returns
    -------
    nodes : list
        GoJS format of nodes. Example:
            {"key":25,"loc":"0 0","text":"Interventionism"}
    links : list
        GoJS format of links between nodes. Example:
            {"from":25,"to":26}

    """
    
    ## DEBATES
    with open(args['debates'],'r',encoding='utf8') as f:
        xml_debates = bs(f.read(), features="xml")
    
    ## Sanity check
    if args['debate'] != 1 and not xml_debates.find("record",id=str(args['debate'])):
        logging.error("No debate found! Program will quit.")
        raise ValueError
    
    ## Recursively get all subdebate IDs under this debate
    debate_ids = get_all_descendant_debates([args['debate']],xml_debates)
    
    ## POSITIONS
    ## Load Positions XML
    with open(args['positions'],'r',encoding="utf8") as f:
        xml_positions = bs(f.read(), features="xml")
    
    ## Recursively get all position IDs under the listed debates.
    position_ids = get_all_descendant_positions(debate_ids,xml_positions)
    
    ## Extract the nodes 
    nodes_positions = get_nodes_positions(position_ids,xml_positions)
    
    ## Extract the links
    links_positions = get_links_positions(position_ids,xml_positions)
    
    ## ARGUMENTS
    ## Load Arguments XML
    with open(args['arguments'],'r',encoding="utf8") as f:
        xml_arguments = bs(f.read(), features="xml")
    
    ## Recursively get all argument IDs under the listed debates and positions.
    argument_ids = get_all_descendant_arguments(position_ids,xml_arguments)
        
    ## Extract the nodes 
    nodes_arguments = get_nodes_arguments(argument_ids,xml_arguments)
    
    ## Extract the links
    links_arguments = get_links_arguments(position_ids,argument_ids,xml_arguments)
    
    ## COMBINE
    nodes = nodes_positions + nodes_arguments
    links = links_positions + links_arguments
    
    return nodes,links

def get_all_descendant_debates(debate_ids,xml_debates):
    """
    Get all descendants of the listed debates.

    Parameters
    ----------
    debate_ids : list
        Debate IDs to find descendants of.
    xml_debates : BeautifulSoup object
        The debates xml file parsed by BeautifulSoup.
    
    Returns
    -------
    debate_ids : list
        The original IDs together with all their descendants.

    """
    
    ## Recursively...
    while True:
        
        ## ...find all debates that are children of the current list...
        def larger_debate_requested(id):
            if id is not None:
                return int(id) in debate_ids # filter functions must return True or False
            
        ## (From the documentation: "Any argument that’s not recognized 
        ##   will be turned into a filter on one of a tag’s attributes.")
        debates_to_add = xml_debates.find_all('larger_debate',id=larger_debate_requested)
        
        ## ...add those children to the current list...
        finished = True
        for larger_debate_node in debates_to_add:
            new_debate = int(larger_debate_node.parent["id"])
            
            ## (Is this a debate we have not yet collected?)
            if new_debate not in debate_ids:
                finished = False
                debate_ids.append(new_debate)
        
        ## ...but quit if no new children were added this time.
        if finished:break
    
    ## Sort the list before returning.
    debate_ids.sort()
    
    return debate_ids

def get_all_descendant_positions(debate_ids,xml_positions):
    """
    Some positions have a tag called <debate> and some have <larger_position>.
    Need to find all of these.

    Parameters
    ----------
    debate_ids : list
        Debate IDs to find child positions of.
    xml_positions : BeautifulSoup object
        E.g. Positions.xml, parsed by BS.

    Returns
    -------
    position_ids : list
        Position IDs to plot.

    """
    
    ## Start with the first batch of Positions.
    def larger_debate_requested(id):
        if id is not None:
            return int(id) in debate_ids # filter functions must return True or False
    
    positions_to_add = xml_positions.find_all('debate',id=larger_debate_requested)
    
    ## Now <positions_to_add> are all the nodes.
    ## Get the IDs.
    position_ids = []
    for position in positions_to_add:
        ## Avoid duplicates
        new_position = int(position.parent['id'])
        if new_position not in position_ids: position_ids.append(new_position)
    
    ## Recursively...
    while True:
        
        ## ...find all positions that are children of the current list...
        def larger_position_requested(id):
            if id is not None:
                return int(id) in position_ids # filter functions must return True or False
            
        ## (From the documentation: "Any argument that’s not recognized 
        ##   will be turned into a filter on one of a tag’s attributes.")
        positions_to_add = xml_positions.find_all('larger_position',id=larger_position_requested)
        
        ## ...add those children to the current list...
        finished = True
        for larger_position_node in positions_to_add:
            new_position = int(larger_position_node.parent["id"])
            
            ## (Is this a debate we have not yet collected?)
            if new_position not in position_ids:
                finished = False
                position_ids.append(new_position)
        
        ## ...but quit if no new children were added this time.
        if finished:break
    
    ## Sort the list before returning.
    position_ids.sort()
    
    return position_ids

def get_nodes_positions(position_ids,xml_positions):
    """
    From an XML string, return nodes as GoJS JSON list

    Parameters
    ----------
    position_ids : list of ints
    xml_positions : BeautifulSoup parser object

    Returns
    -------
    nodes : list
        GoJS format of nodes. Example:
            {"key":25,"text":"Interventionism"}

    """
    
    ## Initialise JSON list of dicts
    nodes = []
    
    ## Get list of position nodes
    records_xml = xml_positions.find_all('record',type="position",id=position_ids)
    
    ## Loop and add
    for record in records_xml:
        record_dict = {
            "key"  : int(record['id']), # the id attribute of the <record> tag
            "text" : record.find('name').text, # the text inside the <name> tag under the <record> tag
            "figure": POSITION_FIGURE
            }
        
        ## Add this record to the JSON list
        nodes.append(record_dict)
    
    return nodes

def get_links_positions(position_ids,xml):
    """
    From an XML string, return links as GoJS JSON list

    Parameters
    ----------
    position_ids: list of ints
    xml : BeautifulSoup parser object

    Returns
    -------
    links : list
        GoJS format of links between nodes. Example:
            {"from":25,"to":26}

    """
    
    ## We have already figured out exactly which positions we need.
    def position_has_parent(tag):
        return tag.name=='record' and tag.find('larger_position')  is not None\
                                  and int(tag.find('larger_position')['id']) in position_ids
    
    ## Get all records with parents
    records_xml = xml.find_all(position_has_parent)
    
    ## Initialise
    links = []
    
    for child_record in records_xml:
        
        ## Create arrow dict object
        arrow_dict = {
            "from": int(child_record.find('larger_position')['id']),
            "to"  : int(child_record['id'])
            }
        
        ## Append arrow to dict
        links.append(arrow_dict)
    
    return links

def get_all_descendant_arguments(position_ids,xml_arguments):
    """
    Filter by arguments relative to the selected positions

    Parameters
    ----------
    position_ids : list of ints
        DESCRIPTION.
    xml_arguments : Beautiful soup object
        DESCRIPTION.

    Returns
    -------
    argument_ids : list of ints
        DESCRIPTION.

    """
    
    ## Some arguments don't have positions as parents, just other arguments.
    ## Need to get all children of positions,
    ##  as well as all children of arguments.
    def argument_has_parent_position(tag):
        return tag.name=='record' and tag.find('position')  is not None\
                                  and int(tag.find('position')['id']) in position_ids
    
    arguments = xml_arguments.find_all(argument_has_parent_position)
    
    ## Extract the IDs from the nodes
    argument_ids = []
    for argument in arguments:
        argument_ids.append(int(argument["id"]))
        
    ## Now recursively find all counterarguments,
    ##  and add them if they aren't already in argument_ids = [].
    ## Recursively...
    while True:
        
        ## ...find arguments that point to known arguments...
        def argument_has_parent_argument(tag):
            return tag.name=='record' and tag.find('counterargument') is not None\
                                      and int(tag.find('counterargument')["id"]) in argument_ids
        
        ## Get all records with parent arguments
        arguments_with_parent_arguments_xml = xml_arguments.find_all(argument_has_parent_argument)
        
        ## Add it if it's not already in there
        finished = True
        for argument in arguments_with_parent_arguments_xml:
            
            ## Convert from string to int
            argument_id_new = int(argument["id"])
            
            ## Is it not already in our list?
            if argument_id_new not in argument_ids:
                
                ## Don't break, because this newly-added argument
                ##  might have counterarguments that haven't yet been added
                finished = False 
                
                ## Add the new argument
                argument_ids.append(argument_id_new)
        
        if finished==True:break
    
    
    return argument_ids

def get_nodes_arguments(argument_ids,xml_arguments):
    """
    From an XML string, return nodes as GoJS JSON list.
    IDs for arguments are offset by 10,000 to prevent conflict with position IDs.
    This will break if you have more than <ARGUMENT_OFFSET> positions!

    Parameters
    ----------
    argument_ids: list of ints
    xml_arguments : BeautifulSoup parser object

    Returns
    -------
    nodes : list
        GoJS format of nodes. Example:
            {"key":10001,"text":"Poverty of the Stimulus (Pullum &amp; Scholz 2002)"}

    """
    
    ## Initialise JSON list of dicts
    nodes = []
    
    ## Just positions for now
    ## Later we will include arguments.
    records_xml = xml_arguments.find_all('record',type="argument",id=argument_ids)
    
    ## Loop and add
    for record in records_xml:
        if record.find('name'):
            record_dict = {
                "key"  : int(record['id'])+ARGUMENT_OFFSET, # the id attribute of the <record> tag
                "text" : record.find('name').text, # the text inside the <name> tag under the <record> tag
                "figure" : ARGUMENT_FIGURE
                }
            
            ## Add this record to the JSON list
            nodes.append(record_dict)
    
    return nodes

def get_links_arguments(position_ids,argument_ids,xml_arguments):
    """
    From an XML string, return links as GoJS JSON list.
    Offset argument IDs by <ARGUMENT OFFSET>

    Parameters
    ----------
    positions_ids : list of ints
    argument_ids  : list of ints
    xml_arguments : BeautifulSoup parser object

    Returns
    -------
    links : list
        GoJS format of links between nodes. Example:
            {"from":25,"to":26}

    """
    
    ## 1. Get two lists: arguments that point to positions, and
    ##     arguments that link to other arguments.
    ##    An argument may appear in both lists.
    
    ## Define complex search function for BeautifulSoup
    ## Find arguments that point to positions
    def argument_has_parent_position(tag):
        return tag.name=='record' and tag.find('position')  is not None\
                                  and int(tag.find('position')['id']) in position_ids
    
    ## Get all records with parent positions
    arguments_with_parent_positions_xml = xml_arguments.find_all(argument_has_parent_position)
    
    ## Find arguments that point to other arguments
    def argument_has_parent_argument(tag):
        return tag.name=='record' and tag.find('counterargument') is not None\
                                  and int(tag.find('counterargument')["id"]) in argument_ids
    
    ## Get all records with parent arguments
    arguments_with_parent_arguments_xml = xml_arguments.find_all(argument_has_parent_argument)
    
    ## 2. Build the links list.
    ## Initialise
    links = []
    
    ## First link arguments to positions
    for record in arguments_with_parent_positions_xml:
        
        ## Create arrow dict object.
        ## Here the arrow goes from the position to the argument.
        ## It might be preferable to do it the other way round.
        arrow_dict = {
            "from": int(record.find('position')['id']),
            "to"  : int(record['id'])+ARGUMENT_OFFSET
            }
        
        ## Determine arrow color
        ## The verdict is determined by the id attribute of the position_verdict tag
        verdict = int(record.find('position').find('position_verdict')['id'])
        
        ## For now, just do green for True, red for everything else
        if verdict == 1:
            arrow_dict["color"] = "green"
        else:
            arrow_dict["color"] = "red"
        
        ## Append arrow to dict
        links.append(arrow_dict)
    
    ## Now link arguments to other arguments
    for record in arguments_with_parent_arguments_xml:
        
        ## Create arrow dict object.
        ## Here the arrow goes from the original argument to the counterargument.
        ## It might be preferable to do it the other way round.
        arrow_dict = {
            "from": int(record.find('counterargument')['id'])+ARGUMENT_OFFSET,
            "to"  : int(record['id'])+ARGUMENT_OFFSET
            }
        
        ## Color: assume all counterarguments are red
        arrow_dict["color"] = "red"
        
        links.append(arrow_dict)
    
    return links

def create_json(nodes,links):
    """
    From a list of nodes and links, create the GoJS JSON object

    Parameters
    ----------
    nodes : TYPE
        DESCRIPTION.
    links : TYPE
        DESCRIPTION.

    Returns
    -------
    json_object : TYPE
        DESCRIPTION.

    """
    
    json_object = {
        "class" : "GraphLinksModel",
        "nodeDataArray" : nodes,
        "linkDataArray" : links
        }
    
    return json_object

def get_json_filepath(args):
    """
    Determine the JSON filepath.
    Basically add "_<debate ID>" to the supplied filepath.

    Parameters
    ----------
    args : dict
        User supplied parameters.

    Returns
    -------
    json_fpath : string
        The filepath that will be used for the JSON.

    """
    
    fpath_raw = args["json"]
    debate_id_str = str(args["debate"])
    
    ## If it already ends with .json, chop that off before adding the debate ID
    if len(fpath_raw) > 5 and fpath_raw[-5:] == '.json':
        fpath_raw = fpath_raw[:-5]
    
    json_fpath = f'{fpath_raw}_{debate_id_str}.json'
    
    return json_fpath

def fix_locations(json_object,fpath_json):
    """
    Nodes and links.
    If the file doesn't yet exist, do nothing.

    Parameters
    ----------
    json_object : TYPE
        DESCRIPTION.
    fpath_html : TYPE
        DESCRIPTION.

    Returns
    -------
    json_object : TYPE
        DESCRIPTION.

    """
    
    ## First add the filename to the json object
    json_object['filename'] = fpath_json
    
    ## Get the current HTML file
    try:
        with open(fpath_json,'r',encoding="utf8") as f:
            json_object_current = json.loads(f.read()) 
    except FileNotFoundError:
        ## The file doesn't exist yet, so no need to specify existing properties.
        ## The file will be created with default properties.
        return json_object
    
    ## Now for each of the nodes we want to add, check whether it already exists in <json_object_current>.
    ## If so, keep its location.
    ## Same with links.
    for node in json_object['nodeDataArray']:
        
        ## Does this node already exist?
        node_current = find_node(json_object_current,node)
        
        if not node_current:continue
        
        ## This node already exists.
        ## Take its location from node_current.
        if "loc" in node_current:
            node["loc"] = node_current["loc"]
        
        ## Take its size from node_current.
        if "size" in node_current:
            node["size"] = node_current["size"]
    
    ## Now do the same for links
    for link in json_object['linkDataArray']:
        
        ## Does this link already exist?
        link_current = find_link(json_object_current,link)
        
        if not link_current:continue
        
        ## This link already exists.
        ## Take its point locations from link_current.
        if "points" in link_current:
            link["points"] = link_current["points"]
    
    return json_object

def find_node(json_object_current,node)->None:
    """
    Determine whether a node with this ID already exists

    Parameters
    ----------
    json_object_current : dict
        DESCRIPTION.
    node : dict
        DESCRIPTION.

    Returns
    -------
    node_current : dict
        DESCRIPTION.

    """
    
    for node_current_candidate in json_object_current['nodeDataArray']: # maybe there's a quicker way to do this
        if node_current_candidate["key"] == node["key"]: return node_current_candidate

def find_link(json_object_current,link)->None:
    """
    Determine whether a link with this from- and to- already exists.

    Parameters
    ----------
    json_object_current : TYPE
        DESCRIPTION.
    link : TYPE
        DESCRIPTION.

    Returns
    -------
    link_current : TYPE
        DESCRIPTION.

    """
    
    for link_current_candidate in json_object_current['linkDataArray']: # maybe there's a quicker way to do this
        if link_current_candidate["from"] == link["from"] and link_current_candidate["to"] == link["to"]: 
            return link_current_candidate

def output_json(json_object,fpath_out):
    """
    Dump JSON to specified file.

    Parameters
    ----------
    json_object : TYPE
        DESCRIPTION.
    fpath_out : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    
    with open(fpath_out,'w',encoding="utf8") as f:
        json.dump(
            json_object,
            f,
            indent=4 # pretty print
            )
    
def output_html(json_object,fpath_html):
    """
    Basically assumes a blockEditor type page
     where the JSON can be dumped into a textarea.
     
    If <fpath_html> doesn't exist, it will be created
     from blockEditorTemplate.html

    Parameters
    ----------
    fpath_html : str
        Filepath to output the HTML file.

    Returns
    -------
    None.

    """
    
    ## Does the html file exist yet?
    try:
        with open(fpath_html,'r',encoding="utf8") as f:
            html = bs(f.read(), features="lxml")
    except FileNotFoundError:
        ## The html file doesn't exist.
        ## Create it from blockEditorTemplate.html
        with open(HTML_TEMPLATE,'r',encoding="utf8") as f:
            html = bs(f.read(), features="lxml")
    
    def textarea_model(tag):
        return tag.name=='textarea' and tag['id']=='mySavedModel'
    
    textarea = html.find(textarea_model)
    
    textarea.string = json.dumps(json_object,indent=4)
    
    ## Dump HTML
    with open(fpath_html,'w',encoding="utf8") as f:
        f.write(str(html))

def launch_html(fpath_html):
    """
    Launch the created/updated HTML file in browser

    Parameters
    ----------
    fpath_html : str
        The HTML file to launch.

    Returns
    -------
    None.

    """
    
    ## For some reason we have to build the filepath this way.
    ## See https://stackoverflow.com/questions/5916270/pythons-webbrowser-launches-ie-instead-of-default-browser-on-windows-relative
    url = os.path.realpath(fpath_html)
    
    ## Launch
    webbrowser.open(url)

'''
    Define command-line arguments to allow the user to run the script
'''
## Explain the program
## On the command line, python convert.py -h will display this information.
parser = argparse.ArgumentParser(description="Convert Hypernomicon XML to GoJS JSON.")

## Add the Debate ID argument
parser.add_argument('--debate',
                    metavar='DEBATE_ID',
                    type=int,
                    nargs='?', # zero or one
                    default=1 # defaults to all debates
                    )

## Add the XML Debates file argument
parser.add_argument('--debates',
                    metavar='XML_DEBATES_FILEPATH',
                    type=str,
                    nargs='?', # zero or one
                    default='Debates.xml'
                    )

## Add the XML Positions file argument
parser.add_argument('--positions',
                    metavar='XML_POSITIONS_FILEPATH',
                    type=str,
                    nargs='?', # zero or one
                    default='Positions.xml' # default to Hypernomicon's Positions file
                    )

## Add the XML Arguments file argument
parser.add_argument('--arguments',
                    metavar='XML_ARGUMENTS_FILEPATH',
                    type=str,
                    nargs='?', # zero or one
                    default='Arguments.xml' # default to Hypernomicon's Arguments file
                    )

## Add the JSON output file argument
parser.add_argument('--json',
                    metavar='JSON_FILEPATH',
                    type=str,
                    nargs='?',
                    default='hyper2gojs.json'
                    )

## Should we also update blockEditor.html?
parser.add_argument('--html',
                    metavar='HTML_FILEPATH',
                    type=str,
                    nargs='?', # zero or one
                    default='blockEditor.html' # default to GoJS example file
                    )

## Should we also launch the requested HTML file?
parser.add_argument('--launch',
                    metavar='LAUNCH_BROWSER',
                    type=bool,
                    nargs='?', # zero or one
                    default=True
                    )

'''
    Main conditional block
'''
if __name__ == '__main__':
    
    ## Get arguments
    args = parser.parse_args()
    
    ## Convert to dict
    args = vars(args)
    
    ## Run the main method
    run(args)