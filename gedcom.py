#
# Gedcom 5.5 Parser
#
# Copyright (C) 2005 Daniel Zappala (zappala [ at ] cs.byu.edu)
# Copyright (C) 2005 Brigham Young University
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
# Please see the GPL license at http://www.gnu.org/licenses/gpl.txt
#
# To contact the author, see http://faculty.cs.byu.edu/~zappala

__all__ = ["Gedcom", "Element", "GedcomParseError"]

# Global imports
import string

class Gedcom(object):
    """ Gedcom parser

    This parser is for the Gedcom 5.5 format.  For documentation of
    this format, see

    http://homepages.rootsweb.com/~pmcbride/gedcom/55gctoc.htm

    This parser reads a GEDCOM file and parses it into a set of
    elements.  These elements can be accessed via a list (the order of
    the list is the same as the order of the elements in the GEDCOM
    file), or a dictionary (the key to the dictionary is a unique
    identifier that one element can use to point to another element).

    """

    def __init__(self,fd,options=None):
        """ Initialize a Gedcom parser. You must supply a Gedcom file.
        """

        self.__element_list = []
        self.__element_dict = {}
        self.__element_top = Element(-1,"","TOP","",self)
        self.__current_level = -1
        self.__current_element = self.__element_top
        self.__individuals = 0
        self.__parse(fd)
        self.__fd = fd
        
#    def __del__(self):
#        self.__element_dict = None

    @classmethod
    def fromfilename(cls, name):
        import codecs
        return cls(codecs.open( name, "r", "utf-8-sig" ))

    def element_list(self):
        """ Return a list of all the elements in the Gedcom file.  The
        elements are in the same order as they appeared in the file.
        """
        return self.__element_list

    def element_dict(self):
        """ Return a dictionary of elements from the Gedcom file.  Only
        elements identified by a pointer are listed in the dictionary.  The
        key for the dictionary is the pointer.
        """
        return self.__element_dict

    def element(self,pointer):
        return self.__element_dict[pointer]

    # Private methods

    def __strip_bom(self,l):
        try:
            bom_info = (
                ('\xEF\xBB\xBF',     3, 'UTF-8'),
                ('\xFE\xFF',         2, 'UTF-16BE'),
                ('\xFF\xFE',         2, 'UTF-16LE'),
                ('\xFF\xFE\x00\x00', 4, 'UTF-32LE'),
                ('\x00\x00\xFE\xFF', 4, 'UTF-32BE'),
                )
                
            for sig, siglen, enc in bom_info:
                if l.startswith(sig):
                    l = l[siglen:]
        finally:
            return l

    def __parse(self,f):
        # open file
        # go through the lines
        number = 1
        for line in f.readlines():
            if number == 1:
                line = self.__strip_bom(line)

            self.__parse_line(number,line)
            number += 1
        self.__count()

    def __parse_line(self,number,line):
        # each line should have: Level SP (Pointer SP)? Tag (SP Value)? (SP)? NL
        # parse the line
        parts = string.split(line)
        place = 0
        l = self.__level(number,parts,place)
        place += 1
        p = self.__pointer(number,parts,place)
        if p != '':
            place += 1
        t = self.__tag(number,parts,place)
        place += 1
        v = self.__value(number,parts,place)

        # create the element
        if l > self.__current_level + 1:
            self.__error(number,"Structure of GEDCOM file is corrupted")

        e = Element(l,p,t,v,self)
        self.__element_list.append(e)
        if p != '':
            self.__element_dict[p] = e

        if l > self.__current_level:
            self.__current_element.add_child(e)
            e.add_parent(self.__current_element)
        else:
            # l.value <= self.__current_level:
            while (self.__current_element.level() != l - 1):
                self.__current_element = self.__current_element.parent()
            self.__current_element.add_child(e)
            e.add_parent(self.__current_element)

        # finish up
        self.__current_level = l
        self.__current_element = e

    def __level(self,number,parts,place):
        if len(parts) <= place:
            self.__error(number,"Empty line")
        try:
            l = int(parts[place])
        except ValueError:
            self.__error(number,"Line must start with an integer level %s" % parts[place])

        if (l < 0):
            self.__error(number,"Line must start with a positive integer")

        return l

    def __pointer(self,number,parts,place):
        if len(parts) <= place:
            self.__error(number,"Incomplete Line")
        p = ''
        part = parts[1]
        if part[0] == '@':
            if part[len(part)-1] == '@':
                p = part
                # could strip the pointer to remove the @ with
                # string.strip(part,'@')
                # but it may be useful to identify pointers outside this class
            else:
                self.__error(number,"Pointer element must start and end with @")
        return p

    def __tag(self,number,parts,place):
        if len(parts) <= place:
            self.__error(number,"Incomplete line")
        return parts[place]

    def __value(self,number,parts,place):
        if len(parts) <= place:
            return ''
        p = self.__pointer(number,parts,place)
        if p != '' and place < 3: #if we get to the fourth then 
            # rest of the line should be empty
            if len(parts) > place + 1:
                self.__error(number,"Too many elements: %s (cannot be greater than %s)" % ( len(parts), place+1 ))
            return p
        else:
            # rest of the line should be ours
            vlist = []
            while place < len(parts):
                vlist.append(parts[place])
                place += 1
            v = string.join(vlist)
            return v
            
    def __error(self,number,text):
        error = "Gedcom format error on line " + str(number) + ': ' + text
        raise GedcomParseError, error

    def __count(self):
        # Count number of individuals
        self.__individuals = 0
        for e in self.__element_list:
            if e.individual():
                self.__individuals += 1

    def __print(self):
        for e in self.element_list:
            print string.join([str(e.level()),e.pointer(),e.tag(),e.value()])


class GedcomParseError(Exception):
    """ Exception raised when a Gedcom parsing error occurs
    """
    
    def __init__(self, value):
        self.value = value
        
    def __str__(self):
        return `self.value`

class Element(object):
    """ Gedcom element

    Each line in a Gedcom file is an element with the format

    level [pointer] tag [value]

    where level and tag are required, and pointer and value are
    optional.  Elements are arranged hierarchically according to their
    level, and elements with a level of zero are at the top level.
    Elements with a level greater than zero are children of their
    parent.

    A pointer has the format @pname@, where pname is any sequence of
    characters and numbers.  The pointer identifies the object being
    pointed to, so that any pointer included as the value of any
    element points back to the original object.  For example, an
    element may have a FAMS tag whose value is @F1@, meaning that this
    element points to the family record in which the associated person
    is a spouse.  Likewise, an element with a tag of FAMC has a value
    that points to a family record in which the associated person is a
    child.
    
    See a Gedcom file for examples of tags and their values.

    """

    def __init__(self,level,pointer,tag,value,gedcom):
        """ Initialize an element.  You must include a level, pointer,
        tag, value, and global element dictionary.  Normally initialized
        by the Gedcom parser, not by a user.
        """
        import weakref
        # basic element info
        self.__level = level
        self.__pointer = pointer
        self.__tag = tag
        self.__value = value
        self.__gedcom = weakref.ref(gedcom)
        # structuring
        self.__children = []
        self.__parentref = None
        
    def __find_element(self,ptr):
        ''' find another element in the gedcom, given a pointer '''
        return self.__gedcom().element_dict().get(ptr,None)
    
    def __event(self,event):
        """ Return the location tuple of the given type as (date,place) """
        if not self.individual():
            return None;

        date = None
        place = None
        addr = None
        addrPlace = None

        for e in self.children():
            if e.tag() == event:
                for c in e.children():
                    if c.tag() == "DATE":
                        date = c.value()
                    if c.tag() == "PLAC":
                        place = c.value()
                    if c.tag() == "ADDR":
                        addrPlace = []
                        addr = c.children()
                        for ac in addr:
                            addrPlace.append(ac.value())

        #now we have to resolve the conflict if any between place and address
        #how do we know which is better? we don't. they may be redundant.
        #given the point of this program, Address is probaby preferable
        if ( addr ):
            place = ", ".join(addrPlace)
    
        return None if ( date, place ) == ( None, None ) else ( date, place )
        
    def __event_year(self,event):
        """ Return the event year of a person in integer format """
        date = ""
        if not self.individual():
            return date

        e = self.__event(event);
            
        try:
            datel = string.split(e[0])
            date = datel[len(datel)-1]
            return int(date)
        except:
            return None

    def level(self):
        """ Return the level of this element """
        return self.__level

    def pointer(self):
        """ Return the pointer of this element """
        return self.__pointer
    
    def tag(self):
        """ Return the tag of this element """
        return self.__tag

    def value(self):
        """ Return the value of this element """
        return self.__value

    def children(self):
        """ Return the child elements of this element """
        return self.__children

    def parent(self):
        """ Return the parent element of this element """
        return self.__parentref()

    def add_child(self,element):
        """ Add a child element to this element """
        self.children().append(element)
        
    def add_parent(self,element):
        import weakref
        """ Add a parent element to this element """
        self.__parentref = weakref.ref(element)

    def individual(self):
        """ Check if this element is an individual """
        return self.tag() == "INDI"

    # criteria matching

    def criteria_match(self,criteria):
        """ Check in this element matches all of the given criteria.
        The criteria is a colon-separated list, where each item in the

        list has the form [name]=[value]. The following criteria are supported:

        surname=[name]
             Match a person with [name] in any part of the surname.
        name=[name]
             Match a person with [name] in any part of the given name.
        birth=[year]
             Match a person whose birth year is a four-digit [year].
        birthrange=[year1-year2]
             Match a person whose birth year is in the range of years from
             [year1] to [year2], including both [year1] and [year2].
        death=[year]
        deathrange=[year1-year2]
        marriage=[year]
        marriagerange=[year1-year2]

        """

        # error checking on the criteria
        try:
            for crit in criteria.split(':'):
                key,value = crit.split('=')
        except:
            return False
            
        match = True
        for crit in criteria.split(':'):
            key,value = crit.split('=')
            if key == "surname" and not self.surname_match(value):
                match = False
            elif key == "name" and not self.given_match(value):
                match = False
            elif key == "birth":
                try:
                    year = int(value)
                    if not self.birth_year_match(year):
                        match = False
                except:
                    match = False
            elif key == "birthrange":
                try:
                    year1,year2 = value.split('-')
                    year1 = int(year1)
                    year2 = int(year2)
                    if not self.birth_range_match(year1,year2):
                        match = False
                except:
                    match = False
            elif key == "death":
                try:
                    year = int(value)
                    if not self.death_year_match(year):
                        match = False
                except:
                    match = False
            elif key == "deathrange":
                try:
                    year1,year2 = value.split('-')
                    year1 = int(year1)
                    year2 = int(year2)
                    if not self.death_range_match(year1,year2):
                        match = False
                except:
                    match = False
            elif key == "marriage":
                try:
                    year = int(value)
                    if not self.marriage_year_match(year):
                        match = False
                except:
                    match = False
            elif key == "marriagerange":
                try:
                    year1,year2 = value.split('-')
                    year1 = int(year1)
                    year2 = int(year2)
                    if not self.marriage_range_match(year1,year2):
                        match = False
                except:
                    match = False
                    
        return match

    def pointer_match(self,pointer):
        """ Match a string with the pointer of an individual"""
        return self.pointer() == pointer
    
    def name_match(self,name,casesensitive=True):
        """ Match a string with either the given name or surname of an individual """
        (first,last) = self.name()
        if ( not casesensitive ):
            name = name.lower()
            first = first.lower()
            last = last.lower()

        parts = string.split(name.strip())
        
        for p in parts:
            if ( p not in first and p not in last ):
                return False
                
        return True
        
    def surname_match(self,name):
        """ Match a string with the surname of an individual """
        (first,last) = self.name()
        return last in name

    def given_match(self,name):
        """ Match a string with the given names of an individual """
        (first,last) = self.name()
        return first in name

    def birth_year_match(self,year):
        """ Match the birth year of an individual.  Year is an integer. """
        return self.birth_year() == year

    def birth_range_match(self,year1,year2):
        """ Check if the birth year of an individual is in a given range.
        Years are integers.
        """
        year = self.birth_year()
        if year >= year1 and year <= year2:
            return True
        return False

    def death_year_match(self,year):
        """ Match the death year of an individual.  Year is an integer. """
        return self.death_year() == year

    def death_range_match(self,year1,year2):
        """ Check if the death year of an individual is in a given range.
        Years are integers.
        """
        year = self.death_year()
        if year >= year1 and year <= year2:
            return True
        return False

    def marriage_year_match(self,year):
        """ Check if one of the marriage years of an individual matches
        the supplied year.  Year is an integer. """
        years = self.marriage_years()
        return year in years

    def marriage_range_match(self,year1,year2):
        """ Check if one of the marriage year of an individual is in a
        given range.  Years are integers.
        """
        years = self.marriage_years()
        for year in years:
            if year >= year1 and year <= year2:
                return True
        return False

    def families(self):
        """ Return a list of all of the family elements of a person. """
        results = []
        for e in self.children():
            if e.tag() == "FAMS":
                f = self.__find_element(e.value())
                if f != None:
                    results.append(f)

        return results

    def name(self):
        """ Return a person's names as a tuple: (first,last) """
        first = ""
        last = ""
        suffix = ""
        if not self.individual():
            return (first,last)
        for e in self.children():
            if e.tag() == "NAME":
                # some older Gedcom files don't use child tags but instead
                # place the name in the value of the NAME tag
                if e.value() != "":
                    name = string.split(e.value(),'/')
                    first = string.strip(name[0])
                    if len(name) > 1:
                        last = string.strip(name[1])
                    if len(name) > 2:
                        suffix = string.strip(name[2])
                else:
                    for c in e.children():
                        if c.tag() == "GIVN":
                            first = c.value()
                        if c.tag() == "SURN":
                            last = c.value()
        return (first,last)

    def surname(self):
        return self.name()[1]
    
    def given(self):
        return self.name()[0]
    
    def full_name(self):
        """ Return a string of the person's name """
        return " ".join(self.name())

    def sex(self):
        if not self.individual():
            return None;
            
        for e in self.children():
            if e.tag() == "SEX":
                return e.value();

        return "?";

    def birth(self):
        """ Return the birth tuple of a person as (date,place) """
        return self.__event("BIRT")

    def birth_year(self):
        """ Return the birth year of a person in integer format """
        return self.__event_year("BIRT")
    
    def death(self):
        """ Return the death tuple of a person as (date,place) """
        return self.__event("DEAT")

    def death_year(self):
        """ Return the death year of a person in integer format """
        date = ""
        return self.__event_year("DEAT")

    def baptism(self):
        """ Return the birth tuple of a person as (date,place) """
        return self.__event("BAPM")

    def burial(self):
        """ Return the baptism tuple of a person as (date,place) """
        return self.__event("BURI")
        
    def deceased(self):
        """ Check if a person is deceased """
        if not self.individual():
            return False
        for e in self.children():
            if e.tag() == "DEAT":
                return True
        return False

    def parents(self):
    	""" Return an individual's parents in a list, 
    	    the father in position 0, mother in 1 
    	"""
    	
    	parents = [None,None]
    	if not self.individual():
    		return parents
    	
    	for e in self.children():
    		if e.tag() == "FAMC":
    			f = self.__find_element(e.value())
    			if f != None:
    				for g in f.children():
    					if g.tag() == "HUSB":
    						parents[0] = self.__find_element(g.value())
    					elif g.tag() == "WIFE":	
    						parents[1] = self.__find_element(g.value())
    	
    	return parents

    def marriages(self):
        """ Return a list of marriage dicts for a person in the format
         { family: FAM pointer (i.e. string),
           spouse: INDI pointer (string),
           date: string,
           place: string }
        """
        marriages = []
        if not self.individual():
            return marriages
            
        for e in self.children():
            if e.tag() == "FAMS":
                f = self.__find_element(e.value())
                if f != None:
                    mar = { "family": e, "spouse": None, "date": None, "place": None }
                    for g in f.children():
	                    if g.tag() == "MARR":
	                        for h in g.children():
	                            if h.tag() == "DATE":
	                                mar["date"] = h.value()
	                            if h.tag() == "PLAC":
	                                mar["place"] = h.value()
	                    elif ( g.tag() == "HUSB" or g.tag() == "WIFE" ) and g.value() != self.pointer():
	                        mar["spouse"] = self.__find_element(g.value())
	                                
                    marriages.append(mar)             

        return marriages

    def marriage_years(self):
        """ Return a list of marriage years for a person, each in integer
        format.
        """
        dates = []
        for m in self.marriages():
            if len(m) > 0:
                try:
                    datel = date.split()
                    if len(datel) > 0:
                        dates.append ( int(datel[len(datel)-1]))
                except:
                    pass
        return dates

    def places(self):
        """ Return a list of tuples (place, year) for a person's locations
        """
        result = []

        for p in [ self.birth(), self.death(), self.baptism(), self.burial() ]:
            if p != None:
                result.append( p )
        
        return result

    def get_individual(self):
        """ Return this element and all of its sub-elements """
        result = str(self)
        for e in self.children():
            result += '\n' + e.get_individual()
        return result
        
    def get_family(self):
        result = self.get_individual()
        for e in self.children():
            if e.tag() == "HUSB" or e.tag() == "WIFE" or e.tag() == "CHIL":
                f = self.__find_element(e.value())
                if f != None:
                    result += '\n' + f.get_individual()
        return result

    def family(self):
        """ Gets the pointer of the family for which this person was a member """
       	if not self.individual():
    		return None

        for e in self.children():
            if e.tag() == "FAMC":
                return e
            
        return None
    
    def offspring(self):
        results = []
        for f in self.families():
            for e in f.children():
                if e.tag() == "CHIL":
                    results.append(self.__find_element(e.value()))

        return results
            
    def __str__(self):
        """ Format this element as its original string """
        result = str(self.level())
        if self.pointer() != "":
            result += ' ' + self.pointer()
        result += ' ' + self.tag()
        if self.value() != "":
            result += ' ' + self.value()
        return result
        
