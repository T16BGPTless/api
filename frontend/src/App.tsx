import React, { useEffect, useState } from "react";
import "./App.css";

type InvoiceSummary = {
  invoiceId: string;
  status: string;
  customerId?: string;
  issueDate?: string;
  totalAmount?: number;
};

type Credit = {
  creditId: string;
  invoiceId: string;
  status: string;
  amount: number;
  createdAt: string;
};

type GenerateInvoiceState = {
  orderXml: string;
  customerId: string;
  dueDate: string;
  totalAmount: string;
  currency: string;
  contractRef: string;
};

const initialGenerateState: GenerateInvoiceState = {
  orderXml: "<Order>\n  <!-- Order XML here -->\n</Order>",
  customerId: "",
  dueDate: "",
  totalAmount: "",
  currency: "AUD",
  contractRef: ""
};

function App() {
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [loadingInvoices, setLoadingInvoices] = useState(false);
  const [invoiceError, setInvoiceError] = useState<string | null>(null);

  const [generateForm, setGenerateForm] =
    useState<GenerateInvoiceState>(initialGenerateState);
  const [generateLoading, setGenerateLoading] = useState(false);
  const [generateMessage, setGenerateMessage] = useState<string | null>(null);

  const [creditInvoiceId, setCreditInvoiceId] = useState<string>("");
  const [creditAmount, setCreditAmount] = useState<string>("");
  const [creditLoading, setCreditLoading] = useState(false);
  const [lastCredit, setLastCredit] = useState<Credit | null>(null);
  const [creditError, setCreditError] = useState<string | null>(null);

  const loadInvoices = async () => {
    setLoadingInvoices(true);
    setInvoiceError(null);
    try {
      const res = await fetch("/v1/invoices");
      if (!res.ok) {
        throw new Error(`Request failed with status ${res.status}`);
      }
      const data: InvoiceSummary[] = await res.json();
      setInvoices(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load invoices";
      setInvoiceError(message);
    } finally {
      setLoadingInvoices(false);
    }
  };

  useEffect(() => {
    void loadInvoices();
  }, []);

  const handleGenerateChange = (
    field: keyof GenerateInvoiceState,
    value: string
  ) => {
    setGenerateForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleGenerateSubmit = async (
    e: React.SyntheticEvent<HTMLFormElement>
  ) => {
    e.preventDefault();
    setGenerateLoading(true);
    setGenerateMessage(null);
    setInvoiceError(null);

    const total = Number(generateForm.totalAmount);

    try {
      const res = await fetch("/v1/invoices/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          orderDocument: generateForm.orderXml,
          userData: {
            customerId: generateForm.customerId || undefined,
            dueDate: generateForm.dueDate || undefined,
            totalAmount: Number.isNaN(total) ? 0 : total,
            currency: generateForm.currency || "AUD",
            lines: []
          },
          contractReference: generateForm.contractRef,
          otherData: {}
        })
      });

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const message = errBody.message || `Failed with status ${res.status}`;
        throw new Error(message);
      }

      const created = await res.json();
      setGenerateMessage(
        `Invoice ${created.invoiceId} created with total ${created.totalAmount}.`
      );
      setGenerateForm(initialGenerateState);
      await loadInvoices();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to generate invoice";
      setGenerateMessage(null);
      setInvoiceError(message);
    } finally {
      setGenerateLoading(false);
    }
  };

  const handleDeleteInvoice = async (invoiceId: string) => {
    if (!window.confirm("Delete this invoice? This cannot be undone.")) {
      return;
    }
    try {
      const res = await fetch(`/v1/invoices/${invoiceId}`, {
        method: "DELETE"
      });
      if (!res.ok && res.status !== 204) {
        const errBody = await res.json().catch(() => ({}));
        const message = errBody.message || `Failed with status ${res.status}`;
        throw new Error(message);
      }
      await loadInvoices();
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to delete invoice";
      setInvoiceError(message);
    }
  };

  const handleCreateCredit = async (
    e: React.SyntheticEvent<HTMLFormElement>
  ) => {
    e.preventDefault();
    setCreditLoading(true);
    setCreditError(null);
    setLastCredit(null);

    const amount = Number(creditAmount);

    try {
      const res = await fetch("/v1/credits", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          invoiceId: creditInvoiceId,
          amount
        })
      });
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        const message = errBody.message || `Failed with status ${res.status}`;
        throw new Error(message);
      }
      const credit: Credit = await res.json();
      setLastCredit(credit);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to raise credit";
      setCreditError(message);
    } finally {
      setCreditLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <h1>Invoice Generation SaaS</h1>
          <p className="app-subtitle">
            Create, validate, and manage UBL invoices from order data.
          </p>
        </div>
      </header>

      <main className="app-main">
        <section className="overview-card">
          <h2>Overview</h2>
          <p>
            The Invoice Generation API creates standardised UBL invoices from
            Order Documents and user data. It retrieves contract information,
            applies pricing rules, and validates invoices for compliance and
            accuracy.
          </p>
          <h3>Value to customers</h3>
          <ul>
            <li>Streamlines invoice creation and management.</li>
            <li>Reduces errors and ensures compliance.</li>
            <li>Provides easy access to invoices for tracking and reporting.</li>
          </ul>
        </section>

        <section className="layout-grid">
          <section className="card">
            <h2>Create invoice from order</h2>
            <p className="card-intro">
              Supply order XML, key invoice data, and a contract reference. The
              service will generate a standardised invoice.
            </p>
            <form className="form" onSubmit={handleGenerateSubmit}>
              <label className="field">
                <span>Order Document (XML)</span>
                <textarea
                  value={generateForm.orderXml}
                  onChange={(e) =>
                    handleGenerateChange("orderXml", e.target.value)
                  }
                  rows={6}
                />
              </label>

              <div className="field-grid">
                <label className="field">
                  <span>Customer ID</span>
                  <input
                    type="text"
                    value={generateForm.customerId}
                    onChange={(e) =>
                      handleGenerateChange("customerId", e.target.value)
                    }
                    placeholder="e.g. CUST-123"
                  />
                </label>
                <label className="field">
                  <span>Due date</span>
                  <input
                    type="date"
                    value={generateForm.dueDate}
                    onChange={(e) =>
                      handleGenerateChange("dueDate", e.target.value)
                    }
                  />
                </label>
              </div>

              <div className="field-grid">
                <label className="field">
                  <span>Total amount</span>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={generateForm.totalAmount}
                    onChange={(e) =>
                      handleGenerateChange("totalAmount", e.target.value)
                    }
                    placeholder="e.g. 199.99"
                  />
                </label>
                <label className="field">
                  <span>Currency</span>
                  <input
                    type="text"
                    value={generateForm.currency}
                    onChange={(e) =>
                      handleGenerateChange("currency", e.target.value)
                    }
                    placeholder="AUD"
                  />
                </label>
              </div>

              <label className="field">
                <span>Contract reference</span>
                <input
                  type="text"
                  value={generateForm.contractRef}
                  onChange={(e) =>
                    handleGenerateChange("contractRef", e.target.value)
                  }
                  placeholder="e.g. CONTRACT-2025-01"
                  required
                />
              </label>

              <button
                type="submit"
                className="primary-button"
                disabled={generateLoading}
              >
                {generateLoading ? "Generating…" : "Generate invoice"}
              </button>

              {generateMessage && (
                <p className="status status-success">{generateMessage}</p>
              )}
            </form>
          </section>

          <section className="card">
            <h2>Invoices</h2>
            <p className="card-intro">
              View all generated invoices to support retrieval, deletion and
              credit operations.
            </p>

            {loadingInvoices && <p>Loading invoices…</p>}
            {invoiceError && (
              <p className="status status-error">
                Error: <code>{invoiceError}</code>
              </p>
            )}

            {!loadingInvoices && !invoiceError && invoices.length === 0 && (
              <p className="muted">No invoices generated yet.</p>
            )}

            {!loadingInvoices && !invoiceError && invoices.length > 0 && (
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Invoice ID</th>
                      <th>Status</th>
                      <th>Customer</th>
                      <th>Issue date</th>
                      <th className="numeric">Total</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {invoices.map((inv) => (
                      <tr key={inv.invoiceId}>
                        <td>
                          <code>{inv.invoiceId}</code>
                        </td>
                        <td>{inv.status}</td>
                        <td>{inv.customerId ?? "—"}</td>
                        <td>{inv.issueDate ?? "—"}</td>
                        <td className="numeric">
                          {inv.totalAmount !== undefined
                            ? inv.totalAmount.toFixed(2)
                            : "—"}
                        </td>
                        <td className="actions">
                          <button
                            type="button"
                            className="ghost-button"
                            onClick={() => handleDeleteInvoice(inv.invoiceId)}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="card">
            <h2>Raise credit</h2>
            <p className="card-intro">
              Apply business corrections by raising credits against existing
              invoices.
            </p>

            <form className="form" onSubmit={handleCreateCredit}>
              <label className="field">
                <span>Invoice</span>
                <select
                  value={creditInvoiceId}
                  onChange={(e) => setCreditInvoiceId(e.target.value)}
                  required
                >
                  <option value="">Select an invoice…</option>
                  {invoices.map((inv) => (
                    <option key={inv.invoiceId} value={inv.invoiceId}>
                      {inv.invoiceId} – {inv.customerId ?? "Customer"} (
                      {inv.totalAmount ?? 0})
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Credit amount</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={creditAmount}
                  onChange={(e) => setCreditAmount(e.target.value)}
                  required
                />
              </label>

              <button
                type="submit"
                className="primary-button"
                disabled={creditLoading}
              >
                {creditLoading ? "Raising credit…" : "Raise credit"}
              </button>

              {creditError && (
                <p className="status status-error">
                  Error: <code>{creditError}</code>
                </p>
              )}

              {lastCredit && (
                <p className="status status-success">
                  Credit {lastCredit.creditId} raised for invoice{" "}
                  {lastCredit.invoiceId} with amount {lastCredit.amount}.
                </p>
              )}
            </form>
          </section>
        </section>
      </main>
    </div>
  );
}

export default App;
