from flask import Blueprint, request, jsonify
from db.supabase import supabase
import jwt
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET", "mysecretkey")

informations_bp = Blueprint("informations", __name__)

# =========================
# AUTH HELPERS
# =========================
def verify_token(request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, "Missing token"

    try:
        token = auth_header.split(" ")[1]
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return decoded, None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except Exception as e:
        return None, str(e)


def get_user_role(user_id):
    try:
        res = (
            supabase.table("users")
            .select("role, email")
            .eq("id", user_id)
            .single()
            .execute()
        )
        if res.data:
            return res.data["role"], res.data["email"]
        return None, None
    except Exception:
        return None, None


def require_role(user_id, allowed_roles):
    role, email = get_user_role(user_id)
    if not role:
        return False, "User not found"
    if role not in allowed_roles:
        return False, "Access denied"
    return True, {"role": role, "email": email}


# =========================
# D – ADD INFORMATION
# =========================
@informations_bp.route("/add", methods=["POST"])
def add_information():
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    data = request.json or {}

    if not all([
        data.get("type_bu"),
        data.get("type_info"),
        data.get("info_date")
    ]):
        return jsonify({"error": "Missing required fields"}), 400

    res = supabase.table("informations").insert({
        "user_id": decoded["user_id"],
        "type_bu": data.get("type_bu"),
        "type_info": data.get("type_info"),
        "laboratoire": data.get("laboratoire"),
        "produit_concurent": data.get("produit"),
        "info_date": data.get("info_date"),
        "comment": data.get("comment"),
    }).execute()

    return jsonify({
        "message": "Information saved",
        "data": res.data
    }), 201


# =========================
# D / A – MY INFORMATIONS
# =========================
@informations_bp.route("/my-informations", methods=["GET"])
def get_my_informations():
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    allowed, _ = require_role(decoded["user_id"], ["D", "A"])
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    infos = (
        supabase.table("informations")
        .select("*")
        .eq("user_id", decoded["user_id"])
        .order("created_at", desc=True)
        .execute()
    )

    return jsonify({
        "count": len(infos.data),
        "data": infos.data
    })


# =========================
# USER PROFILE
# =========================
@informations_bp.route("/profile", methods=["GET"])
def get_profile():
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    user = (
        supabase
        .table("users")
        .select("email, role, view")
        .eq("id", decoded["user_id"])
        .single()
        .execute()
    )

    if not user.data:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "user_id": decoded["user_id"],
        "email": user.data["email"],
        "role": user.data["role"],
        "view": user.data["view"],  # 👈 added
        "name": user.data["email"].split("@")[0]
    })



# =========================
# A – ALL INFORMATIONS (FILTERS)
# =========================
@informations_bp.route("/all-informations", methods=["GET"])
def get_all_informations():
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    allowed, _ = require_role(decoded["user_id"], ["A"])
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    query = supabase.table("informations").select("*, users(email)")

    if request.args.get("date"):
        query = query.eq("info_date", request.args.get("date"))

    if request.args.get("from") and request.args.get("to"):
        query = query.gte("info_date", request.args.get("from")).lte(
            "info_date", request.args.get("to")
        )

    if request.args.get("type_bu"):
        query = query.eq("type_bu", request.args.get("type_bu"))

    if request.args.get("type_info"):
        query = query.eq("type_info", request.args.get("type_info"))

    if request.args.get("user_id"):
        query = query.eq("user_id", request.args.get("user_id"))

    res = query.order("created_at", desc=True).execute()

    return jsonify({
        "count": len(res.data),
        "data": res.data
    })


# =========================
# A – USERS MANAGEMENT
# =========================
@informations_bp.route("/users", methods=["GET"])
def get_users():
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    allowed, _ = require_role(decoded["user_id"], ["A"])
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    users = (
        supabase
        .table("users")
        .select("id, email, role, user_code, view, created_at")  # 👈 view added
        .order("created_at", desc=True)
        .execute()
    )

    return jsonify(users.data)



@informations_bp.route("/users", methods=["POST"])
def create_user():
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    allowed, _ = require_role(decoded["user_id"], ["A"])
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    data = request.json or {}

    email = data.get("email")
    user_code = data.get("user_code")
    role = data.get("role", "D")
    view = data.get("view")  

    if not email or not user_code:
        return jsonify({"error": "Email and user_code are required"}), 400

    if role not in ["A", "D", "R"]:
        return jsonify({"error": "Invalid role"}), 400

    # 👇 Require view ONLY for role R
    if role == "R" and not view:
        return jsonify({"error": "View is required for role R"}), 400

    # 👇 Prevent view for non-R roles
    if role != "R" and view is not None:
        return jsonify({"error": "View is only allowed for role R"}), 400

    if supabase.table("users").select("id").eq("email", email).execute().data:
        return jsonify({"error": "Email already exists"}), 400

    if supabase.table("users").select("id").eq("user_code", user_code).execute().data:
        return jsonify({"error": "User code already exists"}), 400

    user_data = {
        "email": email,
        "user_code": user_code,
        "role": role
    }

    # 👇 Add view only when role == R
    if role == "R":
        user_data["view"] = view

    res = supabase.table("users").insert(user_data).execute()

    return jsonify({
        "message": "User created successfully",
        "data": res.data
    }), 201


@informations_bp.route("/users/<user_id>", methods=["PUT"])
def update_user(user_id):
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    allowed, _ = require_role(decoded["user_id"], ["A"])
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    data = request.json or {}
    update_data = {}

    # Get current user (needed for role/view logic)
    current_user = (
        supabase
        .table("users")
        .select("role, view")
        .eq("id", user_id)
        .single()
        .execute()
    )

    if not current_user.data:
        return jsonify({"error": "User not found"}), 404

    current_role = current_user.data["role"]

    # ========= BASIC FIELDS =========
    if "email" in data:
        update_data["email"] = data["email"]

    if "user_code" in data:
        update_data["user_code"] = data["user_code"]

    # ========= ROLE HANDLING =========
    new_role = current_role
    if "role" in data:
        if data["role"] not in ["A", "D", "R"]:
            return jsonify({"error": "Invalid role"}), 400
        new_role = data["role"]
        update_data["role"] = new_role

    # ========= VIEW HANDLING =========
    if new_role == "R":
        # Role is R → view REQUIRED
        if "view" not in data:
            return jsonify({"error": "View is required for role R"}), 400
        update_data["view"] = data["view"]
    else:
        # Role is NOT R → view MUST be null
        update_data["view"] = None

    if not update_data:
        return jsonify({"error": "No fields to update"}), 400

    supabase.table("users").update(update_data).eq("id", user_id).execute()

    return jsonify({"message": "User updated successfully"})


@informations_bp.route("/users/<user_id>", methods=["DELETE"])
def delete_user(user_id):
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    allowed, _ = require_role(decoded["user_id"], ["A"])
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    if str(user_id) == str(decoded["user_id"]):
        return jsonify({"error": "Cannot delete your own account"}), 400

    supabase.table("users").delete().eq("id", user_id).execute()
    return jsonify({"message": "User deleted successfully"})



@informations_bp.route("/my-view", methods=["GET"])
def get_my_view():
    decoded, error = verify_token(request)
    if error:
        return jsonify({"error": error}), 401

    allowed, user_data = require_role(decoded["user_id"], ["R"])
    if not allowed:
        return jsonify({"error": "Access denied"}), 403

    # Get the 'view' column (e.g., "CVS", "CNS", etc.)
    res_user = supabase.table("users").select("view").eq("id", decoded["user_id"]).single().execute()
    if not res_user.data or not res_user.data.get("view"):
        return jsonify({"error": "No view assigned to user"}), 403

    user_view = res_user.data.get("view").split(",")  # If multiple views, assume comma-separated
    user_view = [v.strip() for v in user_view]  # remove extra spaces

    # Build query
    query = supabase.table("informations").select("*")

    # Filter by user view (type_bu) unless it's "ALL"
    if "ALL" not in user_view:
        query = query.in_("type_bu", user_view)
    
    # If user has "ALL" view and wants to filter by specific BU
    else:
        type_bu = request.args.get("type_bu")
        if type_bu:
            query = query.eq("type_bu", type_bu)

    # Optional filters
    type_info = request.args.get("type_info")
    info_date = request.args.get("date")
    from_date = request.args.get("from")
    to_date = request.args.get("to")

    if type_info:
        query = query.eq("type_info", type_info)

    if info_date:
        query = query.eq("info_date", info_date)
    elif from_date and to_date:
        query = query.gte("info_date", from_date).lte("info_date", to_date)

    res = query.order("created_at", desc=True).execute()

    return jsonify({
        "count": len(res.data),
        "data": res.data
    })