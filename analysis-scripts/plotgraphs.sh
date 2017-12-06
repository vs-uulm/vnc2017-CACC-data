#plot and output crash statistics
#python3 crashStats.py --infolder raw_data/SinusoidalJammingDetail/ --plotfolder graphs --plotname 'SinusoidalJammingDetail' --csvout SinusoidalJammingDetail.csv --plotDeltaV
python3 injectionCrashStats.py --infolder raw_data_new/SinusoidalPosInjection/ --plotfolder graphs_new --plotname 'SinusoidalPosInjection' --csvout SinusoidalPosInjection-new.csv --plotDeltaV
python3 injectionCrashStats.py --infolder raw_data_new/SinusoidalSpeedInjection/ --plotfolder graphs_new --plotname 'SinusoidalSpeedInjection' --csvout SinusoidalSpeedInjection-new.csv --plotDeltaV
python3 injectionCrashStats.py --infolder raw_data_new/SinusoidalAccInjection/ --plotfolder graphs_new --plotname 'SinusoidalAccInjection' --csvout SinusoidalAccInjection-new.csv --plotDeltaV
