#! /usr/bin/env python3
# Split a single .log file into the number of interfaces the log file has inside. For example, if there are
# recorded messages from interface can0 and interface can1, this routine will create two new .log files including 
# the messages from each interface.

import os
from itertools import compress
from tqdm import tqdm
import re
import textwrap
from tkinter import Message, Tk
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename

interfaces = []

Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing

logfilename = askopenfilename(title = "Select Log File",filetypes = (("LOG Files","*.log"),("all files","*.*"))) 

with open (logfilename, "r",encoding="utf8") as inputfile:
    print("Calculating Total Lines... \n")
    numlines = sum(1 for line in inputfile)
inputfile.close()

with open (logfilename, "r",encoding="utf8") as inputfile:
    print("Splitting interfaces... \n")
    linePattern2 = re.compile(r"\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F#]{3}|[0-9A-F#]{8})#([0-9A-F]+)")
    for row in tqdm(inputfile,desc= "Lines", total = numlines,unit = " Lines"):
        try:
            caninterface = linePattern2.search(row).groups()[1]

            try:
                interfaces.index(caninterface)
            except:
                interfaces.append(caninterface)

            basename = os.path.splitext(os.path.basename(logfilename))[0]

            splitfile = str.split(logfilename, basename)

            if basename.find('.') != -1:
                basename = textwrap.shorten( basename, width=basename.find('.'), placeholder='' )  
                
            splitfile[0] = splitfile[0] + basename + "_" + caninterface + ".log"

            with open (splitfile[0], "a",encoding="utf8") as tempinputfile:
                #tempinputfile.seek( 0, 2 )
                #position = tempinputfile.tell()               
                tempinputfile.writelines(row)
                tempinputfile.close

        except:
            print("invalidated line observed: '%s'"% (row[:-1]))
inputfile.close()
