from fastapi.encoders import jsonable_encoder
import requests
from flask import Flask, make_response, redirect, render_template, request, jsonify, url_for

from dataTypes import Permission, Subscription

app = Flask(__name__)
url = "http://localhost:8000"

@app.route("/")
def main():
    user_cookie = request.cookies.get('user')
    if not user_cookie:
        return redirect(url_for('login'))
    try:
        response = requests.get(url + "/users/" + user_cookie)
        response_data = response.json()
        admin = response_data["data"]["admin"]
        if admin:
            response = requests.get(url + "/admin/users?userID=" + user_cookie)
            user_data = response.json()["data"]
            response = requests.get(url + "/admin/subscriptions?userID=" + user_cookie)
            sub_data = response.json()["data"]
            response = requests.get(url + "/admin/permissions?userID=" + user_cookie)
            perm_data = response.json()["data"]
            return render_template("admin.html", 
                                   user_data=user_data, 
                                   sub_data=sub_data, 
                                   perm_data=perm_data)
        else:
            user = response_data["data"]
            if user['subscription'] == "":
                return render_template("index.html", user=user)
            response = requests.get(url + "/subscriptions/" + user["subscription"])
            response_data = response.json()
            subscription = response_data["data"]
            print(subscription)
            permissions = []
            for perm in subscription["permissions"]:
                response = requests.get(url + "/permissions/" + perm)
                perm_data = response.json()["data"]
                permissions.append(perm_data)
                print(perm_data)
            return render_template("index.html", 
                                   user=user, 
                                   subscription=subscription, 
                                   permissions=permissions)
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
            print(response_data)
            resp = make_response(redirect(url_for('main')))
            if 'error' in response_data:
                return jsonify(response_data)
            resp.set_cookie('user', response_data["data"]["_id"])
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


@app.route("/create_permission", methods=["GET", "POST"])
def createPermission():
    if request.method == "POST":
        try:
            data = request.form.to_dict()
            permission = {
                "name": data.get("permission_name"),
                "desc": data.get("permission_description"),
                "access": data.get("access"),
                "user_id": request.cookies.get("user")
            }
            response = requests.post(url + "/permissions",
                                     json=permission,
                                     headers={'Content-Type': "application/json"}
                                    )
            response_data = response.json()
            print(response_data)
            return redirect(url_for("main"))
        except Exception as e:
            return jsonify({"error": str(e)})
    return render_template('admin_perms.html')


@app.route("/edit_permission/<permission_id>", methods=["GET", "POST"])
def editPermission(permission_id):
    if request.method == "POST":
        data = request.form.to_dict()
        permission_data = Permission(**data)
        json_data = jsonable_encoder(permission_data)
        response = requests.put(url + "/permissions/" + permission_id,
                                json=json_data,
                                headers={'Content-Type': "application/json"})
        response_data = response.json()
        print(response_data)
        return redirect(url_for("main"))
    permission = requests.get(url + "/permissions/" + permission_id)
    permission_data = permission.json()["data"]
    print(permission_data)
    return render_template('edit_permission.html', permission=permission_data)


@app.route("/create_subscription", methods=["GET", "POST"])
def createSubscription():
    if request.method == "POST":
        data = request.form.to_dict()
        print("form data: " + str(data))
        subscription = {
            "name": data.get("name"),
            "desc": data.get("description"),
            "access_limit": data.get("limit"),
            "auto": data.get("auto") == 'on',
        }
        response = requests.post(url + "/subscriptions",
                                 json=subscription,
                                 headers={'Content-Type': "application/json"})
        response_data = response.json()
        print(response_data)
        subID = response_data["data"]

        tier = data["plan"]
        permission = 0
        while tier != "tier" + str(permission):
            permission += 1
            response = requests.get(url + "/access/" + "tier" + str(permission))
            response_data = response.json()
            print(response_data)
            permission_data = response_data["data"]
            response = requests.put(url + "/subscriptions/" + subID + "/permission/" + permission_data["_id"],
                                    headers={'Content-Type': "application/json"})
            print(response.json())

        response = requests.get(url + "/username/" + data.get("username"))
        response_data = response.json()
        print(response_data)
        login_data = {"user_id": request.cookies.get("user")}
        response = requests.put(url + "/admin/user/" + response_data["data"]["_id"] + "/subscription/" + subID,
                                json=login_data,
                                headers={'Content-Type': "application/json"})
        print(response.json())
        if response_data["data"]["subscription"] != "":
            response = requests.delete(url + "/subscriptions/" + response_data["data"]["subscription"])
        return redirect(url_for("main"))
    return render_template('admin_subs.html')


@app.route("/admin_edit_subscription/<subscription_id>", methods=["GET", "POST"])
def editSubscription(subscription_id):
    if request.method == "POST":
        data = request.form.to_dict()
        response = requests.get(url + "/subscriptions/" + subscription_id)
        response_data = response.json()
        print(response_data)
        data["permissions"] = response_data["data"]["permissions"]
        subscription_data = Subscription(**data)
        json_data = jsonable_encoder(subscription_data)
        response = requests.put(url + "/subscriptions/" + subscription_id,
                                json=json_data,
                                headers={'Content-Type': "application/json"})
        response_data = response.json()
        print(response_data)
        return redirect(url_for("main"))
    subscription = requests.get(url + "/subscriptions/" + subscription_id)
    subscription_data = subscription.json()["data"]
    print(subscription_data)
    return render_template('admin_edit_subscription.html', subscription=subscription_data)


@app.route("/add_perm/<subscription_id>", methods=["POST"])
def addPerm(subscription_id):
    data = request.form.to_dict()
    response = requests.get(url + "/access/" + data.get("permission_name"))
    response_data = response.json()
    print(response_data)
    permission_data = response_data["data"]
    response = requests.put(url + "/subscriptions/" + subscription_id + "/permission/" + permission_data["_id"],
                            headers={'Content-Type': "application/json"})
    print(response.json())
    return redirect(url_for("main"))


@app.route("/delete_subscription/<subscription_id>", methods=["POST"])
def deleteSubscription(subscription_id):
    response = requests.delete(url + "/subscriptions/" + subscription_id)
    response_data = response.json()
    print(response_data)
    response = requests.get(url + "/user/subscription/" + subscription_id)
    print(response.json())
    data = {"subscription": ""}
    if "data" in response.json():
        response = requests.put(url + "/user/subscription/" + subscription_id, 
                                json=data,
                                headers={'Content-Type': "application/json"})
        print(response.json())
    return redirect(url_for("main"))


@app.route("/delete_permission/<permission_id>", methods=["POST"])
def deletePermission(permission_id):
    response = requests.delete(url + "/permissions/" + permission_id)
    response_data = response.json()
    print(response_data)
    reponse = requests.put(url + "/delete/permission/" + permission_id)
    print(response.json())
    return redirect(url_for("main"))


@app.route("/delete_user/<user_id>/<sub_id>", methods=["POST"])
def deleteUser(user_id, sub_id):
    response = requests.delete(url + "/user/" + user_id)
    response_data = response.json()
    if sub_id:
        response = requests.delete(url + "/subscriptions/" + sub_id)
    print(response_data)
    return redirect(url_for("main"))


@app.route("/add_permission/", methods=["GET", "POST"])
def addPermission():
    if request.method == "POST":
        try: 
            userID = request.cookies.get("user")
            data = request.form.to_dict()
            response = requests.get(url + "/access/" + data.get("permission_access"))
            response_data = response.json()
            print(response_data)
            permission_data = response_data["data"]
            response = requests.get(url + "/users/" + userID)
            user_data = response.json()
            print(user_data)
            response = requests.put(url + "/subscriptions/" + user_data["data"]["subscription"] + "/permission/" + permission_data["_id"])
            print(response.json())
            return redirect(url_for("main"))
        except Exception as e:
            return jsonify({"error": str(e)})
    return render_template("add_permission.html")


@app.route("/remove_permission/", methods=["POST"])
def removePermission():
    data = request.form.to_dict()
    response = requests.get(url + "/access/" + data.get("permission_name"))
    response_data = response.json()
    print(response_data)
    permission_data = response_data["data"]
    response = requests.delete(url + "/delete/permission/" + permission_data["_id"] + "/subscription/" + response_data["subscription_id"])
    print(response.json())
    return redirect(url_for("main"))


@app.route("/change_subscription/", methods=["GET", "POST"])
def changeSubscription():
    if request.method == "POST":
        userID = request.cookies.get("user")
        user = requests.get(url + "/users/" + userID)
        user = user.json()["data"]
        data = request.form.to_dict()
        access_limit = 100 if data.get("subscription") == "tier1" else 200 if data.get("subscription") == "tier2" else 300
        subscription = {
            "name": str(user["username"] + "'s subscription"),
            "desc": str(user["username"] + "'s" + data.get("subscription") + "subscription"),
            "access_limit": access_limit,
            "auto": data.get("auto") == "on",
        }
        response = requests.post(url + "/subscriptions",
                                 json=subscription,
                                 headers={'Content-Type': "application/json"})
        response_data = response.json()
        print(response_data)
        subID = response_data["data"]

        tier = data["subscription"]
        permission = 0
        while tier != "tier" + str(permission):
            permission += 1
            response = requests.get(url + "/access/" + "tier" + str(permission))
            response_data = response.json()
            print(response_data)
            permission_data = response_data["data"]
            response = requests.put(url + "/subscriptions/" + subID + "/permission/" + permission_data["_id"],
                                    headers={'Content-Type': "application/json"})
            print(response.json())
        response = requests.put(url + "/user/" + userID + "/subscription/" + subID)
        print(response.json())

        if user["subscription"] != "":
            response = requests.delete(url + "/subscriptions/" + user["subscription"])
        return redirect(url_for("main"))
    return render_template("change_subscription.html")


@app.route("/cancel_subscription/", methods=["POST"])
def cancelSubscription():
    userID = request.cookies.get("user")
    response = requests.put(url + "/user/" + userID + "/remove_subscription")
    print(response.json())
    return redirect(url_for("main"))


@app.route("/tier1")
def tier1Content():
    userID = request.cookies.get("user")
    response = requests.get(url + "/view/" + userID + "/tier1")
    response_data = response.json()
    if "error" in response_data:
        return jsonify(response_data)
    return '''
    <h1>tier1</h1>
    <p>You are viewing tier 1 content</p>
    <a href="/">Back to main</a>
    '''


@app.route("/tier2")
def tier2Content():
    userID = request.cookies.get("user")
    response = requests.get(url + "/view/" + userID + "/tier2")
    response_data = response.json()
    if "error" in response_data:
        return jsonify(response_data)
    return '''
    <h1>tier2</h1>
    <p>You are viewing tier 2 content</p>
    <a href="/">Back to main</a>
    '''


@app.route("/tier3")
def tier3Content():
    userID = request.cookies.get("user")
    response = requests.get(url + "/view/" + userID + "/tier3")
    response_data = response.json()
    if "error" in response_data:
        return jsonify(response_data)
    return '''
    <h1>tier3</h1>
    <p>You are viewing tier 3 content</p>
    <a href="/">Back to main</a>
    '''

@app.route("/special")
def specialContent():
    userID = request.cookies.get("user")
    response = requests.get(url + "/view/" + userID + "/special")
    response_data = response.json()
    if "error" in response_data:
        return jsonify(response_data)
    return '''
    <h1>special</h1>
    <p>You are viewing special content</p>
    <a href="/">Back to main</a>
    '''


if __name__ == "__main__":
    app.run(port=5000)