#!/usr/bin/env python

def checkstorage():
    from migrastorage import fileStorage
    print ( fileStorage().list_keys() )

def checkdb():
    from migra import MigraGeocoder
    print MigraGeocoder().countcachedaddresses()

def checkmemoryusage(fn,n):
    from gedcom import Gedcom
    from time import sleep

    print ( "Creating %s gedcom objects from %s ... " % ( n, fn ) )    
    for i in range(0,n):
        print ( i + 1 )
        g = None
        time.sleep(10)
        g = Gedcom.fromfilename(fn)

    print ( "We should be done now." )
    g=None
    
    while True:
        sleep(10)

#checkstorage()
#checkdb()
#checkmemoryusage(afilename,2)