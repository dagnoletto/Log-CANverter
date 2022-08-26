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
MsgCounter = 0

Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing

logfilename = askopenfilename(title = "Select Log File",filetypes = (("LOG Files","*.log"),("all files","*.*"))) 

with open (logfilename, "r",encoding="utf8") as inputfile:
    print("Calculating Total Lines... \n")
    numlines = sum(1 for line in inputfile)
inputfile.close()

with open (logfilename, "r",encoding="utf8") as inputfile:
    print("Filtering messages... \n")

    Source_Address = "[19]{2}" # Filtra pelo endereço (source address) em hex
    PGN = "[FF20]{4}" # Filtra pelo PGN (em hex). Este filtro não considera o DP e o EDP! Ou seja, o EDP e o DP podem chegar com qualquer valor, este filtro é meia boca
    #PGN = "[0-9A-F]{4}" # Quando quiser todos os PGNs, usar este"

    Pattern = "\\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F]{2}" + PGN + Source_Address + ")#([0-9A-F]+)"

    linePattern2 = re.compile(Pattern) # Filtra pelo source address (0x19)
    
    #linePattern2 = re.compile(r"\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F]{6}[19]{2})#([0-9A-F]+)") # Filtra pelo source address (0x19)

    #linePattern2 = re.compile(r"\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F]{2}[FF20]{4}[19]{2})#([0-9A-F]+)") # Filtra pelo source address (0x19) e pelo PGN (0xFF20)

    #Source_Address = Source_Address.removeprefix("[")
    Source_Address = Source_Address.removesuffix("{2}")
    #Source_Address = '_' + Source_Address + '_'

    #PGN = PGN.removeprefix("[")
    PGN = PGN.removesuffix("{4}")
    #PGN = '_' + PGN + '_'

    for row in tqdm(inputfile,desc= "Lines", total = numlines,unit = " Lines"):
        try:
            caninterface = linePattern2.search(row).groups()[1]
            msgidstr = linePattern2.search(row).groups()[2] 

            MsgCounter = MsgCounter + 1
            print("\rLine '%s': '%s'"% (MsgCounter,row[:-1]))


            basename = os.path.splitext(os.path.basename(logfilename))[0]

            filteredfile = str.split(logfilename, basename)

            if basename.find('.') != -1:
                basename = textwrap.shorten( basename, width=basename.find('.'), placeholder='' )  
                
            filteredfile[0] = filteredfile[0] + basename + "_" + PGN + Source_Address + ".log"


            try:
                interfaces.index(caninterface)
            except:
                interfaces.append(caninterface) # Primeira vez chegando aqui, verifica se arquivo existe então remove-o
                if os.path.exists(filteredfile[0]):
                    os.remove(filteredfile[0])

            with open (filteredfile[0], "a",encoding="utf8") as tempinputfile:
                #tempinputfile.seek( 0, 2 )
                #position = tempinputfile.tell()               
                tempinputfile.writelines(row)
                tempinputfile.close

        except:
            linePattern2 = re.compile(Pattern) # somente para ter código aqui e não dar erro

if MsgCounter == 0:
    print("\rNo filter matches")

inputfile.close()
