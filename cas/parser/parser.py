#!/usr/bin/env python

import os,sys,re

"""
Renders custom markdown to tex, PDF, and HTML.
Updated from parser.py to include revtex and more explicit data handling.
"""

#---settings
instruct = sys.argv[1]
from parselib import TexDocument
#---we can only run the parser if we have a silo
if not os.path.isdir('history'):
	sys.path.insert(0,'cas')
	from makeface import tracebacker
	tracebacker(Exception('cannot find `history` repo. you may need to run `make init` once!'))
	sys.exit(1)
doc = TexDocument(instruct)
