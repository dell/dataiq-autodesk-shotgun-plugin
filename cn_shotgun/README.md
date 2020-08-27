# README #

Shotgun Plugin for DataIQ
Copyright (C) 2020 Dell Inc or its subsidiaries - all rights reserved
A plugin license is required for each DataIQ Server

### Summary ###

The shotgun plugin connects to the shotgun API and applies tag to the shots found on the filesystem

### Who do I talk to? ###

* greg.shiff@dell.com

### Installation ###

* $> rpm -ivh cn_shotgun-1.0-1.noarch.rpm

### Manual installation ###

* Instructions to install the shotgun plugin without using the package are available here:
cn_shotgun/cn_shotgun.py

### Use the plugin from the Custom Context Menu ###

If the plugin is installed in the standard location of /usr/local/claritynow/scripts/plugins.d/cn_shotgun/ (default), the Custom Context Menu configuration can only be altered in the ccm.control file

If you installed the plugin in /usr/local/claritynow/scripts/usr/cn_shotgun, you can configure the plugin in the GUI's Custom Context Menu configuration dialog:
Check "Enable asynchronous execution" and enter one of the following commands:

* For a single item and multiple items selection (check Applies to root folder in the scope):
cn_shotgun/cn_shotgun.py
