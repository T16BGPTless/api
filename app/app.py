"""Main application file."""

import sys
import os
from flask import Flask
from routes.invoices import invoices_bp
from routes.auth import auth_bp

# Add the directory containing this file to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

# Register route groups
app.register_blueprint(invoices_bp)
app.register_blueprint(auth_bp)


@app.route("/")
def home():
    """Home route."""
    return {"message": "Invoice API running"}


if __name__ == "__main__":
    app.run(debug=True)
