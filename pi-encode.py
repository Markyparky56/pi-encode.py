"""
Pi-Encode encodes an input into a series of fragments of Pi
"""

import sys
import json
import enum
import requests
import argparse
from bitstring import ConstBitStream
from os.path import exists
from requests.structures import CaseInsensitiveDict
from string import Template

class InOutMode(enum.IntEnum):
    Encode=0,
    Decode=1

class CharMode(enum.IntEnum):
    Bytes=0
    Ascii=1
    UTF16=2
    UTF32=3
    UTF8=4
    
class Options:
    def __init__(self):
        self.InputFile: ""
        self.OutputFile: ""
        self.Verbose: False
        self.SaveCachedPiToFile: True
        self.SaveCachedFragments: False
        self.TargetFragmentSize: 10
        self.Mode: CharMode.Bytes
        self.InOutMode: InOutMode.Encode
    
    def printOptions(self):
        outputTemplate = Template(
            "InputFile: ${InputFile}\n" +
            "OutputFile: ${OutputFile}\n" +
            "Verbose: ${Verbose}\n" +
            "SaveCachedPiToFile: ${SaveCachedPiToFile}\n" +
            "SaveCachedFragments: ${SaveCachedFragments}\n" +
            "TargetFragmentSize: ${TargetFragmentSize}\n" +
            "Mode: ${Mode}\n" +
            "InOutMode: ${InOutMode}\n"
        )
        params = {
            "InputFile": self.InputFile,
            "OutputFile": self.OutputFile,
            "Verbose": self.Verbose,
            "SaveCachedPiToFile": self.SaveCachedPiToFile,
            "SaveCachedFragments": self.SaveCachedFragments,
            "TargetFragmentSize": self.TargetFragmentSize,
            "Mode": self.Mode,
            "InOutMode": self.InOutMode
        }
        print(outputTemplate.substitute(params))
    
    def setOptions(self, parsedArgs):
        self.InputFile = parsedArgs.input
        self.OutputFile = parsedArgs.OutputFile
        self.Verbose = parsedArgs.Verbose
        self.SaveCachedPiToFile = parsedArgs.CachePi
        self.SaveCachedFragments = parsedArgs.CacheFrags
        self.TargetFragmentSize = parsedArgs.TargetFragSize
        self.Mode = parsedArgs.Mode
        self.InOutMode = parsedArgs.InOutMode
        #self.printOptions()

# API limits to 1000 digits at a time
urlTemplate = Template('http://api.pi.delivery/v1/pi?start=${startIndex}&numberOfDigits=1000')

# Starter character to denote a pi-encoded file
marker = 'π'

# File header template with marker plus the CharMode used to interpret pi digits
headerTemplate = Template("${marker}${encoding}@")

# Template used to encode a fragment as an index and length in pi
fragmentEncodeTemplate = Template("${index}&${length};")

PiCache = {
    "length": 0,
    "digits": ""
}
MyOptions = Options()
    
parser = argparse.ArgumentParser(description="Encode your favourite files in Pi!", prog="Pi-Encode")
parser.add_argument("--version", action="version")
parser.add_argument("input", metavar="InputFile", type=str, help="source file to encode")
parser.add_argument("-o", dest="OutputFile", type=str, help="file to write out encoded result to")
parser.add_argument("-v", dest="Verbose", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--cache-pi", dest="CachePi", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--cache-frags", dest="CacheFrags", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--target-frag-size", dest="TargetFragSize", nargs="?", default=10, type=int)
modeGroup = parser.add_mutually_exclusive_group(required=True)
modeGroup.add_argument("--bytes", dest="Mode", action="store_const", const=CharMode.Bytes, help="interpret pi digits as byte data")
modeGroup.add_argument("--ascii", dest="Mode", action="store_const", const=CharMode.Ascii, help="interpret pi digits as ascii characters")
modeGroup.add_argument("--utf16", dest="Mode", action="store_const", const=CharMode.UTF16, help="interpret pi digits as utf32 characters")
modeGroup.add_argument("--utf32", dest="Mode", action="store_const", const=CharMode.UTF32, help="interpret pi digits as utf16 characters")
modeGroup.add_argument("--utf8" , dest="Mode", action="store_const", const=CharMode.UTF8 , help="interpret pi digits as utf8 characters")
modeGroup = parser.add_mutually_exclusive_group(required=True)
modeGroup.add_argument("--encode", dest="InOutMode", action="store_const", const=InOutMode.Encode, help="Input is some file to encode")
modeGroup.add_argument("--decode", dest="InOutMode", action="store_const", const=InOutMode.Decode, help="Input is some file to decode")

def fetchPiFromIndex(index):
    if (PiCache["length"] > index):
        if MyOptions.Verbose:
            print("Fetching digits at index " + str(index) + " from cache")
        
        # return digits as substring
        return PiCache["digits"][index:1000]
    else:
        if MyOptions.Verbose:
            print("Requested digits from index " + str(index) + " not in cache, requesting from API")
            
        url = urlTemplate.substitute({"startIndex":index})
        headers = CaseInsensitiveDict()
        headers["Accept"] = "application/json"
        resp = requests.get(url, headers=headers)
        
        json = resp.json()
        newDigits = json["content"]
        PiCache["length"] += 1000
        PiCache["digits"] += newDigits
        
        return newDigits

# Reinterpret the string of pi digits as char array
def piToMode(piStr, mode):
    piStrBytes = bytes(piStr, "utf-8") # piStr is utf-8 encoded
    
    # return byte array using different encoding
    if mode == CharMode.Bytes:
        return piStrBytes
    elif mode == CharMode.Ascii:
        return piStrBytes.decode(encoding="ascii")
    elif mode == CharMode.UTF16:
        return piStrBytes.decode(encoding="utf-16")
    elif mode == CharMode.UTF32:
        return piStrBytes.decode(encoding="utf-32")
    elif mode == CharMode.UTF8:
        return piStrBytes.decode(encoding="utf-8")
    
    
def getInputFile(inputFileName):
    if exists(inputFileName):
        return open(inputFileName, "rb")
    else:
        return None

# def getStringBase(mode):
#     if mode == CharMode.Bytes:
        
    
def beginEncode(mode):
    if inputFile := getInputFile(MyOptions.InputFile):
        fileBits = ConstBitStream(inputFile)
        print(fileBits.bin)

def loadCachedPi():
    if MyOptions.Verbose:
        print("Checking for pi.cache file")
        
    if exists("pi.cache"):
        with open("pi.cache", "r") as inCacheFile:
            global PiCache
            PiCache = json.load(inCacheFile)
            if MyOptions.Verbose:
                print("PiCache found and loaded: ")
                print(PiCache)
    else:
        if MyOptions.Verbose:
            print("pi.cache not found")
        
        # No existing cache, pull in the first 10k digits as a starting point
        for i in range(0, 10000, 1000):
            fetchPiFromIndex(i)
        
def saveCachedPi():
    if MyOptions.Verbose:
        print("Saving PiCache to file")
        
    with open("pi.cache", "w") as outCacheFile:
        json.dump(PiCache, outCacheFile)
    
def main(args):
    parsedArgs = parser.parse_args()
    MyOptions.setOptions(parsedArgs)
    
    if MyOptions.Verbose:
        print(parsedArgs)       
    
    loadCachedPi()
    
    if MyOptions.InOutMode == InOutMode.Encode:
        beginEncode(MyOptions.Mode)
    
    #piDigits = fetchPiFromIndex(0)
    #print(piDigits)
    #piAsBytes = piToMode(piJson["content"], MyOptions.Mode)
    #print(piAsBytes)
    
    if (MyOptions.SaveCachedPiToFile):
        saveCachedPi()

if __name__ == "__main__":
    main(sys.argv)
