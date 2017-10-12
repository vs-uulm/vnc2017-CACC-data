# Data description file
This repository contains data for our paper Analyzing Attacks on Cooperative Adaptive Cruise Control (CACC), accepted at VNC 2017.
It only contains raw simulation output: the source code modifications are in separate repositories, and the data analysis scripts are in the paper repository.

Note that for JammingDetail, we increased the scope of our simulations after an initial round of data analysis, so the run number issued by OMNeT++ is not unique. We did this to include the PLOEG and CONSENSUS controllers into the full analysis (although preliminary analysis with JammingAttack showed they were not affected, we decided to include them, because the different time of attack could have changed this outcome) -- we did not re-run the same simulations with the same parameters, because those simulations are deterministic anyway.
