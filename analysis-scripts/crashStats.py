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
    (config, leaderSpeed, controller, spacing, attackTime, rep) = item.split('_')
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
            print("Error, crash impact <0")
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
    writer.writerow(["config", "leaderSpeed", "controllerID", "controllerSpacing", "attackTime", "repetition", "crashImpact", "crashingVehicle"])
    for item in output:
        writer.writerow(item)

import matplotlib.pyplot as plt
import os, sys, random, re
import matplotlib.patches as mpatches

#colors = {"CACC-5":'r', "CACC-12.5":'y', "CACC-20":'g', "PLOEG":'b', "CONSENSUS":'k'}

tJam = [ time for (_, _, _, _, time, _, _, _, _, _, _) in output]
vAvg = [ speed for (_, speed, _, _, _, _, _, _, _, _, _) in output]

cIDtoStr = {"1":"CACC", "2":"PLOEG", "3":"CONSENSUS"}

controllers=[]
crashesByTimePerController = {}
crashesBySpeedPerController = {}

for line in output:
    (_, speed, cID, cS, time, _, accident, _, _, _, _) = line
    controller = "%s-%s"%(cIDtoStr[cID], cS) if cID=="1" else cIDtoStr[cID]
    if controller not in controllers:
        controllers.append(controller)
    if controller not in crashesByTimePerController:
        crashesByTimePerController[controller] = {}
        crashesBySpeedPerController[controller] = {}
    if plotDeltaV:
        if time not in crashesByTimePerController[controller]:
            crashesByTimePerController[controller][time]=(0, 0.0)
        if speed not in crashesBySpeedPerController[controller]:
            crashesBySpeedPerController[controller][speed]=(0, 0.0)
        if float(accident)>0:

            c, v = crashesByTimePerController[controller][time]
            c += 1
            v += float(accident)
            crashesByTimePerController[controller][time] = (c, v)

            c, v = crashesBySpeedPerController[controller][speed]
            c += 1
            v += float(accident)
            crashesBySpeedPerController[controller][speed] = (c, v)
    else:
        if time not in crashesByTimePerController[controller]:
            crashesByTimePerController[controller][time]=0
        if speed not in crashesBySpeedPerController[controller]:
            crashesBySpeedPerController[controller][speed]=0
        if float(accident)>0:
            crashesByTimePerController[controller][time]+=1
            crashesBySpeedPerController[controller][speed]+=1

print(controllers)
fig = plt.figure()
ax = plt.subplot(111)
#plot by jam time
c=0
for item in controllers:
    if plotDeltaV:
        plt.scatter(tJam, [v/count if count != 0 else -1 for (count, v) in [crashesByTimePerController[item][t] for t in tJam]], color=color[c], marker=marker[c], label=item)
    else:
        plt.scatter(tJam, [crashesByTimePerController[item][t] for t in tJam], color=color[c], marker=marker[c], label=item)
    c+=1

box = ax.get_position()
ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
plt.savefig(join(plotFolder, "crash-time-%s.pdf"%(plotName)))
plt.close()

fig = plt.figure()
ax = plt.subplot(111)
#plot by average speed
c=0
for item in controllers:
    if plotDeltaV:
        plt.scatter(vAvg, [v/count if count != 0 else -1 for (count, v) in [crashesBySpeedPerController[item][v] for v in vAvg]], color=color[c], marker=marker[c], label=item)
    else:
        plt.scatter(vAvg, [crashesBySpeedPerController[item][v] for v in vAvg], color=color[c], marker=marker[c], label=item)
    c+=1

box = ax.get_position()
ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
plt.savefig(join(plotFolder, "crash-speed-%s.pdf"%(plotName)))
plt.close()


(head, tail) = os.path.split(csvout)
tail = "aggregated-" + tail

with open(os.path.join(head, tail), 'w') as outputFile:
    writer = csv.writer(outputFile, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    writer.writerow(["leaderSpeed", "controllerID", "controllerSpacing", "attackTime", "crashImpactAvg", "crashImpactStd", "averageMaxAccel", "averageMaxSpacingError", "maxSpacingError"])
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
