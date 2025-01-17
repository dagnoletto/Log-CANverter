#! /usr/bin/env python3

import cantools
import os
from itertools import compress
from tqdm import tqdm
import re
import csv
import textwrap
from tkinter import Message, Tk
from tkinter.filedialog import askopenfilename
from tkinter.filedialog import asksaveasfilename
from collections import namedtuple
import bitstruct

Number_of_bytes = 0
Number_of_packets = 0
PGN_Transfer = 0
Next_Packet = 0
LargeMsgBytes = []
DM1_id_Transfer = 0
DTCs_Found = []

DTC_Lamp = namedtuple('DTC_Lamp',
                     [
		                'PRL', # Protect lamp
		                'AWL', # Amber warning lamp
		                'RSL', # Red stop lamp
		                'MIL', # Malfunction indicator lamp
		                'FLASH_PRL', # Flash protect lamp
		                'FLASH_AWL', # Flash amber warning lamp
		                'FLASH_RSL', # Flash red stop lamp
		                'FLASH_MIL', # Flash malfunction indicator lamp
                     ])


DTC = namedtuple('DTC',
                     [
                         'SPN',
                         'FMI',
                         'CM',
                         'OC',
                     ])

def decode_DTC(DM1_Data):

    DTC_List = []
    DTC_List.clear()

    if len(DM1_Data) <= 8:
        number_of_DTCs = 1 
    else:
        number_of_DTCs = int( ( len(DM1_Data) - 2 )/4 ) # subtract lamp status

    byte_index = 2  # first DTC position

    Lamp = DTC_Lamp( DM1_Data[0] & 0x03,
                     ( DM1_Data[0] >> 2 ) & 0x03, 
                     ( DM1_Data[0] >> 4 ) & 0x03,
                     ( DM1_Data[0] >> 6 ) & 0x03,
                     DM1_Data[1] & 0x03,
                     ( DM1_Data[1] >> 2 ) & 0x03, 
                     ( DM1_Data[1] >> 4 ) & 0x03,
                     ( DM1_Data[1] >> 6 ) & 0x03,
                     )

    for i in range(number_of_DTCs): 
        spn = DM1_Data[ byte_index ] | ( DM1_Data[ byte_index + 1 ] << 8 ) | ( ( DM1_Data[ byte_index + 2 ] & 0xE0 ) << 11 )
        fmi = DM1_Data[ byte_index + 2 ] & 0x1F
        cm = ( DM1_Data[ byte_index + 3 ] & 0x80 ) >> 7
        oc = ( DM1_Data[ byte_index + 3 ] & 0x7F )    

        dtc_temp = DTC(spn, fmi, cm, oc) 

        DTC_List.append( dtc_temp )
        byte_index = byte_index + 4                            
    
    return (Lamp, DTC_List)

def check_DTCs(List):

    for i in range( len(List) ):
        search_dtc = List[i]

        dtc_found_flag = 0

        size = len(DTCs_Found)

        for a in range( size ):
            if ( search_dtc.SPN == DTCs_Found[a].SPN ) and ( search_dtc.FMI == DTCs_Found[a].FMI ):
                dtc_found_flag = 1
                break

        if ( dtc_found_flag == 0 ) and ( search_dtc.SPN != 0 ): # Considera-se que SPN = 0 seja "sem falhas"
            DTCs_Found.append( search_dtc )


def generate_file_name():
    basename = os.path.splitext(os.path.basename(logfilename))[0]
    outputfile = str.split(logfilename, basename)

    if basename.find('.') != -1:
        basename = textwrap.shorten( basename, width=basename.find('.'), placeholder='' )  
                
    outputfile[0] = outputfile[0] + basename + "_[DM1]" + inputAddr + ".log"
    return outputfile[0]

def save_row(row):

    file = generate_file_name()

    with open (file, "a",encoding="utf8") as tempinputfile:
        #tempinputfile.seek( 0, 2 )
        #position = tempinputfile.tell()               
        tempinputfile.writelines(row)
        tempinputfile.close



interface = []

Tk().withdraw() # we don't want a full GUI, so keep the root window from appearing

logfilename = askopenfilename(title = "Select Log File",filetypes = (("LOG Files","*.log"),("all files","*.*"))) 

with open (logfilename, "r",encoding="utf8") as inputfile:
    print("\r\nCalculating Total Lines... \n")
    numlines = sum(1 for line in inputfile)
inputfile.close()

with open (logfilename, "r",encoding="utf8") as inputfile:

    inputAddr = "0x19" # Node address from which messages will be retrieved

    print("Picking up DM1 messages from %s source address... \n"%inputAddr)

    Source_Address = int( inputAddr.removeprefix("0x"), 16 ) 

    inputAddr = inputAddr.removeprefix("0x")
    inputAddr = '[' + inputAddr[0] + ']' + '[' + inputAddr[1] + ']'

    Pattern = r"\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F#]{3}|[0-9A-F#]{8})#([0-9A-F]+)"
    Pattern = r"\((\d+.\d+)\)\s+([^\s]+)\s+([0-9A-F#]{3}|[0-9A-F#]{6}" + inputAddr + ")#([0-9A-F]+)"

    linePattern2 = re.compile(Pattern) 

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
                        lamp, dtcs = decode_DTC(msgdatabytes)
                        check_DTCs(dtcs)
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
                                barray = bytearray(LargeMsgBytes)
                                newdata = (barray.hex()).upper()
                                lamp, dtcs = decode_DTC(LargeMsgBytes)    
                                check_DTCs(dtcs)
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
inputfile.close()

if len(DTCs_Found) == 0:
    print("\rNo active DTCs found!")
else:
    print("\r\nDTCs found:\n")
    for i in range( len(DTCs_Found) ):
        print("\rSPN: %d FMI: %d CM: %d OC: %d" % (DTCs_Found[i].SPN, DTCs_Found[i].FMI, DTCs_Found[i].CM, DTCs_Found[i].OC) )


# AQUI TRATA DA GERAÇÃO DO ARQUIVO EXCELL!


displaySignalList = []

firstfile = generate_file_name()

secondfile = firstfile.removesuffix(".log")  
tempfile = secondfile + ".temp"      
secondfile += ".csv"

if os.path.exists(tempfile): # Primeira vez chegando aqui, verifica se arquivo existe então remove-o
    os.remove(tempfile)    
if os.path.exists(secondfile): # Primeira vez chegando aqui, verifica se arquivo existe então remove-o
    os.remove(secondfile)  

with open (firstfile, "r",encoding="utf8") as inputfile:
    print("Opening %s \n" % firstfile)
    print("Calculating Total Lines... \n")
    numlines = sum(1 for line in inputfile)
inputfile.close()

with open (firstfile, "r",encoding="utf8") as inputfile:

    with open(tempfile, "w", newline='') as logfile:

        writecsv = csv.writer(logfile,quoting=csv.QUOTE_NONE, delimiter=";")

        displaySignalList.clear()

        displaySignalList.append("Time")
        displaySignalList.append("MIL")
        displaySignalList.append("RSL")
        displaySignalList.append("AWL")
        displaySignalList.append("PRL")
        displaySignalList.append("Flash_MIL")
        displaySignalList.append("Flash_RSL")
        displaySignalList.append("Flash_AWL")
        displaySignalList.append("Flash_PRL")        

        for i in range( len(DTCs_Found) ):
            spn_fmi = "SPN " + str(DTCs_Found[i].SPN) + " " + "FMI " + str(DTCs_Found[i].FMI)
            displaySignalList.append( spn_fmi )

        writecsv.writerow(displaySignalList)

        linePattern = re.compile(r"\((\d+.\d+)\)\s+[^\s]+\s+([0-9A-F#]{3}|[0-9A-F#]{8})#([0-9A-F]+)")

        for row in tqdm(inputfile,desc= "Lines", total = numlines,unit = " Lines"):
            try:

                tokens = linePattern.search(row).groups()
                timestamp = float(tokens[0])
                arbitration_id = int(tokens[1],16)
                msgdatabytes = bytearray.fromhex(tokens[2])

                DM1_id = cantools.j1939.frame_id_pack( 6, 0, 0, 254, 202, 0 )
                if cantools.j1939.pgn_from_frame_id(arbitration_id) == cantools.j1939.pgn_from_frame_id(DM1_id): 
                    lamp, dtcs = decode_DTC(msgdatabytes)
                    Values = []

                    Values.append(str(timestamp).replace(".",",")) # Time
                    Values.append(lamp.MIL) 
                    Values.append(lamp.RSL) 
                    Values.append(lamp.AWL) 
                    Values.append(lamp.PRL) 

                    Values.append(lamp.FLASH_MIL) 
                    Values.append(lamp.FLASH_RSL) 
                    Values.append(lamp.FLASH_AWL)
                    Values.append(lamp.FLASH_PRL)  

                    for i in range( len(DTCs_Found) ):
                        dtc_active = 0
                        for a in range ( len(dtcs) ):
                            if ( DTCs_Found[i].SPN == dtcs[a].SPN ) and ( DTCs_Found[i].FMI == dtcs[a].FMI ):
                                dtc_active = 1
                                break
                        Values.append(dtc_active)                                     

                    writecsv.writerow(Values)
            except:
                print("invalidated line observed: '%s'"% (row[:-1]))
    logfile.close()
inputfile.close()

with open(tempfile, "r") as inputfile:
    with open(secondfile, "w", newline='') as logfile:
        reader = csv.reader(inputfile, delimiter = ';', quotechar = '"')
        writer = csv.writer(logfile,quoting=csv.QUOTE_NONE, delimiter=";")
        for row in tqdm(reader):
            writer.writerow(row)
    logfile.close()
inputfile.close()
os.remove(tempfile)

