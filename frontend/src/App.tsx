import React, { useEffect, useState } from "react";

type InvoiceSummary = {
  invoiceId: string;
  status: string;
  customerId?: string;
  issueDate?: string;
  totalAmount?: number;
};

function App() {
  const [invoices, setInvoices] = useState<InvoiceSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const fetchInvoices = async () => {
      setLoading(true);
      setError("");
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
        setError(message);
      } finally {
        setLoading(false);
      }
    };

    fetchInvoices();
  }, []);

  return (
    <main
      style={{
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        maxWidth: "960px",
        margin: "0 auto",
        padding: "2rem 1.5rem"
      }}
    >
      <header style={{ marginBottom: "2rem" }}>
        <h1 style={{ margin: 0 }}>T16BGPTless Invoice Generation</h1>
        <p style={{ marginTop: "0.5rem", color: "#555" }}>
          React frontend talking to the Flask Invoice Generation API.
        </p>
      </header>

      <section>
        <h2 style={{ marginBottom: "0.5rem" }}>Invoice summaries</h2>
        <p style={{ marginTop: 0, color: "#666", fontSize: "0.95rem" }}>
          Data is loaded from the <code>/v1/invoices</code> endpoint defined in
          the API specification.
        </p>

        {loading && <p>Loading invoices…</p>}
        {error && (
          <p style={{ color: "crimson" }}>
            Error loading invoices: <code>{error}</code>
          </p>
        )}

        {!loading && !error && invoices.length === 0 && (
          <p style={{ color: "#777" }}>No invoices found yet.</p>
        )}

        {!loading && !error && invoices.length > 0 && (
          <table
            style={{
              width: "100%",
              borderCollapse: "collapse",
              marginTop: "1rem",
              fontSize: "0.95rem"
            }}
          >
            <thead>
              <tr>
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ddd",
                    padding: "0.5rem"
                  }}
                >
                  Invoice ID
                </th>
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ddd",
                    padding: "0.5rem"
                  }}
                >
                  Status
                </th>
                <th
                  style={{
                    textAlign: "left",
                    borderBottom: "1px solid #ddd",
                    padding: "0.5rem"
                  }}
                >
                  Customer
                </th>
                <th
                  style={{
                    textAlign: "right",
                    borderBottom: "1px solid #ddd",
                    padding: "0.5rem"
                  }}
                >
                  Total
                </th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.invoiceId}>
                  <td
                    style={{
                      padding: "0.5rem",
                      borderBottom: "1px solid #f0f0f0"
                    }}
                  >
                    <code>{inv.invoiceId}</code>
                  </td>
                  <td
                    style={{
                      padding: "0.5rem",
                      borderBottom: "1px solid #f0f0f0"
                    }}
                  >
                    {inv.status}
                  </td>
                  <td
                    style={{
                      padding: "0.5rem",
                      borderBottom: "1px solid #f0f0f0"
                    }}
                  >
                    {inv.customerId || "—"}
                  </td>
                  <td
                    style={{
                      padding: "0.5rem",
                      borderBottom: "1px solid #f0f0f0",
                      textAlign: "right"
                    }}
                  >
                    {inv.totalAmount ?? 0}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  );
}

export default App;

