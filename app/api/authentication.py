from . import api
from flask_jwt_extended import jwt_required

@api.before_request
@jwt_required()
def auth():
    pass        