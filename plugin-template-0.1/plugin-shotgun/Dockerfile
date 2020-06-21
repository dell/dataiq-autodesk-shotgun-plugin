# Copyright © 2016-2020 Dell Inc. or its subsidiaries.
# All Rights Reserved.
FROM centos:7

ENV LANG en_US.utf-8
ENV LC_ALL en_US.utf-8
ENV CN_HOSTNAME claritynow:30080

EXPOSE 5000

COPY dataiq-plugin /dataiq-plugin
COPY plugin-legacy /plugin-legacy
COPY plugin /plugin

# Create location to store outputs, configs, etc
# Plugins will need to write to this location
# Location will be mapped on the host to: /opt/dataiq/maunakea/data/plugins/<plugin_name>
RUN mkdir -p /hoststorage

# Section 1
# Install basics for OS
RUN yum install -y \
    git \
    vim \
    epel-release \
    yum-utils \
    bind-utils \
    net-tools \
    openssl \
    traceroute

# Section 2
# Install all python2 requirements
# Used exclusively for custom/legacy plugin code
# Flask app and supporting libraries require python3
# If your custom plugin code does not use python2, you can delete this section
RUN yum install -y \
    python-setuptools \
    python-wheel \
    python-pip \
    python2-requests \
    && yum clean all \
    && rm -rf /var/cache/yum
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org
RUN pip install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org -r /plugin/requirements.txt

# Section 3
# Install python3, set as default and install all python3 requirements
# Do not delete this section
RUN yum install -y \
    python3.8 \
    python3-pip \
    python3-requests \
    python3-dateutil \
    && yum clean all \
    && rm -rf /var/cache/yum
RUN vim -c """:g/^\n\# Source/s//alias python='python3'\r# Source/g""" -c ''':x''' ~/.bashrc
RUN cat ~/.bashrc
RUN pip3 install --upgrade pip --trusted-host pypi.org --trusted-host files.pythonhosted.org
RUN pip3 install --upgrade pip flask --trusted-host pypi.python.org
RUN pip3 install -e /dataiq-plugin
RUN pip3 install --trusted-host pypi.python.org -r /plugin-legacy/requirements.txt
RUN export LC_ALL=en_US.utf-8


#RUN rpm -ivh <plugin code rpm file>
COPY exportAndRun.sh /plugin-legacy/
RUN chmod +x /plugin-legacy/exportAndRun.sh

WORKDIR /plugin-legacy

# Define default command.
CMD ["/plugin-legacy/exportAndRun.sh"]
