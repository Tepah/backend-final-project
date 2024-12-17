import asyncio
from datetime import datetime, timedelta
from bson import ObjectId
from dateutil import parser
from fastapi import FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorClient
from dataTypes import Customer, Permission, Subscription
from pymongo.errors import DuplicateKeyError
import certifi

app = FastAPI()

mongo_client = AsyncIOMotorClient("mongodb+srv://potipitak:oDmCEpMls5C8CRRO@cluster0.korqo.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0",
                                  tlsCAFile=certifi.where())
db = mongo_client["backend-final"]
sub_col = db["subscriptions"]
user_col = db["users"]
perm_col = db["permissions"]


@app.get("/test")
async def test_connection():
    try:
        await mongo_client.admin.command('ping')
        print("Connected to MongoDB")
        return {"Message": "Connected to MongoDB"}
    except Exception as e:
        print(f"Error: {e}")
        return {"Error": str(e)}
    

# Subscription Based calls
@app.post("/subscriptions")
async def createSub(data: dict):
    try:
        data["start_date"] = datetime.now()
        subscription = Subscription(**data)
        encoded_sub = jsonable_encoder(subscription)
        result = await sub_col.insert_one(encoded_sub)
        return {"message": "Data has been inserted", "data": str(result.inserted_id)}
    except Exception as e:
        return {"Error" : str(e)}


@app.get("/subscriptions/{id}")
async def getSub(id: str):
    try:
        subscription = await sub_col.find_one({"_id": ObjectId(id)})
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        subscription = objToStr(subscription)
        return {"message": "Subscription found", "data": subscription}
    except Exception as e:
        return {"Error" : str(e)}


@app.put("/subscriptions/{id}")
async def modifySub(id: str, data: dict):
    try:
        print(id)
        subscription = await sub_col.find_one({"_id": ObjectId(id)})
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found.")
        
        updated_data = {**subscription, **data}
        print(updated_data)
        new_subscription = Subscription(**updated_data)
        encoded_sub = jsonable_encoder(new_subscription)
        result = await sub_col.update_one({"_id": ObjectId(id)}, {"$set":encoded_sub})
        return {"message": "Subscription was updated", "data": str(id)}
    except Exception as e:
        return {"Error" : str(e)}


@app.delete("/subscriptions/{id}")
def deleteSub(id: str):
    try:
        result = sub_col.delete_one({"_id": ObjectId(id)})
        return {"message": "Data has been deleted"}
    except Exception as e:
        return {"Error" : str(e)}


# Permission Based calls
@app.get("/permissions/{id}")
async def getPermission(id: str):
    try:
        permission = await perm_col.find_one({"_id": ObjectId(id)})
        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")
        permission = objToStr(permission)
        return {"message": "Permission found", "data": permission}
    except Exception as e:
        return {"Error" : str(e)}

@app.post("/permissions")
async def createPermission(data: dict):
    try:
        user_data = await user_col.find_one({"_id": ObjectId(data.get("user_id", ""))})
        if not user_data or not user_data["admin"]:
            raise HTTPException(status_code=403, detail="Admin required to create permissions")
        permission = Permission(**data)
        encoded_perm = jsonable_encoder(permission)
        res = await perm_col.insert_one(encoded_perm)
        return {"Message": "Permission Created", "Permission ID" : str(res.inserted_id)}
    except Exception as e:
        return {"Error" : str(e)}


@app.put("/permissions/{id}")
async def modifyPermission(id: str, data: dict):
    try:
        permission = Permission(**data)
        encoded_perm = jsonable_encoder(permission)
        res = perm_col.update_one({"_id": ObjectId(id)}, {"$set": encoded_perm})
        return {"message": "Permisssion was changed"}
    except Exception as e:
        return {"Error" : str(e)}

@app.delete("/permissions/{id}")
def deletePermission(id: str):
    try:
        result = perm_col.delete_one({"_id": ObjectId(id)})
        if result.deleted_count > 0:
            return {"message": "Permission has been deleted"}
        else:
            raise HTTPException(status_code=404, detail="Subscription not found")
    except Exception as e:
        return {"Error" : str(e)}


# Customer subscription functions
@app.put("/user/{userID}/subscription/{subID}")
async def changeUserSubscription(userID: str, subID: str):
    try:
        customer = await user_col.find_one({"_id": ObjectId(userID)})
        if not customer:
            raise HTTPException(status_code=404, detail="User not found")
        
        subscription = await sub_col.find_one({"_id": ObjectId(subID)})
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")
        
        customer["subscription"] = str(subscription["_id"])

        res = await user_col.update_one({"_id": ObjectId(userID)}, {"$set": customer})
        
        return {"message": "Subscription has been updated for user: " + userID + "to Subscription ID: " + subID}
    except Exception as e:
        return {"Error": str(e)}
    

@app.get("/user/subscription/{id}")
async def findUserWithSub(id):
    try:
        user = await user_col.find_one({"subscription": id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user = objToStr(user)
        return {"message": "User found", "data": user}
    except Exception as e:
        return {"Error": str(e)}

@app.put("/user/subscription/{id}")
async def changeSubForUser(id: str, data: dict):
    try:
        user = await user_col.find_one({"subscription": id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user["subscription"] = data["subscription"]
        result = user_col.update_one({"_id": ObjectId(user["_id"])}, {"$set": user})
        return {"message": "Subscription has been removed from user"}
    except Exception as e:
        return {"Error": str(e)}


@app.get("/user/{id}/subscription")
async def getUserSubscription(id: str):
    try:
        user = await user_col.find_one({"_id": ObjectId(id)})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        subscription = await sub_col.find_one({"_id": ObjectId(user["subscription"])})

        return {"message": "User subscription aquired", "data": subscription}
    except Exception as e:
        return {"Error": str(e)}


@app.get("/user/{id}/subscription/usage")
def getUserSubUsage(id: str):
    try:
        user = user_col.find_one({"_id": id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        subscription = sub_col.find_one({"_id": user["subscription"]})
        sub = Subscription(**subscription)
        return {"message": "User usage aquired", "requests": sub.get("requests", 0), "limit": sub.get("access_limit", 0)}
    except Exception as e:
        return {"Error": str(e)}


# Admin subscription function
@app.put("/admin/user/{userID}/subscription/")
async def adminAssignUserSub(userID: str, data: dict):
    try:
        user_data = await user_col.find_one({"_id": data.get("user_id", "")})
        if not user_data or not user_data["admin"]:
            raise HTTPException(status_code=403, detail="Logged in user does not have the required permissions.")
        
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        if not user_data:
            raise HTTPException(status_code=404, detail="User does not exist")

        subscription = data.get("subscription", None)
        create_call = await createSub(subscription)
        user = Customer(**user)
        user["subscription"] = create_call.get("data")
        encoded_user = jsonable_encoder(user)
        result = await user_col.update_one({"_id": ObjectId(userID)}, {"$set": encoded_user })
        return {"message": "Subscription for User" + {user["_id"]} + "has changed"}
    except Exception as e:
        return {"Error": str(e)}
    

@app.put("/admin/user/{userID}/subscription/{subID}")
async def adminChangeUserSub(userID: str, subID: str, data: dict):
    try:
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        if not user_data or not user_data["admin"]:
            raise HTTPException(status_code=403, detail="Admin priviledges are required")
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        if not user_data:
            raise HTTPException(status_code=404, detail="User does not exist")
        sub_id = await modifySub(subID, data.get("subscription", {}))
        
        if not sub_id:
            raise HTTPException(status_code=404, detail="Subscription not found")
        print(sub_id)
        user_data["subscription"] = sub_id["data"]
        user = Customer(**user_data)
        encoded_user = jsonable_encoder(user)
        result = user_col.update_one({"_id": ObjectId(userID)}, {"$set": encoded_user})
        return {"message": "Changed subscription for user"}
    except Exception as e:
        return {"Error": str(e)}
    

# Access Control function
@app.get("/access/{userID}/{request}")
async def checkUserAllowed(userID: str, request: str):
    try:
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        if "admin" in user_data and user_data["admin"]:
            return {"message": "User is an Admin", "data": True}
        sub_data = (await getUserSubscription(userID))["data"]
        if not sub_data:
            raise HTTPException(status_code=404, detail="No Subscription data was not found")
        sub = Subscription(**sub_data)

        sub_expired = (await checkUserSubscriptionExpire(userID))["data"]
        if sub_expired: 
            raise HTTPException(status_code=404, detail="Subscription is expired and not renewed")
        access = False
        for permission in sub.permissions:
            permission_data = await perm_col.find_one({"_id": ObjectId(permission)})
            if permission_data["access"] == request:
                access = True
                break

        if sub.requests >= sub.access_limit: access = False

        if not access:
            raise HTTPException(status_code=403, detail="User is not allowed to access this.")
        
        return {"message": "User account Limits aquired", "data": True}
    except Exception as e:
        return {"Error": str(e), "data": False}
    

# Usage Tracking and Limit enforcing
@app.get("/user/{userID}/requests")
async def getUserCurrentRequests(userID: str):
    try:
        sub_data = (await getUserSubscription(userID))
        if not sub_data:
            raise HTTPException(status_code=404, detail="Subscription was not found.")
        return {"Message": "User requests successfully aquired", "data": sub_data["requests"]}
    except Exception as e:
        {"error": str(e)}


@app.put("/user/{userID}/requests")
async def increaseUserCurrentRequests(userID: str):
    try:
        sub_data = (await getUserSubscription(userID))["data"]
        if not sub_data:
            raise HTTPException(status_code=404, detail="Subscription was not found")
        sub_data["requests"] += 1
        result = sub_col.update_one({"_id": ObjectId(sub_data["_id"])}, {"$set":sub_data})
        return {"message": "Request count increased for user"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/user/{userID}/check")
async def checkUserSubscriptionExpire(userID: str):
    try:
        sub_data = (await getUserSubscription(userID))["data"]
        if not sub_data:
            raise HTTPException(status_code=404, detail="Subscription not found")
        start_date = parser.isoparse(sub_data["start_date"])
        expiration = start_date + timedelta(days=30)
        current_date = datetime.now()
        if current_date > expiration and not sub_data["auto"]:
            deleteSub(sub_data["_id"])
            removeUserSubscription(userID)
            return {"message": "Subscription is Expired", "data": True}
        elif current_date > expiration and sub_data["auto"]:
            await resetUserSubscription(userID)
            return {"message": "Subscription has been auto renewed", "data": False}
        else:
            return {"message": "Subscription is active", "data": False}
    except Exception as e:
        return {"error": str(e), "data": True}


@app.put("/user/{userID}/reset")
async def resetUserSubscription(userID: str):
    try:
        sub_data = (await getUserSubscription(userID))["data"]
        if not sub_data:
            raise HTTPException(status_code=404, detail="Subscription not found")
        deleteSub(sub_data["_id"])
        sub_data["requests"] = 0
        new_sub_id = (await createSub(sub_data))["data"]
        changeUserSubscription(userID, new_sub_id)
        return {"message": "Subscription has been Reset", "data": new_sub_id}
    except Exception as e:
        return {"error": str(e)}
    

@app.put("/user/{userID}/remove_subscription")
async def removeUserSubscription(userID: str):
    try:
        sub_data = (await getUserSubscription(userID))["data"]
        if not sub_data:
            raise HTTPException(status_code=404, detail="Subscription not found")
        result = await user_col.update_one({"_id": ObjectId(userID)}, {"$set": {"subscription": ""}})
        deleteSub(sub_data["_id"])
        return {"message": "Subscription has been removed"}
    except Exception as e:
        return {"error": str(e)}


# Other functions
@app.post("/login")
async def loginUser(data: dict):
    try:
        user_data = await user_col.find_one({"username": data.get("username", ""),
                                       "password": data.get("password", "")})
        
        if user_data:
            user_data = objToStr(user_data)
            user_data.pop("password")
            return {"message": "User has logged in.", "data": user_data}
        else:
            raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        return {"error": str(e)}
    

@app.post("/signup")
async def createUser(data: dict):
    try:
        user_data = await user_col.find_one({"username": data.get("username", "")})
        if user_data:
            raise DuplicateKeyError
        if data["username"] == "" or data["password"] == "": 
            raise HTTPException(status_code=400, detail="Requires username and password")
        data["subscription"] = ""
        user = Customer(**data)
        print(user)
        encoded_user = jsonable_encoder(user)
        result = user_col.insert_one(encoded_user)
        return {"message": "Created a new user"}
            
    except DuplicateKeyError:
        return {"error": "Duplicate user error."}
    except Exception as e:
        return {"error": str(e)}
    

@app.delete("/user/{userID}")
async def deleteUser(userID: str):
    try:
        result = user_col.delete_one({"_id": ObjectId(userID)})
        return {"message": "User was deleted", "data": userID}
    except Exception as e:
        return {"error": str(e)}
    

@app.post("/admin")
async def createAdmin(data: dict):
    try:
        if not "username" in data or not "password" in data:
            raise HTTPException(status_code=400, detail="Username and password required")
        user = Customer(**data)
        user["admin"] = True
        encoded_user = jsonable_encoder(user)
        result = user_col.insert_one(encoded_user)
        return {"message": "Created new Admin"}
    except Exception as e:
        return {"error": str(e)}

    
@app.put("/subscriptions/{subID}/permission/{permID}")
async def addSubscriptionPermission(subID: str, permID: str):
    try: 
        sub_data = await sub_col.find_one({"_id": ObjectId(subID)})
        sub_data["permissions"].append(permID)
        result = sub_col.update_one({"_id": ObjectId(subID)}, {"$set":sub_data})
        print("Successful update of permissions to sub")
        return {"message": "Added Permission to sub_data", "data": subID}
    except Exception as e:
        return {"error": str(e)}
    

@app.get("/view/{userID}/{request}")
async def viewPage(userID: str, request: str):
    try:
        if not (await checkUserAllowed(userID, request))["data"]:
            raise HTTPException(status_code=403, detail="User is not allowed to View this page")
        await increaseUserCurrentRequests(userID)
        return {"message": "User viewed page and incremented thier count", "data": "You're accessing the file!"}
    except Exception as e:
        return {"error" : str(e)}
    

@app.get("/users/{userID}")
async def getUser(userID: str):
    try:
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        user = Customer(**user_data)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"messsage": "User found", "data": user}
    except Exception as e:
        return {"error": str(e)}


@app.get("/admin/users")
async def getAllUsers(userID: str = Query(..., description="The ID of the user")):
    try:
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        if not user_data or not user_data["admin"]:
            raise HTTPException(status_code=403, detail="User is not an admin")
        users = await user_col.find().to_list()
        users = objToStr(users)
        return {"message": "returning a list of users", "data": users}
    except Exception as e:
        return {"error": str(e)}


@app.get("/admin/subscriptions")
async def getAllSubs(userID: str = Query(..., description="The ID of the user")):
    try:
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        if not user_data or not user_data["admin"]:
            raise HTTPException(status_code=403, detail="User is not an admin")
        subscriptions = await sub_col.find().to_list()
        subscriptions = objToStr(subscriptions)
        return {"message": "returning a list of subscriptions", "data": subscriptions}
    except Exception as e:
        return {"error": str(e)}
    

@app.get("/admin/permissions")
async def getAllPerms(userID: str = Query(..., description="The ID of the user")):
    try:
        user_data = await user_col.find_one({"_id": ObjectId(userID)})
        if not user_data or not user_data["admin"]:
            raise HTTPException(status_code=403, detail="User is not an admin")
        permissions = await perm_col.find().to_list()
        permissions = objToStr(permissions)
        return {"message": "returning a list of permissions", "data": permissions}
    except Exception as e:
        return {"error": str(e)}
    

@app.get("/username/{username}")
async def getUserID(username: str):
    try:
        user_data = await user_col.find_one({"username": username})
        if not user_data:
            raise HTTPException(status_code=404, detail="User was not found")
        user_data = objToStr(user_data)
        return {"message": "UserID was aquired", "data": user_data}
    except Exception as e:
        return {"error": str(e)}
    

@app.get("/access/{access}")
async def getPermissionID(access: str):
    try:
        perm_data = await perm_col.find_one({"access": access})
        if not perm_data:
            raise HTTPException(status_code=404, detail="Permission not found")
        perm_data = objToStr(perm_data)
        return {"message": "Permission ID was aquired", "data": perm_data}
    except Exception as e:
        return {"error": str(e)}
    

@app.put("/delete/permission/{permID}")
async def deletePermissionFromAll(permID: str):
    try:
        result = await sub_col.update_many(
            {"permissions": permID},
            {"$pull": {"permissions": permID}}
        )
        if result.deleted_count > 0:
            return {"message": "Permission has been deleted"}
        else:
            raise HTTPException(status_code=404, detail="Permission not found")
    except Exception as e:
        return {"error": str(e)}
    

@app.put("/remove/permission/{permID}/subscription/{subID}")
def removePermissionFromSub(permID: str, subID: str):
    try:
        sub_data = sub_col.find_one({"_id": ObjectId(subID)})
        if not sub_data:
            raise HTTPException(status_code=404, detail="Subscription not found")
        sub_data["permissions"].remove(permID)
        result = sub_col.update_one({"_id": ObjectId(subID)}, {"$set": sub_data})
        return {"message": "Permission has been removed from subscription"}
    except Exception as e:
        return {"error": str(e)}
    
    
# Helper function to make ObjectID easier to work with
def objToStr(data):
    if isinstance(data, list):
        return [objToStr(item) for item in data]
    elif isinstance(data, dict):
        return {key: (str(value) if isinstance(value, ObjectId) else value) for key, value in data.items()}
    else:
        return data