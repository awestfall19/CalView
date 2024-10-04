import datetime
from dateutil.relativedelta import relativedelta
from pydsstools.heclib.dss import HecDss
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import panel as pn
import datetime as dt

pn.extension()

import hvplot.pandas
import holoviews as hv
from holoviews import opts

from pydataset import data as demodata

#hv.extension['bokeh']

def getDataFrame(dss_file, s_startDate, s_endDate):
    dss_file = dss_file
    startDate = s_startDate
    endDate = s_endDate
    # Must also provide start date in regular datetime format for looping
    #startDate_1 = dt_startDate

    # Getting the Catalog
    # ## Open the target DSS file and read all paths into a numpy ndarray
    fid = HecDss.Open(dss_file)
    pathNamesDict = fid.getPathnameDict()
    pathNames = np.array(list(pathNamesDict.values())[0])

    # Initially I had assumed we could put the entire DSS file in a dataframe
    # after a few tries where that resulted in run times > 5 min, that looks like a
    # non-starter. Still using the DF approach since pandas has methods to reshape the
    # list of path names
    dfPaths = pd.DataFrame(pathNames, columns=["AllPaths"])

    # ## Split the single column by slashes. This has not been tested with any
    # meaningful variety of DSS file versions
    dfPaths[['blank1', 'A', 'B', 'C', 'D', 'E', 'F', 'blank2']] = dfPaths['AllPaths'].str.split("/", expand=True)
    dfPaths = dfPaths.drop(columns=['AllPaths', 'blank1', 'blank2'])
    # In CalSim convention, the B field is used for the variable name. Some users also set WRIMS
    # to output the results in 10-year chunks, so field D (date) is another sort criteria here
    dfPaths = dfPaths.sort_values(by=['B', 'D'])

    # ## Create extra columns for data contained within the timeseries (not within the path list)
    dfPaths = dfPaths.reindex(columns=dfPaths.columns.tolist() + ['Series_ID', 'TYPE', 'UNITS', 'TS'])

    # ## Specifically for CalSim3 runs, it is necessary to drop duplicate paths because of the 10-year
    # blocks. At this point, the objective is just to get a list of variable names to pull from the
    # DSS file, so are not losing anything by dropping the later 10-year chunks
    dfPaths = dfPaths.drop_duplicates(subset=['B', 'C'])

    # NOTE: Code below was to dump all timeseries into cells in the same dataframe that
    # holds the list of paths.  This is a big ask for most laptops
    # Code for pulling out timeseries should be usable for inidividual timeseries, so
    # those portions are kept. Everything for the "one massive dataframe" approach
    # is commented out but left in the file, since a parallelized approach may
    # still yield some results if applied to

    # # ## Create cell to hold the timeseries. This col must be type 'object'
    # # dfPathsReduced['TS'] = dfPathsReduced['TS'].astype('object')
    # dfPaths = dfPaths.astype({'TYPE': "string"})
    # dfPaths = dfPaths.astype({'UNITS': "string"})
    # dfPaths = dfPaths.astype({'TS': object})
    dfPaths = dfPaths.reset_index()
    dfPaths.drop('index', axis=1, inplace=True)


    # Create a unique name for each series. In CalSim3, output DSS files,
    # the combination of cols B & C will be unique and human-readable, so
    # the idea is to create a list of these, then have the user select from
    # that list which timeseries they want to retrieve
    dfPaths['Series_ID'] = dfPaths.B.str.cat(dfPaths.C, sep="--")

    # Populate the TS col of DataFrame
    # NOTE: specifying start & end dates gets around 10-year chunking issue
    ts_names = dfPaths['B'].unique()
    ts_types = dfPaths['C'].unique()

    # ## Read the first timeseries. For CalSim3 output runs, these should all have the same length,
    # ## so any times
    # ## Not to be used in SV files with year=4000 repeating hack
    # pathNameInit = "/CALSIM/{}/{}/-/1MON/L2020A/".format(TS_names[0], TS_types[0])
    # ts = fid.read_ts(pathNameInit, window=(startDate, endDate), trim_missing=False)
    # values = ts.values

    # Here's another problem - retrieving the "type" and "units" requires getting the entire timeseries.
    # Trying it without writing the ts to the dataframe to make sure it's not too slow
    # Ideally we edit the pydsstools method we're importing for this and suppress the output when
    # it reads a timeseries object.
    # Update I tried this and it's quite slow
    # for index, row in dfPaths.iterrows():
    #     strPath = "/{}/{}/{}/{}/{}/{}/".format(row['A'], row['B'], row['C'], row['D'], row['E'], row['F'])
    #     tsTest = fid.read_ts(strPath, window=(startDate, endDate), trim_missing=False)
    #     # values = tsTest.values.tolist()
    #     dfPaths.at[index, 'TYPE'] = tsTest.type
    #     dfPaths.at[index, 'UNITS'] = tsTest.units
    #     #dfPaths.at[index, 'TS'] = values


    return dfPaths

def plot_TS():
    a=1
    # plot a timeseries with dates specified
    # alternatively use holiviz / panels to make a cool zoomable plot from just the variables selected

    return 0

def plotExceedance():
    a=1
    # Plot Exceedance charts for specific variables


    return 0

if __name__ == "__main__":

    # File names and locations are specific to local development workflow. Adapt as needed

    # path = r"C:\Users\swaers\Desktop\NewMelones_VA\Alt_1\_Reclamation_LTO2021\BA\NAA\CalSim3\2022MED\CalSim3_NAA_2022MED_09072023\DSS\output"
    print('start')
    # User Inputs
    # For now (9/5/2023) must use [DDMMMYY HH:MM:SS] format
    #dss_file = path + r"CS3_LTO_NAA_2022MED_09072023_L2020A_DV_dp.dss"

    # Early objective = recreate the functionality of WRIMS's DSS viewer module

    startDate = "31OCT1921 00:00:00"

    endDate = "30SEP2021 00:00:00"
    startDate_1 = datetime.date(1921, 10, 31)

    dss_file_1 = r"Alt1.dss"
    dss_file_2 = r"Alt2.dss"
    dss_file_3 = r"Alt3.dss"

    data1 = getDataFrame(dss_file_1, startDate, endDate)
    data2 = getDataFrame(dss_file_2, startDate, endDate)
    data3 = getDataFrame(dss_file_3, startDate, endDate)
    #data4 = getDataFrame(dss_file_3, startDate, endDate)

    times = np.array([startDate_1])
    for i in range(1, len(data1.iloc[0]['TS'])):
        print(i)
        times = np.append(times,
                          times[i - 1] + relativedelta(days=+1) + relativedelta(months=+1) - relativedelta(days=+1))

    ts_id_1 = data1['Series_ID'].unique()
    ts_id_2 = data2['Series_ID'].unique()
    ts_id_3 = data3['Series_ID'].unique()
    #ts_id_4 = data4['Series_ID'].unique()

    # 2-file compare
    #list = [data1, data2]
    #common_vars = np.intersect1d(ts_id_1, ts_id_2)

    # 3-file compare
    # list = [data1, data2, data3]
    #common_vars = np.intersect1d(np.intersect1d(ts_id_1, ts_id_2), ts_id_3)

    # 4-file compare
    #list = [data1, data2, data3, data4]
    #common_vars = np.intersect1d(np.intersect1d(np.intersect1d(ts_id_1, ts_id_2), ts_id_3), ts_id_4)

    plot_var = "D_MELON"

    ploty = list[0].loc[list[0]["B"]=="S_MELON"]['TS'].values[0]

    # dummy input
    user_input = "S_MELON"

    while user_input != "quit":
        a = 1
        # ploty =
        # plt.plot(times, ploty)
        # user_input = input("Enter a variable to plot: ")

    print('done')

