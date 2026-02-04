#!/bin/bash
set -e

# Define required packages list (used by all distributions)
REQUIRED_PACKAGES=("jq" "zip" "unzip" "net-tools" "wget" "screen")

# Function to detect the Linux distribution
detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        DISTRO=$DISTRIB_ID
    elif [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="rhel"
    else
        DISTRO=$(uname -s)
    fi
    echo $DISTRO
}

# Function to install Java on Amazon Linux, RHEL, or CentOS
install_java_rpm() {
    echo "Installing Java..."
    # For Amazon Linux 2023 and newer, use Corretto
    if [[ $(cat /etc/os-release | grep VERSION_ID) =~ "2023" ]]; then
        yum install -y java-21-amazon-corretto-headless
    # For Amazon Linux 2
    elif [[ $(cat /etc/os-release | grep VERSION_ID) =~ "2" ]]; then
        amazon-linux-extras install -y java-openjdk17
    # For RHEL/CentOS
    else
        yum install -y java-17-openjdk-headless
    fi
    
    if command -v java &> /dev/null; then
        echo "Java installed successfully: $(java -version 2>&1 | head -n 1)"
        return 0
    else
        echo "Failed to install Java"
        return 1
    fi
}

# Function to install Java on Ubuntu or Debian
install_java_deb() {
    echo "Installing Java..."
    apt-get update
    apt-get install -y openjdk-21-jre-headless
    
    if command -v java &> /dev/null; then
        echo "Java installed successfully: $(java -version 2>&1 | head -n 1)"
        return 0
    else
        echo "Failed to install Java"
        return 1
    fi
}

# Main Java installation function
install_java() {
    # Check if Java is already installed
    if command -v java &> /dev/null; then
        echo "Java is already installed: $(java -version 2>&1 | head -n 1)"
        return 0
    fi

    local distro=$(detect_distro)
    case $distro in
        amzn*|rhel*|centos*)
            install_java_rpm
            ;;
        ubuntu*|debian*)
            install_java_deb
            ;;
        *)
            echo "Unsupported distribution: $distro"
            return 1
            ;;
    esac
}

install_required_packages() {
    local packages_to_install=()

    # Check each package
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if ! dpkg -l | grep -q "^ii.*$package "; then
            echo "$package is not installed"
            packages_to_install+=("$package")
        else
            echo "$package is already installed"
        fi
    done

    # Install missing packages if any
    if [ ${#packages_to_install[@]} -gt 0 ]; then
        echo "Installing missing packages: ${packages_to_install[*]}"
        apt-get update
        if apt-get install -y "${packages_to_install[@]}"; then
            echo "Successfully installed missing packages"
            return 0
        else
            echo "Failed to install some packages"
            return 1
        fi
    else
        echo "All required packages are already installed"
        return 0
    fi
}

install_awscli() {
    if [ ! -f /usr/share/collectd/types.db ]; then
      sudo mkdir -p /usr/share/collectd
      sudo touch /usr/share/collectd/types.db
    fi
    if ! command -v aws >/dev/null 2>&1; then
      curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
      unzip awscliv2.zip
      sudo ./aws/install
    echo "AWS CLI installed successfully"
    else
        echo "AWS CLI is already installed"
    fi 
}

# Main installation function
install_packages() {
    local distro=$(detect_distro)
    case $distro in
        amzn*|rhel*|centos*)
            yum -y install "${REQUIRED_PACKAGES[@]}"
            ;;
        ubuntu*|debian*)
            install_required_packages
            ;;
        *)
            echo "Unsupported distribution: $distro"
            exit 1
            ;;
    esac
}

# Main execution
install_packages
install_awscli
install_java

echo "All packages installed successfully"
