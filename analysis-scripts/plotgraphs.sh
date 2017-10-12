#plot and output crash statistics
python3 crashStats.py --infolder ../SinusoidalJammingDetail/ --plotfolder graphs --plotname 'SinusoidalJammingDetail' --csvout SinusoidalJammingDetail.csv --plotDeltaV
python3 injectionCrashStats.py --infolder ../SinusoidalPosInjection/ --plotfolder graphs --plotname 'SinusoidalPosInjection' --csvout SinusoidalPosInjection.csv --plotDeltaV
python3 injectionCrashStats.py --infolder ../SinusoidalSpeedInjection/ --plotfolder graphs --plotname 'SinusoidalSpeedInjection' --csvout SinusoidalSpeedInjection.csv --plotDeltaV
python3 injectionCrashStats.py --infolder ../SinusoidalAccInjection/ --plotfolder graphs --plotname 'SinusoidalAccInjection' --csvout SinusoidalAccInjection.csv --plotDeltaV
