#!/usr/bin/env bash

# Install ClarityNow!
rpm -ivh /vagrant/claritynow/claritynow-base-2.0.1-1.x86_64.rpm
rpm -ivh /vagrant/claritynow/claritynow-2.11.0-9.x86_64.rpm
cp /vagrant/claritynow/service.cfg /usr/local/claritynow/etc/service.cfg
cp /vagrant/claritynow/autotag.cfg /usr/local/claritynow/etc/autotag.cfg
cp /vagrant/claritynow/credentials.txt /usr/local/claritynow/etc/credentials.txt
cp /vagrant/claritynow/license.txt /usr/local/claritynow/etc/license.txt
echo '10.0.42.11 cndev.trackit.io' >> /etc/hosts

# start rsyslog on boot
chkconfig rsyslog on

# Install java
yum install -y java-1.8.0-openjdk-devel

# Install pip
yum install -y epel-release
yum install -y python-pip

# Install rpmbuild
yum install -y rpm-build

# Install nodejs to generate the doc
yum install -y nodejs npm

# Install git
yum install -y git

/etc/init.d/claritynow start
