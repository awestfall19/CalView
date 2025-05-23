# -------------------------------------------------------------------
# DSS File reader 0.1
# Sam Waers, P.E.; Frankie Nuffer-Rodriguez
#
# Run this file in same directory as dssReadFuncs.py
# See the "import" statements at the top of  in dssReadFuncs.py
# for a list of dependencies which will need to be installed
# in the environment you use for this script.
# -------------------------------------------------------------------

# Import data handling functions from our local module
from csdss_readlib_fullfile import file_reader, pickler, load_pickles, get_trend_fields
from cs3_plotlib import plot_values, plot_time_group, plot_time_exceedance, plot_single_var, run_operation
import panel as pn
import os
from os import path
#TODO
#Put in code to pickle visualized scenario, make sure it includes user run names

# NOTE: need to use name/main for Pool to work outside of script

pn.extension(sizing_mode='stretch_width')

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
            dss_file = pn.widgets.FileSelector(
                name='Select CalSim output DSS file for new run or pickle file for previous run',
                file_pattern = "*.dss",
                only_files=True,
                max_width=900,
                root_directory=os.path.abspath(os.sep)
            )
        else:
            o_instructions = pn.pane.Markdown('### <span style="color:red">Select the pickle files previously created (diffs.pkl, units.pkl, and values.pkl)</span>')
            dss_file = pn.widgets.FileSelector(
                name='Select CalSim output DSS file for new run or pickle file for previous run',
                file_pattern="*.pkl",
                only_files=True,
                max_width=900,
                root_directory=os.path.abspath(os.sep)
            )

        # replace widget and instructions
        file_picker_column.insert(2, o_instructions)
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
                
                ## <span style="color:red">One run must be marked as Baseline for visualizer to work </span>
                """)
            run_name_column.append(run_name_instructions)
            run_name_col_tracker.append("run_name_instructions")

            #have user provide run names for each file, new scenario has been selected
            for file in files:
                dss_run_file_label = pn.pane.Markdown("### File name: " + file)

                baseline_check = pn.widgets.Checkbox(name='Baseline')
                dss_run_name = pn.widgets.TextInput(width=500, placeholder='Enter name for file', disabled=baseline_check)

                run_name_column.append(dss_run_file_label)
                run_name_col_tracker.append("dss_run_file_label")
                run_name_column.append(baseline_check)
                run_name_col_tracker.append("dss_baseline_checkbox")
                run_name_column.append(dss_run_name)
                run_name_col_tracker.append("dss_run_name")

        #using picked files
        else:
            # check to make sure all pickle files have been selected
            b_diffs_flag = False
            b_values_flag = False
            b_units_flag = False
            for file in files:
                if 'diffs.pkl' in file:
                    b_diffs_flag = True
                if 'values.pkl' in file:
                    b_values_flag = True
                if 'units.pkl' in file:
                    b_units_flag = True
            if not (b_units_flag and b_diffs_flag and b_values_flag):
                error_message = pn.pane.Markdown("## Make sure all pickle files are selected.")
                field_column.append(error_message)
                field_col_tracker.append("error_message")
                return
            # no need for fields section, just start pulling the files
            update_run_names(event)

        #Also add optional field add text box
        add_field_instructions = pn.pane.Markdown("""
        # OPTIONAL additional fields: 
        
        ## Add additional fields to visualize that are not present in the default list. Separate with commas, no spaces.
        """)
        field_column.append(add_field_instructions)
        field_col_tracker.append("add_field_instructions")

        add_field_text = pn.widgets.TextInput(width=500)

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

    # Get selected files
    files = file_picker_column[col_tracker.index("dss_file")].value  # Access the global variable

    # look for old error message and remove
    if 'error_message' in field_col_tracker:
        error_index = field_col_tracker.index('error_message')
        field_column.pop(error_index)
        field_col_tracker.pop(error_index)

    #check if we have exactl one file marked as Baseline and if not give an error
    if sum([run_name_column[i].value for i, x in enumerate(run_name_col_tracker) if x == "dss_baseline_checkbox"]) != 1 and "dss" in files[0].rsplit(".",1)[1]:
        error_message = pn.pane.Markdown("## Please make sure that exactly one file is marked as Baseline.")
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
        baseline_indices = [run_name_column[i].value for i, x in enumerate(run_name_col_tracker) if x == "dss_baseline_checkbox"]

        # Get file names
        files = file_picker_column[col_tracker.index("dss_file")].value

        # Get default fields and any added ones
        l_tr_fields = get_trend_fields()
        add_field_list= field_column[1].value.split(",")
        field_list = l_tr_fields + add_field_list

        runs = []

        #Pair file names with user entered run names
        for file_index, run_index in enumerate(dss_name_indices):
            # structure of runs is [["Description_1", ("File_1.dss")],
            #               ["Description_2", ("File_2.dss")],
            #          ...  ["Description_n", ("File_n.dss")]]
            # The names can be anything though, e.g. ["Alt2v1", Alt2v1_VAs.dss"] but must contain one called Baseline
            # find where the box is checked for Baseline and set that to be called Baseline
            if baseline_indices[file_index]:
                runs.append(['Baseline', (files[file_index])])
            else:
                runs.append([run_name_column[run_index].value, (files[file_index])])
        print(runs)
        append_list, baseline_stack, c_default_units = file_reader(runs, field_list)
        pickler(append_list, baseline_stack, c_default_units)

        # This runs no matter what. The pickle files allow you to come back and
        # pull the same variables without waiting for the file reads to complete
        df_all_data, df_diffs, c_default_units = load_pickles()

        # Write to Excel.
        try:
            df_all_data.to_excel("DSS_contents.xlsx")
        except:
            print("Error writing output file. "
                  "Make sure 'DSS_contents.xlsx' is not open.")

        print(f'Pulled: {len(runs)} files')
        print(runs)

    #Load pickles from previous run
    else:
        df_all_data, df_diffs, c_default_units = load_pickles()

    #Now that pickles have been created/loaded, move forward with initiating other tabs
    scenario_names = df_all_data['Scenario'].unique().tolist()
    var_names = df_all_data.columns.to_list()[6:]

    # removing loading before adding tabs
    field_column.pop(-1)
    field_column.param.trigger("objects")

    #Fill in widgets for other tabs
    create_widgets(scenario_names, var_names, df_all_data, c_default_units, df_diffs)

    # once we have the widgets and graphs, remove the file picker
    for _ in range(len(file_picker_display)):
        file_picker_display.pop(0)


def create_widgets(scenario_names, var_names, df_all_data, c_default_units, df_diffs):
    global single_var_plots
    global grouped_plots
    global exceedance_plots
    global timeseries_plots
    global header
    global tabs_row

    # Select which alts to examine
    scen_selector = pn.widgets.MultiChoice(
        name='Scenario selector',
        options=scenario_names,
        value=scenario_names,
        width=400
    )

    # Select the variables
    var_selector = pn.widgets.MultiChoice(
        name='Variable selector',
        options=var_names,
        # value=[var_names[0]],
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
        name='Period selector',
        options={"Water Year": "WY", "Calendar Year": "DY", "Contract Year": "CY",
                 "January": 1, "February": 2, "March": 3, "April": 4,
                 "May": 5, "June": 6, "July": 7, "August": 8,
                 "September": 9, "October": 10, "November": 11, "December": 12},
        width=200
    )

    # Select a single
    single_var_selector = pn.widgets.Select(
        name='Single variable selector',
        options=var_names,
        value=var_names[0]
    )

    month_sel = pn.widgets.Select(
        name='Month selector',
        options=[
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December"]
    )

    stat_sel = pn.widgets.Select(
        name='Statistic selector',
        options=['Average', 'Minimum', 'Maximum']
    )

    # 20241223: Create different dataframes for each function call
    # Trying to fix non-independent plots issue
    # df_all_data_ts = df_all_data.copy(deep=True)
    # df_all_data_ts_diffs = df_diffs.copy(deep=True)

    # remove Baseline from the differences dataframe as all values are zero
    df_diffs = df_diffs[df_diffs.Scenario != 'Baseline']

    # Okay, so separate dfs isn't cutting it.
    # Try turning off y-lim

    bound_plot_ts = pn.bind(
        plot_values,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_all_data,
        c_default_units_all=c_default_units
    )

    bound_plot_diffs_ts = pn.bind(
        plot_values,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_diffs,
        c_default_units_all=c_default_units
    )

    bound_plot_grouped = pn.bind(
        plot_time_group,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_all_data,
        c_default_units_all=c_default_units,
        period_choice=period_selector
    )

    bound_plot_grouped_diff = pn.bind(
        plot_time_group,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_diffs,
        c_default_units_all=c_default_units,
        period_choice=period_selector
    )

    bound_plot_exceedance = pn.bind(
        plot_time_exceedance,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_all_data,
        c_default_units_all=c_default_units,
        period_choice=period_selector
    )

    bound_plot_diffs_exceedance = pn.bind(
        plot_time_exceedance,
        scenario_list=scen_selector,
        var_list=var_selector,
        unit_choice=unit_selector,
        df_all=df_diffs,
        c_default_units_all=c_default_units,
        period_choice=period_selector
    )

    bound_single_var_plot = pn.bind(
        plot_single_var,
        df_all=df_all_data,
        period_choice=period_selector,
        variable=single_var_selector,
        scenario_list=scen_selector,
        units_choice=unit_selector,
        stat_choice=stat_sel,
        c_default_units=c_default_units
    )

    bound_single_var_diff_plot = pn.bind(
        plot_single_var,
        df_all=df_diffs,
        period_choice=period_selector,
        variable=single_var_selector,
        scenario_list=scen_selector,
        units_choice=unit_selector,
        stat_choice=stat_sel,
        c_default_units=c_default_units
    )

    ts_title = pn.pane.Markdown("""
        # Timeseries Plot
    """)

    diffs_ts_title = pn.pane.Markdown("""
        # Timeseries Plot (Difference from Baseline)
    """)

    grouped_title = pn.pane.Markdown("""
        # Time-Aggregated Plot
    """)

    grouped__diff_title = pn.pane.Markdown("""
        # Time-Aggregated Plot (Difference from Baseline)
    """)

    exceedance_title = pn.pane.Markdown("""
        # Exceedance Plot 
    """)

    exceedance_diff_title = pn.pane.Markdown("""
        # Exceedance Plot (Difference from Baseline)
    """)

    single_var_title = pn.pane.Markdown("""
        # Single Variable Comparison
    """)

    single_var_diff_title = pn.pane.Markdown("""
        # Single Variable Comparison (Difference from Baseline)
    """)

    #Add selectors to header row in template and refresh objects
    header.append(scen_selector)
    header.append(var_selector)
    header.append(period_selector)
    header.append(unit_selector)
    header.param.trigger("objects")

    single_var_widgets = pn.Row(single_var_selector, stat_sel, width=750)

    single_var_plots.append(single_var_widgets)
    single_var_plots.append(pn.Row(pn.Column(single_var_title,bound_single_var_plot),pn.Column(single_var_diff_title,bound_single_var_diff_plot)))

    timeseries_plots.append(pn.Column(ts_title,bound_plot_ts))
    timeseries_plots.append(pn.Column(diffs_ts_title,bound_plot_diffs_ts))

    grouped_plots.append(pn.Column(grouped_title,bound_plot_grouped))
    grouped_plots.append(pn.Column(grouped__diff_title,bound_plot_grouped_diff))

    exceedance_plots.append(pn.Column(exceedance_title, bound_plot_exceedance))
    exceedance_plots.append(pn.Column(exceedance_diff_title, bound_plot_diffs_exceedance))

    tabs = pn.Tabs(
        ('Single Variable', single_var_plots),
        ('Timeseries', timeseries_plots),
        ('Time-Aggregated', grouped_plots),
        ('Exceedance', exceedance_plots))

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
dss_file = pn.widgets.FileSelector(
    name='Select CalSim output DSS file for new run or pickle file for previous run',
    file_pattern = "*.dss",
    only_files=True,
    max_width=900,
    root_directory=os.path.abspath(os.sep)
)

#Add all widgets to file_picker_column
file_picker_column.append(file_picker_title)
col_tracker.append("file_picker_title")
file_picker_column.append(old_new_sel)
col_tracker.append("old_new_sel")
file_picker_column.append(o_instructions)
col_tracker.append("instructions")
file_picker_column.append(dss_file)
col_tracker.append("dss_file")

#Watch the old_new_sel widget and call remove_widget function to update dss_file if a change event occurs
choice_watcher = old_new_sel.param.watch(update_dss_file_widget, ['value'], onlychanged=True)

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
