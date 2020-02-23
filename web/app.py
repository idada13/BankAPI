from flask import Flask, jsonify, request
from flask_restful import Api, Resource
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
api = Api(app)

client = MongoClient("mongodb://db:27017")
db = client.BankAccountAPI
users = db["Users"]


def UserExist(username):
	if users.find({"Username":username}).count() == 0:
		return False
	else:
		return True

class Register(Resource):
	def post(self):
		posted_data = request.get_json()

		username = posted_data["username"]
		password = posted_data["password"]

		if UserExist(username):
			retJson = {
			"status": 301,
			"message": "Invalid Username"
		}
			return jsonify(retJson)

		hashed_pw = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())

		users.insert({
			"Username": username,
			"Password": hashed_pw,
			"Balance": 0,
			"Debt": 0
		})

		retJson = {
			"status": 200,
			"message": "You successfully singed up for the API"
		}
		return jsonify(retJson)

# Helper functions to check credentials and send error messages

def verifyPw(username, password):
	if not UserExist(username):
		return False

	hashed_pw = users.find({
		"Username": username
	})[0]["Password"]

	if bcrypt.hashpw(password.encode('utf8'), hashed_pw) == hashed_pw:
		return True
	else:
		return False

def cashWithUser(username):
	cash = users.find({
		"Username": username
	})[0]["Balance"]
	return cash

def debtWithUser(username):
	debt = users.find({
		"Username": username
	})[0]["Debt"]
	return debt

def generateReturnDictionary(status, message):
	retJson = {
		"status": status,
		"message": message
	}
	return retJson

def verifyCredentials(username, password):
	if not UserExist(username):
		return generateReturnDictionary(301, "Invalid Username"), True

	corrent_pw = verifyPw(username, password)

	if not corrent_pw:
		return generateReturnDictionary(302, "Incorrect Password"), True

	return None, False

# Update account functions

def updateAccount(username, balance):
	users.update({
		"Username": username
	},{
		"$set":{
			"Balance": balance
			}
	})

def updateDebt(username, balance):
	users.update({
		"Username": username
	},{
		"$set":{
		"Debt": balance
		}
	})

# 1: Add balance to the account and to bank

class Add(Resource):
	def post(self):
		posted_data = request.get_json()

		username = posted_data["username"]
		password = posted_data["password"]
		money = posted_data["amount"]

		retJson, error = verifyCredentials(username, password)

		if error:
			return jsonify(retJson)

		if money <= 0:
			return jsonify(generateReturnDictionary(304, "You must send the amount that is greater than 0"))

		cash = cashWithUser(username)
		money -= 0.1
		bank_cash = cashWithUser("BANK")
		updateAccount("BANK", bank_cash + 0.1)
		updateAccount(username, cash+money)

		return jsonify(generateReturnDictionary(200, "Amount added to the account"))

#2: Transfer ability
class Transfer(Resource):
	def post(self):
		posted_data = request.get_json()

		username = posted_data["username"]
		password = posted_data["password"]
		to = posted_data["to"]
		money = posted_data["amount"]

		retJson, error = verifyCredentials(username, password)

		if error:
			return jsonify(retJson)

		cash = cashWithUser(username)
		if cash <= 0:
			return jsonify(generateReturnDictionary(304, "Insufficient balance on the account"))

		if not UserExist(to):
			return jsonify(generateReturnDictionary(301, "Reciever username does not exist"))	

		cash_from = cashWithUser(username)
		cash_to = cashWithUser(to)
		bank_cash = cashWithUser("BANK")

		updateAccount("BANK", bank_cash + 0.1)
		updateAccount(to, cash_to + money - 0.1)
		updateAccount(username, cash_from - money)

		return jsonify(generateReturnDictionary(200, "Amount transfered successfully"))

#3: Balance 
# Return the whole document based on the username but exclude the password or the id
class Balance(Resource):
    def post(self):
        postedData = request.get_json()

        username = postedData["username"]
        password = postedData["password"]

        retJson, error = verifyCredentials(username, password)
        if error:
            return jsonify(retJson)

        retJson = users.find({
            "Username": username
        },{
            "Password": 0, #projection
            "_id":0
        })[0]

        return jsonify(retJson)

# 4 Take loan
class TakeLoan(Resource):
	def post(self):
		posted_data = request.get_json()

		username = posted_data["username"]
		password = posted_data["password"]
		money = posted_data["amount"]

		retJson, error = verifyCredentials(username, password)

		if error:
			return jsonify(retJson)

		cash = cashWithUser(username)
		debt = debtWithUser(username)
		updateAccount(username, cash + money)
		updateDebt(username, debt + money)

		return jsonify(generateReturnDictionary(200, "Loan added to your account"))

# Pay back the loan
class PayLoan(Resource):
	def post(self):
		posted_data = request.get_json()

		username = posted_data["username"]
		password = posted_data["password"]
		money = posted_data["amount"]

		retJson, error = verifyCredentials(username, password)

		if error:
			return jsonify(retJson)

		cash = cashWithUser(username)

		if cash < money:
			return jsonify(generateReturnDictionary(303, "Not enough cash in your account"))

		debt = debtWithUser(username)

		updateAccount(username, cash - money)
		updateDebt(username, debt - money)

		return jsonify(generateReturnDictionary(200, "Loan is paid now"))




api.add_resource(Register, '/register')
api.add_resource(Add, '/add')
api.add_resource(Transfer, '/transfer')
api.add_resource(Balance, '/balance')
api.add_resource(TakeLoan, '/takeloan')
api.add_resource(PayLoan, '/payloan')

if __name__=="__main__":
    app.run(host='0.0.0.0')