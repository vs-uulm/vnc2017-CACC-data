#!/usr/bin/python3

import matplotlib.pyplot as plt
import os, sys, random, re
import matplotlib.patches as mpatches


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='plot Distance Values of Vectorfile')
    parser.add_argument('-i', '--infile', type=str, help='Input vector file')
    parser.add_argument('-o', '--plotfile', nargs='?', type=str, help='Output vector file')
    parser.add_argument('-p', '--plotpattern', nargs='?', type=str, help='plot pattern (e.g., NAME-%%s.pdf)')
    args=parser.parse_args()


desiredDataTypes = ["posx","speed","acceleration","controllerAcceleration","distance"]
color = ['y','b','g','r','c','m','#7CFC00','k', '#00CFC7']
marker = ['_','x','|','*','v','^','.','>', '<']

"""
Parses data from the given file (which should be a relative or absolute path, which is immediately passed to open())

Returns a list of vehicles, where each vehicle is a dict, which contains the vehicles' data over time. Index for the dict is desiredDataTypes (see elsewhere in this file), and each of these contains a list of tuples (time, val).
Plotting this list of pairs gives a graph of the appropriate values over time.
"""
def parseData(vecfile):
    
    with open(vecfile,'r') as data:
        content = data.readlines()
    
    paramHeader = True
    vectorHeader = False
    
    numCars = -1
    carList = []
    vectorToID = {}
    vectorToType = {}
    
    for line in content:
        #first, parameterization header
        if paramHeader and not line.startswith('param') and not line.startswith('attr') and not line.startswith('run') and not line.startswith('version'):
            paramHeader = False
            vectorHeader = True
            #print("param header done")
            continue #empty line between headers
        elif paramHeader:
            if 'attr iterationvars' in line or 'attr measurement' in line: continue
            if 'nCars' in line and not carList:
                numCars = int(line.split(' ')[2])
                #prepare array of cars
                for i in range(numCars):
                    myDict = {}
                    for x in desiredDataTypes:
                        myDict[x]=[]
                    carList.append(myDict)
            continue #done parsing vector header
        
        #second, vector header (i.e., which data is in which vector)
        if vectorHeader and not line.startswith('vector'):
            vectorHeader = False
            #print("vector header done")
            continue #empty line between headers
        elif vectorHeader:
            #parse this vector header
            data = line.split()
            vectorID = int(data[1])
            module = data[2].split('[')[1]
            carID = int(module.split(']')[0])
            dataType=data[3]
            if dataType in desiredDataTypes:
              vectorToID[vectorID]=carID
              vectorToType[vectorID]=dataType
            continue #done parsing vector header
    
        #parsing data
        if not paramHeader and not vectorHeader:
            data = line.split('\t')
            vectorID = int(data[0])
            #data[1] is event ID
            timeStamp = float(data[2])
            value = float(data[3])
            if vectorID not in vectorToID:
                continue #ignore this data.
            carID = vectorToID[vectorID]
            dataType = vectorToType[vectorID]
            carList[carID][dataType].append((timeStamp, value))
    return carList

if __name__ == '__main__':
    #if running as main script, plot some stuff and exit
    carList = parseData(args.infile)

    for dataType in desiredDataTypes:
        for i in range(len(carList)):
            car = carList[i]
            plt.plot([left for (left, right) in car[dataType]], [right for (left, right) in car[dataType]],color[i])
        
        plt.savefig(args.plotpattern%(dataType))
        plt.close()
