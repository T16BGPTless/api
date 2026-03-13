import xml.etree.ElementTree as element_tree
from decimal import Decimal, InvalidOperation

# ubl xml namespaces from swagger
INVOICE_UBL_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
INVOICE_CAC_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
)
INVOICE_CBC_FIELDS_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
)

# xml prefixes from swagger aswell
element_tree.register_namespace("", INVOICE_UBL_NS)
element_tree.register_namespace("cac", INVOICE_CAC_NS)
element_tree.register_namespace("cbc", INVOICE_CBC_FIELDS_NS)


# tag name creator!! makes things easier
def _tag(ns: str, name: str) -> str:
    return f"{{{ns}}}{name}"


def _add_text(parent, ns, name, value, attrs=None):
    if attrs is None:
        attrs = {}

    # makes child under parent XMl ele
    element = element_tree.SubElement(parent, _tag(ns, name), attrs)
    # puts the text inside the XML tag
    element.text = str(value)


def _require_string(data: dict, field: str) -> str:
    value = data.get(field)
    # checks value is a string + not empty or spaces
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()


# similar to above but for decimals vv fun yes
def _require_decimal(data: dict, field: str) -> Decimal:
    value = data.get(field)
    if value is None:
        raise ValueError(f"{field} is required")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError(f"{field} must be valid number")
    if number < 0:
        raise ValueError(f"{field} must not be negative")
    return number


def _fmt(value: Decimal) -> str:
    return f"{value:.2f}"


# add customer details onto the invoice which creates the XML structure
def _build_party(parent, tag: str, data: dict):
    wrapper = element_tree.SubElement(parent, _tag(INVOICE_CAC_NS, tag))
    party = element_tree.SubElement(wrapper, _tag(INVOICE_CAC_NS, "Party"))
    name_el = element_tree.SubElement(party, _tag(INVOICE_CAC_NS, "PartyName"))
    _add_text(name_el, INVOICE_CBC_FIELDS_NS, "Name", _require_string(data, "name"))
    tax_el = element_tree.SubElement(party, _tag(INVOICE_CAC_NS, "PartyTaxScheme"))
    _add_text(tax_el, INVOICE_CBC_FIELDS_NS, "CompanyID", _require_string(data, "ABN"))


# creates invoice line by line
def _build_line(parent, line: dict, currency: str):
    el = element_tree.SubElement(parent, _tag(INVOICE_CAC_NS, "InvoiceLine"))
    _add_text(el, INVOICE_CBC_FIELDS_NS, "ID", _require_string(line, "lineId"))
    _add_text(
        el,
        INVOICE_CBC_FIELDS_NS,
        "InvoicedQuantity",
        _require_decimal(line, "quantity"),
    )
    _add_text(
        el,
        INVOICE_CBC_FIELDS_NS,
        "LineExtensionAmount",
        _fmt(_require_decimal(line, "lineTotal")),
        {"currencyID": currency},
    )
    item = element_tree.SubElement(el, _tag(INVOICE_CAC_NS, "Item"))
    _add_text(
        item, INVOICE_CBC_FIELDS_NS, "Description", _require_string(line, "description")
    )
    price = element_tree.SubElement(el, _tag(INVOICE_CAC_NS, "Price"))
    _add_text(
        price,
        INVOICE_CBC_FIELDS_NS,
        "PriceAmount",
        _fmt(_require_decimal(line, "unitPrice")),
        {"currencyID": currency},
    )


# builds the whole invoice and returns it as an XML string
def build_invoice_xml(data: dict) -> str:
    if not isinstance(data, dict):
        raise ValueError("Invoice data must be an object")

    invoice_id = _require_string(data, "invoiceID")
    issue_date = _require_string(data, "issueDate")
    due_date = _require_string(data, "dueDate")
    currency = _require_string(data, "currency")
    total_amount = _require_decimal(data, "totalAmount")

    supplier = data.get("supplier")
    customer = data.get("customer")
    lines = data.get("lines")

    # checks nested structure is all goodies
    if not isinstance(supplier, dict):
        raise ValueError("supplier must be an object")

    if not isinstance(customer, dict):
        raise ValueError("customer must be an object")

    if not isinstance(lines, list) or not lines:
        raise ValueError("lines must be a non-empty array")

    for line in lines:
        if not isinstance(line, dict):
            raise ValueError("Each line must be an object")

    # sum line totals
    line_sum = sum(_require_decimal(line, "lineTotal") for line in lines)

    # checks with total amount
    if line_sum != total_amount:
        raise ValueError("overalltotal must equal sum of line total values")

    # creates root xml i.e <invoice>
    root = element_tree.Element(_tag(INVOICE_UBL_NS, "Invoice"))
    # put in header fields
    _add_text(root, INVOICE_CBC_FIELDS_NS, "ID", invoice_id)
    _add_text(root, INVOICE_CBC_FIELDS_NS, "IssueDate", issue_date)
    _add_text(root, INVOICE_CBC_FIELDS_NS, "DueDate", due_date)

    # supp + customre
    _build_party(root, "AccountingSupplierParty", supplier)
    _build_party(root, "AccountingCustomerParty", customer)

    # totals
    total_el = element_tree.SubElement(root, _tag(INVOICE_CAC_NS, "LegalMonetaryTotal"))
    _add_text(
        total_el,
        INVOICE_CBC_FIELDS_NS,
        "PayableAmount",
        _fmt(total_amount),
        {"currencyID": currency},
    )

    for line in lines:
        if not isinstance(line, dict):
            raise ValueError("Each line must be an object")
        _build_line(root, line, currency)

    return element_tree.tostring(root, encoding="utf-8", xml_declaration=True).decode(
        "utf-8"
    )
