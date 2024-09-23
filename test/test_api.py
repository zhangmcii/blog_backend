from backend_boke.app.api import api
import requests


url = 'http://192.168.1.13:8081'
r = requests.get(url+'/api/v1/posts')
print(r.json())