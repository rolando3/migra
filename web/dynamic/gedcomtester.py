#!/opt/local/bin/python

from gedcom import Gedcom, GedcomIndividual
import json
from migra import MigraPerson, MigraGeocoder, MigraPersonEncoder

import sys
sys.stderr.write ( "Reading file into gedcom object...\n" )

g = Gedcom.fromfilename('/Users/rolando/src/migradata/big.ged')
#g = Gedcom.fromfilename('/Users/rolando/src/migradata/romney2.ged')
gc = MigraGeocoder()

sys.stderr.write ( "Done... Building JSON list...\n" )

pList = []

for i in g.element_list():
    if i.individual():
        pList.append ( MigraPerson(i,0,gc) )

sys.stderr.write ( "Done. Dumping JSON list. . .\n" )

print json.dumps(pList,indent=4,cls=MigraPersonEncoder)

sys.stderr.write ( "Done.\n" )

