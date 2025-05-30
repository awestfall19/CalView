import hvplot.pandas
import pandas as pd
import numpy as np
import panel as pn
import holoviews as hv
from panel.io import hold
from bokeh.models import WheelZoomTool
from csdss_readlib_fullfile import file_reader, pickler, load_pickles, get_trend_fields

def get_vars_list(ls_vars, s_default):
    return [string for string in ls_vars if s_default in string]

def plot_values(scenario_list, var_list, unit_choice, df_all, c_default_units_all, s_comparison, c_field_list):

    df_all_plot = df_all.copy(deep=True)
    df_all_plot.reset_index(inplace=True, drop=True)
    durations = [date.day for date in df_all_plot['Date']]

    # ensure comparison scen is at the end of the list so the coloring is constant with the differences plot
    if s_comparison in scenario_list:
        scenario_list.remove(s_comparison)
        scenario_list.append(s_comparison)

    # check if comparison scen is in the data frame
    # if it's not, then we are creating the differences plot and don't want to include comparison scen
    if s_comparison not in df_all_plot.Scenario.unique():
        scenario_list = [scen for scen in scenario_list if scen != s_comparison]

    if len(scenario_list) == 0:
        return

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
    if var_list == []:
        return pn.pane.Markdown('## Select variables above to display plot.')
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


    # switch from variable name to description
    df_all_plot.rename(c_field_list, axis='columns', inplace=True)
    var_list = [c_field_list[var] for var in var_list]

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

    df_plot = df_wide.drop([var for var in df_wide if var not in keeplist])

    keeplist.remove('Date')

    # add horizontal line if we are doing the differences plot
    if s_comparison not in scenario_list:
        return pn.Column(pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_plot.hvplot(
            x='Date',
            ylabel=unit_choice,
            xlabel='Date',
            grid=True,
            min_height=600,
            label='test'
        ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, index=False, max_height=500))

    else:
        return pn.Column(pn.pane.HoloViews(df_plot.hvplot(
            x='Date',
            ylabel=unit_choice,
            xlabel='Date',
            grid=True,
            min_height=600
        ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, index=False, max_height=500))

def plot_time_group(scenario_list, var_list, unit_choice, df_all,
                    c_default_units_all, period_choice, s_comparison,
                    c_field_list, ls_wyt_selected, b_wyt_period_year, li_wyt_period_months):

    df_all_plot = df_all.copy(deep=True)
    df_all_plot.reset_index(inplace=True, drop=True)
    durations = [date.day for date in df_all_plot['Date']]

    # ensure comparison scen is at the end of the list so the coloring is constant with the differences plot
    if s_comparison in scenario_list:
        scenario_list.remove(s_comparison)
        scenario_list.append(s_comparison)

    # check if comparison scen is in the data frame
    # if its not, then we are creating the differences plot and dont want to include comparison scen
    if s_comparison not in df_all_plot.Scenario.unique():
        scenario_list = [scen for scen in scenario_list if scen != s_comparison]

    # check if any scenarios are selected
    if len(scenario_list) == 0:
        return pn.pane.Markdown("## No data to display")

    # check if any variables are selected
    if len(var_list) == 0:
        return pn.pane.Markdown('## Select variables above to display plot.')

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
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

    # switch from variable name to description
    df_all_plot.rename(c_field_list, axis='columns', inplace=True)
    var_list = [c_field_list[var] for var in var_list]

    # if we are sorting by WYT we need to do some work before switching to wide frame
    if (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        # sort for the years we want
        # see if any years are selected
        if not ls_wyt_selected:
            return pn.pane.Markdown("## No data to display")

        # we do have some selected
        # what the column with the wyt is called
        s_wyt_col = c_field_list[period_choice]

        # select just september since that will have the correct wyt
        df_septembers = df_all_plot[df_all_plot['Month'] == 9]

        # pull the years and scenarios that match the selected wyts
        df_wy_to_use = df_septembers[df_septembers[s_wyt_col].isin(ls_wyt_selected)][['Scenario', 'WY', s_wyt_col]]
        # dictionary to hold {(scenario, WY): WYT}
        c_wy_to_wyt = {}
        for index, row in df_wy_to_use.iterrows():
            c_wy_to_wyt[(row['Scenario'], row['WY'])] = row[s_wyt_col]

        # Assign wyt column to be the final wyt
        def wy_to_wyt(wyt_dict, scen, year):
            try:
                return wyt_dict[(scen, year)]
            except:
                return np.nan

        df_all_plot[s_wyt_col] = df_all_plot.apply(lambda row: wy_to_wyt(c_wy_to_wyt, row['Scenario'], row['WY']), axis=1)

    # Sortable, filter to target scenarios and vars
    df_wide = pd.DataFrame(df_all_plot['Date'].unique(), columns=['Date'])
    df_wide[['WY', 'DY', 'Month']] = df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY','Month']].reset_index(drop=True)
    df_wide.reset_index(inplace=True, drop=True)

    #keeplist = ['Date']
    keeplist = []

    # if grouping by wyt we need to include that variable
    if (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        for scenario in scenario_list:
            df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][[s_wyt_col]]
            df_temp.reset_index(inplace=True, drop=True)
            col_names = [f'{scenario}: {s_wyt_col}']
            df_temp.columns = col_names
            df_wide[col_names] = df_temp[col_names]  # WHAT THE HECK
            for name in col_names:
                keeplist.append(name)

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

        # add horizontal line if we are doing the differences plot
        if s_comparison not in scenario_list:
            return pn.Column(pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_plot.hvplot(
                min_height=600,
                grid=True,
                ylabel=unit_choice,
                xlabel=period_choice,
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, max_height=500))
        else:
            return pn.Column(pn.pane.HoloViews(df_plot.hvplot(
                min_height=600,
                grid=True,
                ylabel=unit_choice,
                xlabel=period_choice,
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, max_height=500))

    # if water year type is selected as period
    elif (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        # filter for selected WYTs
        # get rif of anywhere all wyt columns are empty
        df_wide = df_wide.dropna(subset=keeplist[:len(scenario_list)], how='all')

        # check if we ended up with no matching years
        if df_wide.empty:
            return pn.pane.Markdown("## No data to display")

        # if we want to look at water year totals
        if b_wyt_period_year:
            # drop incomplete years
            df_timecounts = df_wide.groupby(by=['WY']).count()
            droplist = df_timecounts[df_timecounts['Date'] < 12].index
            df_wide = df_wide[df_wide['WY'].isin(droplist) == False]

            # Can't sum dates: drop
            df_wide = df_wide.drop('Date', axis=1)

            # get the year totals
            df_grouped = df_wide.groupby(by=['WY']).sum()

            # assign the WYt to be the correct one
            df_grouped[keeplist[:len(scenario_list)]] = df_grouped[keeplist[:len(scenario_list)]]/12

            # get rid of other columns we dont need
            df_plot = df_grouped[keeplist]
        else:
            if len(li_wyt_period_months) == 0:
                return pn.pane.Markdown("## No data to display")
            # first get rid of the years we dont need
            df_wide = df_wide.dropna(subset=keeplist[:len(scenario_list)], how='all')

            # pull out only those months
            df_wide = df_wide[df_wide['Month'].isin(li_wyt_period_months)]

            # drop incomplete years
            df_timecounts = df_wide.groupby(by=['WY']).count()
            droplist = df_timecounts[df_timecounts['Date'] < len(li_wyt_period_months)].index
            df_wide = df_wide[df_wide['WY'].isin(droplist) == False]

            # Can't sum dates: drop
            df_wide = df_wide.drop('Date', axis=1)

            # get the year totals
            df_grouped = df_wide.groupby(by=['WY']).sum()

            # assign the WYt to be the correct one
            df_grouped[keeplist[:len(scenario_list)]] = df_grouped[keeplist[:len(scenario_list)]] / len(li_wyt_period_months)

            # get rid of other columns we dont need
            df_plot = df_grouped[keeplist]
        s_title = "## " + s_wyt_col + " "

        c_wyt_names = {
            'WYT_SAC_': {1: 'Wet', 2: 'Above Normal', 3: 'Below Normal', 4: 'Dry', 5: 'Critically Dry'},
            'WYT_SJR_': {1: 'Wet', 2: 'Above Normal', 3: 'Below Normal', 4: 'Dry', 5: 'Critically Dry'},
            'WYT_TRIN_': {1: 'Extremely Wet', 2: 'Wet', 3: 'Normal', 4: 'Dry', 5: 'Critically Dry'}
        }
        s_title += ', '.join([c_wyt_names[period_choice][wyt] for wyt in ls_wyt_selected]) + ' Years \n'
        if b_wyt_period_year:
            s_title += "## Water Year Total"
        else:
            li_wyt_period_months.sort()
            ls_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            s_title += "## " + ', '.join([ls_months[i-1] for i in li_wyt_period_months])
        # add horizontal line if we are doing the differences plot
        if s_comparison not in scenario_list:

            return pn.Column(s_title, pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_plot.hvplot.scatter(
                y=keeplist[len(scenario_list):], # to avoid plotting the wyt
                min_height=600,
                grid=True,
                ylabel='Water Year',
                xlabel=period_choice,
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, max_height=500))
        else:
            return pn.Column(s_title, pn.pane.HoloViews(df_plot.hvplot.scatter(
                y=keeplist[len(scenario_list):], # to avoid plotting the wyt
                min_height=600,
                grid=True,
                ylabel=unit_choice,
                xlabel='Water Year',
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, max_height=500))

    # selected a month
    else:
        df_wide = df_wide[df_wide.Month == period_choice]
        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=['DY']).sum()
        df_plot = df_grouped[keeplist]

        # add horizontal line if we are doing the differences plot
        if s_comparison not in scenario_list:
            return pn.Column(pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_plot.hvplot(
                y=keeplist[1:],
                min_height=600,
                ylabel=unit_choice,
                xlabel='Year',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, max_height=500))

        else:
            return pn.Column(pn.pane.HoloViews(df_plot.hvplot(
                y=keeplist[1:],
                min_height=600,
                ylabel=unit_choice,
                xlabel='Year',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_plot, max_height=500))


def plot_time_exceedance(scenario_list, var_list, unit_choice, df_all,
                         c_default_units_all, period_choice, s_comparison, c_field_list,
                         ls_wyt_selected, b_wyt_period_year, li_wyt_period_months):

    df_all_plot = df_all.copy(deep=True)
    df_all_plot.reset_index(inplace=True, drop=True)
    durations = [date.day for date in df_all_plot['Date']]

    # ensure comparison scen is at the end of the list so the coloring is constant with the differences plot
    if s_comparison in scenario_list:
        scenario_list.remove(s_comparison)
        scenario_list.append(s_comparison)

    # check if comparison scen is in the data frame
    # if it's not, then we are creating the differences plot and don't want to include comparison scen
    if s_comparison not in df_all_plot.Scenario.unique():
        scenario_list = [scen for scen in scenario_list if scen != s_comparison]

    # check if any scenarios are selected
    if len(scenario_list) == 0:
        return pn.pane.Markdown("## No data to display")

    # check if any variables are selected
    if len(var_list) == 0:
        return pn.pane.Markdown('## Select variables above to display plot.')

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
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

    # switch from variable name to description
    df_all_plot.rename(c_field_list, axis='columns', inplace=True)
    var_list = [c_field_list[var] for var in var_list]

    # if we are sorting by WYT we need to do some work before switching to wide frame
    if (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        # sort for the years we want
        # see if any years are selected
        if not ls_wyt_selected:
            return pn.pane.Markdown("## No data to display")

        # we do have some selected
        # what the column with the wyt is called
        s_wyt_col = c_field_list[period_choice]

        # select just september since that will have the correct wyt
        df_septembers = df_all_plot[df_all_plot['Month'] == 9]

        # pull the years and scenarios that match the selected wyts
        df_wy_to_use = df_septembers[df_septembers[s_wyt_col].isin(ls_wyt_selected)][['Scenario', 'WY', s_wyt_col]]
        # dictionary to hold {(scenario, WY): WYT}
        c_wy_to_wyt = {}
        for index, row in df_wy_to_use.iterrows():
            c_wy_to_wyt[(row['Scenario'], row['WY'])] = row[s_wyt_col]

        # Assign wyt column to be the final wyt
        def wy_to_wyt(wyt_dict, scen, year):
            try:
                return wyt_dict[(scen, year)]
            except:
                return np.nan

        df_all_plot[s_wyt_col] = df_all_plot.apply(lambda row: wy_to_wyt(c_wy_to_wyt, row['Scenario'], row['WY']), axis=1)

    # Sortable, filter to target scenarios and vars
    df_wide = pd.DataFrame(df_all_plot['Date'].unique(), columns=['Date'])
    df_wide[['WY', 'DY', 'Month']] = df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY','Month']].reset_index(drop=True)
    df_wide.reset_index(inplace=True, drop=True)

    # This will allow us to drop the columns used for sorting / aggregating once the
    # final df_plot has been constructed. Eventually we might write some more streamlined
    # code to calculate WY/DY/etc on the fly
    keeplist = []

    # if grouping by wyt we need to include that variable
    if (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        for scenario in scenario_list:
            df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][[s_wyt_col]]
            df_temp.reset_index(inplace=True, drop=True)
            col_names = [f'{scenario}: {s_wyt_col}']
            df_temp.columns = col_names
            df_wide[col_names] = df_temp[col_names]  # WHAT THE HECK
            for name in col_names:
                keeplist.append(name)

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

        df_exceed = pd.DataFrame(index=df_grouped.index)

        # add exceedance probabilities
        i_n = df_grouped.shape[0]
        ld_probabilities = [m/(i_n+1) * 100 for m in range(i_n, 0, -1)]
        df_exceed['exceedance_probability'] = ld_probabilities

        for var in keeplist:
            if var != 'Date':
                l_sorted = df_grouped[var].sort_values().reset_index(drop=True)
                df_exceed[var] = l_sorted


        # add horizontal line if we are doing the differences plot
        if s_comparison not in scenario_list:
            return pn.Column(pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_exceed.hvplot(
                x='exceedance_probability',
                min_height=600,
                ylabel=unit_choice,
                xlabel='Probability of Exceedance',
                flip_xaxis=True,
                xformatter='%f%%',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_exceed, index=False, max_height=500))

        else:
            return pn.Column(pn.pane.HoloViews(df_exceed.hvplot(
                x='exceedance_probability',
                min_height=600,
                ylabel=unit_choice,
                xlabel='Probability of Exceedance',
                flip_xaxis=True,
                xformatter='%f%%',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_exceed, index=False, max_height=500))

    # if water year type is selected as period
    elif (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        # filter for selected WYTs
        # get rif of anywhere all wyt columns are empty
        df_wide = df_wide.dropna(subset=keeplist[:len(scenario_list)], how='all')

        # check if we ended up with no matching years
        if df_wide.empty:
            return pn.pane.Markdown("## No data to display")

            # if we want to look at water year totals
        if b_wyt_period_year:
            # drop incomplete years
            df_timecounts = df_wide.groupby(by=['WY']).count()
            droplist = df_timecounts[df_timecounts['Date'] < 12].index
            df_wide = df_wide[df_wide['WY'].isin(droplist) == False]

            # Can't sum dates: drop
            df_wide = df_wide.drop('Date', axis=1)

            # get the year totals
            df_grouped = df_wide.groupby(by=['WY']).sum()
            df_grouped.reset_index(inplace=True)

            df_exceed = pd.DataFrame(index=df_grouped.index)

            # add exceedance probabilities
            i_n = df_grouped.shape[0]
            ld_probabilities = [m / (i_n + 1) * 100 for m in range(i_n, 0, -1)]
            df_exceed['exceedance_probability'] = ld_probabilities

            for var in keeplist[len(scenario_list):]:
                if var != 'Date':
                    l_sorted = df_grouped[var].sort_values().reset_index(drop=True)
                    df_exceed[var] = l_sorted

        else:
            if len(li_wyt_period_months) == 0:
                return pn.pane.Markdown("## No data to display")

            # first get rid of the years we dont need
            df_wide = df_wide.dropna(subset=keeplist[:len(scenario_list)], how='all')

            # pull out only those months
            df_wide = df_wide[df_wide['Month'].isin(li_wyt_period_months)]

            # drop incomplete years
            df_timecounts = df_wide.groupby(by=['WY']).count()
            droplist = df_timecounts[df_timecounts['Date'] < len(li_wyt_period_months)].index
            df_wide = df_wide[df_wide['WY'].isin(droplist) == False]

            # Can't sum dates: drop
            df_wide = df_wide.drop('Date', axis=1)

            # get the year totals
            df_grouped = df_wide.groupby(by=['WY']).sum()

            df_grouped.reset_index(inplace=True)

            df_exceed = pd.DataFrame(index=df_grouped.index)

            # add exceedance probabilities
            i_n = df_grouped.shape[0]
            ld_probabilities = [m / (i_n + 1) * 100 for m in range(i_n, 0, -1)]
            df_exceed['exceedance_probability'] = ld_probabilities

            for var in keeplist[len(scenario_list):]:
                if var != 'Date':
                    l_sorted = df_grouped[var].sort_values().reset_index(drop=True)
                    df_exceed[var] = l_sorted

        s_title = "## " + s_wyt_col + " "

        c_wyt_names = {
            'WYT_SAC_': {1: 'Wet', 2: 'Above Normal', 3: 'Below Normal', 4: 'Dry', 5: 'Critically Dry'},
            'WYT_SJR_': {1: 'Wet', 2: 'Above Normal', 3: 'Below Normal', 4: 'Dry', 5: 'Critically Dry'},
            'WYT_TRIN_': {1: 'Extremely Wet', 2: 'Wet', 3: 'Normal', 4: 'Dry', 5: 'Critically Dry'}
        }
        s_title += ', '.join([c_wyt_names[period_choice][wyt] for wyt in ls_wyt_selected]) + ' Years \n'
        if b_wyt_period_year:
            s_title += "## Water Year Total"
        else:
            li_wyt_period_months.sort()
            ls_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            s_title += "## " + ', '.join([ls_months[i-1] for i in li_wyt_period_months])

        # add horizontal line if we are doing the differences plot
        if s_comparison not in scenario_list:
            return pn.Column(s_title, pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_exceed.hvplot(
                x='exceedance_probability',
                min_height=600,
                ylabel=unit_choice,
                xlabel='Probability of Exceedance',
                flip_xaxis=True,
                xformatter='%f%%',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_exceed, index=False, max_height=500))

        else:
            return pn.Column(s_title, pn.pane.HoloViews(df_exceed.hvplot(
                x='exceedance_probability',
                min_height=600,
                ylabel=unit_choice,
                xlabel='Probability of Exceedance',
                flip_xaxis=True,
                xformatter='%f%%',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_exceed, index=False, max_height=500))


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

        # add exceedance probabilities
        i_n = df_grouped.shape[0]
        ld_probabilities = [m / (i_n + 1) * 100 for m in range(i_n, 0, -1)]
        df_exceed['exceedance_probability'] = ld_probabilities

        for var in keeplist:
            if var != 'Date':
                l_sorted = df_grouped[var].sort_values().reset_index(drop=True)
                df_exceed[var] = l_sorted



        # add horizontal line if we are doing the differences plot
        if s_comparison not in scenario_list:
            return pn.Column(pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_exceed.hvplot(
                x='exceedance_probability',
                min_height=600,
                ylabel=unit_choice,
                xlabel='Probability of Exceedance',
                flip_xaxis=True,
                xformatter='%f%%',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_exceed, index=False, max_height=500))

        else:
            return pn.Column(pn.pane.HoloViews(df_exceed.hvplot(
                x='exceedance_probability',
                min_height=600,
                ylabel=unit_choice,
                xlabel='Probability of Exceedance',
                flip_xaxis=True,
                xformatter='%f%%',
                grid=True
            ), sizing_mode='stretch_width', linked_axes=False), pn.pane.DataFrame(df_exceed, index=False, max_height=500))

def plot_bars(df_all, period_choice, var_list, scenario_list,
              units_choice, stat_choice, c_default_units, s_comparison, c_field_list,
              ls_wyt_selected, b_wyt_period_year, li_wyt_period_months):

    df_all_plot = df_all.copy(deep=True)
    df_all_plot.reset_index(inplace=True, drop=True)
    durations = [date.day for date in df_all['Date']]

    # ensure comparison scen is at the end of the list so the coloring is constant with the differences plot
    if s_comparison in scenario_list:
        scenario_list.remove(s_comparison)
        scenario_list.append(s_comparison)

    # check if comparison scen is in the data frame
    # if it's not, then we are creating the differences plot and dont want to include comparison scen
    if s_comparison not in df_all.Scenario.unique():
        scenario_list = [scen for scen in scenario_list if scen != s_comparison]

    # check if no scenarios are selected
    if len(scenario_list) == 0:
        return pn.pane.Markdown("## No data to display")

    # check if no variables are selected
    if len(var_list) == 0:
        return pn.pane.Markdown('## Select variables above to display plot.')

    # to convert from cfs to taf or vice versa
    cfs_taf = np.multiply(durations, (24 * 3600 / 43560 / 1000))
    taf_cfs = np.divide((43560 * 1000 / 24 / 3600), durations)

    # Unit conversion
    for var in var_list:
        try:
            original_unit = c_default_units[var].strip()
        except:
            original_unit = None

        if original_unit not in ['CFS', 'TAF']:
            pass
        elif original_unit == units_choice:
            pass
        elif original_unit == 'CFS':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], cfs_taf)
        elif original_unit == 'TAF':
            df_all_plot[var] = \
                np.multiply(df_all_plot[var], taf_cfs)

    # switch from variable name to description
    df_all_plot.rename(c_field_list, axis='columns', inplace=True)
    var_list = [c_field_list[var] for var in var_list]

    # if we are sorting by WYT we need to do some work before switching to wide frame
    if (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        # sort for the years we want
        # see if any years are selected
        if not ls_wyt_selected:
            return pn.pane.Markdown("## No data to display")

        # we do have some selected
        # what the column with the wyt is called
        s_wyt_col = c_field_list[period_choice]

        # select just september since that will have the correct wyt
        df_septembers = df_all_plot[df_all_plot['Month'] == 9]

        # pull the years and scenarios that match the selected wyts
        df_wy_to_use = df_septembers[df_septembers[s_wyt_col].isin(ls_wyt_selected)][['Scenario', 'WY', s_wyt_col]]
        # dictionary to hold {(scenario, WY): WYT}
        c_wy_to_wyt = {}
        for index, row in df_wy_to_use.iterrows():
            c_wy_to_wyt[(row['Scenario'], row['WY'])] = row[s_wyt_col]

        # Assign wyt column to be the final wyt
        def wy_to_wyt(wyt_dict, scen, year):
            try:
                return wyt_dict[(scen, year)]
            except:
                return np.nan

        df_all_plot[s_wyt_col] = df_all_plot.apply(lambda row: wy_to_wyt(c_wy_to_wyt, row['Scenario'], row['WY']), axis=1)

    # Sortable, filter to target scenarios and vars
    df_wide = pd.DataFrame(df_all_plot['Date'].unique(), columns=['Date'])
    df_wide[['WY', 'DY', 'Month']] = df_all_plot.loc[df_all_plot['Scenario'] == scenario_list[0]][['WY', 'DY', 'Month']].reset_index(drop=True)
    df_wide.reset_index(inplace=True, drop=True)

    keeplist = []
    s_title = ''

    # if grouping by wyt we need to include that variable
    if (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        for scenario in scenario_list:
            df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][[s_wyt_col]]
            df_temp.reset_index(inplace=True, drop=True)
            col_names = [f'{scenario}: {s_wyt_col}']
            df_temp.columns = col_names
            df_wide[col_names] = df_temp[col_names]  # WHAT THE HECK
            for name in col_names:
                keeplist.append(name)
    for var in var_list:
        for index, scenario in enumerate(scenario_list):
            df_temp = df_all_plot.loc[df_all_plot['Scenario'] == scenario][[var]]
            df_temp.reset_index(inplace=True, drop=True)
            col_names = [f'{scenario}: {var}']
            df_temp.columns = col_names
            df_wide[col_names] = df_temp[col_names]
            keeplist.append(col_names[0])

    # ------- Agg ops below -------------
    if period_choice in ['WY', 'DY', 'CY']:
        if period_choice == "CY":
            df_wide['CY'] = np.where(df_wide.Month >= 3, df_wide.DY, df_wide.DY - 1)
        df_timecounts = df_wide.groupby(by=[period_choice]).count()
        droplist = df_timecounts[df_timecounts['Date'] < 12].index
        df_wide = df_wide[df_wide[period_choice].isin(droplist) == False]

        # Can't sum dates: drop
        df_wide = df_wide.drop('Date', axis=1)
        df_grouped = df_wide.groupby(by=[period_choice]).sum()
        df_plot = df_grouped[keeplist]

        # calculate chosen stat
        if stat_choice == 'Average':
            df_stats = df_plot.mean().to_frame()
        elif stat_choice == 'Minimum':
            df_stats = df_plot.min().to_frame()
        else:
            df_stats = df_plot.max().to_frame()

    # if water year type is selected as period
    elif (len(str(period_choice)) >= 3) and (period_choice[:3] == 'WYT'):
        # filter for selected WYTs
        # get rif of anywhere all wyt columns are empty
        df_wide = df_wide.dropna(subset=keeplist[:len(scenario_list)], how='all')

        # check if we ended up with no matching years
        if df_wide.empty:
            return pn.pane.Markdown("## No data to display")

        # if we want to look at water year totals
        if b_wyt_period_year:
            # drop incomplete years
            df_timecounts = df_wide.groupby(by=['WY']).count()
            droplist = df_timecounts[df_timecounts['Date'] < 12].index
            df_wide = df_wide[df_wide['WY'].isin(droplist) == False]

            # Can't sum dates: drop
            df_wide = df_wide.drop('Date', axis=1)

            # get the year totals
            df_grouped = df_wide.groupby(by=['WY']).sum()

            # assign the WYt to be the correct one
            df_grouped[keeplist[:len(scenario_list)]] = df_grouped[keeplist[:len(scenario_list)]] / 12

            # get rid of other columns we dont need
            df_plot = df_grouped[keeplist]
        else:
            if len(li_wyt_period_months) == 0:
                return pn.pane.Markdown("## No data to display")
            # first get rid of the years we dont need
            df_wide = df_wide.dropna(subset=keeplist[:len(scenario_list)], how='all')

            # pull out only those months
            df_wide = df_wide[df_wide['Month'].isin(li_wyt_period_months)]

            # drop incomplete years
            df_timecounts = df_wide.groupby(by=['WY']).count()
            droplist = df_timecounts[df_timecounts['Date'] < len(li_wyt_period_months)].index
            df_wide = df_wide[df_wide['WY'].isin(droplist) == False]

            # Can't sum dates: drop
            df_wide = df_wide.drop('Date', axis=1)

            # get the year totals
            df_grouped = df_wide.groupby(by=['WY']).sum()

            # assign the WYt to be the correct one
            df_grouped[keeplist[:len(scenario_list)]] = df_grouped[keeplist[:len(scenario_list)]] / len(li_wyt_period_months)

            # get rid of other columns we dont need
            df_plot = df_grouped[keeplist]
            # calculate chosen stat
        if stat_choice == 'Average':
            df_stats = df_plot[keeplist[len(scenario_list):]].mean().to_frame()
        elif stat_choice == 'Minimum':
            df_stats = df_plot[keeplist[len(scenario_list):]].min().to_frame()
        else:
            df_stats = df_plot[keeplist[len(scenario_list):]].max().to_frame()

        s_title = "## " + s_wyt_col + " "

        c_wyt_names = {
            'WYT_SAC_': {1: 'Wet', 2: 'Above Normal', 3: 'Below Normal', 4: 'Dry', 5: 'Critically Dry'},
            'WYT_SJR_': {1: 'Wet', 2: 'Above Normal', 3: 'Below Normal', 4: 'Dry', 5: 'Critically Dry'},
            'WYT_TRIN_': {1: 'Extremely Wet', 2: 'Wet', 3: 'Normal', 4: 'Dry', 5: 'Critically Dry'}
        }

        s_title += ', '.join([c_wyt_names[period_choice][wyt] for wyt in ls_wyt_selected]) + ' Years \n'
        if b_wyt_period_year:
            s_title += "## Water Year Total"
        else:
            ls_months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
            li_wyt_period_months.sort()
            s_title += "## " + ', '.join([ls_months[i - 1] for i in li_wyt_period_months])

    # Month chosen
    else:
        df_wide = df_wide[df_wide.Month == period_choice]
        df_grouped = df_wide.groupby(by=['Date']).sum()
        df_plot = df_grouped[keeplist]

        # calculate chosen stat
        if stat_choice == 'Average':
            df_stats = df_plot.mean().to_frame()
        elif stat_choice == 'Minimum':
            df_stats = df_plot.min().to_frame()
        else:
            df_stats = df_plot.max().to_frame()

    # calculate bound, pick colors, and plot for all data above
    # Set upper and lower bounds
    if np.min(df_stats) > 0:
        y_lower = 0
    else:
        y_lower = np.min(df_stats) * 1.05
    if np.max(df_stats) > 0:
        y_upper = np.max(df_stats) * 1.05
    else:
        y_upper = 0

    # full list of color options
    ls_colors = ['#003E51', '#007396', '#C69214', '#FF671F', '#215732', '#4C12A1', '#9A3324'] + hv.Cycle.default_cycles["default_colors"]

    # the colors we need, one for each scenario
    if len(scenario_list) >= len(ls_colors):
        # in case we have more scenarios than colors
        ls_colors_to_use = ls_colors
    else:
        ls_colors_to_use = ls_colors[:(len(scenario_list) % len(ls_colors))]

    # pull out how many times we will need to duplicate this list
    i_full_list, i_remainder_list = divmod(df_stats.shape[0], len(ls_colors_to_use))
    ls_colors_to_use = ls_colors_to_use * i_full_list + ls_colors_to_use[:i_remainder_list]
    df_stats['Color'] = ls_colors_to_use

    # add horizontal line if we are doing the differences plot
    if s_comparison not in scenario_list:
        return pn.Column(s_title,
            pn.pane.HoloViews(hv.HLine(0).opts(color='black', line_width=1) * df_stats.hvplot.bar(
                                                                                                  title='',  color='Color', grid=True,
                                                                                                  ylabel=units_choice,
                                                                                                  ylim=(y_lower, y_upper),
                                   min_height=600, legend=False), sizing_mode='stretch_width', linked_axes=False),
            pn.pane.DataFrame(df_plot, max_height=500))

    else:
        return pn.Column(s_title,
            pn.pane.HoloViews(df_stats.hvplot.bar(
                                                  title='',  color='Color', grid=True,
                                                  ylabel=units_choice,
                                                  ylim=(y_lower, y_upper),
                                                  min_height=600), sizing_mode='stretch_width', linked_axes=False),
            pn.pane.DataFrame(df_plot, max_height=500))

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
