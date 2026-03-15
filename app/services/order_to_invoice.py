"""Map UBL Order JSON (from order_xml_to_json) to invoice InvoiceData shape."""

from decimal import Decimal


def _first(d: dict, *keys: str):
    """Return the first value found for any of the given keys (handles namespace variants)."""
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d:
            return d[k]
    return None


def _text(val) -> str:
    """Extract text from a value; if dict with @value or #text, use that."""
    if val is None:
        return ""
    if isinstance(val, dict):
        return str(val.get("#text", val.get("value", ""))).strip()
    return str(val).strip()


def _decimal(val) -> Decimal:
    """Parse a decimal from order XML text."""
    if val is None:
        return Decimal("0")
    s = _text(val) if isinstance(val, dict) else str(val)
    try:
        return Decimal(s) if s else Decimal("0")
    except Exception:
        return Decimal("0")


def _party_to_supplier_customer(party: dict) -> dict:
    """Map UBL Party (Buyer or Seller) to {name, ABN} for invoice."""
    if not party or not isinstance(party, dict):
        return {"name": "Unknown", "ABN": "00000000000"}
    # Party can be nested under cac:Party
    inner = _first(party, "cac:Party", "Party") or party
    name_el = _first(inner, "cac:PartyName", "PartyName")
    name = _text(_first(name_el, "cbc:Name", "Name") if name_el else None) or "Unknown"
    tax_el = _first(inner, "cac:PartyTaxScheme", "PartyTaxScheme")
    abn = (
        _text(_first(tax_el, "cbc:CompanyID", "CompanyID") if tax_el else None)
        or "00000000000"
    )
    return {"name": name, "ABN": abn}


def _order_line_to_invoice_line(line_or_item: dict) -> dict:
    """Map one OrderLine/LineItem to invoice line shape."""
    if not line_or_item or not isinstance(line_or_item, dict):
        return None
    # LineItem may be under cac:LineItem
    item = _first(line_or_item, "cac:LineItem", "LineItem") or line_or_item
    line_id = _text(_first(item, "cbc:ID", "ID")) or "1"
    qty = _decimal(_first(item, "cbc:Quantity", "Quantity"))
    if qty <= 0:
        qty = Decimal("1")
    ext_el = _first(item, "cbc:LineExtensionAmount", "LineExtensionAmount")
    if isinstance(ext_el, dict):
        line_total = _decimal(ext_el.get("#text") or ext_el.get("value"))
    else:
        line_total = _decimal(ext_el)
    price_el = _first(item, "cac:Price", "Price")
    price_amount = _decimal(
        _first(price_el, "cbc:PriceAmount", "PriceAmount") if price_el else None
    )
    unit_price = (line_total / qty) if qty else Decimal("0")
    if price_amount and price_amount > 0:
        unit_price = price_amount
    desc_el = _first(item, "cac:Item", "Item")
    desc = (
        _text(
            _first(desc_el, "cbc:Description", "cbc:Name", "Description", "Name")
            if desc_el
            else None
        )
        or "Item"
    )
    return {
        "lineId": line_id,
        "quantity": qty,
        "unitPrice": unit_price,
        "lineTotal": line_total,
        "description": desc,
    }


def order_json_to_invoice_data(order_dict: dict, due_date: str = None) -> dict:
    """
    Map UBL Order JSON (as returned by order_xml_to_json) to InvoiceData shape
    expected by build_invoice_xml / generate endpoint.

    Args:
        order_dict: Full parsed order (e.g. {"Order": {...}}).
        due_date: Optional due date (YYYY-MM-DD). If omitted, same as issue date.

    Returns:
        Dict with issueDate, dueDate, currency, totalAmount, supplier, customer, lines.
        invoiceID is added by the generate endpoint.
    """
    root = _first(order_dict, "Order")
    if root is None:
        for v in order_dict.values():
            if isinstance(v, dict) and (
                _first(v, "cac:BuyerCustomerParty") or _first(v, "cbc:IssueDate")
            ):
                root = v
                break
    if not root or not isinstance(root, dict):
        raise ValueError("Order JSON must contain an Order root")

    issue_date = _text(_first(root, "cbc:IssueDate", "IssueDate")) or "2020-01-01"
    due_date = due_date or issue_date

    # Currency and total from AnticipatedMonetaryTotal
    amt_el = _first(root, "cac:AnticipatedMonetaryTotal", "AnticipatedMonetaryTotal")
    currency = "AUD"
    total_amount = Decimal("0")
    if amt_el and isinstance(amt_el, dict):
        pay_el = _first(amt_el, "cbc:PayableAmount", "PayableAmount")
        if isinstance(pay_el, dict):
            currency = (
                _text(pay_el.get("@currencyID") or pay_el.get("currencyID")) or currency
            )
            total_amount = _decimal(pay_el.get("#text") or pay_el.get("value"))
        else:
            total_amount = _decimal(pay_el)
        if not total_amount and total_amount == 0:
            line_el = _first(amt_el, "cbc:LineExtensionAmount", "LineExtensionAmount")
            if isinstance(line_el, dict):
                total_amount = _decimal(line_el.get("#text") or line_el.get("value"))
            else:
                total_amount = _decimal(line_el)
    if currency == "":
        currency = "AUD"

    buyer = _first(root, "cac:BuyerCustomerParty", "BuyerCustomerParty")
    seller = _first(root, "cac:SellerSupplierParty", "SellerSupplierParty")
    customer = _party_to_supplier_customer(buyer)
    supplier = _party_to_supplier_customer(seller)

    order_lines = _first(root, "cac:OrderLine", "OrderLine")
    if order_lines is None:
        order_lines = []
    if isinstance(order_lines, dict):
        order_lines = [order_lines]
    if not isinstance(order_lines, list):
        order_lines = []

    lines = []
    for ol in order_lines:
        line = _order_line_to_invoice_line(ol)
        if line and line.get("description"):
            lines.append(line)

    if not lines:
        lines = [
            {
                "lineId": "1",
                "quantity": Decimal("1"),
                "unitPrice": total_amount if total_amount else Decimal("0"),
                "lineTotal": total_amount if total_amount else Decimal("0"),
                "description": "Order",
            }
        ]
    else:
        line_sum = sum(_decimal(l.get("lineTotal")) for l in lines)
        if total_amount == 0 and line_sum > 0:
            total_amount = line_sum

    # Return JSON-serializable types for use in API requests
    lines_out = []
    for ln in lines:
        lines_out.append(
            {
                "lineId": ln["lineId"],
                "quantity": float(ln["quantity"]),
                "unitPrice": float(ln["unitPrice"]),
                "lineTotal": float(ln["lineTotal"]),
                "description": ln["description"],
            }
        )
    return {
        "issueDate": issue_date,
        "dueDate": due_date,
        "currency": currency,
        "totalAmount": float(total_amount),
        "supplier": supplier,
        "customer": customer,
        "lines": lines_out,
    }
