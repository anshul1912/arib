#!/usr/bin/env python 
# vim: set ts=2 expandtab:
'''
Module: ts2ass
Desc: Extract ARIB CCs from an MPEG transport stream and produce an .ass subtitle file off them.
Author: John O'Neil
Email: oneil.john@gmail.com
DATE: Saturday, May 24th 2014
  
'''
import os
import argparse
import copy
from arib.data_group import next_data_group
from arib.closed_caption import next_data_unit
from arib.closed_caption import StatementBody
import arib.code_set as code_set
import arib.control_characters as control_characters
from arib.ts import next_ts_packet
from arib.ts import next_pes_packet
from arib.ts import PESPacket
from arib.data_group import DataGroup

from arib.ass import ASSFormatter
from arib.ass import ASSFile



def main():
  parser = argparse.ArgumentParser(description='Draw CC Packets from MPG2 Transport Stream file.')
  parser.add_argument('infile', help='Input filename (MPEG2 Transport Stream File)', type=str)
  parser.add_argument('pid', help='Pid of closed caption ES to extract from stream.', type=int)
  args = parser.parse_args()

  pid = args.pid
  infilename = args.infile
  if not os.path.exists(infilename):
    print 'Please provide input Transport Stream file.'
    os.exit(-1)

  #open an Ass file and formatter
  ass_file = ASSFile(infilename+'.ass')
  ass = ASSFormatter(ass_file)

  #CC data is not, in itself timestamped, so we've got to use packet info
  #to reconstruct the timing of the closed captions (i.e. how many seconds into
  #the file are they shown?)
  initial_timestamp = 0
  pes_packet = None
  pes = []
  elapsed_time_s = 0
  for packet in next_ts_packet(infilename):
    #always process timestamp info, regardless of PID
    if packet.adapatation_field() and packet.adapatation_field().PCR():
      current_timestamp = packet.adapatation_field().PCR()
      initial_timestamp = initial_timestamp or current_timestamp
      delta = current_timestamp - initial_timestamp
      elapsed_time_s = float(delta)/90000.0

    #if this is the stream PID we're interestd in, reconstruct the ES
    if packet.pid() == pid:
      if packet.payload_start():
        pes = copy.deepcopy(packet.payload())
      else:
        pes.extend(packet.payload())
      pes_packet = PESPacket(pes)
      

      #if our packet is fully formed (payload all present) we can parse its contents
      if pes_packet.length() == (pes_packet.header_size() + pes_packet.payload_size()):
        
        data_group = DataGroup(pes_packet.payload())

        if not data_group.is_management_data():
        #We now have a Data Group that contains caption data.
        #We take out its payload, but this is further divided into 'Data Unit' structures
          caption = data_group.payload()
          #iterate through the Data Units in this payload via another generator.
          for data_unit in next_data_unit(caption):
            #we're only interested in those Data Units which are "statement body" to get CC data.
            if not isinstance(data_unit.payload(), StatementBody):
              continue

            ass.format(data_unit.payload().payload(), elapsed_time_s)
            #okay. Finally we've got a data unit with CC data. Feed its payload to the custom
            #formatter function above. This dumps the basic text to stdout.
            #cc = formatter(data_unit.payload().payload(), elapsed_time_s)
            #if cc:
              #according to best practice, always deal internally with UNICODE, and encode to
              #your encoding of choice as late as possible. Here, i'm encoding as UTF-8 for
              #my command line.
              #DECODE EARLY, ENCODE LATE
              #print(cc.encode('utf-8'))
    

if __name__ == "__main__":
  main()
