# Introduction

Introduction



Rich is a Python library for writing

rich

text (with color and style) to the terminal, and for displaying advanced content such as tables, markdown, and syntax highlighted code.

Use Rich to make your command line applications visually appealing and present data in a more readable way. Rich can also be a useful debugging aid by pretty printing and syntax highlighting data structures.

Requirements



Rich works with macOS, Linux and Windows.

On Windows both the (ancient) cmd.exe terminal is supported and the new

Windows Terminal

. The latter has much improved support for color and style.

Rich requires Python 3.8.0 and above.

Note

PyCharm users will need to enable “emulate terminal” in output console option in run/debug configuration to see styled output.

Installation



You can install Rich from PyPI with

pip

or your favorite package manager:

pip

install

rich

Add the

-U

switch to update to the current version, if Rich is already installed.

If you intend to use Rich with Jupyter then there are some additional dependencies which you can install with the following command:

pip

install

"rich[jupyter]"

Demo



To check if Rich was installed correctly, and to see a little of what Rich can do, run the following from the command line:

python

-

m

rich

Quick Start



The quickest way to get up and running with Rich is to import the alternative

print

function which takes the same arguments as the built-in

print

and may be used as a drop-in replacement. Here’s how you would do that:

from

rich

import

print

You can then print strings or objects to the terminal in the usual way. Rich will do some basic syntax

highlighting

and format data structures to make them easier to read.

Strings may contain

Console Markup

which can be used to insert color and styles in to the output.

The following demonstrates both console markup and pretty formatting of Python objects:

>>>

print

(

"[italic red]Hello[/italic red] World!"

,

locals

())

This writes the following output to the terminal (including all the colors and styles):

Hello

World!

{

'__annotations__'

:

{}

,

'__builtins__'

:

<

module

'builtins'

(

built-in

)

>

,

'__doc__'

:

None

,

'__loader__'

:

<

class

'_frozen_importlib.BuiltinImporter'

>

,

'__name__'

:

'__main__'

,

'__package__'

:

None

,

'__spec__'

:

None

,

'print'

:

<

function

print at

0x1027fd4c0

>

,

}

If you would rather not shadow Python’s built-in print, you can import

rich.print

as

rprint

(for example):

from

rich

import

print

as

rprint

Continue reading to learn about the more advanced features of Rich.

Rich in the REPL



Rich may be installed in the REPL so that Python data structures are automatically pretty printed with syntax highlighting. Here’s how:

>>>

from

rich

import

pretty

>>>

pretty

.

install

()

>>>

[

"Rich and pretty"

,

True

]

You can also use this feature to try out Rich

renderables

. Here’s an example:

>>>

from

rich.panel

import

Panel

>>>

Panel

.

fit

(

"[bold yellow]Hi, I'm a Panel"

,

border_style

=

"red"

)

Read on to learn more about Rich renderables.

IPython Extension



Rich also includes an IPython extension that will do this same pretty install + pretty tracebacks. Here’s how to load it:

In

[

1

]:

%

load_ext

rich

You can also have it load by default by adding

“rich”

to the

c.InteractiveShellApp.extension

variable in

IPython Configuration

.

Rich Inspect



Rich has an

inspect()

function which can generate a report on any Python object. It is a fantastic debug aid, and a good example of the output that Rich can generate. Here is a simple example:

>>>

from

rich

import

inspect

>>>

from

rich.color

import

Color

>>>

color

=

Color

.

parse

(

"red"

)

>>>

inspect

(

color

,

methods

=

True

)