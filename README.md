## Invoice Generation SaaS – T16BGPTless

An API-first SaaS that generates standardised UBL invoices from Order Documents and user-provided data. It retrieves contract information, applies pricing rules, and validates invoices to ensure compliance, accuracy, and traceability.

---

## Overview

The **Invoice Generation API** creates standardised UBL invoices from Order Documents and user data. It:

- Retrieves pricing and terms from existing contracts.
- Applies pricing rules, discounts, and taxes.
- Validates invoices against business rules and formatting standards.
- Outputs a compliant UBL invoice document ready for downstream accounting systems.

This keeps invoice operations consistent, auditable, and easy to integrate.

---

## Scope

### Target users

- **Accounts receivable teams**: Need fast, accurate invoice creation and tracking.
- **Operations / billing specialists**: Want automated invoice generation from orders without manual data entry.
- **Developers / integrators**: Need a clear, well-documented API to plug into existing order management, ERP, or CRM systems.

---

## Architecture Overview

**Tech stack used in this project**

- **Deployment**: Vercel (serverless / managed hosting)
- **Backend / API**: Python 3 with Flask
- **Frontend**: React (SPA or lightweight UI for testing/integration)
- **Persistence**: AWS‑hosted managed database (final choice between RDS / DynamoDB / Aurora TBD)
- **Data formats**: XML Order Documents and UBL Invoice XML
- **API style**: RESTful JSON APIs orchestrating XML-based invoice generation

---

## API Routes

### Summary table

| Route                                | Method | Description                                                                                       |
|--------------------------------------|--------|---------------------------------------------------------------------------------------------------|
| `/v1/invoices/generate`              | POST   | Generate a standard and compliant invoice from order, user, and contract data.                   |
| `/v1/invoices`                       | GET    | List all invoices with optional filters.                                                          |
| `/v1/invoices/{invoiceId}`           | GET    | Retrieve a full invoice by ID.                                                                    |
| `/v1/invoices/{invoiceId}`           | PUT    | Update invoice user data by ID.                                                                   |
| `/v1/invoices/{invoiceId}`           | DELETE | Delete an invoice by ID.                                                                          |
| `/v1/invoices/{invoiceId}/export`    | GET    | Export a standardised UBL XML invoice.                                                            |
| `/v1/credits`                        | POST   | Raise a credit for an existing invoice.                                                           |
| `/v1/credits/{creditId}`             | GET    | Retrieve a full credit by ID.                                                                     |
| `/v1/invoices/{invoiceId}/apply-credit` | POST | Apply a credit (full or partial) to an invoice.                                                   |
| `/v1/invoices/{invoiceId}/status`    | POST   | Record and validate an invoice status update from an external system.                             |

### Detailed behaviour

#### `/v1/invoices/generate`

- **Description**: Given an Order Document, User Data, Contract Reference, and other data, generates a standard and compliant invoice.
- **Method**: `POST`
- **Parameters (body)**:
  - **Order Document** – Order XML.
  - **User Data JSON** – Additional invoice data, customer info, payment terms.
  - **Contract Reference** – Identifier used to fetch contract pricing/discounts.
  - **Other Data** – Optional fields (e.g. tax rules, special discounts, credit info).
- **Success response**:
  - **201 Created**
  - **Type**: `application/json`
  - **Body**: New **Invoice** object, including `invoiceId`, `status`, and calculated totals.
- **Exceptional flows**:
  - **400 Bad Request** – Missing required fields or malformed XML.
  - **404 Not Found** – `contractRef` does not exist.
  - **422 Unprocessable Entity** – Fails business rules (e.g. invalid pricing).

#### `/v1/invoices`

- **Description**: Provides a list of all invoices.
- **Method**: `GET`
- **Parameters (query, optional)**:
  - `limit`
  - `customer`
  - `status`
  - `date`
- **Success response**:
  - **200 OK**
  - **Type**: `application/json`
  - **Body**: Array of **InvoiceSummary** objects with metadata.
- **Exceptional flows**:
  - **400 Bad Request** – Invalid pagination or filtering parameters.

#### `/v1/invoices/{invoiceId}` – GET

- **Description**: Given a valid `invoiceId`, returns all relevant information about the invoice.
- **Method**: `GET`
- **Parameters**:
  - **Path**: `invoiceId`
- **Success response**:
  - **200 OK**
  - **Type**: `application/json`
  - **Body**: Full **Invoice** object.
- **Exceptional flows**:
  - **404 Not Found** – Invoice ID does not exist.

#### `/v1/invoices/{invoiceId}` – PUT

- **Description**: Updates an invoice’s user data.
- **Method**: `PUT`
- **Parameters**:
  - **Path**: `invoiceId`
  - **Body**: Updated user data JSON.
- **Success response**:
  - **200 OK**
  - **Type**: `application/json`
  - **Body**: **Invoice** object with updated information.
- **Exceptional flows**:
  - **404 Not Found** – Invoice ID does not exist.
  - **409 Conflict** – Invoice is in an invalid state for modification (e.g. already finalised/exported).

#### `/v1/invoices/{invoiceId}` – DELETE

- **Description**: Deletes an invoice.
- **Method**: `DELETE`
- **Parameters**:
  - **Path**: `invoiceId`
- **Success response**:
  - **204 No Content**
  - **Body**: Empty.
- **Exceptional flows**:
  - **404 Not Found** – Invoice ID does not exist.
  - **409 Conflict** – Invoice cannot be deleted because it has been finalised/exported.

#### `/v1/invoices/{invoiceId}/export`

- **Description**: Given a valid `invoiceId`, generates and returns the standardised final invoice.
- **Method**: `GET`
- **Parameters**:
  - **Path**: `invoiceId`
- **Success response**:
  - **200 OK**
  - **Type**: `application/xml`
  - **Body**: Standardised and compliant UBL XML document ready for download or file transfer.
- **Exceptional flows**:
  - **404 Not Found** – Invoice ID does not exist.
  - **400 Bad Request** – Invoice is missing required data for UBL formatting standards.

#### `/v1/credits`

- **Description**: Raises credit for an existing invoice.
- **Method**: `POST`
- **Parameters (body)**:
  - `invoiceId`
- **Success response**:
  - **201 Created**
  - **Type**: `application/json`
  - **Body**: **Credit** object containing `creditId`, `status`, and `amount`.
- **Exceptional flows**:
  - **400 Bad Request** – Amount is zero, negative, or missing.
  - **404 Not Found** – Invoice ID does not exist.

#### `/v1/credits/{creditId}`

- **Description**: Given a valid `creditId`, gets all relevant information for the specified credit.
- **Method**: `GET`
- **Parameters**:
  - **Path**: `creditId`
- **Success response**:
  - **200 OK**
  - **Type**: `application/json`
  - **Body**: Full **Credit** object.
- **Exceptional flows**:
  - **404 Not Found** – Credit ID does not exist.

#### `/v1/invoices/{invoiceId}/apply-credit`

- **Description**: Given a valid `invoiceId`, applies a specified credit to the invoice.
- **Method**: `POST`
- **Parameters**:
  - **Path**: `invoiceId`
  - **Body**:
    - `creditId`
    - `amount`
- **Success response**:
  - **200 OK**
  - **Type**: `application/json`
  - **Body**: **Invoice** object showing updated credit and due amount.
- **Exceptional flows**:
  - **400 Bad Request** – Amount exceeds invoice total or available credit.
  - **404 Not Found** – Invoice ID does not exist.
  - **404 Not Found** – Credit ID does not exist.
  - **409 Conflict** – Credit already applied.

#### `/v1/invoices/{invoiceId}/status`

- **Description**: Given an `invoiceId`, validate the invoice status update from an external system and log it.
- **Method**: `POST`
- **Parameters**:
  - **Path**: `invoiceId`
  - **Body**: `currentStatus`
- **Success response**:
  - **200 OK**
  - **Type**: `application/json`
  - **Body**: Acknowledgement object confirming the status update was recorded and logged.
- **Exceptional flows**:
  - **404 Not Found** – Invoice ID does not exist.
  - **422 Unprocessable Entity** – Invalid status payload received from the accounting/financials system.