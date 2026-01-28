from flask import Blueprint, request, jsonify
from db.supabase import supabase
import jwt
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

auth_bp = Blueprint("auth", __name__)
SECRET_KEY = os.getenv("JWT_SECRET", "mysecretkey") 

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    response = supabase.table("users") \
        .select("*") \
        .eq("email", email) \
        .eq("user_code", password) \
        .execute()

    if not response.data:
        return jsonify({"error": "Invalid credentials"}), 401

    user = response.data[0]

   
    expiration = datetime.utcnow() + timedelta(days=15)
    token = jwt.encode(
        {"user_id": user["id"], "exp": expiration},
        SECRET_KEY,
        algorithm="HS256"
    )

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user_id": user["id"],
        "role": user["role"]
    })
