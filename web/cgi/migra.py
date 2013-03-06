#!/opt/local/bin/python

#this is python 2.7. Frankly I don't 

import sys
import json
import cgi
import traceback
import psycopg2
import decimal
import copy
#import cgitb; cgitb.enable()
from gedcom import *

class MigraDataCache:
    def __init__(self):
        self.__people = []
        self.__links = []
        self.__maxDepth = 10
        
    def people(self):
        return self.__people
        
    def addPerson(self, person):
        self.__people.append(person)

    def person(self,id):
        return self.__peopleDict[id]
        
    def links(self):
        return self.__links
        
    def maxDepth(self):
        return self.__maxDepth
        
    def setMaxDepth(self,d):
        d = int(d)
        if d > 0:
            self.__maxDepth = d

class MigraWalker:
    def __init__(self,gedcom,id,depth):
        self.__cache = MigraDataCache()
        self.__cache.setMaxDepth(depth)
        self.__geocoder = MigraGeocoder()

        e = gedcom.element(id)
        if e.individual():
            p = self.__add_person(e, 0)
            self.__walk_parents(p, 0)                    

    def people(self):
        #this is so clunky
        result = []
        pList = self.__cache.people()
        
        for p in pList:
            result.append(p.asJsonReady())
            
        return result 
            
        
    def links(self):
        return self.__cache.links()

    def __add_person(self,e,l):
        p = MigraPerson(e,l,self.__geocoder)
        self.__cache.addPerson(p);
        return p
    
    def __add_link(self,parent_e,child_e):
        self.__cache.links().append({'parent': parent_e.pointer(), 'child': child_e.pointer() })
    
    def __walk_parents(self,person,l):
    
        l = l + 1    
        if ( l > self.__cache.maxDepth() ):
            return
        
        e = person.element()
        
        for pe in e.parents():
            if pe != None:
                parent = self.__add_person(pe,l)
                
                newPath = list(person.path()) #makes a copy
                newPath.append(person)        #adds an item -- does not return new path value
                parent.path ( newPath )       #append the new path
                
                self.__add_link(pe, e)
                self.__walk_parents(parent, l)

class MigraPerson:
    def __init__(self,e,l,g):
        #given an element, create a person object
        self.__element = e
        self.__generation = l
        self.__geocoder = g #yuck but whatever
        self.__id = e.pointer()
        self.__name = e.full_name()
        self.__sex = e.sex()
        self.__path = []

        self.__place = MigraHelper.get_place(e)
        if self.__place != None:
            self.__placename = self.__place[1]
            self.__latlng = self.__geocoder.geocode(self.__place[1])
            self.__date = MigraHelper.get_year(self.__place)
        else:
            self.__placename = None
            self.__latlng = None
            self.__date = None
        

    def asJsonReady(self):
        path = [person.id() for person in self.__path]        
        return { 'id': self.__id, 'name': self.__name, 'sex': self.__sex, 'generation': self.__generation, 'placename': self.__placename, 'latlng': self.__latlng, 'date': self.__date, 'path': path }
    
    def element(self):
        return self.__element
        
    def id(self):
        return self.__id
        
    def path(self,path=None):
        #given a path from the "ego" set our path attribute.
        if path is not None:
            self.__path = path
            
        return self.__path 
        
class MigraLocation:
    def __init__(self):
        return

class MigraHelper:
    def __init__(self):
        """Not a lot happens here since this guy only has class methods"""
        
    @classmethod
    def get_year(cls, pl):
        """ Given a location tuple (date, location) gets the year part of the date 
        and returns the year """ 
    
        year = None
        if pl[0] != "":
            try:
                datel = pl[0].split()
                if len(datel) > 0:
                    year = int(datel[len(datel)-1])
                else:
                    pass
            except:
                pass
        else:
            pass
            
        return year
        
    @classmethod
    def get_place(cls, i):
        """ Given an individual element, gets the place for that individual.
        First checks birthplace, then death place, then marriage places. """
        
        best = None
        
        for pl in i.places():
        
            year = cls.get_year(pl)
    
            if pl[1] != "" and pl[1] != "Unknown":
                if ( best == None ) and ( pl[0] == "" ):
                    best = pl
                elif ( year != None ):
                    return pl
            
        return best
    
#    if ( best == None ):
#        sys.stderr.write ( "WARNING: No locations found for %s (%s)\n" % ( unicode(" ".join(i.name())).encode("utf-8"), unicode#(i.pointer()).encode("utf-8") ) )
    @classmethod
    def buildListOfIndividuals(cls,g,q):
        fs = cgi.FieldStorage()
        people = []
    
        if not q:
            sys.stderr.write ( "No query string received.\n" )

        for e in g.element_list():
            if e.individual():
                if q:
                    if e.name_match(q,False):
                        people.append ( { 'id': e.pointer(), 'name': e.full_name(), 'surname': e.surname(), 'given': e.given(), 'birth': e.birth_year() } )
                else:
                    people.append ( { 'id': e.pointer(), 'name': e.full_name(), 'surname': e.surname(), 'given': e.given(), 'birth': e.birth_year() } )
                    
        return sorted(people, key=lambda person: person["surname"] + "," + person["given"] )

class MigraError(Exception):
    def __init__ ( self, value ):
        self.value = value
        
    def __str__ ( self ):
        return repr(self.value)    

class MigraJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        super(DecimalEncoder, self).default(o)
    
class MigraGeocoder:
    """This class is for getting stored geocodes"""
    
    def __init__ ( self ):
        """Connect to our database"""
        try:
            self.__con = psycopg2.connect(database='migra', user='postgres', password='shomia')
        except:
            sys.stderr.write ( "Cannot connect to database." + ''.join(traceback.format_exception( *sys.exc_info())[-2:]).strip().replace('\n',': ') )
                    
    def geocode ( self, placename ):
        """ Look on our database for a stored geocode. If none, return None """
        sql = "SELECT lat, lng FROM geocode WHERE placename = %s"
        try:
            cur = self.__con.cursor()
            cur.execute(sql,[placename])
            result = cur.fetchone()
            if ( result == None ):
                #We need to let the client know there is nothing for them here.
                sys.stderr.write ( "WARN: No results for %s" % unicode(placename).encode("utf-8") )
            else:
                return  { 'lat': result[0], 'lng': result[1] }
        except:
            sys.stderr.write ( "Error finding cached geo location for %s.\n" % unicode(placename).encode("utf-8") + ''.join(traceback.format_exception( *sys.exc_info())[-2:]).strip().replace('\n',': ') )
            
        return None
        
    def cache ( self, location ):
        """ Given a location name, store it in the database. Result is irrelevant """
        sql = "INSERT INTO geocode ( placename, lat, lng ) VALUES ( %s, %s, %s );"
        try:
            cur = self.__con.cursor()
            cur.execute(sql,[ location["name"], location["lat"], location["lng"] ])
            self.__con.commit()
            sys.stderr.write ( "Cached <%s>." % unicode(location["name"]).encode("utf-8") )
        except:
            sys.stderr.write (  "Error caching location ( %s, lat: %s, lng: %s)\n" % ( unicode(location["name"]).encode("utf-8"), location["lat"], location["lng"] ) + ''.join(traceback.format_exception( *sys.exc_info())[-2:]).strip().replace('\n',': ') )
            return json.dumps({'status': {'message': 'FAIL', 'code': -1} } )
            
        return json.dumps({'status': { 'message': 'OK', 'code': 0 } })

def header ():
    return "Content-type: application/json\n\n"

def gedcom_fromcgi ( fs ):
    sid = fs.getvalue("sid")
    if sid == None:
        import sha, time
        sid = sha.new(str(time.time())).hexdigest()

    localfilename = "/Users/rolando/src/migra/data/%s.ged" % sid

    if  fs.has_key("gedcom"):
        fd = fs["gedcom"]
        open(localfilename, 'wb').write(fd.file.read())

    return ( sid, Gedcom.fromfilename(localfilename) )

def main ():
    """ what gets called when this web page is hit """

    fs = cgi.FieldStorage()
    action = fs.getvalue("a")

    if action == "" or action == None:
        action = "p"    

    if action == "p":
        #if action is p then we're reading the file and returning a list of individuals
	( sid, g ) = gedcom_fromcgi(fs)
        if g:
            p = MigraHelper.buildListOfIndividuals(g,fs.getvalue("q"))
            print header()
            print json.dumps ( { 'sid': sid, 'people': p, 'parameters': { 'query': fs.getvalue("q") } }, indent=4 )
        else:
            sys.stderr.write("Gedcom build failed") 

    elif action == "w":
        #if action is w then we're walking the tree
        ( sid, g )  = gedcom_fromcgi(fs)
        
        walker = MigraWalker(g,fs.getvalue("i"),fs.getvalue("d"))

        print header()
        result = json.dumps ( { 'sid': sid, 'people': walker.people(), 'links': walker.links(), 'parameters': { 'id': fs.getvalue("i"), 'depth': fs.getvalue("d") } }, indent=4, cls=MigraJSONEncoder )
        sys.stderr.write ( result )
        print result
        
    elif action == "c":
        #caching a latlng
        #client-side geocoding has been done. we are now going to cache 
        gc = MigraGeocoder()
        print header()
        print gc.cache ( json.loads(fs.getvalue("data")) )
        

main()
