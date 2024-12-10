import requests
from flask import Flask, make_response, redirect, render_template, request, jsonify, url_for

app = Flask(__name__)
url = "http://localhost:8000"

@app.route("/")
def main():
    user_cookie = request.cookies.get('user')
    if not user_cookie:
        return redirect(url_for('login'))
    try:
        response = requests.get(url + '/users/' + user_cookie)
        response_data = response.json()
        if response_data["data"]["admin"]:
            response = requests.get(url + "/admin/users?userID=" + user_cookie)
            user_data = response.json()["data"]
            response = requests.get(url + "/admin/subscriptions?userID=" + user_cookie)
            print(response.json())
            sub_data = response.json()["data"]
            response = requests.get(url + "/admin/permissions?userID=" + user_cookie)
            print(response.json())
            perm_data = response.json()["data"]
            return render_template("admin.html", 
                                   user_data=user_data, 
                                   sub_data=sub_data, 
                                   perm_data=perm_data)
        else:
            return render_template("index.html")
    except Exception as e:
        return jsonify({"error": str(e)})
    

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            data = request.form.to_dict()
            response = requests.post('http://localhost:8000/login', 
                                     json=data, 
                                     headers={'Content-Type': 'application/json'})
            response_data = response.json()
            resp = make_response(redirect(url_for('main')))
            resp.set_cookie('user', response_data["data"])
            return resp
        except Exception as e:
            return jsonify({"error": str(e)})
    return render_template('login.html')


@app.route("/logout", methods=["POST"])
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('user', '', expires=0)
    return resp


@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            data = request.form.to_dict()
            response = requests.post('http://localhost:8000/signup', 
                                     json=data, 
                                     headers={'Content-Type': 'application/json'})
            response_data = response.json()
            resp = make_response(redirect(url_for("login")))
            return resp
        except Exception as e:
            return jsonify({"error": str(e)})
    return render_template("register.html")


@app.route("/perm/create", methods=["GET"])
def createPermission():
    return render_template('admin_perms.html')


@app.route("/subscription/create", methods=["GET"])
def createSubscription():
    return render_template('admin_subs.html')



if __name__ == "__main__":
    app.run(port=5000)