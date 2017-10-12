#!/usr/bin/python3

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('-i', '--infolder', type=str, required=True, help='Input vector dir')
parser.add_argument('-p', '--plotname', type=str, required=True, help='Output file name for plots (will be prepended with speed-/time-)')
parser.add_argument('-d', '--plotfolder', type=str, required=True, help='Output folder for plots')
parser.add_argument('-o', '--csvout', type=str, required=True, help='Output CSV with accident stats')
parser.add_argument('-v', '--plotDeltaV', default=False, action="store_true", help='With this switch, average deltaV per accident is plotted instead of the accident count')
args=parser.parse_args()

infolder = args.infolder
csvout = args.csvout
plotFolder = args.plotfolder
plotName = args.plotname
plotDeltaV = args.plotDeltaV

#note: sys.argv is used, so this will grab the same args
from parseData import parseData, color, marker

from os import listdir
from os.path import isfile, join

import numpy as np

def testAccident(path):
    with open(path,'r') as vector:
        lines = vector.readlines()
        line = lines[-1]
        lastTime=line.split()[2]
        return float(lastTime) > 59.9 #sometimes, the last time step could be 60; interval should be 0.1, so >59.9 is OK

vecfiles = [f for f in listdir(infolder) if isfile(join(infolder, f)) and f.endswith('vec')]

output = []
aggOutput = {}
for item in vecfiles:
    #SinusoidalJammingDetail_50_1_13_31_3.vec
    try:
        (config, leaderSpeed, controller, spacing, attackTime, rep) = item.split('_')
    except ValueError:
        print('inconsistent file name: %s'%(item))
    rep = rep.split('.')[0] #remove trailing file type
    carData = parseData(join(infolder, item))
    accident = (59.9 > carData[0]['distance'][-1][0])
    crashImpact = -1
    crashingVehicle = -1
    stabilityAccelImpact = -1
    averageMaxSpacingError = -1
    maxSpacingError = -1
    if accident:
        for v in range(len(carData)):
            if carData[v]['distance'][-1][1] == 0:
                crashingVehicle = v
        if crashingVehicle == -1:
            print("Error, did not find crashing vehicle, but timeline says an accident occurred")
            print([i['distance'][-1][1] for i in carData])
            print([i['speed'][-1][1] for i in carData])
            print([i['distance'][-1][0] for i in carData])
            continue
        if crashingVehicle == 0:
            print("Error, data says leader crashed")
            continue
        crashImpact = carData[crashingVehicle]['speed'][-1][1] - carData[crashingVehicle-1]['speed'][-1][1]
        if crashImpact < 0:
            print([i['distance'][-1][1] for i in carData])
            print([i['speed'][-1][1] for i in carData])
            print([i['acceleration'][-1][1] for i in carData])
            print([i['distance'][-1][0] for i in carData])
    else:
        maxAccelerations = []
        spacingErrors = []
        for v in range(len(carData)):
            maxAccelerations.append(max([v for (t, v) in carData[v]['acceleration']]))
            errors = []
            k=0
            for (timestep, value) in carData[v]['distance']:
                desiredSpacing = -1
                if controller is 1:
                    desiredSpacing = spacing
                elif controller is 2:
                    #note: this assumes carData[v]['distance'][k][0] == carData[v]['speed'][k][0] for all k
                    #2 is the standstill distance, which is assumed to be the same as for the ACC, see here:
                    #https://github.com/michele-segata/plexe-sumo/issues/1
                    # 0.5 is the default headway time defined for the PLOEG controller (ploegH in the Plexe code)
                    desiredSpacing = 2 + 0.5 * carData[v]['speed'][k]
                elif controller is 3:
                    #note: this assumes carData[v]['distance'][k][0] == carData[v]['speed'][k][0] for all k
                    #2 is the standstill distance, which is assumed to be the same as for the ACC, see here:
                    #https://github.com/michele-segata/plexe-sumo/issues/1
                    # 0.8 is the default headway time defined for the CONSENSUS controller (see defaultH in src/microsim/cfmodels/CC_VehicleVariables.cpp)
                    desiredSpacing = 2 + 0.8 * carData[v]['speed'][k]
                k+=1
                errors.append(abs(desiredSpacing - value))
            spacingErrors.append(max(errors))
        #for reasoning why we average/max, see notes at the bottom, where this is aggregatedly written to a file
        stabilityAccelImpact = np.average(maxAccelerations)
        averageMaxSpacingError = np.average(spacingErrors)
        maxSpacingError = max(spacingErrors)
    output.append([config, float(leaderSpeed), controller, spacing, float(attackTime), rep, crashImpact, crashingVehicle, stabilityAccelImpact, averageMaxSpacingError, maxSpacingError])
    if (float(leaderSpeed), controller, spacing, float(attackTime)) in aggOutput:
        aggOutput[(float(leaderSpeed), controller, spacing, float(attackTime))].append((crashImpact, stabilityAccelImpact, averageMaxSpacingError, maxSpacingError))
    else:
        aggOutput[(float(leaderSpeed), controller, spacing, float(attackTime))]=[(crashImpact, stabilityAccelImpact, averageMaxSpacingError, maxSpacingError)]

import csv
with open(csvout, 'w') as outputFile:
    writer = csv.writer(outputFile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    writer.writerow(["config", "leaderSpeed", "controllerID", "controllerSpacing", "attackValue", "repetition", "crashImpact", "crashingVehicle", "averageMaxAccel", "averageMaxSpacingError", "maxSpacingError"])
    for item in output:
        writer.writerow(item)

import matplotlib.pyplot as plt
import os, sys, random, re
import matplotlib.patches as mpatches

#colors = {"CACC-5":'r', "CACC-12.5":'y', "CACC-20":'g', "PLOEG":'b', "CONSENSUS":'k'}

attackVals = sorted(set([ attackVal for (_, _, _, _, attackVal, _, _, _, _, _, _) in output]))
vAvg = sorted(set([ speed for (_, speed, _, _, _, _, _, _, _, _, _) in output]))

cIDtoStr = {"1":"CACC", "2":"PLOEG", "3":"CONSENSUS"}

controllers=[]
crashesByControllerPerSpeed = {}

for line in output:
    (_, speed, cID, cS, attackVal, _, accident, _, _, _, _) = line
    controller = "%s-%s"%(cIDtoStr[cID], cS) if cID=="1" else cIDtoStr[cID]
    if controller not in controllers:
        controllers.append(controller)
    if speed not in crashesByControllerPerSpeed:
        crashesByControllerPerSpeed[speed] = {}
    if attackVal not in crashesByControllerPerSpeed[speed]:
        crashesByControllerPerSpeed[speed][attackVal]={}
    if plotDeltaV:
        if controller not in crashesByControllerPerSpeed[speed][attackVal]:
            crashesByControllerPerSpeed[speed][attackVal][controller]=(0, 0.0)
        if float(accident) > 0:
            (c, v) = crashesByControllerPerSpeed[speed][attackVal][controller]
            c+=1
            v+= float(accident)
            crashesByControllerPerSpeed[speed][attackVal][controller] = (c, v)
    else:
        if controller not in crashesByControllerPerSpeed[speed][attackVal]:
            crashesByControllerPerSpeed[speed][attackVal][controller]=0
        if float(accident) > 0:
            crashesByControllerPerSpeed[speed][attackVal][controller]+=1

#cStrTocID = {"CACC-5":1, "CACC-20":2, "PLOEG":3, "CONSENSUS":4}
cPlotIDToStr = {1:"CACC-5", 2:"CACC-20", 3:"PLOEG", 4:"CONSENSUS"}
controllerPlotIDs = [1,2,3,4]

for speed in vAvg:
    graphName = 'crash-%s-%s.pdf'%(plotName, speed)

    c=0
    fig = plt.figure()
    ax = plt.subplot(111)
    for attackVal in attackVals:
        data=[]
        if plotDeltaV:
            for i in controllerPlotIDs: #this enforces the correct order -- dicts are not necessarily ordered
                (count, dV) = crashesByControllerPerSpeed[speed][attackVal][cPlotIDToStr[i]]
                if count != 0:
                    data.append(dV/count)
                else:
                    data.append(-1)
        else:
            for i in controllerPlotIDs: #this enforces the correct order -- dicts are not necessarily ordered
                data.append(crashesByControllerPerSpeed[speed][attackVal][cPlotIDToStr[i]])
        plt.scatter(controllerPlotIDs, data, color=color[c], marker=marker[c], label=attackVal)
        c+=1

    #resize axis and corresponding plots
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])
    plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
    plt.savefig(join(plotFolder, graphName))
    plt.close()

(head, tail) = os.path.split(csvout)
tail = "aggregated-" + tail

aggregatedData = []

with open(os.path.join(head, tail), 'w') as outputFile:
    writer = csv.writer(outputFile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    writer.writerow(["leaderSpeed", "controllerID", "controllerSpacing", "attackValue", "crashImpactAvg", "crashImpactStd", "averageMaxAccel", "averageMaxSpacingError", "maxSpacingError"])
    for item in aggOutput:
        row = list(item)
        crashImpact = [i[0] for i in aggOutput[item]]
        row.append(np.average(crashImpact)) #avg
        row.append(np.std(crashImpact)) #stdev
        averageMaxAccel = [i[1] for i in aggOutput[item]]
        #average of the max acceleration for each vehicle -> quantifies driver comfort
        #average this over the simulations to compute average comfort
        row.append(np.average(averageMaxAccel))
        averageMaxSpacingError = [i[2] for i in aggOutput[item]]
        #average of the max spacing error for each vehicle -> quantifies driver comfort
        #average this over the simulations to compute average comfort
        row.append(np.average(averageMaxSpacingError))
        #highest observed spacing error per vehicle -> models how close to a crash (or how inefficient the controller is)
        #compute the max to determine the worst value over all sims
        maxMaxSpacingError = [i[3] for i in aggOutput[item]]
        row.append(max(maxMaxSpacingError))
        writer.writerow(row)
        aggregatedData.append(row)
        if len(row) != 9:
            print("weird row: ", row)

if not plotDeltaV:
    import sys
    sys.exit(0)

graphName = 'full-%s.svg'%(plotName)

#font stuff, adapted from http://jonathansoma.com/lede/data-studio/matplotlib/changing-fonts-in-matplotlib/
import matplotlib
matplotlib.rcParams['font.sans-serif'] = "Latin Modern Roman"
matplotlib.rcParams['font.family'] = "sans-serif"

f, axes = plt.subplots(nrows=2, ncols=3, sharex=True)
axcounter=0

for speed in vAvg:
    c=0
    for attackVal in attackVals:
        data=[]
        for i in controllerPlotIDs: #this enforces the correct order -- dicts are not necessarily ordered
            (count, dV) = crashesByControllerPerSpeed[speed][attackVal][cPlotIDToStr[i]]
            if count != 0:
                data.append(dV/count)
            else:
                data.append(None)
        axes[0,axcounter].scatter(controllerPlotIDs, data, color=color[c], marker=marker[c], label=attackVal)
        c+=1

    c=0
    for attackVal in attackVals:
        data=[]
        for i in controllerPlotIDs:
            ID = 1 if i is 1 else i - 1 #this does not work if we have more than 2 constant spacing things..
            spacing = 20 if i is not 1 else 5 #only works because exactly the first constant spacing has 5, all others have 20
            item = []
            #for row in aggregatedData:
            #    if row[0] == speed:
            #        print('speed', speed)
            #        if int(row[1]) is ID:
            #            print('ID', ID)
            #        else:
            #            print('not ID', ID, row[1])
            #            if int(row[2]) is spacing:
            #                print('spacing',spacing)
            #                if row[3] is attackVal:
            #                    print('attackVal',attackVal)
            #    else:
            #        print('not speed', speed, row[0])
            item = [x[8] for x in aggregatedData if x[0] == speed and int(x[1]) == ID and int(x[2]) == spacing and x[3] == attackVal]
            if len(item) is not 1:
                print("Warning, more or less data than expected")
                print(speed, attackVal, i, item, ID, spacing)
                #print(aggregatedData)
            if item[0] > 0:
                data.append(-item[0])
            else:
                #print("no spacing error... accident?",crashesByControllerPerSpeed[speed][attackVal][cPlotIDToStr[i]])
                #print(item)
                data.append(None)
        axes[1,axcounter].scatter(controllerPlotIDs, data, color=color[c], marker=marker[c], label=attackVal)
        c+=1

    axcounter+=1
    print(attackVals)


#resize axis and corresponding plots
f.subplots_adjust(hspace=0,wspace=0)
#box = ax1.get_position()
#ax1.set_position([box.x0, box.y0, box.width * 0.75, box.height])
#box = ax2.get_position()
#ax2.set_position([box.x0, box.y0, box.width * 0.75, box.height])

axes[0,0].get_shared_y_axes().join(axes[0,0], axes[0,1], axes[0,2])
axes[1,0].get_shared_y_axes().join(axes[1,0], axes[1,1], axes[1,2])

axes[0,0].axis([0,5,0,10])
axes[0,0].set_yticklabels([0, 2, 4, 6, 8, 10])
axes[0,0].set_ylabel('Delta v (m/s)')
#axes[0,0].legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

axes[1,0].axis([0,5,-60,0])
axes[1,0].set_yticklabels([-60, -50, -40, -30, -20, -10, 0])
axes[1,0].set_ylabel('max |e| (m)')
axes[1,0].set_xticklabels(['', 'CACC-5', 'CACC-20', 'PLOEG', 'CONSENSUS', ''])

for label in axes[0,1].get_yticklabels():
    label.set_visible(False)
for label in axes[0,2].get_yticklabels():
    label.set_visible(False)
for label in axes[1,1].get_yticklabels():
    label.set_visible(False)
for label in axes[1,2].get_yticklabels():
    label.set_visible(False)

plt.savefig(join(plotFolder, graphName))
plt.close()
