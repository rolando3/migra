import os
import sys
import json
from migra import MigraPersonEncoder

__all__ = [ 'LocalFileStorage', 'AmazonS3FileStorage', 'fileStorage' ]

def fileStorage():
    return AmazonS3FileStorage

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
        
    @classmethod
    def cleanup(cls, age):
        """ delete all files more than age seconds old """
        pass

class AmazonS3FileStorage:
    @classmethod
    def __bucket(cls):
        from boto.s3.connection import S3Connection

        conn = S3Connection(os.environ['AWS_ACCESSKEY'], os.environ['AWS_SECRETKEY'])
        return conn.get_bucket('migra_g.heroku')
    
    @classmethod
    def __key(cls,k=None):
        from boto.s3.connection import Key
        from time import gmtime
        from calendar import timegm
        from random import choice
        
        key = Key(cls.__bucket())
        if k is None:
            key.set_metadata('time',timegm(gmtime()))

            from string import ascii_lowercase as letters
            k = ''
            for i in range(12):
                k += choice(letters)
                    
        key.key = k
        return key

    @classmethod
    def store_file(cls,d):
        awsKey = cls.__key()
        awsKey.set_contents_from_string(json.dumps(d,indent=4,cls=MigraPersonEncoder))

        return awsKey.key
                    
    @classmethod
    def get_file(cls,k):
        awsKey = cls.__key(k)
        return json.loads(awsKey.get_contents_as_string())

    @classmethod
    def check_key(cls,k):
        awsKey = cls.__key(k)
        return awsKey.key

    @classmethod
    def list_keys(cls):
        from boto.s3.connection import Key
        b = cls.__bucket()
        return [ k.key for k in b.list() ]

    @classmethod
    def cleanup(cls, age):
        """ delete all keys more than age seconds old """

        from boto.s3.connection import Key
        from time import gmtime
        from calendar import timegm
        import logging

        delcount = 0        
        curtime = timegm(gmtime())
        b = cls.__bucket()
        for k in b.list():
            key = Key(b)
            key.key = k
            t = key.get_metadata('time')
            if t is None or ( curtime - t > age ):
                delcount =+ 1
                b.delete_key(k)

        logging.info ( "Deleted %s old files." % delcount )