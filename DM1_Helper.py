#! /usr/bin/env python3

import cantools
import os
from itertools import compress
from tqdm import tqdm
import re
import textwrap
from tkinter import Message, Tk
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename

Number_of_bytes = 0
Number_of_packets = 0
PGN_Transfer = 0
Next_Packet = 0
LargeMsgBytes = []
DM1_id_Transfer = 0

def generate_file_name():
    basename = os.path.splitext(os.path.basename(logfilename))[0]
    outputfile = str.split(logfilename, basename)

    if basename.find('.') != -1:
        basename = textwrap.shorten( basename, width=basename.find('.'), placeholder='' )  
                
    outputfile[0] = outputfile[0] + basename + "_[DM1]" + "[" + str(hex(Source_Address)).removeprefix("0x") + "]" + ".log"
    return outputfile[0]

def save_row(row):

    file = generate_file_name()

    with open (file, "a",encoding="utf8") as tempinputfile:
        #tempinputfile.seek( 0, 2 )
        #position = tempinputfile.tell()               
        tempinputfile.writelines(row)
        tempinputfile.close



interface = []
MsgCounter = 0

Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing

logfilename = askopenfilename(title = "Select Log File",filetypes = (("LOG Files","*.log"),("all files","*.*"))) 

with open (logfilename, "r",encoding="utf8") as inputfile:
    print("Calculating Total Lines... \n")
    numlines = sum(1 for line in inputfile)
inputfile.close()

with open (logfilename, "r",encoding="utf8") as inputfile:

    inputAddr = "0x19"

    print("Picking up DM1 messages from %s source address... \n"%inputAddr)

    Source_Address = int( inputAddr.removeprefix("0x"), 16 ) # Filtra pelo endereço (source address) em hex

    Pattern = "\\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F#]{3}|[0-9A-F#]{8})#([0-9A-F]+)"

    linePattern2 = re.compile(Pattern) # Filtra pelo source address (0x19)

    for row in tqdm(inputfile,desc= "Lines", total = numlines,unit = " Lines"):
        try:
            caninterface = linePattern2.search(row).groups()[1]
            msgidstr = linePattern2.search(row).groups()[2] 
            msgdatastr = linePattern2.search(row).groups()[3]

            msgdatabytes = []

            for i in range( int(len(msgdatastr)/2) ):
                msgdatabytes.append( int( msgdatastr[i * 2] + msgdatastr[i * 2 + 1], 16 ) )

            msgid = int(msgidstr, 16)

            J1939_header = cantools.j1939.frame_id_unpack(msgid)

            DM1_id = cantools.j1939.frame_id_pack( 6, 0, 0, 254, 202, Source_Address )
            TP_CM_id = cantools.j1939.frame_id_pack( 7, 0, 0, 236, 255, Source_Address )
            TP_DT_id = cantools.j1939.frame_id_pack( 7, 0, 0, 235, 255, Source_Address )

            if J1939_header.source_address == Source_Address:

                try:
                    interface.index(caninterface)
                except:
                    if len(interface) == 0:       
                        interface.append(caninterface)                  
                        file = generate_file_name()
                        if os.path.exists(file): # Primeira vez chegando aqui, verifica se arquivo existe então remove-o
                            os.remove(file)


            if caninterface == interface[0]:

                if cantools.j1939.pgn_from_frame_id(msgid) == cantools.j1939.pgn_from_frame_id(DM1_id): 
                    save_row(row)               
                elif cantools.j1939.pgn_from_frame_id(msgid) == cantools.j1939.pgn_from_frame_id(TP_CM_id): 
                    
                    ControlByte = msgdatabytes[0]

                    #if   ControlByte == 16:     # TP.CM_RTS
                       
                    #elif ControlByte == 17:     # TP.CM_CTS

                    #elif ControlByte == 19:     # TP.CM_EndOfMsgACK 

                    if ControlByte == 32:        # TP.CM_BAM   
                        Number_of_bytes = ( msgdatabytes[2] << 8 ) | msgdatabytes[1]
                        Number_of_packets = msgdatabytes[3]
                        PGN_Transfer = ( msgdatabytes[7] << 8 ) | ( msgdatabytes[6] << 8 ) | msgdatabytes[5]
                        DM1_id_Transfer = cantools.j1939.frame_id_pack( J1939_header.priority, 0, 0, 254, 202, Source_Address )
                        Next_Packet = 1
                        LargeMsgBytes.clear()
                    #elif ControlByte == 255:    # TP.Conn_Abort   
                elif cantools.j1939.pgn_from_frame_id(msgid) == cantools.j1939.pgn_from_frame_id(TP_DT_id):
                    if msgdatabytes[0] == Next_Packet:
                        if Number_of_bytes >= 7:
                            numbytesToload = 7
                        else:
                            numbytesToload = Number_of_bytes
                        for i in range( numbytesToload ):
                            LargeMsgBytes.append( msgdatabytes[i + 1] )
                        Number_of_bytes = Number_of_bytes - numbytesToload

                        if (Number_of_bytes == 0) and (Next_Packet == Number_of_packets): # Transfer ended row.
                            newid = (str(hex(DM1_id_Transfer)).removeprefix("0x")).upper()
                            newdata =''
                            for i in range( len(LargeMsgBytes) ):
                                newdata = newdata + ( (str(hex(LargeMsgBytes[i])).removeprefix("0x")).upper() )
                            LargeMsgBytes.clear()
                            row = str(row).replace( msgidstr, newid )
                            row = str(row).replace( msgdatastr, newdata )
                            save_row(row) # Atualizar o row com os dados
                            Next_Packet = 0
                        else:
                            Next_Packet = Next_Packet + 1
                #else:
                    #MsgCounter = MsgCounter + 1
                    #print("\rLine '%s': '%s'"% (MsgCounter,row[:-1]))

            

        except:
            linePattern2 = re.compile(Pattern) # somente para ter código aqui e não dar erro

if MsgCounter == 0:
    print("\rNo filter matches")
else:
    print("\rMatching lines '%s'"% MsgCounter)

inputfile.close()
