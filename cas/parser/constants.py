#!/usr/bin/python

#---for write_tex_png function
template = r"""
\documentclass[border=2pt]{standalone}
\usepackage{amsmath}
\usepackage{varwidth}
%s
\begin{document}
\begin{varwidth}{\linewidth}
%s
\end{varwidth}
\end{document}
"""

#---convert markdown to figure
figure_text = r"""
\begin{figure}[htbp]
\centering
\includegraphics%s{%s}
\caption{%s%s}
\end{figure}
"""

#---convert markdown to figure
figure_text = r"""
\begin{figure}[htbp]
\centering
\includegraphics%s{%s}
\caption{%s%s}
\end{figure}
"""

#---convert markdown to HTML figure
figure_text_html = """
<figure id="fig:%s" class="figure">
<a name="fig:%s"></a> 
<img src="%s" style="%s" align="middle">\n%s\n
</figure>
"""
