"""
This script audits the postcodes
"""

#importing necessary packages and modules
import xml.etree.cElementTree as ET

wrong_postcodes = []

def audit_postcode(wrong_postcodes, postalcode):
    """
    This function checks if the postcode is in the expected format or not
    and adds the bad postcodes to a list
    """
    
    if ((len(postalcode) != 5) or (postalcode[0] != '9')):
        wrong_postcodes.append(postalcode)

def is_postcode(element):
    """
    This function checks if the tag represents a postcode or not
    """
    
    return (element.get('k') == "addr:postcode")

def audit_postcodes():
    """
    This function parses over the osm file and audits the
    elements that contain the postcodes
    """
    
    for event, element in ET.iterparse("sample.osm"):
        if element.tag == "tag":
            if is_postcode(element):
                audit_postcode(wrong_postcodes,element.get('v'))
    for postcode in wrong_postcodes:
        print(postcode)
