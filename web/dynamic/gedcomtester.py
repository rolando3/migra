#!/opt/local/bin/python

from gedcom import Gedcom

g = Gedcom.fromfilename('/Users/rolando/src/migradata/romney2.ged')

print g.__All__()