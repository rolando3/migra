#!/usr/bin/env python

from migrastorage import fileStorage
import logging

logging.basicConfig()

#delete everything over an hour old.
fileStorage().cleanup(3600)