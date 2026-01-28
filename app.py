from flask import Flask
from flask_cors import CORS

from routes.auth import auth_bp
from routes.informations import informations_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})


app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(informations_bp, url_prefix="/informations")

@app.route("/")
def home():
    return {"status": "Backend is running 🚀"}

if __name__ == "__main__":
    app.run()
