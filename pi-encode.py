"""
Pi-Encode encodes an input into a series of fragments of Pi
"""

import sys
import json
import enum
import codecs
import requests
import argparse
#from bitstring import ConstBitStream
from os.path import exists
from requests.structures import CaseInsensitiveDict
from string import Template

class InOutMode(enum.IntEnum):
    Encode=0,
    Decode=1

# class CharMode(enum.IntEnum):
#     Bytes=0
#     Ascii=1
#     UTF16=2
#     UTF32=3
#     UTF8=4
    
class Options:
    def __init__(self):
        self.InputFile: ""
        self.OutputFile: ""
        self.Verbose: False
        self.SaveCachedPiToFile: True
        self.SaveCachedFragments: False
        self.TargetFragmentSize: 10
        #self.Mode: CharMode.Bytes
        self.InOutMode: InOutMode.Encode
    
    def printOptions(self):
        outputTemplate = Template(
            "InputFile: ${InputFile}\n" +
            "OutputFile: ${OutputFile}\n" +
            "Verbose: ${Verbose}\n" +
            "SaveCachedPiToFile: ${SaveCachedPiToFile}\n" +
            "SaveCachedFragments: ${SaveCachedFragments}\n" +
            "TargetFragmentSize: ${TargetFragmentSize}\n" +
            #"Mode: ${Mode}\n" +
            "InOutMode: ${InOutMode}\n"
        )
        params = {
            "InputFile": self.InputFile,
            "OutputFile": self.OutputFile,
            "Verbose": self.Verbose,
            "SaveCachedPiToFile": self.SaveCachedPiToFile,
            "SaveCachedFragments": self.SaveCachedFragments,
            "TargetFragmentSize": self.TargetFragmentSize,
            #"Mode": self.Mode,
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
        #self.Mode = parsedArgs.Mode
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
PiFragmentCache = {}
MyOptions = Options()
    
parser = argparse.ArgumentParser(description="Encode your favourite files in Pi!", prog="Pi-Encode")
parser.add_argument("--version", action="version")
parser.add_argument("input", metavar="InputFile", type=str, help="source file to encode")
parser.add_argument("-o", dest="OutputFile", type=str, help="file to write out encoded result to")
parser.add_argument("-v", dest="Verbose", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--cache-pi", dest="CachePi", action=argparse.BooleanOptionalAction, default=True)
parser.add_argument("--cache-frags", dest="CacheFrags", action=argparse.BooleanOptionalAction, default=False)
parser.add_argument("--target-frag-size", dest="TargetFragSize", nargs="?", default=10, type=int)
# binary output mode?
# modeGroup = parser.add_mutually_exclusive_group(required=True)
# modeGroup.add_argument("--bytes", dest="Mode", action="store_const", const=CharMode.Bytes, help="interpret pi digits as byte data")
# modeGroup.add_argument("--ascii", dest="Mode", action="store_const", const=CharMode.Ascii, help="interpret pi digits as ascii characters")
# modeGroup.add_argument("--utf16", dest="Mode", action="store_const", const=CharMode.UTF16, help="interpret pi digits as utf32 characters")
# modeGroup.add_argument("--utf32", dest="Mode", action="store_const", const=CharMode.UTF32, help="interpret pi digits as utf16 characters")
# modeGroup.add_argument("--utf8" , dest="Mode", action="store_const", const=CharMode.UTF8 , help="interpret pi digits as utf8 characters")
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
    
def getPi():
    return PiCache["digits"]
    
    #modedPi = piToMode(PiCache["digits"], MyOptions.Mode)
    #return ConstBitStream(modedPi)

# # Reinterpret the string of pi digits as char array
# def piToMode(piStr, mode):
#     piStrBytes = bytes(piStr, "utf-8") # piStr is utf-8 encoded
    
#     # return byte array using different encoding
#     if mode == CharMode.Bytes:
#         return piStrBytes
#     elif mode == CharMode.Ascii:
#         return piStrBytes.decode(encoding="ascii")
#     elif mode == CharMode.UTF16:
#         return piStrBytes.decode(encoding="utf-16")
#     elif mode == CharMode.UTF32:
#         return piStrBytes.decode(encoding="utf-32")
#     elif mode == CharMode.UTF8:
#         return piStrBytes.decode(encoding="utf-8")    
    
def getInputFile(inputFileName):
    if exists(inputFileName):
        # this might be where the CharModes come in handy?
        return codecs.open(inputFileName, encoding="utf-8", mode="r")
    else:
        return None
    
def fragmentInput(inputFile):
    fragments = []
    while True:
        frag = inputFile.read(MyOptions.TargetFragmentSize)
        if frag:
            fragments.append(frag)
        else:
            # End of file
            break
    return fragments
  
def base10Encode(inputString):
    stringAsBytes = bytes(inputString, "utf-8")
    stringAsBase10 = ""
    for byte in stringAsBytes:
        byteStr = str(byte).rjust(3, '\0') # Pad left with null to aide decoding
        stringAsBase10 += byteStr
    return stringAsBase10

def base10Decode(inputString):
    base10Blocks = []
    for i in range(0, len(inputString), 3):
        base10Blocks.append(inputString[i:i+3])
    decodedBytes = bytearray(len(base10Blocks))
    for i, block in enumerate(base10Blocks):
        blockStr = block.replace('\0', '')
        decodedBytes[i] = int(blockStr)
    return decodedBytes.decode("utf-8")    
  
# def getFragments(fileBits):
#     numFrags = int(fileBits.length / MyOptions.TargetFragmentSize)
#     remainder = fileBits.length % MyOptions.TargetFragmentSize
#     print("fileBits.length: " + str(fileBits.length) + " TargetFragSize: " + str(MyOptions.TargetFragmentSize) + " Remaining Bits: " + str(remainder))
#     if remainder == 0:
#         return (fileBits.cut(MyOptions.TargetFragmentSize), None, numFrags)
#     else:
#         # Include final smaller fragment 
#         length = fileBits.length
#         return (fileBits.cut(MyOptions.TargetFragmentSize), fileBits[length-remainder:length], numFrags+1)

def findFragmentInPi(fragment):
    print("Searching for fragment: " + fragment)
    
    if fragment in PiFragmentCache:
        print("fragment " + fragment + " in cache")
    else:    
        piStr = getPi()
        
        searchStr = fragment.replace('\0', '')
        print("Search Str: " + searchStr)
        pos = piStr.find(searchStr)
        if pos == -1:
            print("fragment not in available pi digits")
        else:
            print("fragment found at index " + str(pos))
            print("read-back: " + str(piStr[pos:pos+len(fragment)]))
            if fragment not in PiFragmentCache:
                PiFragmentCache[fragment] = pos
    
def encodeFragment(index, length):
    return fragmentEncodeTemplate.substitute({"index":index, "length":length})

def writeHeader(outFile):
    header = headerTemplate.subsitute({"marker":marker, "encoding":int(MyOptions.CharMode)})
    outFile.write(header)

def writeFragment(outFile, encodedFragment):
    outFile.write(encodedFragment)
    
def tryFindFragment(frag, i, foundFragments, missingFragments):
    if foundFrag := findFragmentInPi(frag):
        foundFragments[i] = foundFrag
    else:
        missingFragments.append(frag)
    
def beginEncode():
    if inputFile := getInputFile(MyOptions.InputFile):
               
        #print(fileBits.bin)
        #print([fileBits.bin[i:i+10] for i in range(0, len(fileBits.bin), 10)])
        
        fragments = fragmentInput(inputFile)
        print(fragments)
        
        fragmentsBase10 = []
        fragmenIndices = []
        for frag in fragments:
            base10Str = base10Encode(frag)
            fragmentsBase10.append(base10Str)
            findFragmentInPi(base10Str)
        print(fragmentsBase10)
        
        decodedFragments = []
        for base10Frag in fragmentsBase10:
            decodedFragments.append(base10Decode(base10Frag))
        print(decodedFragments)
        
        # for frag in fragments[0]:
        #     print(frag)
        # if fragments[1] != None:
        #     print(fragments[1])
        
        # foundFragments = [None] * fragments[2]
        # missingFragments = []
        # i = 0
        # for frag in fragments[0]:
        #     tryFindFragment(frag, i, foundFragments, missingFragments)
        
        # if fragments[1] != None:
        #     tryFindFragment(frag, i, foundFragments, missingFragments)
            
        # TODO: handle missing fragments by splitting them into ever smaller slices
            
#def beginDecode():
    

def loadCachedPi():
    if MyOptions.Verbose:
        print("Checking for pi.cache file")
        
    if exists("pi.cache"):
        with open("pi.cache", "r") as inCacheFile:
            global PiCache
            PiCache = json.load(inCacheFile)
            piStrLength = len(PiCache["digits"])
            print("PiCache length:" + str(piStrLength))
            if MyOptions.Verbose:
                print("PiCache found and loaded: ")
                print(PiCache)
    else:
        if MyOptions.Verbose:
            print("pi.cache not found")
        
    # Pull in the first 100k digits as a starting point
    for i in range(0, 100000, 1000):
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
        beginEncode()
    else:
        beginDecode()
   
    if (MyOptions.SaveCachedPiToFile):
        saveCachedPi()

if __name__ == "__main__":
    main(sys.argv)
