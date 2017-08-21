---

title: Cassette Demonstration
images: .

>abstract:
This markdown document demonstrates all of the features
available in the cassette. 

authors: John McScience

authors @article: \author{Alternate Name McScience, Ph.D.}

>moreheader:
\usepackage{xspace}

~alias:
  HTML: "`HTML`"
  PDF: "`PDF`"

write_equation_images: true

! change "article" to "true" to render in TeX
article: false

vecbold: true

---

**Note!** If you have ~\LaTeX\xspace|$\rm\LaTeX$~ installed, set `article: true` flag in the header of `demo.md` and run `make` to compile this to a PDF as well.

# Concept

Cassettes are small sets of codes that make it easy to write, share, revise, and remember your academic documents.

!figure: icon
./cas/sources/tiler/cassette.png
{width=0.35}
What a sweet logo! It looks just like an audio cassette inexplicably printing a written document. That the word "cassette" is derived from the diminutive of the French *casse* for *case*. These codes are a "small case for academic documents".

!figure: icon_again
./cas/sources/tiler/cassette.png
{width=0.35}
Repeated.

# Formats {#sec:formats}

Cassette supports both ~\LaTeX\xspace|$\rm\LaTeX$~ and HTML formats. It receives user commans exclusively through the `make` command. By default, every document is rendered to an HTML document which serves as the `make` target. Latex commands are rendered in HTML with `[MathJax](https://www.mathjax.org/)` --- the only caveat is that serving the resulting HTML files over an `http` connection will require users to authorize the use of the `MathJax` server, otherwise they will be looking at the `TeX` source. Only equations will be rendered with `TeX`, however the cassette-inflected markdown syntax covers most of the most popular syntax available in a `TeX` document anyway.

!figure: icon_a_third
./cas/sources/tiler/cassette.png
{width=0.35}
Repeated2.

# Features

Since the cassette code unifies several important document-processing functionalities in one place, we will describe them in no particular order. The purpose of the code is to meet several needs at once without installing new packages. Only python is required, but a solid texlive distribution makes it possible to render more professional articles.

1. Write documents in markdown that strongly resembles the most common markdown flavors (however [there is no formal standard](https://en.wikipedia.org/wiki/Markdown)) and renders the same source to different formats *without user intervention or specification*.
1. Render documents very quickly in readable HTML.
1. Render documents for posterity in one of many PDF formats, some of which are specifically designed for journal submission, and all of which provide a set of raw `TeX` files for easy compiling on other systems.
1. Include bibliographic references from a `bibtex` file with a minimal syntax.
1. Remember previous drafts and text without drowning in rendudant copies of older versions of the document. For this we track documents using a per-sentence `git` repository.
1. Retrieve large images from `ssh` destinations.
1. Render images (and video snapshots) to an HTML gallery which can be served with the cassette to create a simple static site for your collaborators.

## Latex equations

You can use inline equations with dollar-notation e.g. $a=b$. You can also write display equations.

$$
\begin{split}
\langle \mathcal{H}_{{\rm el}} \rangle &= \frac{A}{2} \sum_{{q}} \left\{ \kappa \left[ {q}^4  \langle {h}_{{q}}^{2} \rangle + 2 {q}^2 \langle {h}_{\vec{q}} C_{0,\vec{q}} \rangle + \langle C_{0,\mathbf{q}}^{2} \rangle \right] + \gamma {q^2} \langle {h}_{{q}}^{2} \rangle \right\} \\
\end{split}
$$ {#eq:twentythree} 

## Header material {#sec:header}

The markdown header (the part that preceeds the first triple-dash characters) contains instructions for how to render the document. It expects to find one of three kinds of entries.

1. Single-line key-value pairs which can encode strings or true-false booleans (regardless of capitalization).
2. Multi-line blocks delimited with `>name:` which terminate on `...` or a double newline. These blocks are stripped of newlines and superfluous spacing to form paragraphs of text. They may also include TeX code which is earmarked for a particular LaTeX template by appending e.g. `>name @style:` entries to the name. The `@` prefix may also be used on single-line entries. This feature is the most useful when including specific author lists or significance text for certain LaTeX templates.
3. Multi-line `yaml` dictionaries named via `~name:` which also terminate on `...` or a double newline. 

## Errors

Undefined references get some nice styling. See section @sec:nowhere. Even if you omit a bibliography in the header material, you can still use author references, which are still visible in the PDF format. @Einstein-1917 References like that one will not be processed at all in HTML, and hence retain the prefixed [arobase](https://en.wikipedia.org/wiki/At_sign#Names_in_other_languages). If you choose not to use cassette's internal referencing, you can also use LaTeX ref characters for that format only. We protect against undefined references like \ref{this one} by bolding them in red in LaTeX and adding curly braces for HTML.

# Validation

This document serves to validate many (perhaps all) of the features in cassette. The following list describes many features which are not demonstrated elsewhere in the document.

1. @sec:formats uses the ~\LaTeX\xspace|LaTeX~ logo, which must be rendered separately for both `TeX` and `HTML` formats. This is accomplished with a tilde-bar syntax. Most markdown annotations seek to avoid this *either-or* use case, but sometimes it is necessary.
1. Every usage of the term "HTML" comes in monospace, but this happens automatically. Any `word` can be rendered in monospace by using backticks, however HTML receives backticks automatically via an `alias` sub-dictionary in the header material. The sub-dictionary is written in `yaml` whose name is prefixed by a tilde. The dictionary ends on either a triple-dot ("...") or a double newline (as with the multi-line header blocks). You can also specify the aliases in a single `dispatch.yaml` file. The aliases should be written as regex substitutions, and are applied to the whole document.
1. You can write numbered lists without the correct ordering.
1. Try using the triple dash --- it will produce an [em dash](http://www.thepunctuationguide.com/em-dash.html) character.
1. The `moreheader` command adds latex commands before the document begins (this command is template-specific).
1. You can link to figures, for example @fig:icon.
1.  \ref{oops}


# Words of caution {#sec:caution}

**Nesting syntax.** There is generally no fixed order of precedence for some of the rules. Some items will be rendered differently depending on the level of nesting for the delimiters, for example, contrast `[[Hello]]` (monospace outside highlight) with [[`Hello`]] (comment outside monospace via backticks). Where possibly, the code 

[[HERE ARE SOME EXAMPLES]] `[Monospace](https://en.wikipedia.org/wiki/Monospaced_font)` links work inside backticks, and [`tother`](https://en.wiktionary org/wiki/tother#English) way around.

Also, aliasing a phrase, and then annotating it will often create a redundancy in the source, with somewhat unpredicatable options. Your best bet is to use either an alias or the correct syntax.

# Changelog

## Un-versioned changes

The following changes were made in the home stretch before attaching a version number.

1. Since HTML lacks the section numbering scheme typically used in latex documents, we use the latex-style label in the link (previously this was only a placeholder).
1. Added `moreheader` to the content block. It adds additional latex commands after the header (this command may be be customized to specific latex templates).
1. Minor changes in several places to accomodate python 3. There are a few major changes which are important: (1) cast dictionary member function return values to list because they are now generators, (2) cast arguments to the regex library as strings because assumes some syntax is bytecode, and of course (3) print must be a function.
1. Added YAML parsing to the header material (see @sec:header).
1. Fixed some regexes that were causing problems at the end of the document. This is a nice feature of regex: you can use `\\Z` to indicate the end of a string, even when performing multiline searches.
1. Still no version number ca 14 May 2017 but we made a few updates. Reworked the `write_html` function to prevent the problem whereby figure names were incorrectly replaced such that names with different endings would get prematurely substituted. This was easily solved with a greedy search. The author's regex understanding was mature a while ago; knowing the tricks does not mean you are good at *using* them, however. In the course of fixing the figure regex replacements (which were always working correctly in LaTex, thanks to its stricter scoping rules than my HTML implementations), I also fixed the problem whereby figure references in parentheses were not replaced with links.
1. Added two sections to the "article" LaTeX template that causes undefined citations via `citex` to be written as monospace keys in the document. This means you can use references without a bibliography, and they are still relatively readable. Also added a method that colors undefined `\ref` in red, and braces them in HTML in case users want to use LaTeX references natively. Finally, citations dangling at the end of a paragraph were causing substitution errors which were fixed.

## Needed upgrades

Incoming:

1. Complete nesting tests in the caution section.
1. Interchangable CSS files for the HTML version (currently only headers are interchangeable).
1. Syntax highlighting.
1. Test syntax highlighting via header material (dispatch aliases).
1. Document the equation writer and specify that it only works when you make a PDF.
1. A regex escape syntax (and more broadly, perhaps consider the question of Turing completeness) so that you can use e.g. an underscore in the text. Also apply this to the regex omega-delimiter above.
1. Consider adding code execution in python, which is the native processor anyway.
1. Figure out why you need three compiles to get the comments into PDF documents.
1. Monospace must be bolder or possibly high-lit in latex because it is not visible enough.
1. Figure-naming regex is generally terrible (try: "area" and "area underscore monolayer" to watch it fail). 
1. For some reason you cannot do a triple-hash header followed immediately by a list with latex equations in it. This is a possible mis-diagnosis because it is so absurd.
1. Consolidate changes from `write-ptdins`.
1. Red undefinied references from latex-in-markdown to latex look good but it needs to also do something in HTML?
1. Reference at the end of a section before a header and without a period will cause errors in pdflatex.

End enumerate! 
