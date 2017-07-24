"""
This script audits the street names.
Author: Udacity
"""

#importing necessary packages and modules
import xml.etree.cElementTree as ET
import re
from collections import defaultdict

street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)

expected = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place", "Square", "Lane", "Road", 
            "Trail", "Parkway", "Commons", "Way"]

def audit_street_type(street_types, street_name):
    """
    This function checks if the value of the tag i.e if the street name
    is an expected street name or not and finds all the unexpected street names.
    """
    
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            street_types[street_type].add(street_name)

def is_street_name(element):
    """
    This function checks if the tag is a street address or not
    """

    return (element.get('k') == "addr:street")

def audit_streets():
    """
    This function parses over the file to find all the street tags
    and audits the tags with street addresses
    """
    
    street_types = defaultdict(set)
    for event, element in ET.iterparse("sample.osm"):
        if element.tag == "tag":
            if is_street_name(element):
                audit_street_type(street_types, element.get('v'))
    for key in street_types:
        print(key+" : "+str(street_types[key]))
