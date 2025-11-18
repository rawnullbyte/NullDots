#!/bin/bash

echo "======================================"
echo "===       NullDots Installer       ==="
echo "======================================"

echo "======================================"
echo "=== User Setup                     ==="
echo "======================================"

# Ask if user wants to create new user or use existing
read -p "Do you want to create a new user? (y/n): " CREATE_NEW_USER

if [[ $CREATE_NEW_USER == "y" || $CREATE_NEW_USER == "Y" ]]; then
    read -p "Enter new username: " USERNAME
    read -s -p "Enter password: " PASSWORD
    echo
    
    # Create new user
    useradd -m -G wheel -s /bin/bash $USERNAME
    echo "$USERNAME:$PASSWORD" | chpasswd
    echo "User '$USERNAME' created successfully."
else
    read -p "Enter existing username: " USERNAME
    # Verify user exists
    if ! id "$USERNAME" &>/dev/null; then
        echo "Error: User '$USERNAME' does not exist!"
        exit 1
    fi
    echo "Using existing user '$USERNAME'"
fi

# Add user to sudoers
echo "$USERNAME ALL=(ALL) ALL" >> /etc/sudoers.d/$USERNAME

echo "======================================"
echo "=== Installing dependencies...     ==="
echo "======================================"

# Update and install dependencies as root
pacman -Syu --noconfirm
pacman -S --needed git base-devel jq --noconfirm

# Chaotic AUR setup as root
pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
pacman-key --lsign-key 3056513887B78AEB
pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' --noconfirm
pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm
grep -q "\[chaotic-aur\]" /etc/pacman.conf || echo -e "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist" >> /etc/pacman.conf
pacman -Syu --noconfirm

echo "======================================"
echo "=== Installing AUR helper...       ==="
echo "======================================"

# Install yay as the user (with proper sudo setup)
sudo -u $USERNAME bash << EOF
cd /tmp
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si --noconfirm
cd
rm -rf /tmp/yay
EOF

echo "======================================"
echo "=== Installing packages...         ==="
echo "======================================"

# Install packages as the user
sudo -u $USERNAME bash << EOF
yay -S --noconfirm --needed \
	hyprland waybar alacritty fish \
	python-pywal wpgtk swww gradience kvantum kvantum-theme-materia \
	cliphist wl-clipboard \
	mako \
	grim slurp swappy \
	upower brightnessctl \
	pavucontrol playerctl \
	networkmanager nm-applet bluez bluez-utils blueman \
	fastfetch git stow \
	noto-fonts noto-fonts-emoji ttf-font-awesome polkit-kde-agent xdg-desktop-portal-hyprland \
	ly
EOF

echo "======================================"
echo "=== Copying dotfiles...            ==="
echo "======================================"

copy_dotfiles() {
    local username=$1
    local dotfiles_dir="./dotfiles"
    local config_file="$./dotfiles.json"
    
    if [ ! -f "$config_file" ]; then
        echo "Error: dotfiles.json not found at $config_file"
        return 1
    fi
    
    # Read and process the JSON configuration
    local dotfiles_count=$(jq '.dotfiles | length' "$config_file")
    
    for ((i=0; i<$dotfiles_count; i++)); do
        echo "--------------------------------------"
        
        # Extract configuration for this dotfile entry
        local source=$(jq -r ".dotfiles[$i].source" "$config_file")
        local target=$(jq -r ".dotfiles[$i].target" "$config_file")
        local pre_copy_count=$(jq -r ".dotfiles[$i].pre_copy | length" "$config_file")
        local post_copy_count=$(jq -r ".dotfiles[$i].post_copy | length" "$config_file")
        
        # Replace USER placeholder with actual username
        target="${target//USER/$username}"
        
        echo "Processing: $source -> $target"
        
        # Run pre-copy commands
        if [ $pre_copy_count -gt 0 ]; then
            echo "Running pre-copy commands..."
            for ((j=0; j<$pre_copy_count; j++)); do
                local pre_cmd=$(jq -r ".dotfiles[$i].pre_copy[$j]" "$config_file")
                pre_cmd="${pre_cmd//USER/$username}"
                echo "Executing: $pre_cmd"
                eval "$pre_cmd"
            done
        fi
        
        # Create target directory if it doesn't exist
        mkdir -p "$(dirname "$target")"
        
        # Copy files
        local source_path="$dotfiles_dir/$source"
        if [ -d "$source_path" ]; then
            echo "Copying directory: $source_path to $target"
            cp -r "$source_path" "$target" 2>/dev/null || sudo -u $username cp -r "$source_path" "$target"
        elif [ -f "$source_path" ]; then
            echo "Copying file: $source_path to $target"
            cp "$source_path" "$target" 2>/dev/null || sudo -u $username cp "$source_path" "$target"
        else
            echo "Warning: Source $source_path not found"
            continue
        fi
        
        # Fix permissions
        chown -R $username:$username "$target" 2>/dev/null || true
        
        # Run post-copy commands
        if [ $post_copy_count -gt 0 ]; then
            echo "Running post-copy commands..."
            for ((j=0; j<$post_copy_count; j++)); do
                local post_cmd=$(jq -r ".dotfiles[$i].post_copy[$j]" "$config_file")
                post_cmd="${post_cmd//USER/$username}"
                echo "Executing: $post_cmd"
                eval "$post_cmd"
            done
        fi
        
        echo "Completed: $source"
    done
}

# Call the dotfiles copying function
copy_dotfiles "$USERNAME"

echo "======================================"
echo "=== Configuring Ly Display Manager =="
echo "======================================"

# Enable Ly service
systemctl enable ly.service

echo "======================================"
echo "=== Setting up permissions...      ==="
echo "======================================"

# Ensure user owns their home directory
chown -R $USERNAME:$USERNAME /home/$USERNAME

echo "======================================"
echo "=== Installation completed!        ==="
echo "======================================"