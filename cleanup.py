from migrastorage import fileStorage

#delete everything over an hour old.
fileStorage().cleanup(3600)