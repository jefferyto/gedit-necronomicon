# Necronomicon, a plugin for gedit #

Reopen recently-closed files ("undo close tab")  
<https://github.com/jefferyto/gedit-necronomicon>  
v0.1.1

All bug reports, feature requests and miscellaneous comments are welcome
at the [project issue tracker][].

## No Longer Maintained ##

Since gedit 3.12 added the ability to reopen recently-closed tabs, this
plugin is no longer necessary and will not receive any new updates.

## Requirements ##

This plugin requires gedit 3.

## Installation ##

1.  Download the source code (as [zip][] or [tar.gz][]) and extract.
2.  Copy the `necronomicon` folder and the appropriate `.plugin` file
    into `~/.local/share/gedit/plugins` (create if it does not exist):
    *   For gedit 3.6 and earlier, copy `necronomicon.plugin.python2`
        and rename to `necronomicon.plugin`.
    *   For gedit 3.8 and later, copy `necronomicon.plugin`.
3.  Restart gedit, select **Edit > Preferences** (or
    **gedit > Preferences** on Mac), and enable the plugin in the
    **Plugins** tab.

## Usage ##

The **File > Recently Closed** sub-menu contains the list of
recently-closed files. To reopen one of these files, select the
corresponding menu item.

<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>O</kbd> will also reopen the most
recently closed file.

## Development ##

The code in `necronomicon/utils` comes from [python-gtk-utils][];
changes should ideally be contributed to that project, then pulled back
into this one with `git subtree pull`.

## Credits ##

Inspired by:

*   [Tabs extend][] by Éverton Ribeiro
*   the gedit recent files menu and External tools plugin

## License ##

Copyright &copy; 2013 Jeffery To <jeffery.to@gmail.com>

Available under GNU General Public License version 3


[project issue tracker]: https://github.com/jefferyto/gedit-necronomicon/issues
[zip]: https://github.com/jefferyto/gedit-necronomicon/archive/master.zip
[tar.gz]: https://github.com/jefferyto/gedit-necronomicon/archive/master.tar.gz
[python-gtk-utils]: https://github.com/jefferyto/python-gtk-utils
[Tabs extend]: https://code.google.com/p/gedit-tabsextend/
