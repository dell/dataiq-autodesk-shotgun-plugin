#!/usr/bin/env bash

rm -rf ./rpmbuild/SOURCES/cn_shotgun-1.0/*
cp -a /vagrant/cn_shotgun/ ./rpmbuild/SOURCES/cn_shotgun-1.0/
find ./rpmbuild/SOURCES/cn_shotgun-1.0/ -type f -name '*.pyo' -delete
find ./rpmbuild/SOURCES/cn_shotgun-1.0/ -type f -name '*.pyc' -delete
cp -a rpmbuild/ /root/
rpmbuild -ba /root/rpmbuild/SPECS/cn_shotgun.spec
cp /root/rpmbuild/RPMS/noarch/cn_shotgun-*.noarch.rpm .
cp /root/rpmbuild/SRPMS/cn_shotgun-*.src.rpm .
rm -rf /root/rpmbuild/
