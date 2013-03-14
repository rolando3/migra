import sys
import json
import psycopg2

from gedcom import *

__all__ = [
    "Migra",
    "MigraJSONEncoder" ]
#    "MigraDataCache",
#    "MigraWalker", 
#    "MigraLocation", 
#    "MigraPerson", 
#    "MigraHelper",
#    "MigraGeocoder",
#    "MigraError"]
    
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
    def __init__(self,name,lat,lng):
        self.__name = name
        self.__lat = lat
        self.__lng = lng
        
    def name(self):
        return self.__name;
        
    def lat(self):
        return self.__lat;
    
    def lng(self):
        return self.__lng;

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
    import decimal
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
            import traceback
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
            import traceback
            sys.stderr.write ( "Error finding cached geo location for %s.\n" % unicode(placename).encode("utf-8") + ''.join(traceback.format_exception( *sys.exc_info())[-2:]).strip().replace('\n',': ') )
            
        return None
        
    def cache ( self, location ):
        """ Given a location name, store it in the database. Result is irrelevant """
        sql = "INSERT INTO geocode ( placename, lat, lng ) VALUES ( %s, %s, %s );"
        try:
            cur = self.__con.cursor()
            cur.execute(sql,[ location.name(), location.lat(), location.lng() ])
            self.__con.commit()
            sys.stderr.write ( "Cached <%s>." % unicode(location.name()).encode("utf-8") )
        except:
            import traceback
            sys.stderr.write (  "Error caching location ( %s, lat: %s, lng: %s)\n" % ( unicode(location.name()).encode("utf-8"), location.lat(), location.lng() ) + ''.join(traceback.format_exception( *sys.exc_info())[-2:]).strip().replace('\n',': ') )
            return {'status': {'message': 'FAIL', 'code': -1} }
            
        return {'status': { 'message': 'OK', 'code': 0 } }

class Migra:
    def processGedcom ( self, file, query ):
        #the calling function will have gotten the file from the web server and done something with it.
        #based upon its framework it probably will have saved the file, but who knows? what we need to do:
        #turn the file into a Gedcom object and then return a reference to it and a reference to the
        #list of individuals that match the passed query. this way the frame
        
        #file can be a file name or a file object
        if isinstance(file, basestring):
            g = Gedcom.fromfilename(file)
        else:
            g = Gedcom(file)

        p = MigraHelper.buildListOfIndividuals(g,query)
        
        return (g, p)

    def walk ( self, g, i, d ):
        walker = MigraWalker(g,i,d)
        return { 'sid': 0, 'people': walker.people(), 'links': walker.links(), 'parameters': { 'id': i, 'depth': d } }
        
    def cache ( self, parms ):
        print MigraGeocoder().cache ( MigraLocation(parms["name"],parms["lat"],parms["lng"]) )