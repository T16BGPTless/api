"""Convert UBL Order XML to JSON for storage."""

from defusedexpat import ExpatError

import defusedexpat
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
        # Use a hardened XML parser to mitigate entity expansion and related attacks.
        return xmltodict.parse(xml_string.strip(), expat=defusedexpat)
    except ExpatError as e:
        raise ValueError(f"Invalid XML: {e!s}") from e
