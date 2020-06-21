# prevent python byte compilation and jar repacking by
# overriding rpm macro (super-ick). The file containing
# this macro is here: /usr/lib/rpm/redhat/macros
%global __os_install_post \
/usr/lib/rpm/redhat/brp-compress \
%{!?__debug_package:/usr/lib/rpm/redhat/brp-strip %{__strip}} \
/usr/lib/rpm/redhat/brp-strip-static-archive %{__strip} \
/usr/lib/rpm/redhat/brp-strip-comment-note %{__strip} %{__objdump} \
%{nil}

%global mySourceDir /root/rpmbuild/SOURCES/%{name}-%{version}

Name:	cn_shotgun
Version:	1.0
Release:	2
Summary:	cn_shotgun rpm

Group:  data_management
License: 	DataFrameworks ClarityNow! License
Source:  %{mySourceDir}
#Source0: cn_shotgun.tar.gz

BuildArch:	noarch
BuildRoot: 	%{_tmppath}/%{name}-buildroot

Requires: python >= 2.6.0, claritynow >= 2.8.6-3
%description

cn_shotgun rpm


%prep

%build
%install
install -m 0755 -d $RPM_BUILD_ROOT/usr/local/claritynow/scripts/plugins.d/
install -m 0755 -d $RPM_BUILD_ROOT/usr/local/claritynow/etc/
install -m 0755 -d $RPM_BUILD_ROOT/etc/cron.d/
cp -a %{mySourceDir}/cn_shotgun $RPM_BUILD_ROOT/usr/local/claritynow/scripts/plugins.d/
mv $RPM_BUILD_ROOT/usr/local/claritynow/scripts/plugins.d/cn_shotgun/cn_shotgun.cfg.sample $RPM_BUILD_ROOT/usr/local/claritynow/etc/
mv $RPM_BUILD_ROOT/usr/local/claritynow/scripts/plugins.d/cn_shotgun/autotag.cfg.cn_shotgun.sample $RPM_BUILD_ROOT/usr/local/claritynow/etc/
mv $RPM_BUILD_ROOT/usr/local/claritynow/scripts/plugins.d/cn_shotgun/cn_shotgun $RPM_BUILD_ROOT/etc/cron.d/
%files
%defattr(-,root,root)
/usr/local/claritynow/scripts/plugins.d/cn_shotgun
%dir /usr/local/claritynow/scripts/plugins.d/cn_shotgun
/usr/local/claritynow/etc/cn_shotgun.cfg.sample
/usr/local/claritynow/etc/autotag.cfg.cn_shotgun.sample
%config(noreplace) %attr(660,-,-) /usr/local/claritynow/scripts/plugins.d/cn_shotgun/ccm.control
%config(noreplace) %attr(644,-,-) /etc/cron.d/cn_shotgun

%pre
case "$1" in
  1)
    #install
  ;;
  2)
    #upgrade
  ;;
esac

%post
find /usr/local/claritynow/scripts/plugins.d/cn_shotgun/ -name "*.py" -exec chmod +x {} \;
case "$1" in
  1)
    #install
    while read file; do
      tar -xzf $file -C /usr/local/claritynow/scripts/plugins.d/cn_shotgun/dependencies/
      dir=$(ls $file | sed -e 's/\.tar.gz$//')
      (cd $dir ; python setup.py install)
    done </usr/local/claritynow/scripts/plugins.d/cn_shotgun/dependencies/installation_order.txt
  ;;
  2)
    #upgrade
  ;;
esac

%preun
find /usr/local/claritynow/scripts/plugins.d/cn_shotgun -type f -name '*.pyo' -delete
find /usr/local/claritynow/scripts/plugins.d/cn_shotgun -type f -name '*.pyc' -delete
case "$1" in
  0)
    #uninstallation
  ;;
  1)
    #upgrade
  ;;
esac

%postun
case "$1" in
  0)
    #uninstallation
    rm -rf /usr/local/claritynow/scripts/plugins.d/cn_shotgun
    rm -rf /etc/cron.d/cn_shotgun
  ;;
  1)
    #upgrade
  ;;
esac
