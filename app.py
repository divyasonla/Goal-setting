from flask import Flask, render_template, request, redirect, session
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

import os
import json
app = Flask(__name__)
app.secret_key = "your_secret_key"

# ================= GOOGLE SHEETS CONNECTION =================

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

# # creds = ServiceAccountCredentials.from_json_keyfile_name(
# #     "credentials.json", scope
# # )
# creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)

# Load credentials from individual environment variables
credentials_dict = {
    "type": os.getenv("GOOGLE_CREDENTIALS_TYPE"),
    "project_id": os.getenv("GOOGLE_CREDENTIALS_PROJECT_ID"),
    "private_key_id": os.getenv("GOOGLE_CREDENTIALS_PRIVATE_KEY_ID"),
    "private_key": os.getenv("GOOGLE_CREDENTIALS_PRIVATE_KEY"),
    "client_email": os.getenv("GOOGLE_CREDENTIALS_CLIENT_EMAIL"),
    "client_id": os.getenv("GOOGLE_CREDENTIALS_CLIENT_ID"),
    "auth_uri": os.getenv("GOOGLE_CREDENTIALS_AUTH_URI"),
    "token_uri": os.getenv("GOOGLE_CREDENTIALS_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("GOOGLE_CREDENTIALS_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("GOOGLE_CREDENTIALS_CLIENT_CERT_URL")
}

# scope = ['https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
client = gspread.authorize(creds)
# daily_sheet = client.open_by_key("1yFw0FeX48fpOHYAH3ozjb3Dnn8z-ME1ZSXXvJkGo3J8").worksheet("dailygoals")
daily_sheet = client.open_by_key("1yFw0FeX48fpOHYAH3ozjb3Dnn8z-ME1ZSXXvJkGo3J8").worksheet("DailyGoals")
weekly_sheet = client.open_by_key("1yFw0FeX48fpOHYAH3ozjb3Dnn8z-ME1ZSXXvJkGo3J8").worksheet("WeeklyGoals")
users_sheet = client.open_by_key("1yFw0FeX48fpOHYAH3ozjb3Dnn8z-ME1ZSXXvJkGo3J8").worksheet("Users")


@app.route("/")
def index():

    if "email" not in session:
        return redirect("/login")

    daily_data = daily_sheet.get_all_records()
    weekly_data = weekly_sheet.get_all_records()

    daily_goals = []
    weekly_goals = []

    completed = 0

    # ================= TEACHER =================

    if session.get("role") == "Teacher":

        for r in daily_data:
            daily_goals.append(r["DailyGoal"])

            if r.get("Status") == "Completed":
                completed += 1

        for r in weekly_data:
            weekly_goals.append(r["WeeklyGoal"])

    # ================= STUDENT =================

    else:

        email = session["email"]

        for r in daily_data:
            if r["Email"] == email:
                daily_goals.append(r["DailyGoal"])

                if r.get("Status") == "Completed":
                    completed += 1

        for r in weekly_data:
            if r["Email"] == email:
                weekly_goals.append(r["WeeklyGoal"])

    # ================= STATS =================

    total_daily = len(daily_goals)
    in_progress = total_daily - completed

    weekly_rate = int((completed / total_daily) * 100) if total_daily > 0 else 0

    return render_template(
        "index.html",
        username=session["username"],
        daily_goals=daily_goals,
        weekly_goals=weekly_goals,

        total_daily=total_daily,
        completed=completed,
        in_progress=in_progress,
        weekly_rate=weekly_rate
    )


@app.route("/signup", methods=["GET","POST"])
def signup():

    if request.method == "POST":

        users_sheet.append_row([
            request.form.get("username"),
            request.form.get("email"),
            request.form.get("password"),
            request.form.get("role"),
        ])

        return redirect("/login")

    return render_template("signup.html")

# ================= LOGIN =================

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        users = users_sheet.get_all_records()

        for u in users:
            if u["Email"] == request.form["email"] and u["Password"] == request.form["password"]:
                session["email"] = u["Email"]
                session["username"] = u["Username"]
                session['role'] = u["Role"]
                return redirect("/")

        return "Invalid Login"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/profile")
def profile():

    if "email" not in session:
        return redirect("/login")

    email = session["email"]

    users = users_sheet.get_all_records()

    user_details = None

    for u in users:
        if u["Email"] == email:
            user_details = u
            break

    if user_details:
        session["username"] = user_details["Username"]
        return render_template("profile.html", user=user_details)

    return "User not found"
# ================= DAILY CREATE =================

@app.route("/daily")
def daily():
    return render_template("daily.html")

@app.route("/save_daily", methods=["POST"])
def save_daily():

    daily_sheet.append_row([
    session["username"],
    session["email"],
    request.form["goal"],
    "", "", "", "",
    "In Progress",   # STATUS DEFAULT
    request.form["day"]
    ])

    return redirect("/view_daily")

# ================= VIEW DAILY =================

@app.route("/view_daily")
def view_daily():

    records = daily_sheet.get_all_records()
    goals = []

    for i, r in enumerate(records):

        r["row"] = i+2

        # Teacher sees all
        if session["role"] == "Teacher":
            goals.append(r)

        # Student sees own
        elif r["Email"].strip() == session["email"].strip():
            goals.append(r)

    return render_template("view_daily.html", goals=goals)


# ================= UPDATE DAILY =================

@app.route("/update_daily/<int:row>")
def update_daily(row):

    data = daily_sheet.row_values(row)

    return render_template("update_daily.html", row=row, data=data)

@app.route("/save_update_daily/<int:row>", methods=["POST"])
def save_update_daily(row):

    daily_sheet.update_cell(row,3,request.form["goal"])
    daily_sheet.update_cell(row,4,request.form["reflection"])
    daily_sheet.update_cell(row,5,request.form["wentwell"])
    daily_sheet.update_cell(row,6,request.form["challenges"])
    daily_sheet.update_cell(row,7,request.form["left"])
    daily_sheet.update_cell(row,8,request.form["status"])
    daily_sheet.update_cell(row,9,request.form["day"])
    return redirect("/view_daily")

# ================= DELETE DAILY =================

@app.route("/delete_daily/<int:row>")
def delete_daily(row):

    if session["role"] != "Teacher":
        return redirect("/view_daily")

    daily_sheet.delete_rows(row)
    return redirect("/view_daily")


# ================= WEEKLY CREATE =================

@app.route("/weekly")
def weekly():
    return render_template("weekly.html")

@app.route("/save_weekly", methods=["POST"])
def save_weekly():

    weekly_sheet.append_row([
    session["username"],
    session["email"],
    request.form["goal"],
    "", "", "", "",
    "In Progress",          # STATUS
    request.form["week"]
])


    return redirect("/view_weekly")

# ================= VIEW WEEKLY =================

@app.route("/view_weekly")
def view_weekly():

    records = weekly_sheet.get_all_records()
    goals = []

    for i,r in enumerate(records):
        if session["role"]=="Teacher":
            goals.append(r)
        if r["Email"] == session["email"]:
            r["row"] = i+2
            goals.append(r)

    return render_template("view_weekly_goals.html", goals=goals)

# ================= UPDATE WEEKLY =================

@app.route("/update_weekly/<int:row>")
def update_weekly(row):

    data = weekly_sheet.row_values(row)

    return render_template("update_weekly.html", row=row, data=data)

@app.route("/save_update_weekly/<int:row>", methods=["POST"])
def save_update_weekly(row):

    weekly_sheet.update_cell(row,3,request.form["goal"])
    weekly_sheet.update_cell(row,4,request.form["reflection"])
    weekly_sheet.update_cell(row,5,request.form["wentwell"])
    weekly_sheet.update_cell(row,6,request.form["challenges"])
    weekly_sheet.update_cell(row,7,request.form["left"])
    weekly_sheet.update_cell(row,8,request.form["status"])

    return redirect("/view_weekly")
# ================= DELETE WEEKLY =================

@app.route("/delete_weekly/<int:row>")
def delete_weekly(row):

    if session["role"] != "Teacher":
        return redirect("/view_weekly")

    weekly_sheet.delete_rows(row)
    return redirect("/view_weekly")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))  # Default to 5000 if PORT is not set
    app.run(debug=True, port=port)