#!/usr/bin/env python

#flask implementation of my migra web app

from migra import Migra, MigraPersonEncoder
from migrastorage import fileStorage
from flask import Flask, make_response, request, render_template, url_for, session, jsonify, send_from_directory
import sys
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('MIGRA_SESSIONKEY',None)
migra = Migra()

def jsonresponse(data):
    resp = make_response(json.dumps(data,cls=MigraPersonEncoder))
    resp.headers['Content-Type'] = 'application/json'
    return resp

def __allowed_file(filename):
    return '.' in filename and \
          filename.rsplit('.', 1)[1] in ['ged','zip']
    
@app.route('/')
def index():
    """ Just displays the index template 
        This is where all the HTML action happens. 
        Everything else is a JSON request/response """
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    path = os.path.join(app.root_path, 'static/img')
    sys.stderr.write ( path + "\n" )
    return send_from_directory(path,
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/upload',methods=['POST'])
def upload():
    """ Get the file and the search term from the upload, turn it into a gedcom, do something with this """
    file = request.files['gedcom']
    
    if file and __allowed_file(file.filename):
        all = migra.upload(file)
        session['key'] = fileStorage().store_file(all,session.get('key',None))
        return jsonresponse({'count': len(all.keys())})
    else:
        raise MigraError, ('File not allowed')

@app.route('/filter',methods=['GET','POST'])
def filter():
    q = request.form['q']
    d = fileStorage().get_file(session['key'])
    return jsonresponse({'people': migra.filter ( d, q ), 'parameters': { 'query': q } } )

@app.route('/walk',methods=['GET','POST'])
def walk():
    """Now we have to find our file and send it to gedcom -- unless we can attach the gedcom created earlier via session!"""
    d = fileStorage().get_file(session['key'])
    return jsonresponse( migra.walk(d,request.form['i'],request.form['d']) )
    
@app.route('/cache',methods=['POST'])
def cache():
    '''this caches the data sent. we don't care about the results (though maybe we should) '''
    return jsonresponse( migra.cache(request.form['data']) )
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
