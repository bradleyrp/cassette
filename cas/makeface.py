#!/bin/bash
"exec" "python" "-B" "$0" "$@"

__doc__ = """

MAKEFACE (a.k.a. MAKEfile interFACE)
------------------------------------

A crude but convenient way to make a command-line interface for python. This makeface.py connects the makefile 
to arbitrary python functions found in files specified by the ``commands`` key in ``config.py``. In addition 
to defining the command-line interface, this local configuration file can be used as a catchall for any kinds 
of code-specific settings which need to be manipulated with simple commands.

Note: you avoid using ``make`` keywords as python argument names (e.g. "w" and "s") and avoid using ``*args`` 
and ``**kwargs`` because arguments are passed from the ``Makefile`` to the python functions by using the 
`inspect <https://docs.python.org/2/library/inspect.html>`_ module for introspection. You can access python 
functions from the terminal by running ``make my_python_function some_true_bool_flag kwarg="some value"``. 
Set ``commands`` in the ``config.py`` (which might be managed by other parts of the program) to specify which 
files provide functions to the interface. You can set ``__all__`` in these files to hide extraneous functions 
from ``make``. This copy of ``makeface.py`` is the consensus version, derived from BioPhysCode projects 
(automacs, omnicalc, and factory), each of which use the local configuration file to manage their settings. In
this sense, the ``makeface.py`` scheme provides both a systematic interface to the user and other programs
"""

import os,sys,re,glob
import inspect,traceback,subprocess
import pprint

#---set the local configuration file
config_fn = 'config.py'
#---the default configuration is only written when config.py is absent
default_config = {'commands_aliases':[('set','set_config')]}
#---set the key in the local configuration that points to python scripts to be exposed to `make`
config_key = 'commands'
#---tailor this copy of makeface.py to cassette (note that the makefile points to this makeface.py also)
default_config[config_key] = ['cas/interface.py']
default_config['make_default'] = 'remake'
#---we populate a dictionary of exposed functions
makeface_funcs = {}
#---some flags are disallowed by make because they have special uses
drop_flags = ['w','--','s','ws','sw']
#---we typically disable verbose output
verbose = False
#---adjucate string types between versions
str_types = [str,unicode] if sys.version_info<(3,0) else [str]
#---required hard-coded variables
keys_required = ['config_fn','config_key','default_config']
#---expose some functions from this script
provided_here = ['set_config','setlist','config','unset','help']
#---list of extra functionalities to enable
extra_functionality = ['yaml']

###---UTILITY FUNCTIONS

def str_or_list(x): 
	"""Turn a string or a list into a list."""
	if type(x)==str: return [x]
	elif type(x)==list: return x
	else: raise Exception('str_or_list expects a string or a list')

def strip_builtins(obj):
	"""Remove builtins from a hash in place."""
	if '__all__' in obj.keys(): keys = obj['__all__']
	else: keys = [key for key in obj.keys() if not key.startswith('__')]
	#---let the user tell us which functions to hide or ignore
	hidden = obj.pop('_not_all',[])
	for h in hidden:
		if h not in keys: raise Exception('_not_all asks to hide %s but it is absent'%h)
		keys.remove(h)
	if '_not_all' in keys: keys.remove('_not_all')
	#---if you pop __builtins__ here then the imported functions cannot do essentials e.g. print
	#---...so instead we pass along a copy of the relevant functions for the caller
	return dict([(key,obj[key]) for key in keys])

def abspath(path):
	"""Get the right path."""
	return os.path.abspath(os.path.expanduser(path))

def import_local(fn):
	"""Import a local script manually."""
	if os.path.join(os.getcwd(),os.path.dirname(abspath(fn))) in sys.path: 
		mod = __import__(re.sub(r'\.py$','',os.path.basename(fn)))
		return strip_builtins(mod.__dict__)
	else: raise Exception('could not import locally')

def import_remote(script,is_script=False):
	"""Import a script as a module, directly, iff it is not in the path."""
	dn,fn = os.path.dirname(script),os.path.basename(script)
	if not (is_script or os.path.isdir(dn)): 
		raise Exception('cannot find directory "%s" for script %s'%(dn,script))
	dn_abs = os.path.join(os.getcwd(),dn)
	assert dn_abs not in sys.path,'found "%s" in sys.path already'%dn_abs
	paths = list(sys.path)
	#---prevent modification of paths while we import
	#---! after moving makeface to the runner directory, we loose the '' at the beginning of sys.path
	#---! ...note that running ipdb's set_trace adds it, so the imports work during debugging, but not runtime
	sys.path.insert(0,dn_abs)
	sys.path.insert(0,'')
	if verbose: print('[NOTE] remotely importing %s'%script)
	try: mod = __import__(os.path.splitext(fn)[0])
	#---on import failure we collect functions from the script manually
	except Exception as e:
		tracebacker(e)
		print('[ERROR] remote importing of script %s returned an error: %s'%(script,str(e))) 
		sys.exit(1)
		#---! unlock the following to do manual imports if you think you need them
		mod = {}
		print('[MAKEFACE] about to load a script for ... ')
		exec(open(script).read(),mod)
		print('[WARNING] one of your libraries ("%s") was loaded manually'%script)
	sys.path = paths
	return strip_builtins(mod.__dict__)

def fab(text,*flags):
	"""Colorize the text."""
	#---three-digit codes: first one is style (0 and 2 are regular, 3 is italics, 1 is bold)
	colors = {'gray':(0,37,48),'cyan_black':(1,36,40),'red_black':(1,31,40),'black_gray':(0,37,40),
		'white_black':(1,37,40),'mag_gray':(0,35,47)}
	#---no colors if we are logging to a text file because nobody wants all that unicode in a log
	if flags and sys.stdout.isatty()==True: 
		if any(f for f in flags if f not in colors): 
			raise Exception('cannot find a color %s. try one of %s'%(str(flags),colors.keys()))
		for f in flags[::-1]: 
			style,fg,bg = colors[f]
			text = '\x1b[%sm%s\x1b[0m'%(';'.join([str(style),str(fg),str(bg)]),text)
	return text

def tracebacker(e):
	"""Standard traceback handling for easy-to-read error messages."""
	exc_type,exc_obj,exc_tb = sys.exc_info()
	tag = fab('[TRACEBACK]','gray')
	tracetext = tag+' '+re.sub(r'\n','\n%s'%tag,str(''.join(traceback.format_tb(exc_tb)).strip()))
	print(fab(tracetext))
	print(fab('[ERROR]','red_black')+' '+fab('%s'%e,'cyan_black'))

def bash(command,log=None,cwd=None,inpipe=None,catch=True):
	"""
	Run a bash command
	"""
	if not cwd: cwd = './'
	if log == None: 
		if inpipe: raise Exception('under development')
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash')
		#---note that you can either catch errors and raise exceptions if anything comes out in stderr and 
		#---...then later print up the stdout with a delay or you can pipe the stdout directly to output and
		#---...only later observe the error state when the program returns nonzero. you cannot do both without
		#---...some kind of tee-like solution that would require asynchronous I/O or threading, so anytime you 
		#---...need to invoke python you should obviously just import it and run it and reserve bash for 
		#---...running non-python binaries
		if catch: kwargs.update(stdout=subprocess.PIPE,stderr=subprocess.PIPE)
		proc = subprocess.Popen(command,**kwargs)
		stdout,stderr = proc.communicate()
	else:
		#---if the log is not in cwd we see if it is accessible from the calling directory
		if not os.path.isdir(os.path.dirname(os.path.join(cwd,log))): 
			output = open(os.path.join(os.getcwd(),log),'w')
		else: output = open(os.path.join(cwd,log),'w')
		kwargs = dict(cwd=cwd,shell=True,executable='/bin/bash',
			stdout=output,stderr=output)
		if inpipe: kwargs['stdin'] = subprocess.PIPE
		proc = subprocess.Popen(command,**kwargs)
		if not inpipe: stdout,stderr = proc.communicate()
		else: stdout,stderr = proc.communicate(input=inpipe)
	if stderr: raise Exception('[ERROR] bash returned error state: %s'%stderr)
	if proc.returncode: 
		if log: raise Exception('bash error, see %s'%log)
		else: 
			extra = '\n'.join([i for i in [stdout,stderr] if i])
			raise Exception('bash error with returncode %d. stdout: "%s"\nstderr: "%s"'%(proc.returncode,
				stdout,stderr))
	return {'stdout':stdout,'stderr':stderr}

def command_check(command):
	"""Run a command and see if it completes with returncode zero."""
	print('[STATUS] checking command "%s"'%command)
	try:
		with open(os.devnull,'w') as FNULL:
			proc = subprocess.Popen(command,stdout=FNULL,stderr=FNULL,shell=True,executable='/bin/bash')
			proc.communicate()
			return proc.returncode==0
	except Exception as e: 
		print('[WARNING] caught exception on command_check: %s'%e)
		return False

###---DATAPACK

def asciitree(obj,depth=0,wide=2,last=[],recursed=False):
	"""
	Print a dictionary as a tree to the terminal.
	Includes some simuluxe-specific quirks.
	"""
	corner = u'\u251C'
	corner_end = u'\u2514'
	horizo,horizo_bold = u'\u2500',u'\u2501'
	vertic,vertic_bold = u'\u2502',u'\u2503'
	tl,tr,bl,br = u'\u250F',u'\u2513',u'\u2517',u'\u251B'
	if sys.version_info<(3,0): 
		corner,corner_end,horizo,horizo_bold,vertic,vertic_bold,tl,tr,bl,br = [i.encode('utf-8')
			for i in [corner,corner_end,horizo,horizo_bold,vertic,vertic_bold,tl,tr,bl,br]]
	spacer_both = dict([(k,{0:'\n',
		1:' '*(wide+1)*(depth-1)+c+horizo*wide,
		2:' '*(wide+1)*(depth-1)
		}[depth] if depth <= 1 else (
		''.join([(vertic if d not in last else ' ')+' '*wide for d in range(1,depth)])
		)+c+horizo*wide) for (k,c) in [('mid',corner),('end',corner_end)]])
	spacer = spacer_both['mid']
	if type(obj) in [str,float,int,bool]:
		if depth == 0: print(spacer+str(obj)+'\n'+horizo*len(obj))
		else: print(spacer+str(obj))
	elif type(obj) == dict and all([type(i) in [str,float,int,bool] for i in obj.values()]) and depth==0:
		asciitree({'HASH':obj},depth=1,recursed=True)
	elif type(obj) in [list,tuple]:
		for ind,item in enumerate(obj):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(item) in [str,float,int,bool]: print(spacer_this+str(item))
			elif item != {}:
				print(spacer_this+'('+str(ind)+')')
				asciitree(item,depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			else: print('unhandled tree object')
	elif type(obj) == dict and obj != {}:
		for ind,key in enumerate(obj.keys()):
			spacer_this = spacer_both['end'] if ind==len(obj)-1 else spacer
			if type(obj[key]) in [str,float,int,bool]: print(spacer_this+key+' = '+str(obj[key]))
			#---special: print single-item lists of strings on the same line as the key
			elif type(obj[key])==list and len(obj[key])==1 and type(obj[key][0]) in [str,float,int,bool]:
				print(spacer_this+key+' = '+str(obj[key]))
			#---special: skip lists if blank dictionaries
			elif type(obj[key])==list and all([i=={} for i in obj[key]]):
				print(spacer_this+key+' = (empty)')
			elif obj[key] != {}:
				#---fancy border for top level
				if depth == 0:
					print('\n'+tl+horizo_bold*(len(key)+0)+
						tr+spacer_this+vertic_bold+str(key)+vertic_bold+'\n'+\
						bl+horizo_bold*len(key)+br+'\n'+vertic)
				else: print(spacer_this+key)
				asciitree(obj[key],depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			elif type(obj[key])==list and obj[key]==[]:
				print(spacer_this+'(empty)')
			else: print('unhandled tree object')
	else: print('unhandled tree object')
	if not recursed: print('\n')

###---EXTRAS

if 'yaml' in extra_functionality:
	"""
	Users of YAML will appreciate importing it here with a duplicate-key safety check.
	"""
	import yaml
	from yaml.constructor import ConstructorError
	try: from yaml import CLoader as Loader
	except ImportError: from yaml import Loader
	def no_duplicates_constructor(loader,node,deep=False):
		"""Check for duplicate keys."""
		mapping = {}
		for key_node,value_node in node.value:
			key = loader.construct_object(key_node,deep=deep)
			value = loader.construct_object(value_node,deep=deep)
			if key in mapping: 
				raise ConstructorError('while constructing a mapping',node.start_mark,
					'found duplicate key "%s"'%key,key_node.start_mark)
			mapping[key] = value
		return loader.construct_mapping(node, deep)
	yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,no_duplicates_constructor)

###---CONFIG

def setlist(*args):
	"""
	Special handler for adding list items.
	The first argument must be the key and the following arguments are the values to add. Send kwargs to the
	``unset`` function below to remove items from the list.
	"""
	if len(args)<=1: raise Exception('invalid arguments for setlist. you need at least two: %s'%args)
	key,vals = args[0],list(args[1:])
	config = read_config()
	if key not in config: config[key] = vals
	elif type(config)!=list: raise Exception('cannot convert singleton to list in %s'%config_fn)
	else: config[key] = list(set(config[key]+vals))
	write_config(config)

def interpret_command_text(raw):
	"""
	Interpret text pythonically, if possible.
	Adapted from the pseudo-yaml parser in automacs.
	"""
	try: val = eval(raw)
	except: val = raw
	#---protect against sending e.g. "all" as a string and evaluating to builtin all function
	if val.__class__.__name__=='builtin_function_or_method': result = str(val)
	elif type(val) in [list,dict]: result = val
	elif type(val) in str_types:
		if re.match('^(T|t)rue$',val): result = True
		elif re.match('^(F|f)alse$',val): result = False
		elif re.match('^(N|n)one$',val): result = None
		#---! may be redundant with the eval command above
		elif re.match('^[0-9]+$',val): result = int(val)
		elif re.match('^[0-9]*\.[0-9]*$',val): result = float(val)
		else: result = val
	else: result = val
	return result

def set_config(*args,**kwargs):
	"""
	Update the configuration in a local configuration file (typically ``config.py``).
	This function routes ``make set` calls so they update flags using a couple different syntaxes.
	We make a couple of design choices to ensure a clear grammar: a
	1. a single argument sets a boolean True (use unset to remove the parameter and as a style convention, 
		always assume that something is False by default, or use kwargs to specify False)
	2. pairs of arguments are interpreted as key,value pairs
	3. everything here assumes each key has one value. if you want to add to a list, use ``setlist``
	"""
	outgoing = dict()
	#---pairs of arguments are interpreted as key,value pairs
	if len(args)%2==0: outgoing.update(**dict(zip(args[::2],args[1::2])))
	#---one argument means we set a boolean
	elif len(args)==1: outgoing[args[0]] = True
	else: raise Exception('set_config received an odd number of arguments more than one: %s'%args)
	#---interpret kwargs with an opportunity to use python syntax, or types other than strings
	for key,raw in kwargs.items(): outgoing[key] = interpret_command_text(raw)
	#---read and write the config
	config = read_config()
	#---! previously used a function called add_config to check things
	config.update(**outgoing)
	write_config(config)

def read_config(source=None):
	"""
	Read the configuration from a single dictionary literal in config.py (or the config_fn).
	"""
	source = config_fn if not source else source
	if not os.path.isfile(abspath(source)): 
		if not os.path.isfile(os.path.join(os.getcwd(),source)):
			raise Exception('cannot find file "%s"'%source)
		else: source = os.path.join(os.getcwd(),source)
	else: source = abspath(source)
	try: return eval(open(source).read())
	except: raise Exception('[ERROR] failed to read master config from "%s"'%source)

def write_config(config):
	"""Write the configuration."""
	#---write the config
	with open(config_fn,'w') as fp: 
		fp.write('#!/usr/bin/env python -B\n'+str(pprint.pformat(config,width=110)))

def config():
	"""Print the configuration."""
	config = read_config()
	asciitree({config_fn:config})

def unset(*args):
	"""Remove items from config."""
	config = read_config()
	for arg in args: 
		if arg in config: del config[arg]
		else: print('[WARNING] cannot unset %s because it is absent'%arg)
	write_config(config)

###---CORE

def help():
	"""Report available functions."""
	global makeface_funcs
	print('[STATUS] makeface.py called with either `make help` or no `make_default` '
		'so we are just taking stock')
	if makeface_funcs: asciitree({'make targets':list(sorted(makeface_funcs.keys()))})
	print('[USAGE] `make <target> <args> <kwarg>="<val>" ...`')

def makeface(*arglist):
	"""
	Route ``make`` commands into python.
	"""
	global makeface_funcs
	#---stray characters
	arglist = tuple(i for i in arglist if i not in drop_flags)
	#---unpack arguments
	if arglist == []: raise Exception('[ERROR] no arguments to controller')
	args,kwargs = [],{}
	arglist = list(arglist)
	funcname = arglist.pop(0)
	#---regex for kwargs. note that the makefile organizes the flags for us
	regex_kwargs = r'^(\w+)\="?([\w:~\-\.\/\s]+)"?$'
	while arglist:
		arg = arglist.pop(0)
		#---note that it is crucial that the following group contains all incoming 
		if re.match(regex_kwargs,arg):
			parname,parval = re.findall(regex_kwargs,arg)[0]
			kwargs[parname] = parval
		else:
			if sys.version_info<(3,3): 
				#---the following will be removed by python 3.6
				argspec = inspect.getargspec(makeface_funcs[funcname])
				argspec_args = argspec.args
			else:
				sig = inspect.signature(makeface_funcs[funcname])
				argspec_args = [name for name,value in sig.parameters.items() 
					if value.default==inspect._empty or type(value.default)==bool]
			#---! note that a function like runner.control.prep which uses an arg=None instead of just an
			#---! ...arg will need to make sure the user hasn't sent the wrong flags through.
			#---! needs protection
			if arg in argspec_args: kwargs[arg] = True
			else: args.append(arg)
	args = tuple(args)
	if arglist != []: raise Exception('unprocessed arguments %s'%str(arglist))
	#---"command" is a protected keyword
	if funcname != 'back' and 'command' in kwargs: kwargs.pop('command')
	print('[STATUS] '+fab('makeface.py','mag_gray')+
		' is calling %s with args="%s" and kwargs="%s"'%(funcname,args,kwargs))
	#---if we are debugging then we call without try so that the debugger in sitecustomize.py can
	#---...pick things up after there is an exception (because pm happens after)
	#---! is this scheme deprecated? (previously used sitecustomize.py for automatic debugging)
	if os.environ.get('PYTHON_DEBUG','no') in ['pdb','ipdb']:
		makeface_funcs[funcname](*args,**kwargs)
	else:
		#---if no (auto)debugging then we simply report exceptions as a makeface error
		try: makeface_funcs[funcname](*args,**kwargs)
		except Exception as e: 
			tracebacker(e)
			sys.exit(1)
		except KeyboardInterrupt:
			print('[STATUS] caught KeyboardInterrupt during traceback\n'
				'[CALMDOWN] okay okay ... exiting ...')
			sys.exit(1)

#---process the incoming command-line arguments
if __name__ == "__main__": 

	#---! set the logo or a pointer in the config.py 
	try: from logo import logo
	except: logo = ""
	if logo: print(logo)
	#---check for keys
	for key in keys_required:
		if key not in globals(): 
			raise Exception('makeface.py must have the following keys hardcoded: %s. you are missing %s'%(
				keys_required,key))
	#---if the config file is missing we write the default configuration
	if not os.path.isfile(config_fn): 
		with open(config_fn,'w') as fp: fp.write(str(default_config))
	#---read configuration to retrieve source scripts note this happens every time (even on make's 
	#---...tab-completion, if available) to collect scripts from all open-ended sources. timing: it only 
	#---...requires about 3ms
	configurator = read_config()
	source_scripts = str_or_list(configurator.get(config_key,[]))
	#---filter sys.argv for irrelevant flags
	argvs = [i for i in sys.argv if i not in drop_flags]
	#---if the config.py points to source scripts via the config_key list, we collection their functions
	if source_scripts:
		#---loop over scripts that expose functions to makeface
		for sc in source_scripts:
			fns = glob.glob(sc)
			if not fns:
				raise Exception(
					'configuration at %s specifies functions from %s but it is absent'%(config_fn,sc))
			#---loop over globbed files
			for fn in fns: 
				#---protect against ambiguity between scripts and modules in this importing scheme
				if os.path.isdir(os.path.splitext(fn)[0]) and os.path.isfile(fn):
					print('[ERROR] naming redundancy: "%s" is both a directory and a file'%fn)
					sys.exit(1)
				#---import as a local module
				if (os.path.join(os.getcwd(),os.path.dirname(fn)) in sys.path
					or os.path.dirname(fn)=='.'): 
					new_funcs = import_local(fn)
					makeface_funcs.update(**new_funcs)
					if len(argvs)==1 and verbose: 
						print('[NOTE] imported remotely from %s'%fn)
						print('[NOTE] added functions: %s'%(' '.join(new_funcs)))
				#---import functions from remote locations
				else: 
					new_funcs = import_remote(fn)
					makeface_funcs.update(**new_funcs)
					if len(argvs)==1: 
						if verbose: 
							print('[NOTE] imported remotely from %s'%fn)
							print('[NOTE] added functions: %s'%(' '.join(new_funcs)))
	#---prune non-callables from the list of makeface functions
	for name,obj in list(makeface_funcs.items()):
		if not hasattr(obj,'__call__'): 
			print('[WARNING] removing non-callable %s from makeface'%name)
			del makeface_funcs[name]
	#---insert functions from this script so they are available
	for name in provided_here:
		if name in makeface_funcs: raise Exception('function "%s" has been loaded into makeface '%name+
			'but we want to use the function provided here instead!')
		else: makeface_funcs[name] = globals()[name]
	#---command aliases for usability, namely with the 'set' command which is obviously a python type
	commands_aliases = configurator.get('commands_aliases',[])
	if any([len(i)!=2 for i in commands_aliases]): 
		raise Exception('commands_aliases must be a list of tuples that specify (target,alias) functions')
	for j,i in commands_aliases:
		if i not in makeface_funcs:
			raise Exception('cannot find target command-line function "%s" for alias "%s"'%(i,j)) 
		#---note that we remove the original function after making the alias to avoid redundancy
		else: makeface_funcs[j] = makeface_funcs.pop(i)
	#---no matter what we always list available targets in case the makefile is calling to find targets
	#---this formatting is read by the makefile to get the valid targets (please don't remove it)
	print('[STATUS] entering makeface.py')
	print('[STATUS] available make targets: %s'%(' '.join(makeface_funcs.keys())))
	#---run make with no argument has a couple different behaviors
	if len(argvs)==1: 
		#---default behavior can be set in the configuration
		#---default behavior is only triggered if the makefile does not send along a keyword ('just_looking') 
		#---...which it uses to ensure that we only list the targets in case this is automatic tab completion
		#---...and do not e.g. trigger some kind of default routine
		default_name = configurator.get('make_default',None)
		if default_name:
			if default_name not in makeface_funcs: 
				raise Exception('cannot find make_default function %s in the list of available functions'%
					default_name)
			print(('[STATUS] received `make` and found `make_default` in %s so '
				'we are running a function caled `%s`')%(config_fn,default_name))
			makeface(default_name)
		#---otherwise we list the available functions
		else: help()
	#---makeface is called with a special keyword when makefile is checking targets
	#---note try using ``make help`` if a default gets in the way of seeing what's available
	elif argvs[1]=='CHECKER': pass
	#---if we have a coherent target, then we run it
	else: makeface(*argvs[1:])
