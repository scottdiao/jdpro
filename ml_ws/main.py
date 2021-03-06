from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from flask import Flask, jsonify, request
from werkzeug import secure_filename
import urllib.request
from keras.models import load_model
from keras.preprocessing import image
from keras.applications.inception_v3 import preprocess_input
from flask_cors import CORS
import numpy as np
import tensorflow as tf
import os, pickle, uuid, argparse
import datastore_api as dsa
import cnn
from google.cloud import datastore, storage
import io
try:
    from PIL import ImageEnhance
    from PIL import Image as pil_image
except ImportError:
    pil_image = None


app = Flask(__name__)
CORS(app)
ds = datastore.Client('atomic-amulet-199016')
model_dir = './model/keras/inception_v3.h5'
model = load_model(model_dir)
graph = tf.get_default_graph()

@app.route('/')
def index():
    return "This is a building image recognition web service"

@app.route('/building_uri', methods=['POST'])
def building_uri():
    uri = request.json['uri']
    # if(uri.endswith('.png')):
    #     filename='download.png'
    # elif(uri.endswith('.bmp')):
    #     filename='download.bmp'
    # elif(uri.endswith('.gif')):
    #     filename='download.gif'
    # else:
    #     filename='download.jpg'
    # encrypt_filename = "./uploads/"+str(uuid.uuid1())+filename
    # if not request.json or not 'uri' in request.json:
    #     abort(400)
    # urllib.request.urlretrieve(request.json['uri'], encrypt_filename)
    with urllib.request.urlopen(uri) as image_url:
        f = io.BytesIO(image_url.read())
    response = run_keras_cnn(f)
    # os.remove(encrypt_filename)
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/building_file', methods=['POST'])
def building_file():
    f = request.files['file']
    uuid = request.form.get("uuid")
    file_name = uuid+secure_filename(f.filename)
    # f.save(file_name)
    client=storage.Client(project="atomic-amulet-199016")
    bucket = client.bucket("atomic-amulet-199016")
    blob = bucket.blob(file_name)
    blob.upload_from_file(f, content_type=f.content_type)
    url = blob.public_url
    with urllib.request.urlopen(url) as image_url:
        f = io.BytesIO(image_url.read())
    response = run_keras_cnn(f)
    # response = cnn.run_cnn(file_name)
    # os.remove(file_name)
    return response

@app.route('/upload', methods=['POST'])
def upload():
    response = jsonify({"content":"1"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response

@app.route('/building_list')
def list():
    ds = datastore.Client('atomic-amulet-199016')
    buildings = dsa.list_buildings(ds)
    resjsonlist = []
    for b in buildings:
        resjson = {
            'name': b['name']
        }
        resjsonlist.append(resjson)
    response =  jsonify(resjsonlist)
    return response

def run_keras_cnn(file):
    img_width, img_height = 299, 299
    with open('./model/keras/class_dict.pkl', 'rb') as f:
        class_dict = pickle.load(f)
    x = image.load_img(file, target_size=(img_width, img_height))
    x = np.expand_dims(x, axis=0)
    x=x.astype("float32")
    x.setflags(write=1)
    x = preprocess_input(x)
    global graph
    with graph.as_default():
        preds = model.predict(x)
    preds = np.squeeze(preds)
    top_k = preds.argsort()[-5:][::-1]
    resjsonlist = []
    for i in top_k:
        label = class_dict[i].lower()
        entity = dsa.load_building(ds, label)
        resjson = {
            'label': label,
            'alias': entity['alias'],
            'place_id': entity['place_id'],
            'probability': str(preds[i])
        }
        resjsonlist.append(resjson)
        print(label, preds[i])
    response =  jsonify(resjsonlist)
    return response


if __name__ == '__main__':
    app.run(debug=False)
