# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/jammy64"

  # Allocate resources
  config.vm.provider "virtualbox" do |vb|
    vb.memory = "8192"
    vb.cpus = 4
  end

  # Forward port for llama server
  config.vm.network "forwarded_port", guest: 8080, host: 8081

  # Sync project directory
  config.vm.synced_folder ".", "/vagrant"

  # Provision script
  config.vm.provision "shell", inline: <<-SHELL
    set -e

    # Update system
    apt-get update
    apt-get install -y curl build-essential python3-pip git

    # Install uv
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv to PATH for all users
    echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> /home/vagrant/.bashrc

    # Install dependencies
    cd /vagrant
    /home/vagrant/.cargo/bin/uv sync

    echo "Vagrant VM ready! SSH in and run benchmarks."
  SHELL
end
