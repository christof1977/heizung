#!/bin/bash

env=env/bin/python3
pydocs=env/bin/pydoc-markdown

files=( "steuerung" )

if test -f "$pydocs"; then
	echo "pydoc-markdown available ... continuing"
else
	$env -m pip install pydoc-markdown
fi

for file in "${files[@]}"
do
   : 
   $pydocs -p $file --render-toc > $file.md
done


