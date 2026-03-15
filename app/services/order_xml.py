"""Convert UBL Order XML to JSON for storage."""

from xml.parsers.expat import ExpatError

import xmltodict


def order_xml_to_json(xml_string: str) -> dict:
    """
    Convert UBL Order XML to a JSON-serialisable dict.

    Args:
        xml_string: Raw XML string (e.g. UBL Order document).

    Returns:
        Nested dict representation of the XML (tag names may include
        namespace prefixes, e.g. 'cbc:ID').

    Raises:
        ValueError: If the input is empty or not valid XML.
    """
    if not xml_string or not xml_string.strip():
        raise ValueError("Order XML must not be empty")
    try:
        return xmltodict.parse(xml_string.strip())
    except ExpatError as e:
        raise ValueError(f"Invalid XML: {e!s}") from e
