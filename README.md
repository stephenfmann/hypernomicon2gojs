# Hypernomicon2GoJS

Convert [Hypernomicon](https://sourceforge.net/projects/hypernomicon/) XML to GoJS [Block Editor](https://gojs.net/latest/samples/blockEditor.html) JSON.

## Motivation

Hypernomicon, a tool for maintaining a personal database linking positions and arguments in the philosophy literature, stores entries as XML files.
To visualise logical relationships between philosophical positions and arguments, it is desirable to convert the XML to a format readable by a visualisation tool.

This repository contains Python scripts that translate Hypernomicon's XML into a JSON object readable by the Block Editor of GoJS, an HTML-and-Javascript based visualisation tool.

## How to use

`python convert.py [--input XML_FILEPATH] [--output JSON_FILEPATH] [--html HTML_FILEPATH]`
