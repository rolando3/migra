#!/opt/local/bin/python
#flask implementation of my migra web app

from migra import Migra, MigraPersonEncoder
from flask import Flask, make_response, request, render_template, url_for, session, jsonify
import sys
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('MIGRA_SESSIONKEY','CJ!31ioQcw89*')
app.config['UPLOAD_FOLDER'] = os.environ.get('MIGRA_UPLOADFOLDER','')
migra = Migra()

def fileStorageClass():
    return AmazonS3FileStorage

def jsonresponse(data):
    resp = make_response(json.dumps(data,indent=4,cls=MigraPersonEncoder))
    resp.headers['Content-Type'] = 'application/json'
    return resp

class LocalFileStorage:
    @classmethod
    def store_file(cls,d):
        """ Given a dict of all of the people in our gedcom, store it somewhere, and then pass back an 
            identifier that will make it easy to find on the second pass."""
        from tempfile import NamedTemporaryFile
    
        f = NamedTemporaryFile(suffix='.json',dir=app.config['UPLOAD_FOLDER'],delete=False)
        fn = f.name
        f.write(json.dumps(d,indent=4,cls=MigraPersonEncoder))
        f.close()
        return fn.split('/')[-1]
        
    @classmethod
    def get_file(cls,k):
        """ Given a key, get the stored file and return the deserialized object """
        f = open('/'.join((app.config['UPLOAD_FOLDER'],k)),'r')    
        d = json.load(f)
        f.close()
        return d

class AmazonS3FileStorage:

    @classmethod
    def __key(cls,k=None):
        from boto.s3.connection import S3Connection, Key

        conn = S3Connection(os.environ['AWS_ACCESSKEY'], os.environ['AWS_SECRETKEY'])
        bucket = conn.get_bucket('migra_g.heroku')
        key = Key(bucket)
        if k is None:
            import random
            from string import ascii_lowercase as letters
            k = ''
            for i in range(12):
                k += random.choice(letters)
                
        key.key = k
        return key

    @classmethod
    def store_file(cls,d):
        awsKey = cls.__key()
        
        sys.stderr.write ( "KEY *** %s ***\n" % awsKey )
        awsKey.set_contents_from_string(json.dumps(d,indent=4,cls=MigraPersonEncoder))

        return awsKey.key
                    
    @classmethod
    def get_file(cls,k):
        awsKey = cls.__key(k)
        return json.loads(awsKey.get_contents_as_string())
        

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
        session['key'] = fileStorageClass().store_file(fullDict)
        return jsonresponse({'people':filteredList,'parameters':{'query':query}})
    else:
        raise MigraError, ('File not allowed')
        
@app.route('/walk',methods=['GET','POST'])
def walk():
    """Now we have to find our file and send it to gedcom -- unless we can attach the gedcom created earlier via session!"""
    d = fileStorageClass().get_file(session['key'])
    
    return jsonresponse( migra.walk(d,request.form['i'],request.form['d']) )
    
@app.route('/cache',methods=['POST'])
def cache():
    '''this caches the data sent. we don't care about the results (though maybe we should) '''
    return migra.cache(request.form['data'])
    
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)