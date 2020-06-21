#!/bin/bash
docker load -i plugin-shotgun-image-1.0-3.tar.gz
./start
echo "The Plugin has been installed."
echo "To enable the plugin, please go to the DataIQ UI and navigate to Settings->Data management configuration."
echo "Then scroll down to the Plugins section, click on the kebab menu for this Plugin and select 'Enable'."
