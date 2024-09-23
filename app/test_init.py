import requests

# url = 'http://localhost:8081'

url = 'http://192.168.1.13:8081'


res = requests.post(url+'/auth/login', json={'uiAccountName':'David Richardson', 'uiPassword':'123'})
print(res.json())
token = res.json().get('token')


res = requests.get(url+'/logined')
print(res.json())

res = requests.get(url+'/logined', headers={'Authorization':token})
print(res)

res = requests.get(url+'/protected', headers={'Authorization':token})
print(res)


res = requests.get(url+'/main/user/zsc', headers={'Authorization':token})
print(res)


