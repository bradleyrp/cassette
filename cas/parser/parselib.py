#!/usr/bin/python

import os,sys,re,subprocess,glob
from collections import OrderedDict as odict
from constants import *
from copy import deepcopy
import tempfile
import shutil
import yaml

###---STANDALONES

def write_tex_png(formula,name,count,label=None,vectorbold=False):
	"""
	Convert a TeX equation to PNG.
	Take a formula and write an equation based on the document name and an optional label. 
	We also receive the count in case uses wish to put it in the filename.
	"""
	#---specify the template for a standalone equation
	#---note the linewidth below might be too small for lengthy equations
	template_tex_png = '\n'.join([r"",r"\documentclass[border=2pt]{standalone}",r"\usepackage{varwidth}",
		r"\usepackage{amsmath}",r"%s",r"\begin{document}",r"\begin{varwidth}{\linewidth}",
		r"\begin{equation*}","%s",r"\end{equation*}",r"\end{varwidth}",r"\end{document}"])
	tmpdir = tempfile.mkdtemp()
	outtex = (template_tex_png%('' if not vectorbold 
		else TexDocument.vector_bold_command,formula.strip('., '))).split('\n')
	for ll,line in enumerate(outtex):
		if re.match(r'^\\label',line): outtex[ll] = ''
	print_tex = [i for i in outtex if not re.match('^\s*$',i)]
	with open('%s/snaptex2.tex'%tmpdir,'w') as fp: fp.write('\n'.join(print_tex))
	os.system('pdflatex --output-directory=%s %s/snaptex2.tex'%(tmpdir,tmpdir))
	os.system('convert -trim -density 300 '+
		'%s/snaptex2.pdf -quality 100 printed/%s-%s.png'%(tmpdir,name,
			os.path.basename(tmpdir) if not label else label))

def linesnip(lines,*regex,**kwargs):
	"""
	Custom function for choosing sections of the markdown file for specific processing rules.
	"""
	is_header = kwargs.get('is_header',True)
	if len(regex)==1:
		#---a single regex will return the line numbers for all matches
		line_nos = [ii for ii,i in enumerate(lines) if re.match(regex[0],i)]
	else:
		#---if multiple regexes then we return the line number for first match for each kind
		line_nos = []
		for reg in regex:
			sub_lines = lines[(slice(None,None) if len(line_nos)==0 else slice(line_nos[-1]+1,None))]
			new_lineno = [ii+(1 if len(line_nos)==0 else line_nos[-1]) 
				for ii,i in enumerate(sub_lines) if re.match(reg,i)]
			new_lineno = len(lines)-1 if new_lineno == [] else new_lineno[0]
			line_nos.append(new_lineno)
	#---if there are exactly two regexes we assume this is ending in a slice object so we move the end
	if is_header and len(line_nos)==2: line_nos[1] += 1
	return line_nos

###---CLASSES

class MDHeaderText:

	def __init__(self,lines):

		"""
		A class which holds the header information from a markdown file.

		header material specification
			1. the header is delimited by lines containing "---"
			2. start a multiline item with ">key:" and end it with blank line or "..."
			3. keys may contain spaces
			4. keys with trailing "@template" items will only apply to those (LaTeX) templates if available
			5. within each item, all newlines and tabs are collapsed into spaces
		"""

		#---extract the header
		regex_header_block = r"-{3,}\n(.*?\n-{3,})(.+)"
		header_pull = re.compile(regex_header_block,re.M+re.DOTALL)
		self.header,body = header_pull.match(lines).groups()

		#---container
		self.core = {'body':body}
		def register_header(m): 
			assert m.group(1) not in self.core
			key,val = m.group(1),m.group(2)
			self.core[key] = val
			if re.match('(True|true|yes|Y|y)',val): self.core[key] = True
			elif re.match('^(False|false|no|N|n)$',val): self.core[key] = False
	
		#---regex defns
		#---specify the formats for different items in the header block
		regex_comment_line = r'\n\s*\!.*?\n'
		regex_header_parse = [
			('regex_header_block',(r"^>([ \w\@]+)\s*:\s*\n?$(.*?)\n([\.]{3,}|\n|[-]{3,})",re.M+re.DOTALL)),
			('regex_header_yaml',(r"^(~.*?)\s*:\s*\n(.*?)\n([\.]{3,}|\n|[-]{3,})",re.M+re.DOTALL)),
			('regex_header_single',(r"^([ \w\@]+):\s*(.*?)\s*$",re.M)),]

		#---parse the header
		self.header = re.sub(regex_comment_line,'\n\n',self.header,re.MULTILINE)

		for key,(regex,flags) in regex_header_parse:
			self.header = re.compile(regex,flags if flags else 0).sub(register_header,self.header)
		self.header = self.header.strip('\n-').strip()
		if self.header: raise Exception('unprocessed header items: "%s"'%self.header)

		#---post-process any tilde-prefixed keys as yaml
		#---development note: it would be better to have a custom decorator so that each regex
		#---...header style could have its own processing function like this one
		for key in [i for i in self.core.keys() if re.match('^~',i)]:
			x = self.core.pop(key)
			self.core[re.sub('^~','',key)] = yaml.load(x)
		#---clean the header items
		for key in [i for i in self.core if i!='body']:
			if type(self.core[key]) not in [bool,dict]:
				#---remove trailing whitespace
				self.core[key] = self.core[key].strip('\n')
				#---collapse newline, newline-tab, and newline-space into spaces only
				self.core[key] = re.sub(r"([^\n])\s*\n\s*([^\n])",r"\1 \2",self.core[key])

		#---set the article-specific customizer syntax (acts on keys and will be split later)
		self.regex_article_specific = '^(.*?)@(.+)'

	def __getitem__(self,key,default=None): return self.core.get(key,default)
	def bool(self,key,default=False):
		if 'key' in self.core and not type(self.core[key])==bool: 
			raise Exception('"%s"="%s" does not yield a boolean'%(key,core[key]))
		else: return self.core.get(key,default)
	def spec(self,key,default=False):
		"Development note: this wraps __getattr__ until the latter is implemented in TexDocument."
		return self.__getitem__(key,default=default)
	def customs(self,article=None):
		"Unpack the article-specific specs into a dictionary."
		key_to_specific_articles = dict([(i,[(j.strip(),[l.strip() for l in k.split('@')])
			for j,k in re.findall(self.regex_article_specific,i)][0]) 
			for i in self.core.keys() if re.match(self.regex_article_specific,i)])
		if not article:
			return dict(key_to_specific_articles)
		else: 
			return dict([(j,i) for i,(j,k) in key_to_specific_articles.items() if article in k])

def underscore(x): return re.sub('_','ZZZ',x)

class TexDocument:

	"""
	Holds a LaTeX/HTML document for rendering from MARKDOWN.

	notes on constants:
		Class variables include both "rules" (which use lambda functions) and "subs" (substitutions).
	"""

	#---where to store rendered documents and paraphanalia
	package_prefix = 'printed/'
	#---which type of la/tex citaitons to use
	citation_type = 'cite'
	latex_header_replacer = '^%---REPLACE\s*(.*?)\s*$'
	latex_sectioner = '^%---SECTION\s*(.*?)\s*$'
	markup_regex = "\\\pdfmarkupcomment\\[markup=[A-Za-z]+,color=[A-Za-z]+\\]\{([^\}]+)\}\{[^\}]*\}"
	vector_bold_command = r"% all vectors are bold"+'\n'+r'\renewcommand{\vec}[1]{\mathbf{#1}}'+'\n'
	labelchars = '[A-Za-z0-9_-]'
	#---note that trailing parentheses is a spacing character because figure references can be parenthetical
	spacing_chars = '\s:\.,\)'
	#---!temporary hack. removing the hyphen
	#bibkey = '[a-zA-Z\-]+-[0-9]{4}[a-z]?'
	bibkey = '[a-zA-Z\-]+-?[0-9]{4}[a-z]?'
	available_tex_formats = ['article']
	author_affiliation_regex = '^([^@]+)(?<!\\s)\\s*@?(.*)$'
	equation_prefix = r"\renewcommand{\theequation}{%s\arabic{equation}}"
	section_prefix = r"\renewcommand{\thesection}{%s\arabic{section}}"
	figure_prefix = r"\renewcommand{\thefigure}{%s\arabic{figure}}"
	table_prefix = r"\renewcommand{\thetable}{%s\arabic{table}}"
	figure_regex = '!figure:\s*(?:([^\n]+))\n([^\n]+)\s(.*?)(?=\n\n|\Z)'
	regex_block_comment = r"(?:[:]{3})\s*\n(.*?)\n\s*(?:[:]{3})\s*\n"
	regex_line_comment = r"^[:]{3,}\s*[^\s]+(.+)"
	regex_equation = r"^\$\$\s*$(.*?)\n\$\$\s*(?:\{#eq:([^\}]+)\})?"
	#---the following inline comment cannot start the line, otherwise use the line comment
	regex_inline_comment = r"[^\:](?:[\:]{2})(.*?)(?:[\:]{2})"
	puredir = 'history'

	#---rules for TeX documents
	rules_tex = {
		#---turn hash-prefixed headings into section delimiters with an optional label
		'^(#+)(\*)?\s*(.*?)\s*(?:\{#sec:(.+)\})?$':lambda s : '\%s%s{%s%s}\n'%(
			{1:'section',2:'subsection',3:'subsubsection',4:'paragraph',5:'subparagraph'}[len(s[0])],
			s[1],s[2],'' if not s[3] else r"\label{sec:%s}"%underscore(s[3])),}

	#---replacement rules for HTML
	rules_html = {
		'^(#+)(\*)?\s*(.*?)\s*(?:\{#sec:(.+)\})?$':lambda s : '\n<br><h%d %s>%s</h%d>\n'%(
			len(s[0])+1,'id="%s"'%('-'.join(s[2].split(' ')).lower() if not s[3] 
			else s[3]),s[2],len(s[0])+1),
		'^>+\s*$':lambda s : s,
		'^[0-9]+\.\s?(.+)':lambda s : '<li>%s</li>\n'%s,
		'^\s*$':lambda s : '<p>',}

	#---note that order matters in the following dictionary
	subs_tex = odict([
		('\[\[([^\]]+)\]\]',r"\pdfmarkupcomment[markup=Highlight,color=yellow]{\1}{}"),
		(regex_inline_comment,r""),
		(regex_line_comment,r""),
		('\[([^\]]+)\]\(([^\)]+)\)',r'\href{\2}{\1}'),
		('\<\<([^\>]+)\>\>',
			r"\\textcolor{babypink}{\pdfmarkupcomment[markup=Highlight,color=aliceblue]{\1}{}}"),
		('\$([^\$]+)\$',r"$\mathrm{\1}$"),
		('\*\*([^\*]+)\*\*',r'\\textbf{\1}'),
		('\*([^\*]+)\*',r'\emph{\1}'),
		('"([^"]+)"',r"``\1''"),
		('^[0-9]+\.\s?(.+)',r'\item \1'+'\n'),
		#(r"\%",r"\\%"),
		#(r"([0-9]+)?\?%",r"\1%"),
		('([^`])`([^`]+)`',r"\1 \\texttt{\2}"),
		(r"@chap:(%s+)"%labelchars,r"\\ref{chap:\1}"),
		#---or inline pygments/minted: ('`([^`]+)`\s\<(.+)\>',r"\mintinline{\2}{\1}",)
		(r"\#",r"\\#"),
		#---switch between TeX/HTML
		(r"~(.*?)\|(.*?)~",r"\1"),])

	#---multiline regex substitutions or replacements for LaTeX
	subs_multi_tex = {
		'\n\n([0-9]+\.)':r"\\begin{enumerate} \\item ",
		'\n([0-9]+\.\s*[^\n]+)\n\n':'\n'+r"\1"+'\n'+r"\\end{enumerate}"+'\n',
		regex_block_comment:'\n',
		regex_equation:
			lambda x : '\n'+r"\begin{equation}%s"%('' if x[1] else r'\notag')+x[0]+'\n'+"%s\end{equation}"%
			(r"\label{eq:%s}"%underscore(x[1])+'\n' if x[1] else '')+'\n\n',}

	#---? figure will not be capitalized sometimes
	#---? double asterisk may not work if dictionary in wrong order
	subs_html = odict([
		(r" \\\\ ",''),
		('\*\*([^\*]+)\*\*',r'<strong>\1</strong>'),
		('\*([^\*]+)\*',r'<em>\1</em>'),
		('\[\[([^\]]+)\]\]',r"""<span style="background-color: #FFFF00">\1</span>"""),
		('\<\<([^\>]+)\>\>',r"""<span style="background-color: #F0F8FF; color: #F4C2C2">\1</span>"""),
		(regex_inline_comment,r""),
		(regex_line_comment,r""),
		('\$([^\$]+)\$',r"$\mathrm{\1}$"),
		("\\\pdfmarkupcomment\\[markup=[A-Za-z]+,color=[A-Za-z]+\\]\{([^\}]+)\}\{[^\}]*\}",
			r"""<span style="background-color: #FFFF00">\1</span>"""),
		('(?:``)([^\']+)(?:\'\')',r"&#8220;\1&#8221;"),
		('`([^`]+)`',r"<code>\1</code>"),
		('\[([^\]]+)\]\(([^\)]+)\)',r'<a href="\2">\1</a>'),
		('^>\s*(.+)',r"<blockquote>\1</blockquote>"),
		#---had to remove the following for python3
		# '\\\AA':'\unicode{x212B}',
		(r"@chap:(%s+)"%labelchars,r'<a href="\1.html">N</a>'),
		(r"\\vspace\{([^\}]+)\}",""),
		(r"~(.*?)\|(.*?)~",r"\2"),
		#---latex-only refs get some styling that harkens to tex
		(r"\\ref{(.*?)}",r"@{\1}"),])

	subs_multi_html = {
		regex_block_comment:'\n',
		'\n\n([0-9]+\.)':'\n<ol>\n'+r"\1",
		'\n([0-9]+\.\s*[^\n]+)\n\n':'\n'+r"\1"+'\n</ol>\n',
		r"(?:\\begin\{table\})(.*?)(?:\\end\{table\})":
			'<text style="color:gray"><strong>cannot render tex table (see the PDF)</strong></text>',}

	#---order matters
	special_subs_tex = odict([
		(r'%',r'\%'),
		(r' "',r' ``'),
		#---! previously (r'" ',"'' "),
		(r' \'',r' `'),
		(r'\' ',"' "),
		(r'~',r'$\sim$'),
		(r'\.\.\.',r'\ldots'),
		(r"([0-9]+\.?[0-9]*)%",r"\1\%"),])
	special_subs_html = odict([
		(r'---',r'&mdash;'),])
	
	def __init__(self,fn,**kwargs):
		"""
		This constructor organizes all of the document processing. See the class docstring for details.
		"""
		if type(fn)==list: raise Exception('expecting a file name')
		else: 
			with open(fn) as fp: self.raw = fp.read()
			self.name = re.findall('([^\/]+)\.md$',fn)[0]
		#---parse the header and store the body
		self.specs = MDHeaderText(self.raw)
		self.body = self.specs.core.pop('body')
		#---boolean which (when false) supresses any tex comments in latex header (useful for submissions)
		self.tex_comments = self.specs.bool('tex_comments')
		if kwargs: raise TypeError('unexpected **kwargs: %r'%kwargs)

		#---user may set the tex binary
		#---! we should warn the user that pdflatex doesn't do comments nicely
		self.latex_binary = self.specs.spec('latex_binary','pdflatex')

		#---some details from dispatch.yaml e.g. global substitutions
		dispatch_fn = 'dispatch.yaml'
		if os.path.isfile(dispatch_fn): 
			with open(dispatch_fn) as fp:
				dis = yaml.load(fp.read())
			aliases = {}
			#---aliases that should apply to both HTML and LaTeX
			if 'alias' in dis: aliases.update(**dis['alias'])
			#---local alias dictionary in the header overrides dispatch
			if self.specs['alias']: aliases.update(**eval(self.specs['alias']))
			for subs in ['subs_tex','subs_html']:
				tex_html_subs = [(i,j) for i,j in aliases.items()]+\
					[(key,val) for key,val in getattr(self,subs).items()]
				setattr(self,subs,odict(tex_html_subs))

		#---autodetect available LaTeX headers
		self.available_tex_formats = [re.match('^header-(.+)\.tex',os.path.basename(fn)).group(1)
			for fn in glob.glob('cas/sources/header-*.tex')]

		#---figure paths and equation settings (e.g. vectorbold) must be decided on the fly
		self.vectorbold = self.specs.bool('vectorbold')
		self.image_location = self.specs.spec('images')
		self.subs_multi_tex.update(**{self.figure_regex:self.figure_convert_tex})
		self.subs_multi_html.update(**{
			self.figure_regex:self.figure_convert_html,
			self.regex_equation:
				lambda x : '\n$$'+('' if not self.vectorbold else self.vector_bold_command)+
					r"\begin{equation}%s"%('' if x[1] else r'\notag')+x[0]+"%s\end{equation}"%
					(r"\label{eq:%s}"%underscore(x[1]) if x[1] else '')+'$$\n',})
		#---handle block code here
		self.subs_multi_html.update(**{'\n~~~\n(.*?)\n~~~\n':lambda x:
			'<br><br><textarea style="'+
			'width:100%;white-space: pre;overflow-wrap: normal;overflow-x: auto;resize: none;'+
			'" rows="'+str(len(x[0].splitlines())-1+1)+'">'+x[0]+
			'</textarea><br><br>'})
			#---! added three rows above because it was too squished if you have overruns and the horizontal scroll

		#---figure style for turning @fig:name into e.g. "figure (2)"
		#---figure prefix for making supplements with figures numbered "S1" usw
		#---the figure style is automatically uppercased at the beginning of a sentence
		#---the styles and prefixes also apply to equations and sections for the supplements
		self.figstyle = self.specs.spec('figstyle','figure (%s)').strip('"')
		self.secstyle = self.specs.spec('secstyle','section (%s)').strip('"')
		self.secstyle_html = self.specs.spec('secstyle','&sect;%s').strip('"')
		self.eqnstyle = self.specs.spec('eqnstyle','equation (%s)').strip('"')
		self.figpref = self.specs.spec('figpref',default='')
		self.secpref = self.specs.spec('secpref',default='')
		self.eqnpref = self.specs.spec('eqnpref',default='')
		self.tabpref = self.specs.spec('tabpref',default='')

		#---prefixing happens live so we populate the subs here
		self.subs_tex.update(**{'@fig:(%s+)'%self.labelchars:
			lambda x:self.figstyle%(r"\ref{fig:%s}"%(underscore(x.group(1))))})
			#---previously: but some texlive forbids underscores: self.figstyle%(r"\\ref{fig:\1}")})
		self.subs_tex.update(**{'@sec:(%s+)'%self.labelchars:
			lambda x:self.secstyle%(r"\ref{fig:%s}"%(underscore(x.group(1))))})
			#---previously: self.secstyle%(r"\\ref{sec:\1}")})
		self.subs_tex.update(**{'@eq:(%s+)'%self.labelchars:
			lambda x:self.eqnstyle%(r"\ref{eq:%s}"%(underscore(x.group(1))))})
			#---previously: self.eqnstyle%(r"\\ref{eq:\1}")})
		self.subs_html.update(**{'@sec:(%s+)'%self.labelchars:
			'<a href="#%s">%s</a>'%(r"\1",self.secstyle_html%(self.secpref+r"\1")),
			'@(eq:%s+)'%self.labelchars:self.eqnstyle%r"$\eqref{\1}$"})
		self.bibfile = self.specs.spec('bibliography')
		self.write_equation_images = self.specs.bool('write_equation_images')

		#---keep track of images
		#---! some of these might be deprecated?
		self.images,self.equation_counter,self.refs = [],0,[]

		#---select latex header types and loop over requested document types
		self.render_types = [i for i in self.available_tex_formats if self.specs.bool(i)]
		for rt in self.render_types:
			self.style = rt
			if self.specs.bool(rt):

				self.parts = odict()
				self.package_dir = 'printed/'+self.name+'-'+rt
				if not os.path.isdir('printed'): os.mkdir('printed')
				if not os.path.isdir(self.package_dir): os.mkdir(self.package_dir)
				#---tagalongs must be a python list of files to bring along
				if self.specs.spec('tagalongs'):
					along_list = eval(self.specs.spec('tagalongs'))
					for fn in along_list: shutil.copy(fn,os.path.join(self.package_dir,''))
				with open('./cas/sources/header-%s.tex'%rt) as fp: self.parts['header'] = fp.readlines()
				#---the "LOCAL" keyword in a TeX header comment specifies files that must be copied
				regex = '^\s*%-+\s*LOCAL\s*([^\s]+)\s*$'
				reqs = [re.match(regex,i).group(1) for i in self.parts['header'] if re.match(regex,i)]
				for req in reqs: shutil.copy(os.path.join('cas/sources',req),self.package_dir)

				self.sections = odict([(re.findall(self.latex_sectioner,i)[0],ii) 
					for ii,i in enumerate(self.parts['header']) if re.match(self.latex_sectioner,i)])
				#---! note this is clumsy and repetitive
				#---mark the line number for replacements
				self.header_replacements = odict([(re.findall(self.latex_header_replacer,i)[0],ii) 
					for ii,i in enumerate(self.parts['header']) if re.match(self.latex_header_replacer,i)])

				self.embed_bbl = self.specs.bool('embed_bbl')
				#---! always embed BBL
				self.embed_bbl = True
				
				#---cancel if necessary
				if self.specs.bool('avoid'): continue

				#---PARSERS
				print("[STATUS] rendering to PDF in %s format"%rt)
				self.direct()
				self.proc()
				self.bib()

				#---the NOCOMPILE comment flag prevents compile steps in the case of e.g. chapters
				nocompile = any([i for i in self.parts['header'] if re.match('^\s*%-+\s*NOCOMPILE',i)])

				#---extras
				if not nocompile:
					if self.vectorbold: 
						for line in self.vector_bold_command.split('\n'):
							self.header_more(line)
					#---! need to add header extras from specs here in a standard format
					if self.eqnpref : self.header_more(self.equation_prefix%self.eqnpref)
					if self.secpref: self.header_more(self.section_prefix%self.secpref)
					if self.figpref: self.header_more(self.figure_prefix%self.figpref)
					if self.tabpref: self.header_more(self.table_prefix%self.tabpref)
					#---check for custom "moreheader" entries to add to the latex header
					extras = self.specs.customs(article=self.style).get('moreheader',None) 
					if not extras: 
						extras_general = self.specs.spec('moreheader',None)
						if extras_general: self.header_more(extras_general)
					else: self.header_more(self.specs.spec(extras))

				#---write and render
				self.write_relative(fn=self.name,dn=self.package_dir,nocompile=nocompile)
				if not nocompile: self.render()

		#---! do we need at least one PDF style to get the self.parts and is this necessary?
		#---render HTML if desired
		if self.specs.spec('images'):
			self.image_location = os.path.join(self.specs.spec('images'),'')
		#---! removed the option otherwise make always makes: self.html_output = self.specs.bool('html')
		self.html_output = True
		self.html_template = self.specs.spec('html_template','header.html')
		if self.html_output: 
			self.direct_html()
			self.proc(version='html')
			self.bibliography_html()
			self.write_html(fn=self.name,dn='./')
		self.notes = self.specs.bool('notes')
		if self.notes: self.direct_notes()

		#---after all this we save a sentence-split version of the file and commit it
		self.posterity()

	def posterity(self):
		"""
		Save a version of this file suitable for git, specifically with one sentence per line.
		"""
		perfect_text = self.specs.header
		perfect_text += re.sub("(\.|\?|\.\")[ \t]+([^\n])",r"\1\n\2",self.body)
		perfect_text = re.sub('[\n]{2,}','\n\n',perfect_text)
		purename = self.puredir+'/'+self.name+'.pure'
		with open(purename,'w') as fp: fp.write(perfect_text)
		print('[STATUS] wrote %s'%purename)

	def direct(self):
		"""
		Prepare each section of the document according to replacement flags in the LaTeX 
		header and a set of simple rules.
		"""
		#---retrieve a footer if it exists
		footer_fn = 'cas/sources/footer-%s.tex'%self.style
		if os.path.isfile(footer_fn):
			with open(footer_fn) as fp: footer_lines = fp.readlines()
		else: footer_lines = []

		#---default header settings for LaTeX
		instructions = {
			'end':r'\end{document}',
			'maketitle':'\\maketitle',
			'title':r'\title{%s}'%self.specs.spec('title'),
			'abstract':('\n\\begin{abstract}\n'+
				self.specs.spec('abstract')+'\n\\end{abstract}'
				if self.specs.spec('abstract') else ''),
			'body':self.body,
			'bbl':'\\bibliography{%s}\n'%
				os.path.abspath(self.specs.spec('bibliography')) 
				if self.specs.spec('bibliography') else None,
			'footer':footer_lines,}

		#---loop over the sections marked in comments in the header
		replacement_markers = [(i.lower(),j) for i,j in 
			tuple(self.sections.items())+tuple(self.header_replacements.items())]
		#---assemble items from the specs that apply only to this article
		custom_specs = self.specs.customs(article=self.style)
		#---loop over necessary replacements (denoted either "REPLACE" or "SECTION")
		for placeholder,header_lineno in replacement_markers: 
			#---if the placeholder is marked as a section in the header we add it as a section
			if placeholder in instructions and placeholder.upper() in self.sections: 
				self.add(**{placeholder.lower():instructions[placeholder]})
			#---if the placeholder is a default REPLACE found in instructions we replace it here
			elif placeholder in instructions:
				self.parts['header'][self.header_replacements[placeholder.upper()]] = \
					instructions[placeholder]
			#---apply article-specific replacements or sections from the header
			else:
				if placeholder in custom_specs.keys():
					extracted = self.specs[custom_specs[placeholder]]
					if placeholder.upper() in self.sections: self.add(**{placeholder:extracted})
					else: self.parts['header'][self.header_replacements[placeholder.upper()]] = extracted

	def direct_html(self):
		"""
		Prepare each section of the document according to replacement flags in the 
		header and a set of simple rules.
		"""
		#---while the direct function for latex infers sections from comments we hard-code them for html
		self.parts = {}
		with open('./cas/sources/%s'%self.html_template,'r') as fp: self.html_header = fp.readlines()
		#---replace title in html header
		for ll,l in enumerate(self.html_header):
			if re.search('@TITLE',l) != None: 
				self.html_header[ll] = re.sub('@TITLE',self.specs.spec('title'),l)
			#---previously used for "new fonts"
			extra_css = "\n"
			if re.search('@EXTRA_CSS',l) != None: 
				self.html_header[ll] = re.sub('@EXTRA_CSS',extra_css,l)
		self.parts['header'] = self.html_header

		#---add authors
		author_text = [] 
		author = self.specs.spec('author')
		if author:
			author_text.append('\n<br><h3>Authors</h3><ul>\n')
			for a in author: author_text.append('<li> %s'%a)
			author_text.append('</ul>\n')
		self.parts['author'] = author_text

		#---add abstract
		abstract_text = []
		abstract = self.specs.spec('abstract')
		if abstract:
			abstract_text.append('<h3>Abstract</h3>\n')
			abstract_text.append(abstract+'\n')
		self.parts['abstract'] = abstract_text

		#---track the parts list here in parselib rather than in the html header
		self.parts['body'] = self.body
		self.parts_list = ['header','author','abstract','body']

	def bibliography_html(self):
		"""
		Make the HTML bibliograpy.
		"""
		if not self.bibfile: return
		self.parts_list.append('bibliography')
		html = []

		if not os.path.isfile(self.bibfile):
			raise Exception('cannot find bibliography %s. remove it from the header or find it'%self.bibfile)
		with open(self.bibfile,'r') as fp: biblines = fp.readlines()
		#---entry starting line numbers
		lnos = linesnip(biblines,'@',is_header=False)
		#---we must exclude comments from the bib file
		bibkeys = [re.findall('@[A-Za-z]+\s?\{([^,]+),',biblines[ll])[0] 
			for ll in lnos if re.match('^@(?!comment)',biblines[ll])]

		regex_bibref = r"\[?@(%s)(?:\s|\])?"
		reforder_non_unique = re.findall(regex_bibref%self.bibkey,self.body)
		reforder = []
		for r in reforder_non_unique:
			if r not in reforder: reforder.append(r)
		ordlookup = dict([(i,ii+1) for ii,i in enumerate(reforder)])
		html.append('<br><h2>References</h2><br>\n<ol>\n')
		html.append('<ol>\n')
		
		#---replace references with numbers
		for lineno,line in enumerate(self.parts['body']):
			if re.search('@%s'%self.bibkey,line) != None:
				for found in re.findall('@(%s)+'%self.bibkey,line):
					try:
						self.parts['body'][lineno] = re.sub('@%s'%found,
							'[<a href="#refno%d">%d</a>]'%(ordlookup[found],ordlookup[found]),
							self.parts['body'][lineno])
					except: raise Exception('cannot link %s'%found)

		details = {}
		for key in sorted(ordlookup.keys()):
			#---extract data from bibtex
			dat = ''.join(biblines[slice(*linesnip(biblines,'@[A-Za-z]+\{%s'%key,'@'))])
			authors = ''.join(re.findall('(?:A|a)uthor\s*=\s*\{([^\}]+)',dat))
			try: year = int(re.findall('(?:Y|y)ear\s*=\s*\{([^\}]+)',dat)[0])
			except: raise Exception('[ERROR] cannot find bibkey "%s" in the database'%key)
			title = re.findall('(?:T|t)itle\s*=\s*\{([^\}]+)',dat)[0]
			try: journal = re.findall('Journal\s*=\s*\{([^\}]+)',dat)[0]
			except: journal = ''
			try: url = re.findall('(?:U|u)rl\s*=\s*\{([^\}]+)',dat)[0]
			except: url = "BROKEN LINK"
			if journal != '':
				entry = '%s<br><a href="%s">%s</a>.<br><em>%s</em>, %d.'%(authors,url,title,journal,year)
			else:
				#---! probably a book?
				entry = '%s<br><a href="%s">%s</a>, %d.'%(authors,url,title,year)
			details[key] = entry

		#---loop over references at the end
		for refno,ref in enumerate(reforder):
			refkey = bibkeys.index(ref)
			html.append('<li><a name="refno%d"></a>%s</li>'%(refno+1,details[bibkeys[refkey]]))

		#---add html lines to the bibliography
		self.parts['bibliography'] = html

	def proc(self,part='body',version='latex'):
		"""
		Perform all text transformations for the body of a document.
		"""
		if version == 'latex': 
			rules = self.rules_tex
			subs = self.subs_tex
			special_subs = self.special_subs_tex
			subs_multi = self.subs_multi_tex
		elif version == 'html': 
			rules = self.rules_html
			subs = self.subs_html
			subs_multi = self.subs_multi_html
			special_subs = self.special_subs_html
		else: raise Exception('unclear rules version: %s'%version)

		#---multiline substitutions
		newlined = ''.join(self.parts[part])
		#---collect image names and paths for later
		#---track the order of images for numbering in HTML and conversion to PDF in LaTeX
		#---! note that we disallow the use of the regular markdown figure syntax, which must be removed
		self.images = [i[:2] for i in re.findall(self.figure_regex,newlined,re.MULTILINE+re.DOTALL)]
		if self.images and not os.path.isdir(str(self.image_location)):
			raise Exception('invalid image location %s'%self.image_location)
		missing_images = [fn for name,fn in self.images 
			if not os.path.isfile(os.path.join(self.image_location,fn))]
		if any(missing_images):
			raise Exception('[ERROR] missing images:\n%s\n'%'\n'.join(missing_images))
		#---intervene to write all the equations to separate PNGs
		if version == 'latex' and self.write_equation_images:
			rule = re.compile(self.regex_equation,re.MULTILINE+re.DOTALL)
			for ii,(equation,name) in enumerate(rule.findall(newlined)):
				write_tex_png(equation,
					self.name,self.equation_counter,vectorbold=self.vectorbold,label=name)
		#---block comments only work when you compile!
		comps = [(rule,re.compile(rule,re.MULTILINE+re.DOTALL),convert) 
			for rule,convert in subs_multi.items()]
		for raw_rule,rule,convert in comps:
			if type(convert)==str:
				try: newlined = rule.sub(convert,newlined)
				except: raise Exception('[ERROR] failed to convert %s to %s'%(str(raw_rule),convert))
			else:
				caught = rule.search(newlined)
				while caught:
					newlined = ''.join([
						newlined[:caught.start()],
						convert(caught.groups()),
						newlined[caught.end():]])
					caught = rule.search(newlined)
		self.parts[part] = newlined.splitlines(True)
		
		#---entire-line replacements in the body
		for lineno,line in enumerate(self.parts[part]):
			for rule in rules:
				if re.match(rule,line):
					self.parts[part][lineno] = rules[rule](re.findall(rule,line)[0])

		#---substitution rules
		for lineno,line in enumerate(self.parts[part]):
			for rule,convert in subs.items():
				self.parts[part][lineno] = re.sub(rule,convert,self.parts[part][lineno])

		#---special latex substitutions
		for lineno,line in enumerate(self.parts[part]):
			for a,b in special_subs.items(): 
				self.parts[part][lineno] = re.sub(a,b,self.parts[part][lineno])

		#---capitalize figures
		for lineno,line in enumerate(self.parts[part]):
			self.parts[part][lineno] = re.sub(r'\. figure',r'. Figure',self.parts[part][lineno])
			self.parts[part][lineno] = re.sub('^figure','Figure',self.parts[part][lineno])

	def write_html(self,fn,dn):
		"""
		Render markdown to HTML.
		"""
		#---make a copy of self.parts which we will make path substitutions in
		specific_parts = {}
		#---loop over each part and make the substitutions
		for key in self.parts_list:
			val = self.parts[key]
			specific_parts[key] = val
			#import pdb;pdb.set_trace()
			imagenos = list(zip(*self.images))[0] if self.images else []
			#---since figure_convert_html writes the bold figure titles carefully, we can simply replace 
			#---...these by name. note that the greedy search in strong tags makes this precise
			#---! switching to block of text from lines --- note that we should remove the lined versions
			#---! ...and operate with blocks more often. we suffix the newline here so the HTML is not all on one line
			#---! ...and also so that
			specific_parts[key] = ['%s\n'%i for i in 
				re.sub('<strong>@fig:(.*?)</strong>',
				lambda x:'<strong>Figure %d. </strong>'%(imagenos.index(x.group(1))+1),
				''.join(specific_parts[key])).split('\n')]
			#---replace figure pointers with links
			for ll,line in enumerate(specific_parts[key]):
				#---search and replace figure captions made by figure_convert_html
				if re.search('@fig',specific_parts[key][ll]) != None:
					for figlabel in re.findall('@fig:(%s+)'%self.labelchars,specific_parts[key][ll]):
						if figlabel not in imagenos:
							raise Exception('figure named "%s" not found in the list of figures: %s'%(
								figlabel,imagenos))
						if re.search('@fig:%s([%s])'%(figlabel,self.spacing_chars),
							specific_parts[key][ll]):
							specific_parts[key][ll] = re.sub(
								'@fig:(%s)([%s])'%(figlabel,self.spacing_chars),
								lambda x:self.figstyle%(
									r'<a href="#fig:%s">%s%d</a>%s'%(
										figlabel,self.figpref,imagenos.index(x.group(1))+1,x.group(2))),
								specific_parts[key][ll])
				#---capitalize figures
				#---! redundant with proc
				for lineno,line in enumerate(self.parts[key]):
					self.parts[key][lineno] = re.sub(r'\. figure',r'. Figure',self.parts[key][lineno])
					self.parts[key][lineno] = re.sub('^figure','Figure',self.parts[key][lineno])
		with open(os.path.join(dn,fn+'.html'),'w') as fp:
			for key in self.parts_list:
				if key in specific_parts:
					val = specific_parts[key]
					if type(val)==str: fp.write(val)
					elif type(val)==list: fp.write(''.join(val))
					else: raise Exception('\n[ERROR] cannot understand this part of the document: %s'%key)
					fp.write('\n')

	def header_more(self,line):
		"""
		Add a line to the header.
		"""
		lastline = next(ii for ii,i in enumerate(self['header']) if re.match('^\s*\%-+END HEADER',i))
		self['header'].insert(lastline,line)

	def __getitem__(self,index): return self.parts[index]

	def body(self):
		"""
		Extract the body of the text, separating it from the header.
		"""
		return self.raw[linesnip(self.raw,'^-+\s+?$')[-1]+1:]

	def add(self,**kwargs):
		"""
		Add a component of the document.
		"""
		for key,val in kwargs.items(): self.parts[key] = val

	def write(self,fn):
		"""
		Write the document to tex format.
		"""
		with open(fn,'w') as fp:
			for key,val in self.parts.items():
				if type(val)==str: fp.write(val)
				elif type(val)==list:
					for line in val: fp.write(line)
				else: 
					import pdb;pdb.set_trace()
					raise Exception('\n[ERROR] cannot understand this part of the document: %s'%key)
				fp.write('\n')

	def write_relative(self,fn,dn,nocompile=False):
		"""
		Write a relative copy of the tex file inside a pack folder with path substitutions 
		and fetch dependencies.
		!LATER EXPAND THIS TO HANDLE BODY TEX FILES!
		"""

		#---convert images to PDF
		image_spot = self.image_location if self.image_location else ''
		for label,path in self.images:
			image_source = os.path.join(os.getcwd(),image_spot,path)
			if not os.path.isfile(os.path.join(dn,'fig_%s.pdf'%label)):
				print("[STATUS] converting image to PDF: %s"%label)
				proc = subprocess.Popen('convert %s fig_%s.pdf'%(image_source,label),shell=True,cwd=dn)
				output,error = proc.communicate()
				if proc.returncode!=0: 
					raise Exception('convert failed. make sure imagemagick is installed')

		#---copy the bibfile and refer to the local copy
		if self.bibfile:
			local_bibfile = os.path.basename(self.bibfile)
			shutil.copyfile(self.bibfile,os.path.join(dn,local_bibfile))
			self.parts['bbl'] = "\\bibliography{%s}\n"%local_bibfile
		else: self.parts['bbl'] = '\n'

		#---required for multiple bibliographies if compiling chapters
		if nocompile: 
			#---! hacked for thesis
			#---! ...self.parts['bbl'] = r"\bibliographystyle{iitmthesis}"+'\n'+self.parts['bbl']
			#---! ...self.parts['bbl'] = r"\bibliographystyle{iitmthesis}"
			del self.parts['bbl']
			self.parts['body'].insert(0,r"\chapter{%s}\label{chap:%s}"%(self.specs.spec('title'),
				self.name)+'\n')

		#---make a copy of self.parts which we will make path substitutions in
		specific_parts = odict()
		#---loop over each part and make the substitutions
		for key,val in self.parts.items():
			specific_parts[key] = val
			for label,path in self.images:
				specific_parts[key] = [
					#---! mimic the path-making above and remove it because everything is now relative
					#---! this is a hackish way to apply self.image_location
					re.sub(os.path.join(os.getcwd(),path),
						'{fig_%s}.pdf'%label,str(line)) for line in specific_parts[key]
					if self.tex_comments or not re.match('\s*%',str(line))]

		final_text = ''
		for key,val in specific_parts.items():
			if type(val)==str: final_text += val
			elif type(val)==list: 
				for line in val: final_text += line
			else: 
				import pdb;pdb.set_trace()
				raise Exception('\n[ERROR] cannot understand this part of the document: %s'%key)
			final_text += '\n'

		#---remove double newlines
		final_text = re.sub('[\n]{3,}','\n',final_text,re.M)

		with open(os.path.join(dn,fn+'.tex'),'w') as fp: fp.write(final_text)

	def render(self):
		"""
		Render the LaTeX document to pdf.
		This creates a self-contained copy of the document suitable for submission or sharing with anybody
		who has a working TeX environment.
		"""
		#---before rendering we execute any bash scripts
		if self.specs.spec('bashrun'): os.system(self.specs.spec('bashrun'))
		#---we only render self-contained tex packages to the to printed directories now
		#---new method is entirely local so we overwrite the bbl
		#---! shell-escape only required for minted (for syntax highlighting)
		latex_command = '%s -shell-escape'%self.latex_binary
		directory = self.package_dir
		try:
			proc = subprocess.Popen(latex_command+' %s.tex'%self.name,shell=True,cwd=directory)
			proc.communicate()
			#---! need to use subprocess on os.system below and also log the results
			if self.bibfile:
				subprocess.check_call('bibtex %s'%self.name,cwd=directory,shell=True)
				if self.embed_bbl:
					#---intervene here to add the bbl file 
					bbl_filename, = glob.glob(self.package_dir+'/*.bbl')
					with open(bbl_filename) as fp: self.parts['bbl'] = fp.readlines()
					#---rewrite the tex file here
					self.write_relative(fn=self.name,dn=self.package_dir)
			#---note that we have to run two more times per latex convetion
			#---even if we lack a bib we still need to run twice more to render the comments
			proc = subprocess.Popen(latex_command+' %s.tex'%self.name,shell=True,cwd=directory)
			proc.communicate()
			proc = subprocess.Popen(latex_command+' %s.tex'%self.name,shell=True,cwd=directory)
			proc.communicate()
			#---write a short script to recompile everything
			with open(os.path.join(directory,'rerender.sh'),'w') as fp:
				fp.write('#!/bin/bash\n')
				for extension in ['.blg','.aux','.bbl','.out','Notes.bib','.log']:
					fp.write('rm -f %s%s\n'%(self.name,extension))
				for line in [
					latex_command+' %s.tex\n'%self.name,
					'bibtex %s\n'%self.name,
					latex_command+' %s.tex\n'%self.name,
					latex_command+' %s.tex\n'%self.name]:
					fp.write(line)
			#---after packing we zip everything
			#---! disabled for now
			if False:
				print("[STATUS] zipping")
				proc = subprocess.Popen('zip -r %s.zip %s'%(directory,directory),cwd=os.getcwd(),shell=True)
				proc.communicate()
		except KeyboardInterrupt:
			proc.terminate()
			print("[STATUS] received exit signal")
			print("[STATUS] cleaning files")
			for fn in glob.glob('cas/hold/%s*'%self.name): os.remove(fn)
			print("[STATUS] cancelled")
			sys.exit(1)
		except Exception as e: raise Exception(e)

	def parse_figure(self,caption):
		"""
		Given the figure caption (all lines after the declaration/name and the path), extract
		useful information about how to format a figure.
		"""
		#---extract any modifiers from the caption
		regex_param_line = '^(\s*\{)(.+)(\}\s*)$'
		#---defaults
		extras,style = {'width':1},[]
		if re.match(regex_param_line,caption,re.MULTILINE): 
			extras_group = re.match(regex_param_line,caption,re.MULTILINE)
			extras = dict([i.split('=') for i in extras_group.group(2).split(',')])
			caption = re.sub(''.join(extras_group.groups()),'',caption,re.MULTILINE).strip('\n')
		for key,val in extras.items():
			try: extras[key] = eval(extras[key])
			except: pass
		return caption,extras

	def figure_convert_tex(self,extracts):
		"""
		Convert a figure block into a LaTeX figure.
		"""
		#---unpack the items from regex_figure (first group has the label, second has the path)
		path = os.path.abspath(extracts[1])
		#---the third group is the caption from which we pop any lines solely inside braces
		caption = extracts[2].strip('\n')
		caption,mods = self.parse_figure(caption)
		#---defaults
		width = 1.0
		for key,val in mods.items():
			if key == 'width': width = val
			#---! keys for wrap figure stashed here
			elif key in ['nlines','position','wrapw']: pass
			else: raise Exception('[ERROR] not sure how to handle figure mod: %s=%s'%(str(key),str(val)))
		label = (r"\label{fig:%s}"%underscore(extracts[0]) if extracts[0] else '')
		figure_bracket = (r"\begin{figure}[htbp]",r"\end{figure}")
		if self.specs.spec('wrap_figure',False):
			nlines = mods.get('nlines',10)
			position = mods.get('position','l')
			wrap_width = mods.get('wrapw',0.5)
			figure_bracket = (r"\begin{wrapfigure}[%d]{%s}{%s\textwidth}"%(
				nlines,position,'%0.2f'%wrap_width),
				r"\end{wrapfigure}")
		text = (figure_bracket[0]+'\n'+r"\centering"+'\n'+
			r"\includegraphics[width=%.2f\linewidth]{%s}"%(width,path)+
			'\n'+r"\caption{%s%s}"%(caption,label)+'\n'+
			figure_bracket[1]+'\n\n')
		return text

	def figure_convert_html(self,extracts):
		"""
		Convert markdown figure to HTML with numbering.
		"""
		#---unpack the items from regex_figure (first group has the label, second has the path)
		path = os.path.join(self.image_location if self.image_location else '',extracts[1])
		#---the third group is the caption from which we pop any lines solely inside braces
		caption = extracts[2].strip('\n')
		caption,mods = self.parse_figure(caption)
		#---defaults
		style = ""
		for key,val in mods.items():
			if key == 'width': style = style + "width:%d"%(int(val*100))+'%;'
			#---! keys for wrap figure stashed here
			elif key in ['nlines','position','wrapw']: pass
			else: raise Exception('[ERROR] not sure how to handle figure mod: %s=%s'%(str(key),str(val)))
		label = extracts[0] if extracts[0] else False
		figure_text_html = '\n'.join([
			'<figure %sclass="figure">'%('id="fig:%s" '%label if label else ''),
			'<a %s></a>'%('name="fig:%s"'%label if label else ''),
			'<img src="%s" style="%s" align="middle">'%(path,style),
			"<figcaption><strong>%s</strong>\n%s"%("@fig:%s"%label if label else "Figure",caption),
			'</figcaption></figure>\n\n',
			])
		return figure_text_html

	def blanker(self,part='body'):
		"""
		Remove anything in the pattern.
		HACKED to only remove markups.
		THIS IS DEPRECATED: make a flag for suppressing comments!
		"""
		#---substitution rules
		for lineno,line in enumerate(self.parts[part]):
			for rule,convert in self.subs_tex.items():
				self.parts['body'][lineno] = re.sub(self.markup_regex,'',self.parts['body'][lineno])

	def bib(self,part='body'):
		"""
		Replace markdown citations with LaTeX citations.
		"""
		#---use re.split and re.findall to iteratively replace references in groups
		for lineno,line in enumerate(self.parts[part]):
			#---! hacking the bibkey some more. see self.bibkey defn
			if re.search('(\[?@[a-zA-Z]+-?[0-9]{4}[a-z]?\s?;?\s?)+\]?',line)!=None:
				refs = re.findall('\[?@(%s)(?:\s\|\Z|\])?'%self.bibkey,line)
				notrefs = re.split('@%s'%self.bibkey,line)
				self.refs.extend(refs)
				#---! cannot start a line with a reference
				newline = list([notrefs[0].rstrip('[')])
				inside_reference = False
				for ii,i in enumerate(notrefs[1:]):
					if inside_reference == False: 
						newline.append('\%s{'%self.citation_type)
						inside_reference = True
					newline.append(refs[ii])
					#---terminate the reference at the end of the line automatically
					#---...this was added because references as the end of a line were not terminating
					#if re.match('^\s*$',i): 
					#	newline.append('}'+i.lstrip(']'))
					#	inside_reference = False
					#---! is this terminating the references? 
					if re.match('^[ \t]*;?[ \t]$',i): 
						#import pdb;pdb.set_trace()
						newline.append(',')
					#---otherwise terminate
					elif inside_reference: 
						newline.append('}'+i.lstrip(']'))
						inside_reference = False
					else: newline.append(i.rstrip('['))
				self.parts[part][lineno] = ''.join(newline)	
