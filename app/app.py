"""Main application file."""

from flask import Flask, redirect
from app.routes.auth import auth_bp
from app.routes.invoices import invoices_bp
from app.routes.orders import orders_bp

app = Flask(__name__)

# Register route groups
app.register_blueprint(auth_bp)
app.register_blueprint(invoices_bp)
app.register_blueprint(orders_bp)


@app.route("/")
def home():
    """Redirects to swagger."""
    return redirect("https://docs.gptless.au")


if __name__ == "__main__":
    app.run(debug=True)
