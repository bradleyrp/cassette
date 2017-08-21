#!/usr/bin/python

"""
Writes an index.html file for a set of documents.
"""

#---start the HTML template here
html = ["""<link rel="stylesheet" href="./cas/sources/main.css" type="text/css"/>"""]

import os,sys,glob,re,datetime,subprocess

#---get data from dispatch.yaml
title = os.path.basename(os.getcwd())
description,order = '',None
if os.path.isfile('dispatch.yaml'):
	import yaml
	with open('dispatch.yaml') as fp: toc = yaml.load(fp.read())
	if 'description' in toc: description = toc['description']
	if 'order' in toc: order = toc['order']
	if 'title' in toc: title = toc['title'] 

#---timestamp in the description
description = description + '<br>updated '+'{:%Y.%m.%d.%H%M}'.format(datetime.datetime.now())

#---compile lists
print_dn = 'printed'
printed_dns = [i for i in glob.glob(print_dn+'/*') 
	if i!='printed/combos' and i[-4:]!='.zip' and os.path.isdir(i)]
copies = {}
#---check for pdfs
for item in printed_dns:
	name,format = re.match('^%s\/(.+)-([^-]+)'%print_dn,item).groups()
	if name not in copies: copies[name] = {}
	if 'pdf' not in copies[name]: copies[name]['pdf'] = []
	if format not in copies[name]['pdf'] and os.path.isfile(print_dn+'/%s-%s/%s.pdf'%(name,format,name)):
		copies[name]['pdf'].append(format)
#---check for html
for item in [i for i in glob.glob('*.md') if i!='README.md']:
	name = re.match('^(.+)\.md',item).group(1)
	if name not in copies: copies[name] = {}
	if 'html' not in copies[name]: copies[name]['html'] = ['html']

html += ['<title>%s</title><body>\n<div id="wrapper"><div id="main_content">'%title]
html += ['<h1><img src="cas/sources/cassette.png" '+
	'style="max-width:60px;max-height:60px;vertical-align:middle;padding:10px;">%s</h1>'%title]

#---pdf path naming convention
pather = {
	'pdf':lambda name,format : 'printed/%s-%s/%s.pdf'%(name,format,name),
	'html':lambda name : '%s.html'%name,}
section_names = {'pdf':'<strong>pdf</strong> <text color="gray">(LaTeX)</text>',
	'html':'<strong>web</strong>'}

#---assemble orderings
index = [[],[]]
#---if not order from dispatch.yaml we use ul and sort by modification time for the markdown file
#---! need to do the reverse lookup on the markdown files
if not order: 
	try: index[1] = sorted(copies.keys(),key=lambda x:os.path.getmtime(x+'.md'))[::-1]
	except: index[1] = sorted(copies.keys())
else: 
	index[0] = order
	leftovers = [i for i in copies.keys() if i not in order] 
	index[1] = sorted(leftovers,key=lambda x:os.path.getmtime(x+'.md'))[::-1]
if description: html += ['<br><code>%s</code>'%description]

#---! hackish, use dispatch.yaml
dissertation_fn = 'dissertation/dissertation.pdf'
if os.path.isfile(dissertation_fn):
	html += ['<h3><strong>dissertation</strong> ',
		'<strong>[<a href="%s" target=\"_blank\" style="color:red;">pdf</a>]</strong>'%dissertation_fn,
		'</h3>']

#---write the sections
for section in ['html','pdf']:
	html += ["<h3>%s</h3>"%section_names[section]]
	for ind,t in zip(index,'ou'):
		html += ["<%sl>"%t]
		for name in ind:
			if section == 'pdf':
				link = ["<li>%s: "%name]
				if 'pdf' in copies[name]:
					for format in copies[name]['pdf']:
						point = pather['pdf'](name,format)
						link += [(' <strong>[<a style="color:red;" '+
							'href="%s" target=\"_blank\">%s</a>]</strong>')
							%(point,format)]
					link += ["</li>"]
					html += [''.join(link)]
			else:
				if 'html' in copies[name]: 
					html += ['<li><a style="color:red;" href="%s" target=\"_blank\">%s</a></li>'%
						(pather['html'](name),name)]
		html += ["</%sl>"%t]

if False:
	if any(printed_dns):
		html += ["<h3>compressed LaTeX sources</h3><ul>"]
		for dn in printed_dns:
			#---after packing we zip everything
			print("[STATUS] zipping")
			proc = subprocess.Popen('zip -r %s.zip %s'%(dn,dn),cwd=os.getcwd(),shell=True)
			proc.communicate()
			html += ["<li><a style=\"color:red;\" href=\"%s.zip\">%s.zip</a></li>"%(dn,dn)]
		html += ['</ul>']

#---zip archives
zipped_fns = [i for i in glob.glob('printed/*.zip') if i!='README.md']
if any(zipped_fns):
	html += ["<h3>zipped sources (LaTeX)</h3><ul>"]
	for fn in zipped_fns: 
		html += ["<li><a style=\"color:red;\" href=\"%s\">%s</a></li>"%(fn,os.path.basename(fn))]
	html += ['</ul>']

#---source markdown files
markdown_fns = [i for i in glob.glob('*.md') if i!='README.md']
if any(markdown_fns):
	html += ["<h3>markdown source</h3><ul>"]
	for fn in markdown_fns: 
		html += ["<li><a style=\"color:red;\" href=\"%s\">%s</a></li>"%(fn,fn)]
	html += ['</ul>']

#---check for combos
combo_fns = glob.glob('printed/combos/*.pdf')
if any(combo_fns):
	html += ["<h3>combined pdf (LaTeX)</h3><ul>"]
	for fn in combo_fns: 
		html += ["<li><a style=\"color:red;\" href=\"%s\">%s</a></li>"%
			(fn,os.path.basename(fn))]
	html += ['</ul>']

#---check for combos
tiles_fns = glob.glob('tile-*.html')
if any(tiles_fns):
	html += ["<h3>galleries</h3><ul>"]
	for fn in tiles_fns: 
		html += ["<li><a style=\"color:red;\" href=\"%s\">%s</a></li>"%
			(fn,os.path.basename(fn))]
	html += ['</ul>']

#---write index file
html += ["</div></div></body>"]
with open('index.html','w') as fp:
	for line in html: fp.write(line+'\n')
