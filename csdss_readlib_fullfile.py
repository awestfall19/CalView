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
num_fixed = 7

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
    li_wyt_cols = [index+num_fixed for index, colname in enumerate(df_all_data.iloc[:, num_fixed:]) if c_default_units[colname] == 'NONE']
    li_fixed_cols_indices = list(range(0, num_fixed)) + li_wyt_cols
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

def load_pickles(ls_files):
    if not ls_files:
        ls_files = ['values.pkl', 'diffs.pkl', 'units.pkl', 'fields.pkl']
    s_values_path = ''
    s_diffs_path = ''
    s_units_path = ''
    s_fields_path = ''
    for file in ls_files:
        # check for each file type and assign the path name
        if 'values.pkl' in file:
            s_values_path = file
        if 'diffs.pkl' in file:
            s_diffs_path = file
        if 'units.pkl' in file:
            s_units_path = file
        if 'fields.pkl' in file:
            s_fields_path = file
    try:
        load_data = open(s_values_path, 'rb')
        df_all_data = pickle.load(load_data)
        load_data.close()
    except:
        print("Missing \"values.pkl\". Please run pickler")

    try:
        load_diffs = open(s_diffs_path, 'rb')
        df_diffs = pickle.load(load_diffs)
        load_diffs.close()
    except:
        print("Missing \"diffs.pkl\". Please run pickler")

    try:
        load_units = open(s_units_path, 'rb')
        c_default_units = pickle.load(load_units)
        load_units.close()
    except:
        print("Missing \"units.pkl\". Please run pickler")

    try:
        load_fields = open(s_fields_path, 'rb')
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
        cy = [startDate_1.year - 1]
    else:
        cy = startDate_1.year

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
            cy = np.append(cy, current_time.year - 1)
        else:
            cy = np.append(cy, current_time.year)

    df_ts = pd.DataFrame(index=times)
    for t, ts in enumerate(list(c_target_ts_list_final.keys())):
        if isinstance(ts_list[t].values[0], np.float32):
            df_ts[ts] = ts_list[t].values.astype('float64')
        else:
            df_ts[ts] = ts_list[t].values

    df_ts.insert(0, 'JanDecYear', years)
    df_ts.insert(0, 'MarFebYear', cy)
    df_ts.insert(0, 'OctSeptYear', wy)
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
    c_field_list_final = c_field_list.copy()
    c_default_units_all = {}

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
            c_default_units_all.update(c_default_units)
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
            c_default_units_all.update(c_default_units)
            results[run[0]] = result

        # close the process pool
        pool.close()
        # wait for all tasks to finish
        pool.join()

    append_list = []
    baseline_stack = []

    # add calculated fields
    for i in range(len(runs)):
        results[runs[i][0]], c_field_list_final, c_default_units_all = calculated_fields(results[runs[i][0]], c_field_list_final, c_default_units_all)

    for i in range(len(runs)):
        append_list.append(results[runs[i][0]])
        baseline_stack.append(results[s_comparison])
    # print(f"Run time for pulling DSS data with multiprocessing = "
    #       f"{(time.time() - start_time)} seconds")
    print(f'Added {list(set(c_field_list_final.keys()) - set(c_field_list.keys()))} to field list.')
    print(f'Removed {list(set(c_field_list.keys()) - set(c_field_list_final.keys()))} from field list.')

    # add s_comparison to c_default_units so we have it stored
    c_default_units_all['comparison scenario'] = s_comparison
    # add the run names in
    for run_name, file_name in runs:
        c_default_units_all[run_name] = path.basename(file_name)

    return append_list, baseline_stack, c_default_units_all, c_field_list_final


def calculated_fields(df_all, c_field_list, c_default_units):
    # dictionary of what fields each calculated field needs
    c_fields_for_calculated = {
        'Total System Storage SWP and CVP': ['S_TRNTY', 'S_SHSTA', 'S_OROVL', 'S_FOLSM', 'S_SLUIS_CVP', 'S_SLUIS_SWP'],
        'Total Exports SWP and CVP': ['C_CAA003_SWP', 'C_DMC003', 'C_CAA003_CVP'],
        'Total San Luis Storage SWP and CVP': ['S_SLUIS_CVP', 'S_SLUIS_SWP'],
        'Flow Shortage on Sac Reg for Salinity': ['RSREQSACDV', 'JPREQSACDV', 'EMREQSACDV', 'COREQSACDV', 'C_SAC041', 'SP_SAC083_YBP037'],
        'Flow Shortage on X2 Delta Req Outflow': ['MRDO_FINALDV', 'NDOI'],
        'MRDO_SHORT': ['MRDO_FINALDV', 'NDOI_MIN'],
        'Combined Madera and Friant-Kern Canals Diversion': ['D_MLRTN_FRK000', 'D_MLRTN_MDC006'],
        'Stanislaus River Delivery - Oakdale North / SSJID 1+2': ['D_STS059_OAK001', 'D_SSJ004_61_PA1', 'D_WDWRD_61_PA3', 'D_WTPDGT_61_NU2'],
        'CVP Delivery Total': ['DEL_CVP_TOTAL_N', 'DEL_CVP_TOTAL_S'],
        'CVP Delivery PMI N (w CCWD)': ['DEL_CVP_PMI_N', 'D420'],
        'CVP Delivery North (w CCWD)': ['DEL_CVP_TOTAL_N', 'DEL_CVP_PMI_N', 'DEL_CVP_PMI_N_WAMR', 'D420']
    }

    # loop through the calculate fields and try anf add them
    for calculated_field in list(c_fields_for_calculated.keys()):
        # grab list of required fields
        sl_needed_fields = c_fields_for_calculated[calculated_field]

        # check if every needed field has been pulled
        if set(sl_needed_fields).issubset(set(c_field_list.keys())):

            # get the units
            ls_units = [c_default_units[var] for var in sl_needed_fields]

            # make sure all the units match
            if len(set(ls_units)) > 1:
                print('All units do not match for calculated variable: ', calculated_field)

            # add the default units
            c_default_units[calculated_field] = ls_units[0]

            # add the new calculated variable to the field list dictionary
            c_field_list[calculated_field] = calculated_field + ' (Calculated Field)'

            # add the calculated field to the dataframe
            match calculated_field:
                case 'Total System Storage SWP and CVP':
                    df_all[calculated_field] = df_all['S_TRNTY'] + df_all['S_SHSTA'] + df_all['S_OROVL'] + df_all['S_FOLSM'] + df_all['S_SLUIS_CVP'] + df_all['S_SLUIS_SWP']
                case 'Total Exports SWP and CVP':
                    df_all[calculated_field] = df_all['C_CAA003_SWP'] + df_all['C_DMC003'] + df_all['C_CAA003_CVP']
                case 'Total San Luis Storage SWP and CVP':
                    df_all[calculated_field] = df_all['S_SLUIS_CVP'] + df_all['S_SLUIS_SWP']
                case 'Flow Shortage on Sac Reg for Salinity':
                    df_all[calculated_field] = np.maximum(df_all[['RSREQSACDV', 'JPREQSACDV', 'EMREQSACDV', 'COREQSACDV']].max(axis=1) - (df_all['C_SAC041'] + df_all['SP_SAC083_YBP037']), 0)
                case 'Flow Shortage on X2 Delta Req Outflow':
                    df_all[calculated_field] = np.maximum(df_all['MRDO_FINALDV'] - df_all['NDOI'], 0)
                case 'MRDO_SHORT':
                    df_all[calculated_field] = df_all['MRDO_FINALDV'] - df_all['NDOI_MIN']
                case 'Combined Madera and Friant-Kern Canals Diversion':
                    df_all[calculated_field] = df_all['D_MLRTN_FRK000'] + df_all['D_MLRTN_MDC006']
                case 'Stanislaus River Delivery - Oakdale North / SSJID 1+2':
                    df_all[calculated_field] = df_all['D_STS059_OAK001'] + df_all['D_SSJ004_61_PA1'] + df_all['D_WDWRD_61_PA3'] + df_all['D_WTPDGT_61_NU2']
                case 'CVP Delivery Total':
                    df_all[calculated_field] = df_all['DEL_CVP_TOTAL_N'] + df_all['DEL_CVP_TOTAL_S']
                case 'CVP Delivery PMI N (w CCWD)':
                    df_all[calculated_field] = df_all['DEL_CVP_PMI_N'] + df_all['D420']
                case 'CVP Delivery North (w CCWD)':
                    df_all[calculated_field] = df_all['DEL_CVP_TOTAL_N'] - df_all['DEL_CVP_PMI_N'] + df_all['DEL_CVP_PMI_N_WAMR'] + df_all['D420']
                case _:
                    pass
    return df_all, c_field_list, c_default_units
