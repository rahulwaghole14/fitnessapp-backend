from flask import Flask, render_template, request, redirect, url_for, flash
import requests

app = Flask(__name__)
app.secret_key = "secret315"

FASTAPI_URL = "http://127.0.0.1:8001"

@app.route("/")
def login_page():
    return render_template("login.html")

@app.route("/register")
def register_page():
    return render_template("register.html")

@app.route("/forgot-password")
def forgot_password_page():
    return render_template("forgot_password.html")

@app.route("/forgot-password/verify/<email>")
def forgot_password_verify_page(email):
    return render_template("forgot_password_verify.html", email=email)

@app.route("/forgot-password/reset/<email>/<otp>")
def forgot_password_reset_page(email, otp):
    return render_template("forgot_password_reset.html", email=email, otp=otp)


#Regitration using OTP
# @app.route("/do-register", methods=["POST"])
# def do_register():
#     data = {
#         "email": request.form.get("email"),
#         "password": request.form.get("password")
#     }
#
#     try:
#         response = requests.post(
#             f"{FASTAPI_URL}/register",
#             json=data,
#             timeout=5
#         )
#
#         # ✅ Check response type safely
#         if "application/json" in response.headers.get("Content-Type", ""):
#             result = response.json()
#         else:
#             flash("Invalid response from authentication service")
#             return redirect(url_for("register_page"))
#
#         # ❌ Error from FastAPI
#         if response.status_code != 200:
#             flash(result.get("detail", "Registration failed"))
#             return redirect(url_for("register_page"))
#
#         # ✅ Success → go to OTP verification
#         flash(result.get("message", "OTP sent to your email"))
#         return redirect(url_for("verify_otp", email=data["email"]))
#
#     except requests.exceptions.Timeout:
#         flash("FastAPI service timeout")
#         return redirect(url_for("register_page"))
#
#     except requests.exceptions.ConnectionError:
#         flash("FastAPI service is not running")
#         return redirect(url_for("register_page"))
#
#     except requests.exceptions.RequestException:
#         flash("Something went wrong")
#         return redirect(url_for("register_page"))
#
# @app.route("/verify-otp/<email>")
# def verify_otp(email):
#     return render_template("verify_otp.html", email=email)
#
# @app.route("/do-verify", methods=["POST"])
# def do_verify():
#     data = {
#         "email": request.form.get("email"),
#         "otp": request.form.get("otp")
#     }
#
#     try:
#         response = requests.post(
#             f"{FASTAPI_URL}/verify-otp",
#             json=data,
#             timeout=5
#         )
#
#         if "application/json" in response.headers.get("Content-Type", ""):
#             result = response.json()
#         else:
#             flash("Invalid response from authentication service")
#             return redirect(url_for("verify_otp", email=data["email"]))
#
#         if response.status_code != 200:
#             flash(result.get("detail", "OTP verification failed"))
#             return redirect(url_for("verify_otp", email=data["email"]))
#
#         flash(result.get("message", "Email verified successfully"))
#         return redirect(url_for("login_page"))
#
#     except requests.exceptions.Timeout:
#         flash("FastAPI service timeout")
#         return redirect(url_for("verify_otp", email=data["email"]))
#
#     except requests.exceptions.ConnectionError:
#         flash("FastAPI service is not running")
#         return redirect(url_for("verify_otp", email=data["email"]))
#
#     except requests.exceptions.RequestException:
#         flash("Something went wrong")
#         return redirect(url_for("verify_otp", email=data["email"]))
#
# @app.route("/resend-otp", methods=["POST"])
# def resend_otp():
#     data = {
#         "email": request.form.get("email")
#     }
#
#     try:
#         response = requests.post(
#             f"{FASTAPI_URL}/resend-otp",
#             json=data,
#             timeout=5
#         )
#
#         if "application/json" in response.headers.get("Content-Type", ""):
#             result = response.json()
#         else:
#             flash("Invalid response from authentication service")
#             return redirect(url_for("verify_otp", email=data["email"]))
#
#         if response.status_code != 200:
#             flash(result.get("detail", "OTP resend failed"))
#             return redirect(url_for("verify_otp", email=data["email"]))
#
#         flash(result.get("message", "New OTP sent to your email"))
#         return redirect(url_for("verify_otp", email=data["email"]))
#
#     except requests.exceptions.Timeout:
#         flash("FastAPI service timeout")
#         return redirect(url_for("verify_otp", email=data["email"]))
#
#     except requests.exceptions.ConnectionError:
#         flash("FastAPI service is not running")
#         return redirect(url_for("verify_otp", email=data["email"]))
#
#     except requests.exceptions.RequestException:
#         flash("Something went wrong")
#         return redirect(url_for("verify_otp", email=data["email"]))

@app.route("/do-register", methods=["POST"])
def do_register():
    data = {
        "username": request.form["username"],
        "email": request.form["email"],
        "password": request.form["password"]
    }

    response = requests.post(f"{FASTAPI_URL}/register", json=data)
    return response.json()

# FORGOT PASSWORD - SEND OTP
@app.route("/forgot-password/send-otp", methods=["POST"])
def forgot_password_send_otp():
    data = {
        "email": request.form.get("email")
    }

    try:
        response = requests.post(
            f"{FASTAPI_URL}/forgot-password/send-otp",
            json=data,
            timeout=5
        )

        if "application/json" in response.headers.get("Content-Type", ""):
            result = response.json()
        else:
            flash("Invalid response from authentication service")
            return redirect(url_for("forgot_password_page"))

        if response.status_code != 200:
            flash(result.get("detail", "OTP send failed"))
            return redirect(url_for("forgot_password_page"))

        flash(result.get("message", "Password reset OTP sent to your email"))
        return redirect(url_for("forgot_password_verify_page", email=data["email"]))

    except requests.exceptions.Timeout:
        flash("FastAPI service timeout")
        return redirect(url_for("forgot_password_page"))

    except requests.exceptions.ConnectionError:
        flash("FastAPI service is not running")
        return redirect(url_for("forgot_password_page"))

    except requests.exceptions.RequestException:
        flash("Something went wrong")
        return redirect(url_for("forgot_password_page"))

# FORGOT PASSWORD - VERIFY OTP
@app.route("/forgot-password/verify-otp", methods=["POST"])
def forgot_password_verify_otp():
    data = {
        "email": request.form.get("email"),
        "otp": request.form.get("otp")
    }

    try:
        response = requests.post(
            f"{FASTAPI_URL}/forgot-password/verify-otp",
            json=data,
            timeout=5
        )

        if "application/json" in response.headers.get("Content-Type", ""):
            result = response.json()
        else:
            flash("Invalid response from authentication service")
            return redirect(url_for("forgot_password_verify_page", email=data["email"]))

        if response.status_code != 200:
            flash(result.get("detail", "OTP verification failed"))
            return redirect(url_for("forgot_password_verify_page", email=data["email"]))

        flash(result.get("message", "OTP verified successfully"))
        return redirect(url_for("forgot_password_reset_page", email=data["email"], otp=data["otp"]))

    except requests.exceptions.Timeout:
        flash("FastAPI service timeout")
        return redirect(url_for("forgot_password_verify_page", email=data["email"]))

    except requests.exceptions.ConnectionError:
        flash("FastAPI service is not running")
        return redirect(url_for("forgot_password_verify_page", email=data["email"]))

    except requests.exceptions.RequestException:
        flash("Something went wrong")
        return redirect(url_for("forgot_password_verify_page", email=data["email"]))


# FORGOT PASSWORD - RESET PASSWORD
@app.route("/forgot-password/reset-password", methods=["POST"])
def forgot_password_reset_password():
    new_password = request.form.get("new_password")
    confirm_password = request.form.get("confirm_password")

    # Validate password confirmation
    if new_password != confirm_password:
        flash("Passwords do not match")
        return redirect(url_for("forgot_password_reset_page",
                                email=request.form.get("email"),
                                otp=request.form.get("otp")))

    data = {
        "email": request.form.get("email"),
        "otp": request.form.get("otp"),
        "new_password": new_password
    }

    try:
        response = requests.post(
            f"{FASTAPI_URL}/forgot-password/reset-password",
            json=data,
            timeout=5
        )

        if "application/json" in response.headers.get("Content-Type", ""):
            result = response.json()
        else:
            flash("Invalid response from authentication service")
            return redirect(url_for("forgot_password_reset_page",
                                    email=data["email"], otp=data["otp"]))

        if response.status_code != 200:
            flash(result.get("detail", "Password reset failed"))
            return redirect(url_for("forgot_password_reset_page",
                                    email=data["email"], otp=data["otp"]))

        flash(result.get("message", "Password reset successfully"))
        return redirect(url_for("login_page"))

    except requests.exceptions.Timeout:
        flash("FastAPI service timeout")
        return redirect(url_for("forgot_password_reset_page",
                                email=data["email"], otp=data["otp"]))

    except requests.exceptions.ConnectionError:
        flash("FastAPI service is not running")
        return redirect(url_for("forgot_password_reset_page",
                                email=data["email"], otp=data["otp"]))

    except requests.exceptions.RequestException:
        flash("Something went wrong")
        return redirect(url_for("forgot_password_reset_page",
                                email=data["email"], otp=data["otp"]))


@app.route("/do-login", methods=["POST"])
def do_login():
    data = {
        "email": request.form.get("email"),
        "password": request.form.get("password")
    }

    try:
        response = requests.post(
            f"{FASTAPI_URL}/login",
            json=data,
            timeout=5
        )

        if "application/json" in response.headers.get("Content-Type", ""):
            result = response.json()
        else:
            flash("Invalid response from authentication service")
            return redirect(url_for("login_page"))

        if response.status_code != 200:
            flash(result.get("detail", "Login failed"))
            return redirect(url_for("login_page"))

        flash(result.get("message", "Login successful"))
        return redirect(url_for("dashboard"))

    except requests.exceptions.Timeout:
        flash("FastAPI service timeout")
        return redirect(url_for("login_page"))

    except requests.exceptions.ConnectionError:
        flash("FastAPI service is not running")
        return redirect(url_for("login_page"))

    except requests.exceptions.RequestException:
        flash("Something went wrong")
        return redirect(url_for("login_page"))

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

if __name__ == "__main__":
    app.run(debug=True, port=5000)
