#!/usr/bin/python

import os,sys,re,glob,yaml,tempfile,subprocess,shutil

#---settings
tiler_code = 'cas/parser/tiler.py'

#---parse a dispatch.yaml if exists
dispatch_fn = 'dispatch.yaml'
if os.path.isfile(dispatch_fn): 
	with open(dispatch_fn) as fp: dis = yaml.load(fp.read())
else: sys.exit()

#---extra arguments
todo = {}
kwarglist = ['from']
arglist = ['dissertation','combos','zipper','pull','gallery']
for key in kwarglist:
	arg = re.search('(from)=(.+)',' '.join(sys.argv))
	if arg: todo[arg.group(1)] = arg.group(2)
for key in arglist: todo[key] = key in sys.argv 

#---do something
if not any(todo.values()): raise Exception('[ERROR] nothing to dispatch')

###---MAIN

#---zip a particular article
if todo['zipper']:
	import pdb;pdb.set_trace()
	os.system('rm printed/*.zip')
	print_dn = 'printed'
	printed_dns = [i for i in glob.glob(print_dn+'/*') if i!='printed/combos' and i[-4:]!='.zip']
	for dn in printed_dns:
		proc = subprocess.Popen('zip -r %s.zip %s'%(os.path.basename(dn),os.path.basename(dn)),
			cwd=os.path.dirname(dn),shell=True)
		proc.communicate()

#---make image galleries
if 'gallery' in todo and todo['gallery']:
	#---loop over image links in the dispatch.yaml file and make a tiler for each
	for key in [key for key in dis.keys() if 'type' in dis[key] and dis[key]['type']=='image-link']:
		val = dis[key]
		tmpfn = tempfile.NamedTemporaryFile(delete=False)
		maps = {'path':{
			'dropdir':os.getcwd(),
			'dropfile':'tile-%s.html'%key,
			'tile-files':'cas/sources/tiler/',
			'thumb-files':'cas/hold/thumbs-%s/'%key,
			'images':val['location'],
			}}
		tmpfn.write(str.encode(str(maps)))
		tmpfn.close()
		os.system(tiler_code+' '+tmpfn.name)

#---assemble pull lists
if 'pull' in todo and todo['pull']: 
	pulls = [key for key in dis if 'type' in dis[key] and dis[key]['type']=='sync-pull']
elif 'from' in todo: 
	pulls = [key for key in dis if 'type' in dis[key] and dis[key]['type']=='sync-pull' 
		and re.findall('^(.+)@(.+):(.+)$',dis[key]['from'])[0][1]==todo['from']]
else: pulls = []

#---pull from valid targets
for key in pulls:
	val = dis[key]
	#---! change to subprocess, check file name redundancy if one "down" folder
	#---check hostnames
	regex_host = '^(?:(.+):)?(.+)$'
	from_host = re.match(regex_host,val['from']).group(1)
	try: hostname = os.environ['HOSTNAME']
	except: 
		import socket
		hostname = socket.gethostname()
	if from_host and re.search(from_host,hostname):
		sourcepath = re.match(regex_host,val['from']).group(2)
	else: sourcepath = val['from']
	if 'files' not in val: 
		if 'excludes' not in val: flag_exclude = ''
		else: 
			tmpfn = tempfile.NamedTemporaryFile(delete=False)
			exclude_list = [val['excludes']] if type(val['excludes'])==str else val['excludes']
			for exclude in exclude_list: tmpfn.write(exclude+'\n')
			tmpfn.close()
			flag_exclude = '--exclude-from=%s '%tmpfn.name
		#---! somewhat clumsy
		source = os.path.join(sourcepath,'') if '*' not in sourcepath else sourcepath
		cmd = 'rsync -ariv %s%s ./%s'%(flag_exclude,source,val['to'])
	else:
		if not os.path.isdir(val['to']): os.mkdir(val['to'])
		#---! DEPRECATED
		if False:
			pull_dns,pull_fns = [],[]
			for fn in val['files']:
				pull_fns.append(fn)
				dn = os.path.dirname(fn)
				if dn not in pull_dns: pull_dns.append(dn)
			tmpfn = tempfile.NamedTemporaryFile(delete=False)
			#---! viciously ugly code
			pull_dns = [os.path.join(m,'') for n in [['/'.join(j[:k]) 
				for k in range(1,len(j))] for j in [i.split('/') for i in pull_dns]] for m in n if m!='']
			for dn in pull_dns: tmpfn.write('+ '+os.path.join(dn,'')+'\n')
			for fn in pull_fns: tmpfn.write('+ '+fn+'\n')
			tmpfn.write('- *\n')
			tmpfn.close()
			cmd = 'rsync -ariv --include-from=%s %s ./%s/'%(tmpfn.name,os.path.join(sourcepath,''),val['to'])
		#---simple solution with explict paths
		cmd = 'rsync -ariv ' +' '.join([sourcepath+'/'+fn for fn in val['files']])+\
			' ./%s/'%(val['to'])
	print('[SYNC] pulling from %s to %s with "%s"'%(sourcepath,val['to'],cmd))
	os.system(cmd)

#---compile the dissertation
if todo['dissertation']:
	details = dis['dissertation']
	dn = os.path.join(details['where'],'')
	#---for every key in "blocks", write that value to a tex file required by dissertation.tex
	for blockkey in details['blocks']:
		with open(dn+blockkey+'.tex','w') as fp: fp.write(details[blockkey])
	#---write chapters and appendices to the chapterlist
	chapters = details['chapters']
	appendix = details['appendix']
	with open(dn+'chapterlist.tex','w') as fp:
		for fn in chapters:
			fp.write(r"\input{%s.tex}"%fn+'\n')
		if any(appendix):
			fp.write(r"\appendix"+'\n')
			for fn in appendix:
				fp.write(r"\input{%s.tex}"%fn+'\n')
	#---check for tagalongs
	tagalongs = []
	for chap in chapters+appendix:
		with open(chap+'.md') as fp: text = fp.read()
		check_tag = re.search('\ntagalongs:\s*(.+)\s*\n',text,re.MULTILINE)
		#---! no file overwrite check here
		if check_tag:
			tag_fns = eval(check_tag.group(1))
			for fn in tag_fns: shutil.copy(fn,os.path.join(dn,''))
	with open(dn+'chapterlist.sh','w') as fp:
		fp.write("#/bin/bash\nchapters=(%s)\n"%(' '.join(["'%s'"%i for i in chapters+appendix])))
	proc = subprocess.Popen('./script-make.sh',cwd=dn,shell=True,executable='/bin/bash')
	proc.communicate()

#---concatenate PDFs
if todo['combos']:
	raise Exception('under development')
	del val['type']
	if val and not os.path.isdir('printed/combos/'): os.mkdir('printed/combos/')
	for key,order in val.items():
		cmd = ('gs -q -dNOPAUSE -dBATCH -sDEVICE=pdfwrite -sOutputFile=printed/combos/%s.pdf %s'%
			(key,' '.join(['printed/%s.pdf'%i for i in order])))
		print(cmd)
		os.system(cmd)
