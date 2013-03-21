import logging
from migrastorage import fileStorage

logging.basicConfig()
fileStorage().cleanup(3600)
