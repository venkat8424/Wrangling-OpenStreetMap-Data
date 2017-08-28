"""
Author : Sai Venkat Kotha
This script audits the housenumbers
"""

#importing necessary packages and modules
import xml.etree.cElementTree as ET
import re

hnumbers = []

hnumber_re = re.compile(r'(^[0-9]+$)|(^[0-9]+[a-zA-Z]$)')

def audit_housenumber(housenumber):
    """
    This function checks if the housenumber is in the
    expected format or not and adds the bad housenumbers
    to a list.
    """
    
    if re.match(hnumber_re, housenumber) is None:
        hnumbers.append(housenumber)

def is_housenumber(element):
    """
    This function checks if the tag contains a house number
    or not.
    """
    
    return (element.get('k') == "addr:housenumber")

def audit_housenumbers():
    """
    This function parses over the osm file and audits
    the elements that contain the housenumbers
    """
    
    for event, element in ET.iterparse("sample.osm"):
        if element.tag == "tag":
            if is_housenumber(element):
                audit_housenumber(element.get('v'))
    for number in hnumbers:
        print(number)
