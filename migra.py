import sys
import json
import psycopg2

from gedcom import *

#this will be set in the geocoder's init
geocoder = None

__all__ = [
    "Migra",
    "MigraPersonEncoder",
    "MigraGeocoder" ]

class MigraWalker:
    def __init__(self,dict,id,depth):
        self.__cache = dict
        self.__maxDepth = int(depth)

        self.__focusID = id
        
        self.__people = []
        self.__links = []
        
        focus = dict[id]
        if focus:
            p = self.__add_person(focus, 0)
            self.__walk_parents(focus, 0)                    

    def people(self):
        return self.__people
            
    def links(self):
        return self.__links

    def __add_person(self,p,l):
        p['generation']=l
        self.__people.append(p)
        return p
    
    def __add_link(self,parent,child):
        self.__links.append({'parent': parent['id'], 'child': child['id'] })
    
    def __walk_parents(self,person,l):    
        l = l + 1    

        if ( l > self.__maxDepth ):
            return
        
        for n in person['parents']:
            id = person['parents'][n]
        
            if id is not None:
                #if this id is already part of this person's path we are going to end up in a recursive shitshow.
                for i in person['path']:
                    if i == id:
                        sys.stderr.write ( 'Recursion weirdness around %s and %s\n' % ( person['name'], self.__cache[id]['name'] ) )
                        break
                else:
                    p = self.__cache[id]
                    if p != None:
                        parent = self.__add_person(p,l)
                        
                        parent['path'] = list(person['path']) or [] #makes a copy
                        parent['path'].append(person['id'])        #adds an item -- does not return new path value                    
                        
                        self.__add_link(parent,person)
                        self.__walk_parents(parent, l)

class MigraPerson (GedcomIndividual):
    def __init__(self,e,l=0):
        #given an element, create a person object
        super(MigraPerson, self).__init__(e)
        self.__generation = l
        self.__path = []
        self.__location = None

        loc = MigraHelper.get_place(e)
       
        if loc:
            self.__location = { 
                'name': loc[1], 
                'latlng': geocoder.geocode(loc[1]), 
                'date': MigraHelper.get_year(loc) 
            }
    
    def path(self,path=None):
        #given a path from the "ego" set our path attribute.
        if path is not None:
            self.__path = path

        return self.__path 
     
    def location(self):
        return self.__location
        
    def generation(self):
        return self.__generation

class MigraPersonEncoder(json.JSONEncoder):
    def default(self, o):
        import decimal
        if isinstance(o, decimal.Decimal):
            return float(o)            
        else:
            return { 'id': o.id(), 
                     'name': o.name(), 
                     'sex': o.sex(), 
                     'birth': o.birth(), 
                     'death': o.death(), 
                     'marriages': o.marriages(), 
                     'parents': o.parents(),
                     'location': o.location(),
                     'generation': o.generation(),
                     'offspring': o.offspring(),
                     'path': [person.id() for person in o.path()],
                   }

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
        First checks birthplace, then death place, etc... """
        
        best = None
        
        for pl in i.places():
            year = cls.get_year(pl)
    
            if pl[1] != "" and pl[1] != "Unknown":
                if ( best == None ) and ( pl[0] == "" ):
                    best = pl
                elif ( year != None ):
                    return pl
            
        return best
    
    @classmethod
    def buildListOfIndividuals(cls,l,q):
        import sys
        people = []
    
        if not q: sys.stderr.write ( "No query string received.\n" )

        q = q.lower()

        filtered = []
        for p in l:
            uname = unicode(p.name(),"utf-8").lower()
            if ( uname.find(q) >= 0 ):    
                filtered.append ( p )

        return sorted(filtered, key=lambda person: person.name() )

class MigraError(Exception):
    def __init__ ( self, value ):
        self.value = value
        
    def __str__ ( self ):
        return repr(self.value)    

class MigraGeocoder:
    """This class is for getting stored geocodes"""
    
    def __init__ ( self ):
        """Connect to our database"""
        
        global geocoder
        geocoder = self
        
        try:
            self.__con = psycopg2.connect(database='migra', user='postgres', password='shomia')
        except:
            import traceback
            sys.stderr.write ( "Cannot connect to database." + ''.join(traceback.format_exception( *sys.exc_info())[-2:]).strip().replace('\n',': ') )
                    
    def geocode ( self, placename ):
        """ Look on our database for a stored geocode. If none, return None """
        if placename is None: return None
        
        sql = "SELECT lat, lng FROM geocode WHERE placename = %s"
        try:
            cur = self.__con.cursor()
            cur.execute(sql,[placename])
            result = cur.fetchone()
            if result is not None :
                return  { 'lat': result[0], 'lng': result[1] }

        except:
            import traceback
            sys.stderr.write ( "Error finding cached geo location. %s \n" % ''.join(traceback.format_exception( *sys.exc_info())[-2:]).strip().replace('\n',': ') )
            
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
    def __init__(self):
        MigraGeocoder()

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

        full = []
        dict = {}
        for i in g.element_list():
            if i.individual():
                p = MigraPerson(i)
                dict[i.pointer()] = p
                full.append ( p )

        filtered = MigraHelper.buildListOfIndividuals(full,query)

        return (dict, filtered)

    def walk ( self, dict, id, depth ):
        '''Given a full list of all people, and a focal node, and a depth, tell the walker to walk back as far as it can '''
        walker = MigraWalker(dict,id,int(depth))
        return { 'people': walker.people(), 'links': walker.links(), 'parameters': { 'id': id, 'depth': depth } }
        
    def cache ( self, parms ):
        print MigraGeocoder().cache ( MigraLocation(parms["name"],parms["lat"],parms["lng"]) )

