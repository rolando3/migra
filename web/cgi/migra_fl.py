#!/opt/local/bin/python
#flask implementation of my migra web app

from migra import Migra, MigraJSONEncoder
from flask import Flask, make_response, request, render_template, url_for, session
#from flaskext.uploads import ( UploadSet, configure_uploads )
import json
import sys

app = Flask(__name__)
app.secret_key = 'shlabittyboopityboo'
#gedcoms = flaskext.uploads.UploadSet(name='gedcoms', extensions=('ged') + flaskext.uploads.ARCHIVES )
#configure_uploads(app,(gedcoms))

migra = Migra()

def jsonresponse(data):
    resp = make_response(json.dumps(data,indent=4)) #,cls=MigraJSONEncoder))
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
    file = request.files['gedcom']
    if file and __allowed_file(file.filename):
        ( g, p ) = migra.processGedcom(file,query)
        session['g']=g
        return jsonresponse({'people':p})
        
    return jsonresponse({'error': 'This is terrible'})

@app.route('/test',methods=['GET','POST'])
def test():
    return jsonresponse({'hello': 'dingleberry'})

@app.route('/walk',methods=['GET','POST'])
def walk():
    """Now we have to find our file and send it to gedcom -- unless we can attach the gedcom created earlier via session!"""
    return jsonresponse(migra.walk(session['g'],request.form['i'],request.form['d']))
    
@app.route('/cache',methods=['POST'])
def cache():
    return migra.cache(request.form['data'])
    
if __name__ == '__main__':
    app.run(debug=True)