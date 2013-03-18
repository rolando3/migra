#!/opt/local/bin/python
#flask implementation of my migra web app

from migra import Migra, MigraPersonEncoder
from flask import Flask, make_response, request, render_template, url_for, session
import json
import sys
import os

app = Flask(__name__)
app.config['SESSION_SECRETKEY'] = os.environ.get('MIGRA_SESSIONKEY','shlabittyboopityboo')
app.config['UPLOAD_FOLDER'] = os.environ.get('MIGRA_UPLOADFOLDER','/Users/rolando/Downloads/gedtemp')

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
    """ Just displays the index template """
    """ This is where all the action happens. Everything else is a JSON request/response """
    return render_template('index.html')
    
@app.route('/upload',methods=['POST'])
def upload():
    """ Get the file and the search term from the upload, turn it into a gedcom, do something with this """
    query = request.form['q']

    import os
    from tempfile import NamedTemporaryFile
    file = request.files['gedcom']
    
    #uploads not permitted in Heroku. Need to send this over to amazon. For now this will have to do.
    
    if file and __allowed_file(file.filename):
        ( fullDict, filteredList ) = migra.processGedcom(file,query)

        f = NamedTemporaryFile(suffix='.ged',dir=app.config['UPLOAD_FOLDER'],delete=False)
        fn = f.name
        f.write(json.dumps(fullDict,indent=4,cls=MigraPersonEncoder))
        f.close()
        
        session['gedcomfile'] = fn.split('/')[-1]

        return jsonresponse({'people':filteredList,'parameters':{'query':query}})
    else:
        raise MigraError, ('File not allowed')
        
    raise MigraError, ('I don\'t even know what is happening')

@app.route('/walk',methods=['GET','POST'])
def walk():
    """Now we have to find our file and send it to gedcom -- unless we can attach the gedcom created earlier via session!"""
    f = open('/'.join((app.config['UPLOAD_FOLDER'],session['gedcomfile'])),'r')    
    d = json.load(f)
    f.close()
    
    return jsonresponse( migra.walk(d,request.form['i'],request.form['d']) )
    
@app.route('/cache',methods=['POST'])
def cache():
    return migra.cache(request.form['data'])
    
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)