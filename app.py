from flask import Flask
from flask_cors import CORS
import time

from routes.auth import auth_bp
from routes.informations import informations_bp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

start_time = time.time()


app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(informations_bp, url_prefix="/informations")

@app.route("/")
def home():
    return {"status": "Backend is running "}

@app.route("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": int(time.time() - start_time)
    }, 200

@app.route("/ready")
def ready():
    return {"ready": True}, 200

if __name__ == "__main__":
    app.run()
