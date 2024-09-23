from flask_jwt_extended import JWTManager,create_access_token
# flask 实例
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = "DSFD"
jwt = JWTManager(app)

a = create_access_token('nihao')
print(a)