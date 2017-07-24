"""
This script cleans the audited elements and writes
the data from the osm file to csv files
"""

#importing necessary packages and modules
import xml.etree.cElementTree as ET
import re
from collections import defaultdict
import csv
import codecs
import pprint
import cerberus
import schema

from streets_audit import *
from postcodes_audit import *
from housenumber_audit import *

OSM_PATH = "sample.osm"

NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

SCHEMA = schema.schema

NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

street_mapping = {"Rd":"Road", "broadway":"Broadway", "street":"Street", "avenue":"Avenue", "Ave.":"Avenue", \
                  "AVE":"Avenue", "St.":"Street", "way":"Way", "Blvd.":"Boulevard", "St":"Street", "Ave":"Avenue", \
                 "parkway":"Parkway", "blvd":"Boulevard", "Hwy":"Highway", "Dr":"Drive", "Ctr":"Center", "Rd.":"Road",\
                 "st":"Street", "Blvd":"Boulevard"}

def clean_street(element, street_name):
    """
    This function checks if the street name is in the
    expected format or not and if the street name is not in the
    proper format it uses the street_mapping dictionary to replace
    the improper names with proper names
    """
    
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expected:
            if street_type in street_mapping:
                new_street_type = street_mapping[street_type]
                new_street_name = street_name[:len(street_name)-len(street_type)]+new_street_type
                return new_street_name
            else:
                return street_name
        else:
            return street_name
    else:
        return street_name

def clean_postcode(element, postalcode):
    """
    This function checks if the postcode is in the proper
    format or not and if the postcode is not in the proper format
    it uses the postcode_re regular expression to find the expected pattern
    and replaces the bad postcode with the expected pattern. If the postcode does
    not contain the expected pattern also, the value "unknown" is stored as the
    postcode
    """
    
    postcode_re = re.compile(r'9[0-9]{4}')
    if ((len(postalcode) != 5) or (postalcode[0] != '9')):
        m = postcode_re.search(postalcode)
        if m:
            postcode = m.group()
        else:
            postcode = "unknown"
    else:
        postcode = postalcode
    return postcode

bad_hnum_re = re.compile(r'(^[0-9]+-[a-zA-Z]$)|(^[0-9]+ [a-zA-Z]$)')
hnum_suite_re = re.compile(r'(ste)|(ste\.)|(suite)')
hnum_plus_re = re.compile(r'^[0-9]+\+[0-9]+$')

def clean_housenumber(element):
    """
    This function checks if the house number is in the expected format
    or not and if the house number is in the wrong format, the function
    checks for multiple wrong formats and replaces the bad housenumber
    with a cleaned house number
    """
    
    house_number = element.get('v')
    if re.match(hnumber_re, house_number) is None:
        if house_number[len(house_number)-1] == "-":
            new_house_number = house_number.replace("-","")
        elif ";" in house_number:
            new_house_number = house_number.replace(";",",")
        elif re.match(bad_hnum_re, house_number) is not None:
            if "-" in house_number:
                new_house_number = house_number.replace("-","")
            else:
                new_house_number = house_number.replace(" ","")
        elif re.search(hnum_suite_re, house_number) is not None:
            m = hnum_suite_re.search(house_number)
            pattern = m.group()
            index = house_number.find(pattern)
            if index == 0:
                new_house_number = "Suite"+house_number[len(pattern):]
            else:
                new_house_number = house_number[:index]+"Suite"+house_number[index+len(pattern):]
        elif re.match(hnum_plus_re, house_number) is not None:
            new_house_number = house_number.replace("+","-")
        else:
            new_house_number = house_number
    else:
        new_house_number = house_number
    return new_house_number

def clean_field(element):
    """
    This function checks if the tag represents a street_address or
    postcode or housenumber and invokes the respective cleaning function.
    If the tag represents none of those, the function simply returns its
    value
    """
    
    if is_street_name(element):
        value = clean_street(element, element.get('v'))
    elif is_postcode(element):
        value = clean_postcode(element, element.get('v'))
    elif is_housenumber(element):
        value = clean_housenumber(element)
    else:
        value = element.get('v')
    return value

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,\
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    """
    This function properly cleans the elements and stores them
    in the respective dictionaries or lists
    """

    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    if element.tag == 'node':
        for field in node_attr_fields:
            if element.get(field) is not None:
                if field == 'id' or field == 'uid' or field == 'changeset':
                    node_attribs[field] = int(element.get(field))
                elif field == 'lat' or field == 'lon':
                    node_attribs[field] = float(element.get(field))
                else:
                    node_attribs[field] = element.get(field)
            else:
                return
        for tag in element.iter('tag'):
            temp = {}
            k = tag.get('k')
            if re.match(LOWER_COLON,k) is not None:
                temp_list = k.split(":")
                if len(temp_list) == 2:
                    k_type = temp_list[0]
                    key = temp_list[1]
                elif len(temp_list) == 3:
                    k_type = temp_list[0]
                    key = temp_list[1]+":"+temp_list[2]
            elif re.match(problem_chars,k) is not None:
                pass
            else:
                k_type = default_tag_type
                key = k
            value = clean_field(tag)
            temp["id"] = int(element.get('id'))
            temp["key"] = key
            temp["value"] = value
            temp["type"] = k_type
            tags.append(temp)
        return {'node': node_attribs, 'node_tags': tags}
    elif element.tag == 'way':  
        for field in way_attr_fields:
            if element.get(field) is not None:
                if (field == 'id') or (field == 'uid') or (field == 'changeset'):
                    way_attribs[field] = int(element.get(field))
                else:
                    way_attribs[field] = element.get(field)
            else:
                return
        for tag in element.iter('tag'):
            temp = {}
            k = tag.get('k')
            if re.match(LOWER_COLON,k) is not None:
                temp_list = k.split(":")
                if len(temp_list) == 2:
                    k_type = temp_list[0]
                    key = temp_list[1]
                elif len(temp_list) == 3:
                    k_type = temp_list[0]
                    key = temp_list[1]+":"+temp_list[2]
            elif re.match(problem_chars,k) is not None:
                pass
            else:
                k_type = default_tag_type
                key = k
            value = clean_field(tag)
            temp["id"] = int(element.get('id'))
            temp["key"] = key
            temp["value"] = value
            temp["type"] = k_type
            tags.append(temp)
        position = 0
        for nd in element.iter("nd"):
            temp = {}
            temp["id"] = int(element.get('id'))
            temp["node_id"] = int(nd.get('ref'))
            temp["position"] = int(position)
            position += 1
            way_nodes.append(temp)
        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}

def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)
        
        raise Exception(message_string.format(field, error_string))

class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v, unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""
    

    with codecs.open(NODES_PATH, 'w') as nodes_file,\
    codecs.open(NODE_TAGS_PATH, 'w') as nodes_tags_file,\
    codecs.open(WAYS_PATH, 'w') as ways_file,\
    codecs.open(WAY_NODES_PATH, 'w') as way_nodes_file,\
    codecs.open(WAY_TAGS_PATH, 'w') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])

process_map(OSM_PATH, True)
