#!/usr/bin/env bash

rm -rf /vagrant/build_dataiq_plugin/plugin-shotgun /vagrant/build_dataiq_plugin/dataiq-shotgun
cp -r /vagrant/plugin-template-0.1/plugin-shotgun .
cp -r /vagrant/plugin-template-0.1/dataiq-shotgun .
cp -r /vagrant/cn_shotgun/*.py /vagrant/build_dataiq_plugin/plugin-shotgun/plugin/
rm /vagrant/build_dataiq_plugin/dataiq-shotgun/plugin-shotgun-debug.yaml /vagrant/build_dataiq_plugin/dataiq-shotgun/plugin-shotgun.yaml
cp /vagrant/build_dataiq_plugin/plugin-shotgun/plugin-shotgun-debug.yaml /vagrant/build_dataiq_plugin/dataiq-shotgun/
cp /vagrant/build_dataiq_plugin/plugin-shotgun/plugin-shotgun.yaml /vagrant/build_dataiq_plugin/dataiq-shotgun/
cp /vagrant/build_dataiq_plugin/plugin-shotgun/plugin/ca.control /vagrant/build_dataiq_plugin/dataiq-shotgun/
