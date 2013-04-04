import os
import sys
import json
from migra import MigraPersonEncoder

__all__ = [ 'LocalFileStorage', 'AmazonS3FileStorage', 'fileStorage' ]

def fileStorage():
    return AmazonS3FileStorage

class LocalFileStorage:
    @classmethod
    def __getfolder(cls):
        return os.environ.get('MIGRA_UPLOADFOLDER','.')

    @classmethod
    def store_file(cls,d,k=None):
        """ Given a dict of all of the people in our gedcom, store it somewhere, and then pass back an 
            identifier that will make it easy to find on the second pass."""
        from tempfile import NamedTemporaryFile
    
        f = NamedTemporaryFile(suffix='.json',dir=cls.__getfolder(),delete=False)
        sys.stderr.write ( " saving to %s \n" % f.name )
        f.write(json.dumps(d,cls=MigraPersonEncoder))
        f.close()
        return f.name.split('/')[-1]
        
    @classmethod
    def get_file(cls,k):
        """ Given a key, get the stored file and return the deserialized object """
        f = open('/'.join((cls.__getfolder(),k)),'r')
        d = json.load(f)
        f.close()
        return d

    @classmethod
    def cleanup(cls, age):
        """ delete all files more than age seconds old """
        from time import gmtime
        from calendar import timegm
        
        delcount = 0
        fo = cls.__getfolder()
        curtime = timegm(gmtime())

        for file in os.listdir(fo):
            path = '/'.join((fo,file))
            mod = os.stat(path).st_mtime
            if ( curtime - mod > age ):
                delcount =+ 1
                os.remove(path)

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
        
        if k is None:
            key = Key(cls.__bucket())
            from string import ascii_lowercase as letters
            k = ''
            for i in range(12):
                k += choice(letters)
            key.key = k
            key.set_metadata('time',timegm(gmtime()))
        else:
            key = cls.__bucket().get_key(k)

        return key

    @classmethod
    def store_file(cls,d,k=None):
        awsKey = cls.__key(k)
        if awsKey is None:
            awsKey = cls.__key()
        
        awsKey.set_contents_from_string(json.dumps(d,cls=MigraPersonEncoder))

        return awsKey.key
                    
    @classmethod
    def get_file(cls,k):
        awsKey = cls.__key(k)
        if awsKey is None:
            raise ValueError, ("The key %s no longer exists" % k)
        else:
            return json.loads(awsKey.get_contents_as_string())

    @classmethod
    def list_keys(cls):
        from time import gmtime
        from calendar import timegm
        b = cls.__bucket()
        result = []
        now = timegm(gmtime())
        for k in b.list():
            key = b.get_key(k)
            if key.get_metadata('time') is None:
                result.append ( ( key.key, None ) )
            else:
                result.append ( ( key.key, now - int( key.get_metadata('time'))))
            
        return result

    @classmethod
    def cleanup(cls, age):
        """ delete all keys more than /age/ seconds old """

        from boto.s3.connection import Key
        from time import gmtime
        from calendar import timegm
        import logging

        delcount = 0        
        curtime = timegm(gmtime())
        b = cls.__bucket()
        for k in b.list():
            key = b.get_key(k)
            t = key.get_metadata('time')
            if t is None:
                #do nothing
                pass
            elif ( curtime - int(t) > age ):
                delcount =+ 1
                b.delete_key(k)

        logging.info ( "Deleted %s old files." % delcount )
