#!/usr/bin/env python

from migrastorage import fileStorage

def checkstorage():
    print ( fileStorage().list_keys() )

checkstorage()
