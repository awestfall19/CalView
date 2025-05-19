import time
import hvplot.pandas
import pandas as pd
import numpy as np
from panel.io import hold
from bokeh.models import WheelZoomTool
from csdss_readlib_fullfile import file_reader, pickler, load_pickles, get_trend_fields

def get_vars_list(ls_vars, s_default):
    return [string for string in ls_vars if s_default in string]

def plot_values(scenario_list, var_list, unit_choice, df_all, c_default_units_all):

    df_all_plot = df_all.copy(deep=True)

    durations = [date.day for date in df_all_plot['Date']]

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
    if var_list == []:
        return
    for var in var_list:
        try:
            original_unit = c_default_units_all[var].strip()
        except:
            original_unit = None

        if original_unit not in ['CFS', 'TAF']:
            pass
        elif original_unit == unit_choice:
            pass
        elif original_unit == 'CFS':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], cfs_taf)
        elif original_unit == 'TAF':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], taf_cfs)

    # Sortable, filter to target scenarios and vars
    df_wide = pd.DataFrame(df_all_plot['Date'].unique(), columns=['Date'])

    keeplist = ['Date']

    for scenario in scenario_list:
        df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][var_list]
        df_temp.reset_index(inplace=True, drop=True)
        col_names = [f'{scenario}: {var}' for var in var_list]
        df_temp.columns = col_names
        df_wide[col_names] = df_temp[col_names]
        for name in col_names:
            keeplist.append(name)
        debug = True

    df_plot = df_wide.drop([var for var in df_wide if var not in keeplist])

    keeplist.remove('Date')
    print(df_plot[keeplist].min().min(), df_plot[keeplist].max().max())
    return df_plot.hvplot(
        x='Date',
        ylabel=unit_choice,
        min_height=600,
        #ylim=(df_plot[keeplist].min().min(), df_plot[keeplist].max().max())
    )

def plot_time_group(scenario_list, var_list, unit_choice, df_all,
                    c_default_units_all, period_choice):

    df_all_plot = df_all.copy(deep=True)

    durations = [date.day for date in df_all_plot['Date']]

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
    if var_list == []:
        return
    for var in var_list:
        try:
            original_unit = c_default_units_all[var].strip()
        except:
            original_unit = None

        if original_unit not in ['CFS', 'TAF']:
            pass
        elif original_unit == unit_choice:
            pass
        elif original_unit == 'CFS':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], cfs_taf)
        elif original_unit == 'TAF':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], taf_cfs)

    # Sortable, filter to target scenarios and vars
    df_wide = pd.DataFrame(df_all_plot['Date'].unique(), columns=['Date'])
    df_wide[['WY', 'DY', 'Month']] = df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY','Month']]

    #keeplist = ['Date']
    keeplist = []

    for scenario in scenario_list:
        df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][var_list]
        df_temp.reset_index(inplace=True, drop=True)
        col_names = [f'{scenario}: {var}' for var in var_list]
        df_temp.columns = col_names
        df_wide[col_names] = df_temp[col_names]       # WHAT THE HECK
        for name in col_names:
            keeplist.append(name)
        debug = True

    # ------- Agg ops below -------------
    df_wide[['WY', 'DY','Month']] = \
        df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY','Month']]

    # Remove incomplete years (default CS3 runs typically based on WY)
    # Grouping by calendar year or contract year (Mar-Feb) leaves partial
    # years @ start/end of run

    # grouping by period choice
    # if we chose a year option
    if period_choice in ["WY", "DY", "CY"]:
        if period_choice == "CY":
            df_wide['CY'] = np.where(df_wide.Month >= 3, df_wide.DY, df_wide.DY-1)
        df_timecounts = df_wide.groupby(by=[period_choice]).count()
        droplist = df_timecounts[df_timecounts['Date'] < 12].index
        df_wide = df_wide[df_wide[period_choice].isin(droplist) == False]
        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=[period_choice]).sum()
        df_plot = df_grouped[keeplist]
        return df_plot.hvplot(
            min_height=600, ylabel=unit_choice
        )

    # selected a month
    else:
        df_wide = df_wide[df_wide.Month == period_choice]
        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=['DY']).sum()
        df_plot = df_grouped[keeplist]
        return df_plot.hvplot(
            min_height=600, xlabel='Year', ylabel=unit_choice,
            legend="bottom"
        )


def plot_time_exceedance(scenario_list, var_list, unit_choice, df_all,
                    c_default_units_all, period_choice):

    df_all_plot = df_all.copy(deep=True)
    durations = [date.day for date in df_all_plot['Date']]

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
    if var_list == []:
        return
    for var in var_list:
        try:
            original_unit = c_default_units_all[var].strip()
        except:
            original_unit = None

        if original_unit not in ['CFS', 'TAF']:
            pass
        elif original_unit == unit_choice:
            pass
        elif original_unit == 'CFS':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], cfs_taf)
        elif original_unit == 'TAF':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], taf_cfs)

    # Sortable, filter to target scenarios and vars
    df_wide = pd.DataFrame(df_all_plot['Date'].unique(), columns=['Date'])
    df_wide[['WY', 'DY', 'Month']] = df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY','Month']]

    # This will allow us to drop the columns used for sorting / aggregating once the
    # final df_plot has been constructed. Eventually we might write some more streamlined
    # code to calculate WY/DY/etc on the fly
    keeplist = []

    for scenario in scenario_list:
        df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][var_list]
        df_temp.reset_index(inplace=True, drop=True)
        col_names = [f'{scenario}: {var}' for var in var_list]
        df_temp.columns = col_names
        df_wide[col_names] = df_temp[col_names]       # WHAT THE HECK
        for name in col_names:
            keeplist.append(name)
        debug = True

    # ------- Agg ops below -------------

    df_wide[['WY', 'DY','Month']] = \
        df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY','Month']]

    # Remove incomplete years (default CS3 runs typically based on WY)
    # Grouping by calendar year or contract year (Mar-Feb) leaves partial
    # years @ start/end of run
    # period_choice = 'DY' #dbg only
    if period_choice in ['WY', 'DY', 'CY']:
        if period_choice == 'CY':
            df_wide['CY'] = np.where(df_wide.Month >= 3, df_wide.DY, df_wide.DY - 1)
        df_timecounts = df_wide.groupby(by=[period_choice]).count()
        droplist = df_timecounts[df_timecounts['Date'] < 12].index
        df_wide = df_wide[df_wide[period_choice].isin(droplist) == False]

        # Exceedance

        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=[period_choice]).sum()
        df_grouped.reset_index(inplace=True)
        # plot_pos = df_grouped.index
        df_exceed = pd.DataFrame(index=df_grouped.index)

        for var in keeplist:
            if var != 'Date':
                l_sorted = df_grouped[var].sort_values().reset_index(drop=True)
                df_exceed[var] = l_sorted

        # Debug only
        # titlestr = f'df_plot_{time.time()}.xlsx'
        # df_plot.to_excel(titlestr)

        #print(df_plot)
        # print(unit_choice)
        # print(scenario_list)
        # print(var_list)
        return df_exceed.hvplot(
            min_height=600, ylabel=unit_choice
        )

    # month choice
    else:
        df_wide = df_wide[df_wide.Month == period_choice]

        # Exceedance

        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=['DY']).sum()
        df_grouped.reset_index(inplace=True)
        # plot_pos = df_grouped.index
        df_exceed = pd.DataFrame(index=df_grouped.index)

        for var in keeplist:
            if var != 'Date':
                l_sorted = df_grouped[var].sort_values().reset_index(drop=True)
                df_exceed[var] = l_sorted

        # Debug only
        # titlestr = f'df_plot_{time.time()}.xlsx'
        # df_plot.to_excel(titlestr)

        # print(df_plot)
        # print(unit_choice)
        # print(scenario_list)
        # print(var_list)
        return df_exceed.hvplot(
            min_height=600, ylabel=unit_choice
        )

def plot_single_var(df, period_choice, variable, scenario_list,
                    units_choice, stat_choice, c_default_units):

    df_all_plot = df.copy(deep=True)

    durations = [date.day for date in df_all_plot['Date']]

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
    try:
        original_unit = c_default_units[variable].strip()
    except:
        original_unit = None

    if original_unit not in ['CFS', 'TAF']:
        pass
    elif original_unit == units_choice:
        pass
    elif original_unit == 'CFS':
        df_all_plot[variable] = \
            np.multiply(df_all_plot[variable], cfs_taf)
    elif original_unit == 'TAF':
        df_all_plot[variable] = \
            np.multiply(df_all_plot[variable], taf_cfs)
    # Sortable, filter to target scenarios and vars
    df_wide = pd.DataFrame(df_all_plot['Date'].unique(), columns=['Date'])
    df_wide[['WY', 'DY', 'Month']] = df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY', 'Month']]

    keeplist = []

    for scenario in scenario_list:
        df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][[variable]]
        df_temp.reset_index(inplace=True, drop=True)
        col_names = [f'{scenario}: {variable}']
        df_temp.columns = col_names
        df_wide[col_names] = df_temp[col_names]
        for name in col_names:
            keeplist.append(name)

    # ------- Agg ops below -------------
    df_wide[['WY', 'DY', 'Month']] = \
        df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY', 'Month']]

    if period_choice in ['WY', 'DY', 'CY']:
        if period_choice == "CY":
            df_all_plot['CY'] = np.where(df_all_plot.Month >= 3, df_all_plot.DY, df_all_plot.DY - 1)
        df_timecounts = df_wide.groupby(by=[period_choice]).count()
        droplist = df_timecounts[df_timecounts['Date'] < 12].index
        df_wide = df_wide[df_wide[period_choice].isin(droplist) == False]

        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=[period_choice]).sum()
        df_plot = df_grouped[keeplist]

        # calculate chosen stat
        if stat_choice == 'Average':
            df_stats = df_plot.mean()
        elif stat_choice == 'Minimum':
            df_stats = df_plot.min()
        else:
            df_stats = df_plot.max()

        #Set upper and lower bounds
        if np.min(df_stats) > 0:
            ylower = 0
        else:
            ylower = np.min(df_stats)*1.1

        return df_stats.hvplot.bar(color='#00809e', title=variable+' '+stat_choice,
                                   ylabel=units_choice, ylim=(ylower,np.max(df_stats)*1.1), min_height=600)

    # Month chosen
    else:
        df_wide = df_wide[df_wide.Month == period_choice]
        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=['DY']).sum()
        df_plot = df_grouped[keeplist]

        # calculate chosen stat
        if stat_choice == 'Average':
            df_stats = df_plot.mean()
        elif stat_choice == 'Minimum':
            df_stats = df_plot.min()
        else:
            df_stats = df_plot.max()

        return df_stats.hvplot.bar(color='#00809e', title=variable + ' ' + stat_choice,
                                   ylabel=units_choice, min_height=600)

def run_operation(df, op_choice):
    #If user selects scenario that has been previously run, grab pickle files
    if op_choice == "Previously used files":
        # This runs no matter what. The pickle files allow you to come back and
        # pull the same variables without waiting for the file reads to complete
        df_all_data, df_diffs, c_default_units = load_pickles()



    #Else, request file names and begin new DSS Reader run
    '''
    else:
        append_list, baseline_stack, c_default_units = file_reader(runs, field_list)
        pickler(append_list, baseline_stack, c_default_units)
         # Write to Excel.
        try:
            df_all_data.to_excel("DSS_contents.xlsx")
        except:
            print("Error writing output file. "
                  "Make sure 'DSS_contents.xlsx' is not open.")
    '''
