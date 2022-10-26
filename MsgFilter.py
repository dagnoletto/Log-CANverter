#! /usr/bin/env python3

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

    Source_Address = "0x19" # Node address from which messages will be retrieved

    PGN = "[FF20]{4}" # Filtra pelo PGN (em hex). Este filtro não considera o DP e o EDP! Ou seja, o EDP e o DP podem chegar com qualquer valor, este filtro é meia boca
    #PGN = "[0-9A-F]{4}" # Quando quiser todos os PGNs, usar este"

    print("Picking up messages from %s source address... \n"%Source_Address)
    
    Source_Address = Source_Address.removeprefix("0x")
    Source_Address = '[' + Source_Address[0] + ']' + '[' + Source_Address[1] + ']'

    Pattern = r"\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F]{2}" + PGN + Source_Address + ")#([0-9A-F]+)"

    linePattern2 = re.compile(Pattern)

    PGN = PGN.removesuffix("{4}")

    for row in tqdm(inputfile,desc= "Lines", total = numlines,unit = " Lines"):
        try:
            caninterface = linePattern2.search(row).groups()[1]
            msgidstr = linePattern2.search(row).groups()[2] 

            MsgCounter = MsgCounter + 1
            #print("\rLine '%s': '%s'"% (MsgCounter,row[:-1]))


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
else:
    print("\rMatching lines '%s'"% MsgCounter)

inputfile.close()
