from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from flask import Flask, jsonify, request
import urllib.request
import argparse
from flask_cors import CORS
import numpy as np
import tensorflow as tf


app = Flask(__name__)
CORS(app)

file_name = "./download.jpg"
model_file = "./model/output_graph.pb"
label_file = "./model/output_labels.txt"
input_height = 299
input_width = 299
input_mean = 0
input_std = 255
input_layer = "Placeholder"
output_layer = "final_result"

def load_graph(model_file):
  graph = tf.Graph()
  graph_def = tf.GraphDef()

  with open(model_file, "rb") as f:
    graph_def.ParseFromString(f.read())
  with graph.as_default():
    tf.import_graph_def(graph_def)

  return graph

def read_tensor_from_image_file(file_name,
                                input_height=299,
                                input_width=299,
                                input_mean=0,
                                input_std=255):
  input_name = "file_reader"
  output_name = "normalized"
  file_reader = tf.read_file(file_name, input_name)
  if file_name.endswith(".png"):
    image_reader = tf.image.decode_png(
        file_reader, channels=3, name="png_reader")
  elif file_name.endswith(".gif"):
    image_reader = tf.squeeze(
        tf.image.decode_gif(file_reader, name="gif_reader"))
  elif file_name.endswith(".bmp"):
    image_reader = tf.image.decode_bmp(file_reader, name="bmp_reader")
  else:
    image_reader = tf.image.decode_jpeg(
        file_reader, channels=3, name="jpeg_reader")
  float_caster = tf.cast(image_reader, tf.float32)
  dims_expander = tf.expand_dims(float_caster, 0)
  resized = tf.image.resize_bilinear(dims_expander, [input_height, input_width])
  normalized = tf.divide(tf.subtract(resized, [input_mean]), [input_std])
  sess = tf.Session()
  result = sess.run(normalized)

  return result

def load_labels(label_file):
  label = []
  proto_as_ascii_lines = tf.gfile.GFile(label_file).readlines()
  for l in proto_as_ascii_lines:
    label.append(l.rstrip())
  return label

@app.route('/')
def index():
    return "This is a building image recognition web service"

def run_cnn():
	graph = load_graph(model_file)
	t = read_tensor_from_image_file(
	  file_name,
	  input_height=input_height,
	  input_width=input_width,
	  input_mean=input_mean,
	  input_std=input_std)

	input_name = "import/" + input_layer
	output_name = "import/" + output_layer
	input_operation = graph.get_operation_by_name(input_name)
	output_operation = graph.get_operation_by_name(output_name)

	with tf.Session(graph=graph) as sess:
		results = sess.run(output_operation.outputs[0], {
			input_operation.outputs[0]: t
		})
		results = np.squeeze(results)

	top_k = results.argsort()[-5:][::-1]
	labels = load_labels(label_file)
	resjsonlist = []
	for i in top_k:
		resjson = {
			'label': labels[i],
			'probability': str(results[i])
	    }
		resjsonlist.append(resjson)
		print(labels[i], results[i])
	response =  jsonify(resjsonlist)

	return response

@app.route('/download', methods=['POST'])
def download_image():
    print("downloading........")
    if not request.json or not 'uri' in request.json:
        abort(400)
    urllib.request.urlretrieve(request.json['uri'], "./download.jpg")
    response = run_cnn()
    response.headers.add('Access-Control-Allow-Origin', '*')

    return response


if __name__ == '__main__':
    app.run(debug=True)
