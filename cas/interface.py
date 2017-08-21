#!/usr/bin/env python

"""
Cassette command-line interface.
"""

import os,sys,subprocess,glob,re,shutil,datetime,time
import yaml

#---this script is a peer of makeface
from makeface import asciitree,fab,bash,str_or_list,command_check

#---name the silo for tracking clean copies of the texts
siloname = 'history'

#---this script is imported by makeface.py so we only expose relevant functions
__all__ = ['init','remake','pull','index','dev','bootstrap']

###---INITIALIZATION

def make_silo(name=None):
	"""
	Create a directory for tracking changes to the documents via git.
	"""
	if not name:
		global siloname
		name = siloname
	#---create the silo if absent
	if not os.path.isdir(name):
		bash('git init %s'%name)
		bash('git --git-dir ./%s/.git --work-tree=%s commit --allow-empty -m "initial commit"'%(name,name))
	else: raise Exception('make_silo was called but %s exists'%name)

def prepare_tracker():
	"""Move the cassette codes and make a new repository to track the drafts."""
	#---move the cassette codes into a separate repository location
	shutil.move('.git','.gitcas')
	#---initialize the repo for the "dirty" copy of our drafts. the "silo" holds the "clean" copy
	#---...which is suffixed ".pure" and has one sentence per line for easy review in git
	bash('git init .')
	bash('git commit --allow-empty -m "initial commit"')
	#---retrieve the canonical gitignore for a cassette project
	shutil.copyfile('cas/parser/gitignore-data','./.gitignore')
	bash('git add .gitignore')
	bash('git commit --allow-empty -m "added gitignore"')

def init():
	"""Move the git codes into place. Runs only once."""
	important_file = 'cas/parser/parselib.py'
	#---if .gitcas is absent and we find parselib.py in the current .git then we must move it out of the way
	#---...once. this function should only run once
	if not os.path.isdir('.gitcas') and os.path.isdir('.git'):
		print('[STATUS] checking that .git holds cas/parser/parser.py before moving it out of the way')
		#---only proceed if the .git directory is the cassette codes
		if command_check('git ls-files %s --error-unmatch'%important_file):
			make_silo()
			prepare_tracker()	
			print('[STATUS] moved cassette codes to `.gitcas` and prepared a repository for tracking')
		else: print('[WARNING] .gitcas is missing and .git is present but it lacks a key file (%s) '%
			important_file+'so we cannot init')
	else: print('[WARNING] already initialized')

def index():
	"""Run the script to make the index."""
	bash('python cas/parser/indexer.py')
	print("[INDEX] file:///%s/index.html"%os.getcwd())

###---DOCUMENT PROCESSING

def docket():
	"""
	Figure out what needs to be done.

	Note the previous makefile contained (a) many utility functions that called codes (which have since been
	replaced by a the makeface.py/config.py scheme) and (b) a more typical makefile pipeline that checked for
	changes to markdown files and recompiled HTML and other formats from these files whenever they were 
	updated. For greater control, we have extracted these functions from make to python. We begin by compiling
	a list of things to do.
	"""
	#---in the previous makefile we recompiled documents with target "%.html: %md" which means that all 
	#---...markdown files must be compiled to HTML on an update
	check_files = lambda y: map(lambda x:re.match('^(.*?)\.%s$'%y,x).group(1),glob.glob('*.%s'%y))
	targets = check_files('md')
	results = check_files('html')
	instructions = dict()
	for base in targets:
		if base not in results: instructions[base] = 'new'
		else:
			if os.path.getmtime('%s.md'%base)>os.path.getmtime('%s.html'%base): instructions[base] = 'update'
			else: print('[STATUS] %s is up to date'%base)
	return instructions

def remake_single(name):
	"""Rerender a document and track it."""
	global siloname
	bash('python ./cas/parser/parser.py %s.md'%name)
	print('[STATUS] compiled %s.md'%name)
	print('[VIEW] file:///%s.html'%os.path.join(os.getcwd(),name))
	print('[STATUS] saving %s.md'%name)
	fn_rel = os.path.join('history',name+'.pure')
	was_committed = command_check(
		'git --git-dir=./%s/.git --work-tree=%s/ ls-files %s.pure --error-unmatch'%(
			siloname,siloname,name))
	if not was_committed:
		print('[STATUS] adding %s to the silo'%(fn_rel))
		bash('git --git-dir=./%s/.git --work-tree=%s/ add %s.pure'%(
			siloname,siloname,name))
		bash('git --git-dir=./%s/.git --work-tree=%s/ commit -m "added %s"'%(
			siloname,siloname,name+'.pure'))
	has_changes = not command_check(
		'git --git-dir=./%s/.git --work-tree=%s/ diff --exit-code'%(siloname,siloname))
	if has_changes:
		timestamp = datetime.datetime.fromtimestamp(time.time()).strftime('%Y.%m.%d.%H%M')
		message = "%s +%s.md"%(timestamp,name)
		cmd = 'git --git-dir ./%s/.git --work-tree=%s commit -a -m "%s"'%(siloname,siloname,message)
		print('[STATUS] detected changes so we are committing via `%s`'%cmd)
		bash(cmd)
	else: print('[STATUS] no changes to %s'%fn_rel)

def remake():
	"""
	Coordinating function which renders documents that have changes.
	"""
	print('[STATUS] running remake')
	instructions = docket()
	for key,val in instructions.items():
		if val=='new': print('[RENDER] writing %s for the first time'%key)
		if val in ['update','new']: 
			print('[RENDER] updating %s'%key)
			remake_single(key)
		else: raise Exception('invalid state %s for %s'%(val,key))

def read_dispatch():
	"""
	Read the dispatch.yaml for functions that use it, which functions were formerly housed together and 
	completed tasks like rendering the tiler and 
	"""
	#---parse a dispatch.yaml if exists
	dispatch_fn = 'dispatch.yaml'
	if os.path.isfile(dispatch_fn): 
		with open(dispatch_fn) as fp: dis = yaml.load(fp.read())
		return dis
	else: raise Exception('cannot read dispatch.yaml')

def sync_pull(**val):
	"""
	Synchronize files.
	! change to subprocess, check file name redundancy if one "down" folder
	"""
	#---check hostnames
	regex_host = '^(?:(.+):)?(.+)$'
	from_host = re.match(regex_host,val['from']).group(1)
	dest = val.get('to',None)
	source = val.get('from',None)
	if not dest: raise Exception('dictionary "%s" needs a "to"'%val['pull_name'])
	try: 
		hostname = os.environ['HOSTNAME']
	except: 
		import socket
		hostname = socket.gethostname()
	if from_host and re.search(from_host,hostname):
		sourcepath = re.match(regex_host,source).group(2)
	else: sourcepath = source
	if 'files' in val and not val['files']:
		raise Exception('remove files from this entry to sync everything, otherwise add files!')
	elif 'files' in val:
		if not os.path.isdir(dest): os.mkdir(dest)
		#---simple solution with explict paths
		cmd = 'rsync -ariv ' +' '.join([sourcepath+'/'+fn for fn in val['files']])+\
			' ./%s/'%(dest)
	#---if files are not specified we sync everything
	else: 
		if 'excludes' not in val: flag_exclude = ''
		else: 
			tmpfn = tempfile.NamedTemporaryFile(delete=False)
			exclude_list = [val['excludes']] if type(val['excludes'])==str else val['excludes']
			for exclude in exclude_list: tmpfn.write(exclude+'\n')
			tmpfn.close()
			flag_exclude = '--exclude-from=%s '%tmpfn.name
		#---ask for everything
		source_this = os.path.join(sourcepath,'') if '*' not in sourcepath else sourcepath
		if not source_this: raise Exception('!')
		cmd = 'rsync -ariv %s%s ./%s'%(flag_exclude,source_this,dest)
	print('[SYNC] pulling from %s to %s with "%s"'%(sourcepath,dest,cmd))
	bash(cmd,catch=False)

def pull(which='all'):
	"""
	Copy data from remote machines per instructions in ``dispatch.yaml``.
	Formerly executed via a set of codes called "dispatch" and set up for a dissertation.
	"""
	dis = read_dispatch()
	#---collect pull references
	targets = dict([(key,str_or_list(val.get('recipe',['all'])))
		for key,val in dis.items() if type(val)==dict and val.get('type',None)=='pull'])
	asciitree(dict(pull_targets=targets))
	print('[NOTE] only keys for pulls marked with "recipe" (value) "all" are pulled by default '
		'otherwise use `make pull <recipe>`')
	#---filter by recipe name
	targets_filtered = [k for k,v in targets.items() if which in v]
	if not targets_filtered:
		raise Exception('cannot pull any items with recipe named "%s" (note "all" is the default)'%which)
	for key in targets_filtered: 
		print(fab('[PULL]','cyan_black')+' according to "%s"'%key)
		sync_pull(**dict(dis[key],pull_name=key))

def dev(*args,**kwargs):
	"""
	Shortcut to interface with the cassette codes after an init.
	"""
	prefix = 'git --git-dir=.gitcas'
	if not os.path.isdir(siloname): raise Exception('silo at %s is absent'%siloname)
	#---the makefile changes the arguments slightly but we still retain this shortcut for convenience
	#---...with special exceptions for commit and restriction on the commands we can run
	if not args: 
		raise Exception('invalid call to `make dev`, an alias for `git --git-dir=.gitcas`: %s, %s'%
		(args,kwargs))
	arg,details = args[0],args[1:]
	#---only allow certain git commands
	valid_targets = ['status','commit','diff','add','push']
	if arg not in valid_targets: 
		raise Exception('invalid argument %s, must be in %s'%(arg,valid_targets))
	#---special handling for commits because the makefile eats "-m". note this is experimental.
	if arg=='commit':
		message = ' '.join(details)
		if not details: raise Exception('cannot find a message in this commit')
		print('[STATUS] committing to cassette with message "%s"'%message)
		bash('%s commit -m "%s"'%(prefix,message),catch=False)
	elif arg in ['status','diff','push']:
		#---no keywords allowed
		if kwargs: raise Exception('invalid kwargs %s'%kwargs)
		if details: raise Exception('invalid args %s'%details)
		bash('%s %s'%(prefix,arg),catch=False)
	elif arg=='add':
		if '.' in details or '*' in details: raise Exception('do not add indiscriminately! '
			'you will accidentally commit data to the code!')
		fns = ' '.join(details)
		print('[STATUS] adding files %s'%fns)
		bash('%s add %s'%(prefix,fns),catch=False)
	else: raise Exception('invalid argument %s'%arg)

def bootstrap(host=None,source=None):
	"""
	Pull down a git repository from a remote location
	"""
	if not source: raise Exception('you must send host and source. '
		'if local, omit host and send the source via source="<path>"') 
	hostname = '%s:'%host if host else ''
	if not os.path.isdir(siloname): 
		print('[STATUS] no silo yet so we are initializing for you')
		init()
	#---command sequence for rearranging the repositories
	cmds = [
		'git remote add origin %s%s'%(hostname,source),
		'git fetch origin master',
		'git branch --set-upstream-to=origin/master master',
		['git pull --no-edit --allow-unrelated-histories','git pull --no-edit']]
	#---loop over sets of commands
	for cmd in cmds:
		#---try each command in a set until one works
		for cmd_sub in str_or_list(cmd):
			try: 
				print('[STATUS] running command "%s"'%cmd_sub)
				bash(cmd_sub,catch=False)
				break
			except: continue
	print('[STATUS] bootstrap complete')
