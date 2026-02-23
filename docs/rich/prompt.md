# Prompt

Prompt



Rich has a number of

Prompt

classes which ask a user for input and loop until a valid response is received (they all use the

Console API

internally). Here’s a simple example:

>>>

from

rich.prompt

import

Prompt

>>>

name

=

Prompt

.

ask

(

"Enter your name"

)

The prompt may be given as a string (which may contain

Console Markup

and emoji code) or as a

Text

instance.

You can set a default value which will be returned if the user presses return without entering any text:

>>>

from

rich.prompt

import

Prompt

>>>

name

=

Prompt

.

ask

(

"Enter your name"

,

default

=

"Paul Atreides"

)

If you supply a list of choices, the prompt will loop until the user enters one of the choices:

>>>

from

rich.prompt

import

Prompt

>>>

name

=

Prompt

.

ask

(

"Enter your name"

,

choices

=

[

"Paul"

,

"Jessica"

,

"Duncan"

],

default

=

"Paul"

)

By default this is case sensitive, but you can set

case_sensitive=False

to make it case insensitive:

>>>

from

rich.prompt

import

Prompt

>>>

name

=

Prompt

.

ask

(

"Enter your name"

,

choices

=

[

"Paul"

,

"Jessica"

,

"Duncan"

],

default

=

"Paul"

,

case_sensitive

=

False

)

Now, it would accept “paul” or “Paul” as valid responses.

In addition to

Prompt

which returns strings, you can also use

IntPrompt

which asks the user for an integer, and

FloatPrompt

for floats.

The

Confirm

class is a specialized prompt which may be used to ask the user a simple yes / no question. Here’s an example:

>>>

from

rich.prompt

import

Confirm

>>>

is_rich_great

=

Confirm

.

ask

(

"Do you like rich?"

)

>>>

assert

is_rich_great

The Prompt class was designed to be customizable via inheritance. See

prompt.py

for examples.

To see some of the prompts in action, run the following command from the command line:

python

-

m

rich

.

prompt