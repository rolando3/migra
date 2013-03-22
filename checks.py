#!/usr/bin/env python


def checkstorage():
    from migrastorage import fileStorage
    print ( fileStorage().list_keys() )

def checkdb():
    from migra import MigraGeocoder
    print MigraGeocoder().countcachedaddresses()

checkstorage()
checkdb()
