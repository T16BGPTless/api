import requests
import pytest
import xml.dom.minidom
import re
import uuid
from datetime import datetime
import re
import xml.etree.ElementTree as ET


BASE_URL = "https://y1j7xv2ua6.execute-api.us-east-1.amazonaws.com/v1"

def remove_id_and_uuid(xml):
    xml = re.sub(r"<ns1:UUID>.*?</ns1:UUID>", "<ns1:UUID></ns1:UUID>", xml)
    xml = re.sub(r"<ns1:ID>.*?</ns1:ID>", "<ns1:ID></ns1:ID>", xml)
    return xml

def get_id_from_xml(xml):
    root = ET.fromstring(xml)
    # not sure why we need {urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2} but google said so and it works
    return root.find("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID").text