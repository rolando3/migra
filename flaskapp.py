#!/usr/bin/env python

#flask implementation of my migra web app

from migra import Migra, MigraPersonEncoder
from migrastorage import fileStorage
from flask import Flask, make_response, request, render_template, url_for, session, jsonify
import sys
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('MIGRA_SESSIONKEY','CJ!31ioQcw89*')
app.config['UPLOAD_FOLDER'] = os.environ.get('MIGRA_UPLOADFOLDER','')
migra = Migra()

def jsonresponse(data):
    resp = make_response(json.dumps(data,indent=4,cls=MigraPersonEncoder))
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
    
@app.route('/upload',methods=['POST'])
def upload():
    """ Get the file and the search term from the upload, turn it into a gedcom, do something with this """
    query = request.form['q']
    file = request.files['gedcom']
    
    #uploads not permitted in Heroku. Need to send this over to amazon. For now this will have to do.
    if file and __allowed_file(file.filename):
        ( fullDict, filteredList ) = migra.processGedcom(file,query)
        session['key'] = fileStorage().store_file(fullDict)
        return jsonresponse({'people':filteredList,'parameters':{'query':query}})
    else:
        raise MigraError, ('File not allowed')
        
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
