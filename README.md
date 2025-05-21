# Temporary Pre-Visuzalizer Run Requirements:
Run CalSim_DSS_Reader on the needed CalSim3 output DSS files prior to running the visualizer
Place output of the CalSim_DSS_Reader in the Visualizer Folder before running the Visualizer code.

# To Launch a Run
python cs3_viz_app_main.py

# To compile executable 
pyinstaller --clean --additional-hooks-dir=. --add-data TR_fields.txt:. --add-data usbr_logo.jpg:. -F cs3_viz_app_main.py