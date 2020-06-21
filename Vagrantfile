# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
    config.vm.define "claritynow" do |node|
        node.vm.box = "geerlingguy/centos7"
        config.vm.box_version = '1.2.20'
        node.vm.hostname = "claritynow"
        node.vm.network "private_network", ip: "10.0.42.11"
        node.vm.provider :virtualbox do |vb|
            vb.cpus = 2
            vb.memory = 2048
        end
        node.vm.provision :shell, path: "install_base.sh"
    end
    config.vm.define "dataiq-shotgun" do |node|
    node.vm.box = "geerlingguy/centos7"
    config.vm.box_version = '1.2.20'
    node.vm.hostname = "dataiq-shotgun"
    node.vm.network "private_network", ip: "10.0.42.12"
    node.vm.provider :virtualbox do |vb|
        vb.cpus = 4
        vb.memory = 8192
    end
end
    config.vm.post_up_message = "
    vagrant ssh claritynow
    vagrant ssh dataiq-shotgun"
end
