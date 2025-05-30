import datetime
from dateutil.relativedelta import relativedelta
from pydsstools.heclib.dss import HecDss
import pandas as pd
import numpy as np
import time
import pickle
from multiprocessing import Pool
from os import path

# num_fixed = # of columns that are the same in all cases
num_fixed = 6

def get_trend_fields():
    # dictionary to hold fields and description in the form {field: description}
    c_tr_fields = {}
    try:
        # this line is needed for the file to correctly be found once this is bundled into an executable
        s_path_to_fields = path.abspath(path.join(path.dirname(__file__), 'TR_fields.txt'))
        with open(s_path_to_fields, "r") as f:
            lines = f.readlines()
    except:
        print('Failed to open TR_fields.txt')

    for line in lines:

        line = line.strip()
        curr_field = line.split('\t')
        if len(curr_field) != 2:
            continue
        else:
            field, description = curr_field
        field = field.strip(' ').upper()
        description = description.strip('\n')
        description = description + ' (' + field + ')'
        c_tr_fields[field] = description

    for field, description in c_tr_fields.items():
        if field == '':
            c_tr_fields.pop(field)
    return c_tr_fields

def pickler(append_list, baseline_stack, c_default_units, c_field_list):
    df_all_data = pd.DataFrame()
    df_all_data = pd.concat(append_list)
    df_all_data.reset_index(drop=True, inplace=True)
    df_all_data.index.name = "Index"

    df_baseline_stack = pd.concat(baseline_stack)
    df_baseline_stack.reset_index(drop=True, inplace=True)
    df_baseline_stack.index.name = "Index"

    # Calc diffs for the alts vs baseline
    # columns that shouldn't be subtracted
    li_wyt_cols = [index for index, colname in enumerate(df_all_data) if len(colname) >= 3 and colname[:3] == 'WYT']
    li_fixed_cols_indices = li_wyt_cols + list(range(0, num_fixed))
    df_fixed_cols = df_all_data.iloc[:, li_fixed_cols_indices]

    li_numeric_col_indices = [i for i in range(len(df_all_data.columns)) if i not in li_fixed_cols_indices]
    df_all_data_numeric = df_all_data.iloc[:, li_numeric_col_indices]

    df_baseline_numeric = df_baseline_stack.iloc[:, li_numeric_col_indices]
    df_diff_numeric = df_all_data_numeric.subtract(df_baseline_numeric)
    df_diffs = pd.concat([df_fixed_cols, df_diff_numeric], axis=1)

    pickled_vals = open('values.pkl', 'wb')
    pickle.dump(df_all_data, pickled_vals)
    pickled_vals.close()

    pickled_diffs = open('diffs.pkl', 'wb')
    pickle.dump(df_diffs, pickled_diffs)
    pickled_diffs.close()

    # Pickle units dictionary
    pickled_units = open('units.pkl', 'wb')
    pickle.dump(c_default_units, pickled_units)
    pickled_units.close()

    #pickle field descriptions
    pickled_fields = open('fields.pkl', 'wb')
    pickle.dump(c_field_list, pickled_fields)
    pickled_fields.close()

def load_pickles():
    try:
        load_data = open('values.pkl', 'rb')
        df_all_data = pickle.load(load_data)
        load_data.close()
    except:
        print("Missing \"values.pkl\". Please run pickler")

    try:
        load_diffs = open('diffs.pkl', 'rb')
        df_diffs = pickle.load(load_diffs)
        load_diffs.close()
    except:
        print("Missing \"diffs.pkl\". Please run pickler")

    try:
        load_units = open('units.pkl', 'rb')
        c_default_units = pickle.load(load_units)
        load_units.close()
    except:
        print("Missing \"units.pkl\". Please run pickler")

    try:
        load_fields = open('fields.pkl', 'rb')
        c_field_list = pickle.load(load_fields)
        load_fields.close()
    except:
        print("Missing \"fields.pkl\". Please run pickler")

    return (df_all_data, df_diffs, c_default_units, c_field_list)




def single_file_pull(dss_file, c_target_ts_list, scenario_name):
    startDate = "31OCT1921 00:00:00"
    endDate = "30SEP2021 00:00:00"
    startDate_1 = datetime.date(1921, 10, 31)

    fid = HecDss.Open(dss_file)

    # getPathnamesDict returns a dict of pathnames.
    # All CalSim outputs are contained in 'TS'
    pathNamesDict = fid.getPathnameDict()
    pathNames = np.array(list(pathNamesDict.values())[0])

    dfPaths = pd.DataFrame(pathNames, columns=["AllPaths"])
    # If the interpreter gives an error
    dfPaths[['blank1', 'A', 'B', 'C', 'D', 'E', 'F', 'blank2']] = \
            dfPaths['AllPaths'].str.split("/", expand=True)
    dfPaths = dfPaths.drop(columns=['AllPaths', 'blank1', 'blank2'])

    dfPaths = dfPaths.sort_values(by=['B', 'D'])
    dfPaths = dfPaths.drop_duplicates(subset=['B', 'C'])
    dfPaths = dfPaths.reset_index()
    dfPaths.drop('index', axis=1, inplace=True)

    c_target_ts_list_final = c_target_ts_list.copy()
    # use our list of variables to search the DSS File. For CS3, b parts are unique
    target_path_list = []
    for b_part in c_target_ts_list.keys():
        # make sure it is uppercase
        b_part_upper = b_part.upper()
        try:
            c_part = dfPaths[dfPaths['B'] == b_part]['C'].iloc[0]
            a_part = dfPaths[dfPaths['B'] == b_part]['A'].iloc[0]
            f_part = dfPaths[dfPaths['B'] == b_part]['F'].iloc[0]
            target_pathName = f'/{a_part}/{b_part_upper}/{c_part}//1MON/{f_part}/'
            target_path_list.append(target_pathName)
        except:
            c_target_ts_list_final.pop(b_part)

    # Empty lists for timeseries
    ts_list = []
    c_default_units = pd.Series()
    # iterate through list of variables and populate the timeseries and unit lists
    for i, p in enumerate(target_path_list):
        working_ts = fid.read_ts(p, window=(startDate, endDate), trim_missing=False)
        ts_list.append(working_ts)
        # unit_list.append(working_ts.units)
        c_default_units[list(c_target_ts_list_final.keys())[i]] = working_ts.units

    times = np.array([startDate_1])
    years = [startDate_1.year]
    months = [startDate_1.month]

    # Convert CY to WY
    if startDate_1.month > 9:
        wy = [startDate_1.year + 1]
    else:
        wy = [startDate_1.year]

    # Convert CY to delivery (contract) year
    if startDate_1.month < 3:
        dy = [startDate_1.year - 1]
    else:
        dy = startDate_1.year

    # Note loops starts at 1 not zero
    for i in range(1, len(ts_list[0].values)):
        # hack to find end of month: look at last date (should be last day of last month)
        # Add a day (first day of this month), then add a month (first day of next month)
        # Subtract a day (last day of this month)
        current_time = times[i - 1] \
                       + relativedelta(days=+1) \
                       + relativedelta(months=+1) \
                       - relativedelta(days=+1)
        times = np.append(times, current_time)
        years = np.append(years, current_time.year)
        months = np.append(months, current_time.month)
        if current_time.month > 9:
            wy = np.append(wy, current_time.year + 1)
        else:
            wy = np.append(wy, current_time.year)

        if current_time.month < 3:
            dy = np.append(dy, current_time.year - 1)
        else:
            dy = np.append(dy, current_time.year)

    df_ts = pd.DataFrame(index=times)
    for t, ts in enumerate(list(c_target_ts_list_final.keys())):
        df_ts[ts] = ts_list[t].values

    # Duplicate columns with other (cfs/taf) unit
    durations = [t.day for t in
                 times]  # list of month durations for our timeframe of interest

    df_ts.insert(0, 'DY', dy)
    df_ts.insert(0, 'WY', wy)
    df_ts.insert(0, 'Month', months)
    df_ts.insert(0, 'Year', years)
    df_ts.insert(0, 'Scenario', scenario_name)
    df_ts['Date'] = df_ts.index
    date_temp = df_ts.pop('Date')
    df_ts.insert(0, 'Date', date_temp)

    return df_ts, c_target_ts_list_final, c_default_units

def file_reader(runs: list[list], c_field_list, s_comparison):
    """
    reads in the list of runs. can be multiproccessing or not by changing multiprocess to True.
    Parameters
        runs: list of runs and run names in the form [["Description_1", ("File_1.dss")], ...]
        c_field_list: dictionary of fields and descriptions {field: description, ...}
        s_comparison: string, name of the comparison scenario
    returns
        append_list: list of the dataframes of each run
        baseline_stack: a list of dataframes of the comparison scenerio as many times as there are runs
        c_default_units: dictionary of the default units for each field
        c_field_list_final: dictionary of the final version of c_field_list

    """
    results = {}
    c_default_units_all = pd.Series()
    c_field_list_final = c_field_list.copy()

    multiprocess = False

    # Non-multi version for debug
    if multiprocess == False:
        for run in runs:
            print('Working on', run[0])
            result, c_target_ts_list, c_default_units = \
                single_file_pull(run[1], c_field_list, run[0])

            # make sure to remove ones that were not found
            c_field_list_final = {field: c_field_list_final[field] for field in c_field_list_final if field in c_target_ts_list}
            # add into dictionary to store
            c_default_units_all[run[0]] = c_default_units
            results[run[0]] = result
    else:
        # create pool
        pool = Pool()
        # Create and start runs
        for run in runs:
            print(f'Working on {run[0]} - multiproc')
            result, c_target_ts_list, c_default_units = pool.apply_async(single_file_pull,
                                                                       args=(run[1], c_field_list, run[0])).get()

            # make sure to remove ones that were not found
            c_field_list_final = {field: c_field_list_final[field] for field in c_field_list_final if field in c_target_ts_list}

            # add into dictionary to store
            c_default_units_all[run[0]] = c_default_units
            results[run[0]] = result

        # close the process pool
        pool.close()
        # wait for all tasks to finish
        pool.join()

    append_list = []
    baseline_stack = []

    for i in range(len(runs)):
        append_list.append(results[runs[i][0]])
        baseline_stack.append(results[s_comparison])
    # print(f"Run time for pulling DSS data with multiprocessing = "
    #       f"{(time.time() - start_time)} seconds")
    print(f'Removed {list(set(c_field_list.keys()) ^ set(c_field_list_final.keys()))} from field list.')

    # add s_comparison to c_default_units so we have it stored
    c_default_units['comparison scenario'] = s_comparison

    return append_list, baseline_stack, c_default_units, c_field_list_final
