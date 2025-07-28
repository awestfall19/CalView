# -------------------------------------------------------------------
# DSS File reader 0.1
# Sam Waers, P.E.; Frankie Nuffer-Rodriguez
#
# Run this file in same directory as dssReadFuncs.py
# See the "import" statements at the top of  in dssReadFuncs.py
# for a list of dependencies which will need to be installed
# in the environment you use for this script.
# -------------------------------------------------------------------
import pandas as pd

# Import data handling functions from our local module
from csdss_readlib_fullfile import file_reader, pickler, load_pickles, get_trend_fields
from cs3_plotlib import plot_values, plot_time_group, plot_time_exceedance, plot_bars, monthly_pattern
import panel as pn
import os
from os import path
import holoviews as hv

#TODO
#Put in code to pickle visualized scenario, make sure it includes user run names

# NOTE: need to use name/main for Pool to work outside of script
pn.extension(sizing_mode='stretch_width')
pn.extension(notifications=True)

# change default colors to first go through Reclamation colors and then original default colors for line plots
hv.opts.defaults(hv.opts.Curve(color=hv.Cycle(['#003E51', '#007396', '#C69214', '#FF671F', '#215732', '#4C12A1', '#9A3324'] + hv.Cycle.default_cycles["default_colors"])))
hv.opts.defaults(hv.opts.Bars(color=hv.Cycle(['#003E51', '#007396', '#C69214', '#FF671F', '#215732', '#4C12A1', '#9A3324'] + hv.Cycle.default_cycles["default_colors"])))
hv.opts.defaults(hv.opts.Scatter(color=hv.Cycle(['#003E51', '#007396', '#C69214', '#FF671F', '#215732', '#4C12A1', '#9A3324'] + hv.Cycle.default_cycles["default_colors"])))

#Visualizer formatting code

# path for the compiled executable to find logo
s_logo_path = path.abspath(path.join(path.dirname(__file__), 'usbr_logo.jpg'))

template = pn.template.BootstrapTemplate(
    title="DSS Results Viewer for CalSim 3",
    logo=s_logo_path,
    header_background='white',
    header_color='black'
)

# Create row that can be added to template to refresh header(template itself is static)
header = pn.Row()
# Now the row can be edited in trigger functions and will refresh to show header/sliders after file picker tab
template.main.append(header)

#create a row to hols the tabs
tabs_row = pn.Row()
template.main.append(tabs_row)

# Define a Panel Column to hold widgets for the file picker tab
file_picker_column = pn.Column()
col_tracker = []
#Define panel file_picker_column to hold file name text input
run_name_column = pn.Column()
run_name_col_tracker = []
#Define panel file_picker_column to hold field selector drop down
field_column = pn.Column()
field_col_tracker = []

#Initialize columns for additional tabs after file picker tab
#These will be filled in by the upate_run_names function when the other tabs are enabled after user has completed file picker
single_var_plots = pn.Column()
timeseries_plots = pn.Row()
grouped_plots = pn.Row()
exceedance_plots = pn.Row()
monthly_plots = pn.Column()
def update_dss_file_widget(event):
    global file_picker_column  # Access the global variable
    if event.name == "value":
        file_picker_column.pop(col_tracker.index("dss_file"))  # Remove the dss_file widget
        col_tracker.remove("dss_file")
        file_picker_column.pop(col_tracker.index("instructions"))
        col_tracker.remove("instructions")

        #Add back dss_file widget with updated file pattern
        if event.new == "New CalSim outputs":
            o_instructions = pn.pane.Markdown("### Select the DSS files to be read in.")
            o_instructions_tooltip = pn.widgets.TooltipIcon(value="Move all DSS files from 'File Browser' section to 'Selected files' section then click 'Continue'")
            dss_file = pn.widgets.FileSelector(
                name='Select CalSim output DSS file for new run or pickle file for previous run',
                file_pattern = "*.dss",
                only_files=True,
                max_width=1000,
                root_directory=os.path.abspath(os.sep)
            )
        else:
            o_instructions = pn.pane.Markdown('### <span style="color:red">Select the pickle files previously created (diffs.pkl, units.pkl, values.pkl, and fields.pkl)</span>')
            o_instructions_tooltip = pn.widgets.TooltipIcon(value="Move the four pkl files from 'File Browser' section to 'Selected files' section then click 'Continue'")
            dss_file = pn.widgets.FileSelector(
                name='Select CalSim output DSS file for new run or pickle file for previous run',
                file_pattern="*.pkl",
                only_files=True,
                max_width=1000,
                root_directory=os.path.abspath(os.sep)
            )

        # replace widget and instructions
        file_picker_column.insert(2, pn.Row(o_instructions, o_instructions_tooltip))
        col_tracker.insert(2, "instructions")
        file_picker_column.insert(3, dss_file)
        col_tracker.insert(3, "dss_file")

    file_picker_column.param.trigger("objects")  # Trigger UI update

def add_run_names_widget(event):
    # print(event)
    global file_picker_column
    global col_tracker
    global run_name_column
    global run_name_col_tracker
    global field_column
    global field_col_tracker

    # look for old error message and remove
    if 'error_message' in field_col_tracker:
        error_index = field_col_tracker.index('error_message')
        field_column.pop(error_index)
        field_col_tracker.pop(error_index)

    # check if we have already pressed the button and remove everything if so
    if 'add_field_text' in field_col_tracker:
        for _ in range(len(field_col_tracker)):
            field_col_tracker.pop(0)
            field_column.pop(0)
        for _ in range(len(run_name_col_tracker)):
            run_name_col_tracker.pop(0)
            run_name_column.pop(0)


    files = file_picker_column[col_tracker.index("dss_file")].value

    # Check if user is running previous scenario or new
    if len(files) > 0:
        if "dss" in files[0].rsplit(".", 1)[1]:
            run_name_instructions = pn.pane.Markdown(""" 
                # Enter a run name for each file (e.g. Baseline, Alt1, etc.). 
                """, renderer='markdown'
                                                     )
            run_name_instructions_comparison = pn.pane.Markdown("""                
                ## <span style="color:red">One run must be marked for comparison.</span>
                """, renderer='markdown'
                                                                )
            run_name_instructions_tooltip = pn.widgets.TooltipIcon(value='A plot of differences will be created based off this scenario.')
            run_name_column.append(pn.Column(run_name_instructions, pn.Row(run_name_instructions_comparison, run_name_instructions_tooltip)))
            run_name_col_tracker.append("run_name_instructions")

            #have user provide run names for each file, new scenario has been selected
            for file in files:
                dss_run_file_label = pn.pane.Markdown("### File name: " + file)

                comparison_check = pn.widgets.Checkbox(name='Comparison scenario')
                dss_run_name = pn.widgets.TextInput(max_width=500, placeholder='Enter name for file')
                dss_run_name_tooltip = pn.widgets.TooltipIcon(value='Enter the name you want displayed for this run.')

                run_name_column.append(dss_run_file_label)
                run_name_col_tracker.append("dss_run_file_label")
                run_name_column.append(comparison_check)
                run_name_col_tracker.append("dss_comparison_checkbox")
                run_name_column.append(pn.Row(dss_run_name, dss_run_name_tooltip))
                run_name_col_tracker.append("dss_run_name")

        #using picked files
        else:
            # check to make sure all pickle files have been selected
            b_diffs_flag = False
            b_values_flag = False
            b_units_flag = False
            b_fields_flag = False
            for file in files:
                if 'diffs.pkl' in file:
                    b_diffs_flag = True
                if 'values.pkl' in file:
                    b_values_flag = True
                if 'units.pkl' in file:
                    b_units_flag = True
                if 'fields.pkl' in file:
                    b_fields_flag = True
            if not (b_units_flag and b_diffs_flag and b_values_flag and b_fields_flag):
                error_message = pn.pane.Markdown("## Make sure all pickle files are selected.")
                field_column.append(error_message)
                field_col_tracker.append("error_message")
                return
            # no need for fields section, just start pulling the files
            update_run_names(event)

        # add option to override TR_fields.txt
        override_TR_fields_instructions = pn.pane.Markdown("""
        # OPTIONAL override default fields:""", renderer='markdown')
        override_TR_fields_instructions_deatils = pn.pane.Markdown("""
        
        ## If you would like to override the built in default fields, select a text file with your preferred fields.
        
        ### Each line must be a field with the variable name followed by a space or tab followed by the description of the variable. This is the default format if copied and pasted from an excel sheet.
        
        ### Example:
        
        > S_FOLSM Folsom Storage
        >
        > S_SHSTA Shasta Storage
        >
        > ...
        """, renderer='markdown')
        override_TR_fields_instructions_tooltip = pn.widgets.TooltipIcon(value='A default list of fields and descriptions is built in. If you want to override this list, upload a new list here. If no file is selected, the built-in list is used.')
        field_column.append(pn.Column(pn.Row(override_TR_fields_instructions, override_TR_fields_instructions_tooltip), override_TR_fields_instructions_deatils))
        field_col_tracker.append("override_instructions")

        override_file = pn.widgets.FileInput(accept='.txt', multiple=False, max_width=500)

        field_column.append(override_file)
        field_col_tracker.append("override_file")

        #Also add optional field add text box
        add_field_instructions = pn.pane.Markdown("""
        # OPTIONAL additional fields: """, renderer='markdown')
        add_field_instructions_details = pn.pane.Markdown("""
        
        ## Add additional fields to visualize that are not present in the default list (or your chosen list). 
        
        ### Each line is a field with the variable name followed by a space or tab followed by the description of the variable. This is the default format if copied and pasted from an excel sheet.
        
        ### Example:
        
        > S_FOLSM Folsom Storage
        >
        > S_SHSTA Shasta Storage
        >
        >...
        
        """, renderer='markdown')
        add_field_instructions_tooltip = pn.widgets.TooltipIcon(value='If you want to include fields that are not in the default list, add them here. If left blank, only the default list will be pulled from files.')
        field_column.append(pn.Column(pn.Row(add_field_instructions, add_field_instructions_tooltip), add_field_instructions_details))
        field_col_tracker.append("add_field_instructions")

        add_field_text = pn.widgets.TextAreaInput(name='', placeholder='S_FOLSM\tFolsom Storage\nS_SHSTA\tShasta Storage', auto_grow=True, width=500)

        field_column.append(add_field_text)
        field_col_tracker.append("add_field_text")

        # Add another continue button for when user is done adding run names to files
        done_naming = pn.widgets.Button(name="Continue", width=500, button_type='primary')
        # When user is done adding file/run names, save inputs to variables
        done_naming.on_click(update_run_names)

        field_column.append(done_naming)
        field_col_tracker.append("done_naming")

    #Refresh field file_picker_column
    field_column.param.trigger("objects")

    #Refresh run names file_picker_column
    run_name_column.param.trigger("objects")  # Trigger UI update

def update_run_names(event):
    global file_picker_column
    global col_tracker
    global run_name_column
    global run_name_col_tracker
    global field_column
    global field_col_tracker
    global file_picker_display
    global s_comparison

    # Get selected files
    files = file_picker_column[col_tracker.index("dss_file")].value  # Access the global variable

    # look for old error message and remove
    if 'error_message' in field_col_tracker:
        error_index = field_col_tracker.index('error_message')
        field_column.pop(error_index)
        field_col_tracker.pop(error_index)

    #check if we have exactl one file marked for comparison and if not give an error
    if sum([run_name_column[i].value for i, x in enumerate(run_name_col_tracker) if x == "dss_comparison_checkbox"]) != 1 and "dss" in files[0].rsplit(".",1)[1]:
        error_message = pn.pane.Markdown("## Please make sure that exactly one file is marked for comparison.")
        field_column.append(error_message)
        field_col_tracker.append('error_message')
        return

    # row to indicate that the files are being read and it is loading
    loading_row = pn.Row(pn.indicators.LoadingSpinner(
                value=True, height=30, width=30, color="primary"
            ), pn.pane.Markdown("""
            ## Loading in data. New files will take longer than previously generated visuals.
            
            ### Once new files have been read in, they will be saved to pickle files that can be used on the previously generated visuals tab for faster startup.
            """))
    field_column.append(loading_row)
    field_col_tracker.append('loading_row')

    #Check if files are dss or pkl (new or old scenario)
    if "dss" in files[0].rsplit(".",1)[1]:
        # Get indices of dss run names
        dss_name_indices = [i for i, x in enumerate(run_name_col_tracker) if x == "dss_run_name"]
        # get the value of the checkbox for each run
        comparison_indices = [run_name_column[i].value for i, x in enumerate(run_name_col_tracker) if x == "dss_comparison_checkbox"]

        # Get file names
        files = file_picker_column[col_tracker.index("dss_file")].value

        # Get default fields and any added ones
        # pulling from TR_fields.txt
        c_tr_fields = get_trend_fields()

        # get the overridden fields
        override_TR_fields = field_column[field_col_tracker.index("override_file")].value
        c_override_fields = {}
        if override_TR_fields:
            override_TR_fields_text = override_TR_fields.decode()
            for line in override_TR_fields_text.split('\n'):
                line = line.strip()
                new_field = line.split(maxsplit=1)
                if len(new_field) == 0:
                    continue
                elif len(new_field) == 1:
                    field = new_field[0]
                    field = field.strip(' ').upper()
                    if field in c_tr_fields.keys():
                        c_override_fields[field] = c_tr_fields[field]
                    else:
                        c_override_fields[field] = field
                else:
                    field, description = new_field

                    field = field.strip(' ').upper()
                    description = description.strip('\n')
                    description = description + ' (' + field + ')'
                    c_override_fields[field] = description

        # to hold the ones entered in the optional field
        c_new_fields = {}
        if field_column[field_col_tracker.index("add_field_text")].value != '':
            for line in field_column[field_col_tracker.index("add_field_text")].value.split('\n'):
                line = line.strip()
                new_field = line.split(maxsplit=1)
                if len(new_field) == 0:
                    continue
                elif len(new_field) == 1:
                    field = new_field[0]
                    field = field.strip(' ').upper()
                    c_new_fields[field] = field
                else:
                    field, description = new_field

                    field = field.strip(' ').upper()
                    description = description.strip('\n')
                    description = description + ' (' + field + ')'
                    c_new_fields[field] = description
        if override_TR_fields:
            c_field_list = c_override_fields | c_new_fields
        else:
            c_field_list = c_tr_fields | c_new_fields
        runs = []

        #Pair file names with user entered run names
        for file_index, run_index in enumerate(dss_name_indices):
            # structure of runs is [["Description_1", ("File_1.dss")],
            #               ["Description_2", ("File_2.dss")],
            #          ...  ["Description_n", ("File_n.dss")]]
            # The names can be anything though, e.g. ["Alt2v1", Alt2v1_VAs.dss"]

            # find where the box is checked for comparison and set somparison name tracker to files name
            if comparison_indices[file_index]:
                # update global variable
                s_comparison = run_name_column[run_index][0].value

            runs.append([run_name_column[run_index][0].value, (files[file_index])])
        print(runs)
        append_list, baseline_stack, c_default_units, c_field_list = file_reader(runs, c_field_list, s_comparison)
        pickler(append_list, baseline_stack, c_default_units, c_field_list)

        # This runs no matter what. The pickle files allow you to come back and
        # pull the same variables without waiting for the file reads to complete
        df_all_data, df_diffs, c_default_units, c_field_list = load_pickles([])

        # Write to Excel.
        # try:
        #     df_all_data.to_excel("DSS_contents.xlsx")
        # except:
        #     print("Error writing output file. ")

        print(f'Pulled: {len(runs)} files')
        print(runs)

    #Load pickles from previous run
    else:
        df_all_data, df_diffs, c_default_units, c_field_list = load_pickles(files)

    # need to pull comparison scenario from un pickled files
    s_comparison = c_default_units['comparison scenario']

    #Now that pickles have been created/loaded, move forward with initiating other tabs
    scenario_names = df_all_data['Scenario'].unique().tolist()

    # removing loading before adding tabs
    loading_index = field_col_tracker.index('loading_row')
    field_column.pop(loading_index)
    field_col_tracker.pop(loading_index)
    field_column.param.trigger("objects")

    #Fill in widgets for other tabs
    create_widgets(scenario_names, c_field_list, df_all_data, c_default_units, df_diffs)

    # once we have the widgets and graphs, remove the file picker
    for _ in range(len(file_picker_display)):
        file_picker_display.pop(0)

def create_plot_title(s_title, s_comparison='', s_period='', s_stat=''):
    """
    To create the titles for the plots that change when values are updated
    """
    c_period_code_to_name = {"JanDecYear": "January-December", "OctSeptYear": "October-September", "MarFebYear": "March-February",
                             1: "January", 2: "February", 3: "March", 4: "April",
                             5: "May", 6: "June", 7: "July", 8: "August",
                             9: "September", 10: "October", 11: "November", 12: "December",
                             '11-3': 'November-March', '8-10': 'August-October', '10-1': 'October-January',
                             '12-2': 'December-February', '3-5': 'March-May', '3-6': 'March-June',
                             '6-9': 'June-September', '9-11': 'September-November'
                             }
    s_final_title = "# "
    if s_stat:
         s_final_title += s_stat + ' Value ' + s_title
    else:
        s_final_title += s_title
    if s_comparison:
        s_final_title += " (Difference from " + s_comparison + ")"
    if s_period:
        if s_period in c_period_code_to_name.keys():
            s_final_title += " (" + c_period_code_to_name[s_period] + ")"
        # this is when we are grouping by wyt
        else:
            s_final_title += " (Water Year Type)"
    return pn.pane.Markdown(s_final_title)

def hide_show_wyt(event):
    global header

    # make sure that the header has been populated
    if len(header) > 2:
        # check if a WYT is selected
        if (len(str(event.new)) >= 3) and (event.new[:3] == 'WYT'):
            # turn on the visibility
            header[2][1].visible = True
        elif event.new == 'SHASTABIN_':
            header[2][1].visible = True
        else:
            # turn it off
            header[2][1].visible = False
    return


def update_wyt_names(target, event):
    if event.new != event.old:
        if (len(str(event.new)) >= 3 and event.new[:3] == 'WYT') or event.new == 'SHASTABIN_':
            c_wyt_names = {
                'WYT_SAC_': {'Wet': 1, 'Above Normal': 2, 'Below Normal': 3, 'Dry': 4, 'Critically Dry': 5},
                'WYT_SJR_': {'Wet': 1, 'Above Normal': 2, 'Below Normal': 3, 'Dry': 4, 'Critically Dry': 5},
                'WYT_TRIN_': {'Extremely Wet': 1, 'Wet': 2, 'Normal': 3, 'Dry': 4, 'Critically Dry': 5},
                'WYT_SHASTA_CVP_': {'Non-Critical': 0, 'ShastaCritical': 1},
                'WYT_FEATHER_': {'Non-Critical': 1, 'Critically Dry': 2},
                'WYT_SJRRP_DV': {'Wet': 1, 'Normal-Wet': 2, 'Normal-Dry': 3, 'Dry': 4, 'Critical High': 5, 'Critical Low': 6},
                'WYT_AMERD983_CVP_': {'Non-Critical': 1, 'Critically Dry': 2},
                'SHASTABIN_': {'1a': 1, '1b': 2, '2a': 3, '2b': 4, '3a': 5, '3b': 6},
                'Default': [1, 2, 3, 4, 5]
            }
            try:
                target.options = c_wyt_names[event.new]
                target.value = list(c_wyt_names[event.new].values())
            except:
                target.options = c_wyt_names['Default']
                target.value = c_wyt_names['Default']
    return


def wyt_period_toggle(target, event):
    # disable months if the button is toggled
    target.disabled = event.new


def create_widgets(scenario_names, c_field_list, df_all_data, c_default_units, df_diffs):
    global single_var_plots
    global grouped_plots
    global exceedance_plots
    global timeseries_plots
    global monthly_plots
    global header
    global tabs_row
    global s_comparison

    # Select which alts to examine
    scen_selector = pn.widgets.MultiChoice(
        name='Scenario Selector',
        options=scenario_names,
        value=scenario_names,
        option_limit=len(scenario_names),
        search_option_limit=len(scenario_names),
        width=400
    )


    unit_selector = pn.widgets.RadioButtonGroup(
        name='Units selector',
        options=['TAF', 'CFS'],
        button_style='outline',
        button_type='primary',
        width=200,
        margin=32
    )

    period_selector = pn.widgets.Select(
        name='Period Selector',
        groups={'Year': {"January-December": "JanDecYear", "October-September": "OctSeptYear", "March-February": "MarFebYear"},
                'Month': {"January": 1, "February": 2, "March": 3, "April": 4,
                          "May": 5, "June": 6, "July": 7, "August": 8,
                          "September": 9, "October": 10, "November": 11, "December": 12},
                "Partial Year": {'November-March': '11-3', 'August-October': '8-10', 'October-January': '10-1',
                                 'December-February': '12-2', 'March-May': '3-5', 'March-June': '3-6',
                                 'June-September': '6-9', 'September-November': '9-11'},
                'Water Year Type': {description: wyt for wyt, description in c_field_list.items() if len(wyt) >=3 and wyt[:3] == 'WYT'},
                '': {description: var for var, description in c_field_list.items() if var == 'SHASTABIN_'}
                },
        width=300
    )

    wyt_selector = pn.widgets.CheckButtonGroup(
        name='Water Year Type',
        options={'Wet': 1, 'Above Normal': 2, 'Below Normal': 3, 'Dry': 4, 'Critically Dry': 5},
        button_type='primary',
        button_style='outline'
    )

    wyt_period_selector = pn.widgets.CheckButtonGroup(
        name='WYT Period Selector',
        options={"January": 1, "February": 2, "March": 3, "April": 4,
                    "May": 5, "June": 6, "July": 7, "August": 8,
                   "September": 9, "October": 10, "November": 11, "December": 12
                   },
        button_type='primary',
        button_style='outline'
    )
    wyt_period_selector_year = pn.widgets.Toggle(
        name='Water Year Total',
        button_type='primary',
        button_style='outline')

    # to update the visibility when period is changed
    wyt_watcher = period_selector.param.watch(hide_show_wyt, 'value')

    # to update the names when the period is changed
    wyt_names_linked = period_selector.link(wyt_selector, callbacks={'value': update_wyt_names})

    wyt_period_linked = wyt_period_selector_year.link(wyt_period_selector, callbacks={'value': wyt_period_toggle})

    period_selector.param.trigger('value')

    # for the field names we need a diction of {description: field}
    c_description_to_field = {description: field for field, description in c_field_list.items()}

    # Select the variables (no water year types)
    var_selector = pn.widgets.MultiChoice(
        name='Variable Selector',
        options=c_description_to_field,
        value=[list(c_description_to_field.values())[0]],
        option_limit=len(list(c_description_to_field.keys())),
        search_option_limit=len(list(c_description_to_field.keys())),
        width=400
    )

    bar_stat_sel = pn.widgets.Select(
        name='Statistic Selector',
        options=['Average', 'Minimum', 'Maximum',
                 '90% Exceedence Probability', '75% Exceedence Probability', '50% Exceedence Probability',
                 '25% Exceedence Probability', '10% Exceedence Probability'],
        width=400
    )

    monthly_stat_sel = pn.widgets.Select(
        name='Statistic Selector',
        options=['Average', 'Minimum', 'Maximum',
                 '90% Exceedence Probability', '75% Exceedence Probability', '50% Exceedence Probability',
                 '25% Exceedence Probability', '10% Exceedence Probability'],
        width=400
    )

    exceedance_show_year_check = pn.widgets.Checkbox(name='Show year in table')
    exceedance_show_year_check_diffs = pn.widgets.Checkbox(name='Show year in table')

    # remove comparison scen from the differences dataframe as all values are zero
    df_diffs = df_diffs[df_diffs.Scenario != s_comparison]

    bound_plot_ts = pn.bind(
        plot_values,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_all_data,
        c_default_units=c_default_units,
        s_comparison=s_comparison,
        c_field_list=c_field_list
    )

    bound_plot_diffs_ts = pn.bind(
        plot_values,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_diffs,
        c_default_units=c_default_units,
        s_comparison=s_comparison,
        c_field_list=c_field_list
    )

    bound_plot_grouped = pn.bind(
        plot_time_group,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_all_data,
        c_default_units=c_default_units,
        period_choice=period_selector,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        li_wyt_selected=wyt_selector,
        b_wyt_period_year=wyt_period_selector_year,
        li_wyt_period_months=wyt_period_selector
    )

    bound_plot_grouped_diff = pn.bind(
        plot_time_group,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_diffs,
        c_default_units=c_default_units,
        period_choice=period_selector,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        li_wyt_selected=wyt_selector,
        b_wyt_period_year=wyt_period_selector_year,
        li_wyt_period_months=wyt_period_selector
    )

    bound_plot_exceedance = pn.bind(
        plot_time_exceedance,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_all_data,
        c_default_units=c_default_units,
        period_choice=period_selector,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        li_wyt_selected=wyt_selector,
        b_wyt_period_year=wyt_period_selector_year,
        li_wyt_period_months=wyt_period_selector,
        b_show_year=exceedance_show_year_check
    )

    bound_plot_diffs_exceedance = pn.bind(
        plot_time_exceedance,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_diffs,
        c_default_units=c_default_units,
        period_choice=period_selector,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        li_wyt_selected=wyt_selector,
        b_wyt_period_year=wyt_period_selector_year,
        li_wyt_period_months=wyt_period_selector,
        b_show_year=exceedance_show_year_check_diffs
    )

    bound_single_var_plot = pn.bind(
        plot_bars,
        df_all=df_all_data,
        period_choice=period_selector,
        var_list=var_selector,
        scenario_list=scen_selector,
        unit_choice=unit_selector,
        stat_choice=bar_stat_sel,
        c_default_units=c_default_units,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        li_wyt_selected=wyt_selector,
        b_wyt_period_year=wyt_period_selector_year,
        li_wyt_period_months=wyt_period_selector
    )

    bound_single_var_diff_plot = pn.bind(
        plot_bars,
        df_all=df_diffs,
        period_choice=period_selector,
        var_list=var_selector,
        scenario_list=scen_selector,
        unit_choice=unit_selector,
        stat_choice=bar_stat_sel,
        c_default_units=c_default_units,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        li_wyt_selected=wyt_selector,
        b_wyt_period_year=wyt_period_selector_year,
        li_wyt_period_months=wyt_period_selector
    )

    bound_monthly_plot = pn.bind(
        monthly_pattern,
        df_all=df_all_data,
        var_list=var_selector,
        scenario_list=scen_selector,
        unit_choice=unit_selector,
        stat_choice=monthly_stat_sel,
        c_default_units=c_default_units,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        period_choice=period_selector,
        li_wyt_selected=wyt_selector
    )

    bound_monthly_diffs_plot = pn.bind(
        monthly_pattern,
        df_all=df_diffs,
        var_list=var_selector,
        scenario_list=scen_selector,
        unit_choice=unit_selector,
        stat_choice=monthly_stat_sel,
        c_default_units=c_default_units,
        s_comparison=s_comparison,
        c_field_list=c_field_list,
        period_choice=period_selector,
        li_wyt_selected=wyt_selector
    )

    ts_title = pn.pane.Markdown("# Timeseries Plot"
                                )

    diffs_ts_title = pn.pane.Markdown("# Timeseries Plot (Difference from " + s_comparison + ")"
                                      )

    grouped_title = pn.bind(create_plot_title,
                            s_title="Time-Aggregated Plot",
                            s_comparison='',
                            s_period=period_selector)

    grouped__diff_title = pn.bind(create_plot_title,
                            s_title="Time-Aggregated Plot",
                            s_comparison=s_comparison,
                            s_period=period_selector)

    exceedance_title = pn.bind(create_plot_title,
                               s_title="Exceedance Plot",
                               s_comparison='',
                               s_period=period_selector)

    exceedance_diff_title = pn.bind(create_plot_title,
                             s_title="Exceedance Plot",
                             s_comparison=s_comparison,
                             s_period=period_selector)

    single_var_title = pn.bind(create_plot_title,
                               s_title="Bar Plot",
                               s_comparison='',
                               s_period=period_selector,
                               s_stat=bar_stat_sel)

    single_var_diff_title = pn.bind(create_plot_title,
                                    s_title="Bar Plot",
                                    s_comparison=s_comparison,
                                    s_period=period_selector,
                                    s_stat=bar_stat_sel)

    monthly_title = pn.bind(create_plot_title,
                            s_title="Monthly Pattern",
                            s_stat=monthly_stat_sel)

    monthly_diffs_title = pn.bind(create_plot_title,
                            s_title="Monthly Pattern",
                            s_comparison=s_comparison,
                            s_stat=monthly_stat_sel)

    # metadata for meta data tab
    run_names = {scen: c_default_units[scen] for scen in scenario_names}
    df_run_names = pd.DataFrame.from_dict(run_names, orient='index', columns=['File Name'])
    df_run_names.index.name = 'Scenario Name'

    o_scen_names_title = pn.pane.Markdown("# Files and names")

    df_field_names = pd.DataFrame.from_dict(c_field_list, orient='index', columns=['Description'])
    df_field_names.index.name = 'Field'
    df_field_names['Default Units'] = df_field_names.index.map(c_default_units)

    o_field_names_title = pn.pane.Markdown("# Fields and descriptions")


    c_calcs_for_calculated = {
        'Total System Storage SWP and CVP': 'S_TRNTY + S_SHSTA + S_OROVL + S_FOLSM + S_SLUIS_CVP + S_SLUIS_SWP',
        'Total Exports SWP and CVP': 'C_CAA003_SWP + C_DMC003 + C_CAA003_CVP',
        'Total San Luis Storage SWP and CVP': 'S_SLUIS_CVP + S_SLUIS_SWP',
        'Flow Shortage on Sac Reg for Salinity': 'MAX(MAX(RSREQSACDV, JPREQSACDV, EMREQSACDV, COREQSACDV) - (C_SAC041 + SP_SAC083_YBP037), 0)',
        'Flow Shortage on X2 Delta Req Outflow': 'MAX(MRDO_FINALDV - NDOI, 0)',
        'MRDO_SHORT': 'MRDO_FINALDV - NDOI_MIN',
        'Combined Madera and Friant-Kern Canals Diversion': 'D_MLRTN_FRK000 + D_MLRTN_MDC006',
        'Stanislaus River Delivery - Oakdale North / SSJID 1+2': 'D_STS059_OAK001 + D_SSJ004_61_PA1 + D_WDWRD_61_PA3 + D_WTPDGT_61_NU2',
        'CVP Delivery Total': 'DEL_CVP_TOTAL_N + DEL_CVP_TOTAL_S',
        'CVP Delivery PMI N (w CCWD)': 'DEL_CVP_PMI_N + D420',
        'CVP Delivery North (w CCWD)': 'DEL_CVP_TOTAL_N - DEL_CVP_PMI_N + DEL_CVP_PMI_N_WAMR + D420'
    }
    c_used_calc_fields = {field: c_calcs_for_calculated[field] for field in c_calcs_for_calculated if field in c_field_list.keys()}
    df_calc_fields = pd.DataFrame.from_dict(c_used_calc_fields, orient='index', columns=['Formula'])
    df_calc_fields.index.name = 'Calculated Field'

    o_calc_field_title = pn.pane.Markdown("# Calculated Fields")

    o_metadata = pn.Column(
        o_scen_names_title,
        pn.pane.DataFrame(df_run_names),
        pn.Row(
            pn.Column(
                o_field_names_title,
                pn.pane.DataFrame(df_field_names)
            ),
            pn.Column(
                o_calc_field_title,
                pn.pane.DataFrame(df_calc_fields)
            )
        )

    )

    #Add selectors to header row in template and refresh objects
    header.append(scen_selector)
    header.append(var_selector)
    header.append(pn.Column(period_selector, pn.Column(wyt_selector, pn.Row(wyt_period_selector_year, wyt_period_selector), visible=False), max_width=300))
    header.append(unit_selector)
    header.param.trigger("objects")

    single_var_widgets = pn.Row(bar_stat_sel)

    single_var_plots.append(single_var_widgets)
    single_var_plots.append(pn.Row(pn.Column(single_var_title,bound_single_var_plot),pn.Column(single_var_diff_title,bound_single_var_diff_plot)))

    timeseries_plots.append(pn.Column(ts_title,bound_plot_ts))
    timeseries_plots.append(pn.Column(diffs_ts_title,bound_plot_diffs_ts))

    grouped_plots.append(pn.Column(grouped_title,bound_plot_grouped))
    grouped_plots.append(pn.Column(grouped__diff_title,bound_plot_grouped_diff))

    exceedance_plots.append(pn.Column(exceedance_title, bound_plot_exceedance, exceedance_show_year_check))
    exceedance_plots.append(pn.Column( exceedance_diff_title, bound_plot_diffs_exceedance, exceedance_show_year_check_diffs))

    monthly_plots.append(pn.Row(monthly_stat_sel))
    monthly_plots.append(pn.Row(pn.Column(monthly_title, bound_monthly_plot), pn.Column(monthly_diffs_title, bound_monthly_diffs_plot)))

    tabs = pn.Tabs(
        ('Bar Plot', single_var_plots),
        ('Timeseries', timeseries_plots),
        ('Time-Aggregated', grouped_plots),
        ('Exceedance', exceedance_plots),
        ('Monthly Pattern', monthly_plots),
        ('Metadata', o_metadata)
    )

    tabs_row.append(tabs)
    tabs_row.param.trigger("objects")

make_archive = False

# This is a list of the variables you want to retrieve.
# These correspond to the B part in the DSS pathname.
# Variables that are not present in all runs are thrown out
# though this behavior can be changed if needed.

###### File Picker Tab code ##################
#Title for file picker tab
file_picker_title = pn.pane.Markdown("""
    # Select Files
""")
file_picker_title_tooltip = pn.widgets.TooltipIcon(value='Once a set of DSS files have been read in the first time, they are saved to .pkl files that are much quicker to read in later. Note that you cannot pull additional fields when using the pkl files, the DSS files must be re-read in.', margin=0)

#Create radio button widget to select running with old or new scenario
old_new_sel = pn.widgets.RadioButtonGroup(
    #name='',
    value="New CalSim outputs",
    button_style='outline',
    button_type='primary',
    options=["New CalSim outputs", "Previously generated visuals"],
    max_width=1000
)

#Create file selector widget
o_instructions = pn.pane.Markdown("### Select the DSS files to be read in.")
o_instructions_tooltip = pn.widgets.TooltipIcon(value="Move all DSS files from 'File Browser' section to 'Selected files' section then click 'Continue'")
dss_file = pn.widgets.FileSelector(
    name='Select CalSim output DSS file for new run or pickle file for previous run',
    file_pattern = "*.dss",
    only_files=True,
    max_width=1000,
    root_directory=os.path.abspath(os.sep)
)

#Add all widgets to file_picker_column
file_picker_column.append(pn.Row(file_picker_title, file_picker_title_tooltip))
col_tracker.append("file_picker_title")
file_picker_column.append(old_new_sel)
col_tracker.append("old_new_sel")
file_picker_column.append(pn.Row(o_instructions, o_instructions_tooltip))
col_tracker.append("instructions")
file_picker_column.append(dss_file)
col_tracker.append("dss_file")

#Watch the old_new_sel widget and call remove_widget function to update dss_file if a change event occurs
choice_watcher = old_new_sel.param.watch(update_dss_file_widget, ['value'], onlychanged=True)

# name of the scenario that will be compared to, Baseline as a default
s_comparison = 'Baseline'

#Add Done Selecting Files button
done_selecting = pn.widgets.Button(name="Continue", max_width=1000, button_type='primary')

#When done selecting file button is clicked, add text boxes for user to name each file's run
#Eventually, this will only be for new dss files because pickle will hold run names
done_selecting.on_click(add_run_names_widget)

file_picker_column.append(done_selecting)
col_tracker.append("done_selecting")

# Set up the initial layout
file_picker_display = pn.Row(file_picker_column, pn.Column(run_name_column, field_column), margin=20)

template.main.append(file_picker_display)

# when this file is ran, the site will automatically launch
pn.serve(template, show=True)
