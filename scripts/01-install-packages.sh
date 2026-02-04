#!/bin/bash
set -e

echo "[$(date)] Starting package installation"

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
    echo "[$(date)] Installing Java for RPM-based system..."
    # For Amazon Linux 2023 and newer, use Corretto
    if [[ $(cat /etc/os-release | grep VERSION_ID) =~ "2023" ]]; then
        echo "[$(date)] Detected Amazon Linux 2023, installing Corretto 21"
        yum install -y java-21-amazon-corretto-headless || {
            echo "ERROR: Failed to install Java 21 Corretto" >&2
            return 1
        }
    # For Amazon Linux 2
    elif [[ $(cat /etc/os-release | grep VERSION_ID) =~ "2" ]]; then
        echo "[$(date)] Detected Amazon Linux 2, installing OpenJDK 17"
        amazon-linux-extras install -y java-openjdk17 || {
            echo "ERROR: Failed to install Java 17 via amazon-linux-extras" >&2
            return 1
        }
    # For RHEL/CentOS
    else
        echo "[$(date)] Installing OpenJDK 17 for RHEL/CentOS"
        yum install -y java-17-openjdk-headless || {
            echo "ERROR: Failed to install Java 17 OpenJDK" >&2
            return 1
        }
    fi
    
    if command -v java &> /dev/null; then
        echo "[$(date)] Java installed successfully: $(java -version 2>&1 | head -n 1)"
        return 0
    else
        echo "ERROR: Java command not found after installation" >&2
        return 1
    fi
}

# Function to install Java on Ubuntu or Debian
install_java_deb() {
    echo "[$(date)] Installing Java for Debian-based system..."
    apt-get update || {
        echo "ERROR: apt-get update failed" >&2
        return 1
    }
    apt-get install -y openjdk-21-jre-headless || {
        echo "ERROR: Failed to install OpenJDK 21" >&2
        return 1
    }
    
    if command -v java &> /dev/null; then
        echo "[$(date)] Java installed successfully: $(java -version 2>&1 | head -n 1)"
        return 0
    else
        echo "ERROR: Java command not found after installation" >&2
        return 1
    fi
}

# Main Java installation function
install_java() {
    # Check if Java is already installed
    if command -v java &> /dev/null; then
        echo "[$(date)] Java is already installed: $(java -version 2>&1 | head -n 1)"
        return 0
    fi

    local distro=$(detect_distro)
    echo "[$(date)] Detected distribution: $distro"
    case $distro in
        amzn*|rhel*|centos*)
            install_java_rpm || {
                echo "ERROR: Java installation failed for RPM-based system" >&2
                return 1
            }
            ;;
        ubuntu*|debian*)
            install_java_deb || {
                echo "ERROR: Java installation failed for Debian-based system" >&2
                return 1
            }
            ;;
        *)
            echo "ERROR: Unsupported distribution: $distro" >&2
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
    echo "[$(date)] Installing required packages..."
    local distro=$(detect_distro)
    case $distro in
        amzn*|rhel*|centos*)
            yum -y install "${REQUIRED_PACKAGES[@]}" || {
                echo "ERROR: Failed to install packages via yum" >&2
                return 1
            }
            ;;
        ubuntu*|debian*)
            install_required_packages || {
                echo "ERROR: Failed to install packages via apt" >&2
                return 1
            }
            ;;
        *)
            echo "ERROR: Unsupported distribution: $distro" >&2
            return 1
            ;;
    esac
    echo "[$(date)] Required packages installed successfully"
}

# Main execution
echo "[$(date)] Starting package installation process"

install_packages || {
    echo "ERROR: Package installation failed" >&2
    exit 1
}

install_awscli || {
    echo "ERROR: AWS CLI installation failed" >&2
    exit 1
}

install_java || {
    echo "ERROR: Java installation failed" >&2
    exit 1
}

echo "[$(date)] All packages installed successfully"
