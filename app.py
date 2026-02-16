import logging
from flask import Flask, request, jsonify
from flask_wtf.csrf import CSRFProtect

# Initialize the Flask app
app = Flask(__name__)

# Configuration for CSRF protection
app.config['SECRET_KEY'] = 'your_secret_key_here'
csrf = CSRFProtect(app)

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle exceptions and log them."""
    logging.error(f"An error occurred: {e}")
    return jsonify({"error": "An internal error occurred. Please try again later."}), 500

@app.route('/api/resource', methods=['POST'])
@csrf.exempt  # Example, use cautiously in real scenarios
def create_resource():
    """Endpoint to create a new resource."""
    try:
        data = request.json
        # Process your data here
        
        return jsonify({"message": "Resource created successfully!"}), 201
    except Exception as e:
        logging.error(f"Failed to create resource: {e}")
        return jsonify({"error": "Failed to create resource"}), 400

if __name__ == '__main__':
    app.run(debug=False)