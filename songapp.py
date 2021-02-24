from flask import Flask
from flask import request
from flask import jsonify
from pymongo import MongoClient
import hashlib
import jwt
import flask
import time
import json
from bson import json_util

app = Flask(__name__)
app.config["DEBUG"] = True

client = MongoClient('localhost', 27017)
database = client.songapp
user_details = database.user_details
song_details = database.song_details
playlist_details = database.playlist_details


def token_required():
    headers = flask.request.headers
    bearer_token = headers.get('Authorization')
    token = bearer_token.split()[1]
    print(token)
    if token:
        
        secret_key = 'abcd'
        decoded = jwt.decode(token, secret_key, options={'verify_exp': False})
        print(decoded)
        global valid_user
        valid_user = user_details.find_one({'email': decoded['user']})
        print(valid_user)
        return jsonify({"message": "Authorization successful"})
    elif not token:
        print("in elif")
        return jsonify({'message': 'Unsuccessful Authorization'}), 403
    return jsonify({"message": "Invalid User"})

@app.route('/songapp/register_user', methods=['POST'])

def register():
     register_user = {
        'name': request.json['name'],
        'contactno': request.json['contactno'],
        'email': request.json['email'],
        'password': request.json['password'],
        'type_of_user': request.json['type_of_user']
    }
     salt = "7ik"
     db_password = register_user['password'] + salt
     print(db_password)
     h = hashlib.md5(db_password.encode())
     print(h)
     hashed = h.hexdigest()
     print(hashed)
     register_user['password'] = hashed
     user_details.insert_one(register_user)
     return({'message':"You are into song app"})

@app.route('/songapp/user_login', methods=['POST'])
def login():
    user_login = {
        'email': request.json['email'],
        'password': request.json['password'],
        }
    check_user = user_details.find_one({'email': user_login['email']})
    print(check_user)
    salt = "7ik"
    entered_password = user_login['password'] + salt
    print(entered_password)
    h = hashlib.md5(entered_password.encode())
    print(h)
    hashed = h.hexdigest()
    print(hashed)
    user_login['password'] = hashed
    if(check_user['password']==user_login['password']):
        print("in if")
        secret_key = 'abcd'
        payload = {'user': check_user['email'], 'exp': time.time() + 300}
        print(payload)
        jwt_token = jwt.encode(payload, secret_key)
        print(jwt_token)
        response = {
            'token': jwt_token.decode()
        }
        print(response)
        return jsonify({"message": "login success", "data": response})
    else:
        return jsonify({"message": "Name/password mismatch.. Pls try again"})

@app.route('/songapp/update/user_details', methods=['POST'])

def update_user():
        token_required()
        new_contact = {'contactno': request.json['contactno']}
        print(new_contact)
        user_details.update_one(valid_user, {'$set': {'contactno': new_contact['contactno']}})
        return jsonify({"message": "Details are updated"})

@app.route('/songapp/delete/user', methods=['POST'])
def delete_member():
    token_required()
    b = playlist_details.aggregate(
        [{'$match': {'name': valid_user['name']}},
         {'$group': {'_id': 'null', 'count': {'$sum': 1}}}
         ]
    )
    c = list(b)
    print(c)
    if len(c) == 0:
        print("in if")
        del_user = user_details.find_one_and_delete({'name': valid_user['name']})
        print(del_user)
        return jsonify({"message": "Your account is deleted from the app"})
    elif c[0]['count'] < 0:
        print("in elif")
        return jsonify({"message": "Please delete your playlist to delete your account"})

@app.route('/songapp/upload', methods=['POST'])

def upload():
    token_required()
    upload_song = {
        'name_of_song': request.json['name_of_song'],
        'artist': request.json['artist'],
        'genre': request.json['genre']
    }
    if valid_user['type_of_user'] == "premium":
        song_details.insert_one(upload_song)
        return jsonify({"message": "song is successfully uploaded"})
    else:
        return jsonify({"message": "only premium members can upload songs in the app"})

@app.route('/songapp/create_playlist', methods=['POST'])

def create_songlist():
    token_required()
    get_name = {'name_of_playlist': request.json['name_of_playlist']}
    b = playlist_details.aggregate(
                                            [{'$match': {'name': valid_user['name']}},
                                            {'$group': {'_id': 'null', 'count': {'$sum': 1}}}
                                         ]

    )
    c = list(b)
    print(c)
    if len(c) == 0 or c[0]['count'] < 3 and valid_user['type_of_user'] == 'free':
        print("in songlist if")
        playlist_details.insert_one({'name_of_playlist': get_name['name_of_playlist'], 'name': valid_user['name'], 'songs': []})
        return jsonify({"message": "playlist is successfully created"})
    elif c[0]['count'] == 3 and valid_user['type_of_user'] == 'free':
        print("in elif")
        return jsonify({"message": "You are allowed to create only 3 playlist"})
    elif valid_user['type_of_user'] == 'premium':
        print("in playlist else")
        playlist_details.insert_one({'name_of_playlist': get_name['name_of_playlist'], 'name': valid_user['name'], 'songs': []})
        playlist_details.update_one(get_name, {'$set': {'name': valid_user['name']}})
        return jsonify({"message": "playlist is created successfully"})
    else:
        return jsonify({"message": "Enter the name of playlist"})

@app.route('/songapp/addSongToplaylist', methods=['POST'])
def add_song():
    token_required()
    get_name = {'name_of_playlist': request.json['name_of_playlist']}
    get_name_of_song = {'name_of_song': request.json['name_of_song']}
    x = playlist_details.find_one({'name_of_playlist': get_name['name_of_playlist']})
    print(x)
    if x['name_of_playlist'] == get_name['name_of_playlist']:
        playlist_details.update_one(x, {'$push': {'songs': get_name_of_song}})
        return jsonify({"message": "Song is successfully added to your playlist"})
    else:
        return jsonify({"message": "This playlist was not created"})

@app.route('/songapp/view_user/fav', methods=['POST'])
def fav_list():
    token_required()
    b = playlist_details.aggregate([
        {'$match': {'name': valid_user['name']}},
        {"$unwind": "$songs"},
        {
            '$lookup':
                {
                    'from': 'song_details',
                    'localField': 'songs.name_of_song',
                    'foreignField': 'name_of_song',
                    'as': 'fav_list'
                }
        },
        {"$unwind": "$fav_list"},
        {'$facet':
             {
                "categorizeByArtist": [
                                         {'$group':
                                              {'_id':"$fav_list.artist",
                                               'count': {'$sum': 1}}}
                                    ],
                 "categorizeByGenre": [
                                        {'$group':
                                            {'_id': "$fav_list.genre",
                                             'count': {'$sum': 1}}}
                                    ]
             }
      }
    ])
    y = list(b)
    print(y)
    for i in y:
        c = max(i['categorizeByArtist'], key=lambda x: x['count'])
        d = max(i['categorizeByGenre'], key=lambda x: x['count'])
    print(c)
    print(d)
    res = c["_id"]
    print(res)
    res1 = d["_id"]
    print(res1)
    res_obj = {
        "Your fav artist is": res,
        "Your fav genre is": res1
    }

    return json.dumps(res_obj, indent=4, default=json_util.default)


app.run()
