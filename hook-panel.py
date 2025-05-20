from PyInstaller.utils.hooks import collect_data_files

# This file is needed to get pyinstaller to correctly include panel

datas = collect_data_files('panel', include_py_files=True) + \
        collect_data_files('pyviz_comms', include_py_files=True) + \
        collect_data_files('bokeh')  # See https://github.com/pyinstaller/pyinstaller/pull/4746