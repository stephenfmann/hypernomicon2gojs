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
    objects,arrows = parse_xml(args['input'])
    
    ## Create JSON
    json_object = create_json(objects,arrows)
    
    ## Dump JSON
    output_json(json_object,args['output'])
    
    ## Output HTML
    output_html(json_object,args['html'])

def parse_xml(fpath_xml):
    """
    Get basic info on objects and arrows from XML file.

    Parameters
    ----------
    fpath_xml : string
        Filepath location of XML file.

    Returns
    -------
    objects : list
        GoJS format of objects. Example:
            {"key":25,"loc":"0 0","text":"Interventionism"}
    arrows : list
        GoJS format of arrows between objects. Example:
            {"from":25,"to":26}

    """
    
    ## Load XML
    with open(fpath_xml,'r') as f:
        xml = bs(f.read(), features="xml")
    
    ## Extract the objects
    objects = get_objects(xml)
    
    ## Extract the arrows
    arrows = get_arrows(xml)
    
    
    return objects,arrows

def get_objects(xml):
    """
    From an XML string, return objects as GoJS JSON list

    Parameters
    ----------
    xml : BeautifulSoup parser object

    Returns
    -------
    objects : list
        GoJS format of objects. Example:
            {"key":25,"loc":"0 0","text":"Interventionism"}

    """
    
    ## Initialise JSON list of dicts
    objects = []
    
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
        objects.append(record_dict)
    
    return objects

def get_arrows(xml):
    """
    From an XML string, return arrows as GoJS JSON list

    Parameters
    ----------
    xml : BeautifulSoup parser object

    Returns
    -------
    arrows : list
        GoJS format of arrows between objects. Example:
            {"from":25,"to":26}

    """
    
    ## Define complex search function for BeautifulSoup
    def position_has_parent(tag):
        return tag.name=='record' and tag.find('larger_position')  is not None
    
    ## Get all records with parents
    records_xml = xml.find_all(position_has_parent)
    
    ## Initialise
    arrows = []
    
    for child_record in records_xml:
        
        ## Create arrow dict object
        arrow_dict = {
            "from": int(child_record.find('larger_position')['id']),
            "to"  : int(child_record['id'])
            }
        
        ## Append arrow to dict
        arrows.append(arrow_dict)
    
    return arrows

def create_json(objects,arrows):
    """
    From a list of objects and arrows, create the GoJS JSON object

    Parameters
    ----------
    objects : TYPE
        DESCRIPTION.
    arrows : TYPE
        DESCRIPTION.

    Returns
    -------
    json_object : TYPE
        DESCRIPTION.

    """
    
    json_object = {
        "class" : "GraphLinksModel",
        "nodeDataArray" : objects,
        "linkDataArray" : arrows
        }
    
    return json_object

def output_json(json_object,fpath_out):
    
    with open(fpath_out,'w') as f:
        json.dump(
            json_object,
            f,
            indent=4 # pretty print
            )

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
parser.add_argument('--output',
                    metavar='JSON_FILEPATH',
                    type=str,
                    nargs='?', # zero or one
                    default='Positions.json' # default output file
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