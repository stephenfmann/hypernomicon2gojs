# -*- coding: utf-8 -*-

import json
import argparse
from bs4 import BeautifulSoup as bs


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
    
    ## Parse the input
    nodes,links = parse_xml(args['input'])
    
    ## Create JSON
    json_object = create_json(nodes,links)
    
    ## Fix the locations of known nodes and links
    json_object = fix_locations(json_object,args['json'])
    
    ## Dump JSON
    output_json(json_object,args['json'])
    
    ## Output HTML
    output_html(json_object,args['html'])
    

def parse_xml(fpath_xml):
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
    
    ## Load XML
    with open(fpath_xml,'r') as f:
        xml = bs(f.read(), features="xml")
    
    ## Extract the nodes
    nodes = get_nodes(xml)
    
    ## Extract the links
    links = get_links(xml)
    
    
    return nodes,links

def get_nodes(xml):
    """
    From an XML string, return nodes as GoJS JSON list

    Parameters
    ----------
    xml : BeautifulSoup parser object

    Returns
    -------
    nodes : list
        GoJS format of nodes. Example:
            {"key":25,"loc":"0 0","text":"Interventionism"}

    """
    
    ## Initialise JSON list of dicts
    nodes = []
    
    ## Just positions for now
    ## Later we will include arguments.
    records_xml = xml.find_all('record',type="position")
    
    ## Loop and add
    for record in records_xml:
        record_dict = {
            "key"  : int(record['id']), # the id attribute of the <record> tag
            "text" : record.find('name').text # the text inside the <name> tag under the <record> tag
            }
        
        ## Add this record to the JSON list
        nodes.append(record_dict)
    
    return nodes

def get_links(xml):
    """
    From an XML string, return links as GoJS JSON list

    Parameters
    ----------
    xml : BeautifulSoup parser object

    Returns
    -------
    links : list
        GoJS format of links between nodes. Example:
            {"from":25,"to":26}

    """
    
    ## Define complex search function for BeautifulSoup
    def position_has_parent(tag):
        return tag.name=='record' and tag.find('larger_position')  is not None
    
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

def output_json(json_object,fpath_out):
    
    with open(fpath_out,'w') as f:
        json.dump(
            json_object,
            f,
            indent=4 # pretty print
            )

def fix_locations(json_object,fpath_json):
    """
    Nodes and links

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
    
    ## Get the current HTML file
    with open(fpath_json,'r') as f:
        # html = bs(f.read(), features="lxml")
        json_object_current = json.loads(f.read()) 
    
    ## Get the textarea containing the current JSON
    # def textarea_model(tag):
    #     return tag.name=='textarea' and tag['id']=='mySavedModel'
    
    # textarea = html.find(textarea_model)
    
    ## Get the current JSON object from the HTML file
    # json_object_current = json.loads(textarea.text) 
    
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
    
def output_html(json_object,fpath_html):
    """
    Basically assumes a blockEditor type page
     where the JSON can be dumped into a textarea

    Parameters
    ----------
    fpath_html : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    
    with open(fpath_html,'r') as f:
        html = bs(f.read(), features="lxml")
    
    def textarea_model(tag):
        return tag.name=='textarea' and tag['id']=='mySavedModel'
    
    textarea = html.find(textarea_model)
    
    textarea.string = json.dumps(json_object,indent=4)
    
    ## Dump HTML
    with open(fpath_html,'w') as f:
        f.write(str(html))


'''
    Define command-line arguments to allow the user to run the script
'''
## Explain the program
## On the command line, python convert.py -h will display this information.
parser = argparse.ArgumentParser(description="Convert Hypernomicon XML to GoJS JSON.")

## Add the XML input file argument
parser.add_argument('--input',
                    metavar='XML_FILEPATH',
                    type=str,
                    nargs='?', # zero or one
                    default='Positions.xml' # default to Hypernomicon's Positions file
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
'''
    Main conditional block
'''
if __name__ == '__main__':
    
    ## Get arguments
    args = parser.parse_args()
    
    ## Convert to dict
    args_dict = vars(args)
    
    ## Call main method with these arguments
    run(args_dict)