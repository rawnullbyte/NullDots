#!/bin/bash
set -e

echo "== NullDots Installer =="

### USER SETUP ###
read -p "Create new user? (y/n): " CREATE
if [[ "$CREATE" =~ ^[Yy]$ ]]; then
    read -p "Username: " USERNAME
    read -s -p "Password: " PASSWORD
    echo
    useradd -m -G wheel -s /bin/bash "$USERNAME"
    echo "$USERNAME:$PASSWORD" | chpasswd
else
    read -p "Existing username: " USERNAME
    id "$USERNAME" &>/dev/null || { echo "User not found."; exit 1; }
fi

# Add minimal sudoers entry
echo "$USERNAME ALL=(ALL) ALL" > /etc/sudoers.d/"$USERNAME"

### SYSTEM + DEPS ###
pacman -Syu --noconfirm
pacman -S --needed git base-devel jq --noconfirm

### CHAOTIC AUR ###
pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com
pacman-key --lsign-key 3056513887B78AEB
pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' --noconfirm
pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm
grep -q "\[chaotic-aur\]" /etc/pacman.conf || \
    echo -e "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist" >> /etc/pacman.conf
pacman -Syu --noconfirm

### YAY INSTALL ###
sudo -u "$USERNAME" bash <<EOF
cd /tmp
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si --noconfirm
rm -rf /tmp/yay
EOF

### MAIN PACKAGES ###
sudo -u "$USERNAME" yay -S --noconfirm --needed \
    hyprland waybar alacritty fish \
    python-pywal wpgtk swww gradience kvantum kvantum-theme-materia \
    cliphist wl-clipboard mako grim slurp swappy \
    upower brightnessctl pavucontrol playerctl \
    networkmanager nm-applet bluez bluez-utils blueman \
    fastfetch git stow \
    noto-fonts noto-fonts-emoji ttf-font-awesome \
    polkit-kde-agent xdg-desktop-portal-hyprland \
    ly

### DOTFILES COPY ###
copy_dotfiles() {
    local user=$1
    local dir="./dotfiles"
    local cfg="./dotfiles.json"
    [[ -f "$cfg" ]] || { echo "dotfiles.json missing"; return 1; }

    local count=$(jq '.dotfiles | length' "$cfg")

    for ((i=0; i<count; i++)); do
        local src=$(jq -r ".dotfiles[$i].source" "$cfg")
        local tgt=$(jq -r ".dotfiles[$i].target" "$cfg")
        tgt="${tgt//USER/$user}"

        mkdir -p "$(dirname "$tgt")"

        # Pre-commands
        jq -r ".dotfiles[$i].pre_copy[]" "$cfg" 2>/dev/null | while read cmd; do
            [[ -n "$cmd" ]] && eval "${cmd//USER/$user}"
        done

        # Copy
        if [[ -d "$source_path" ]]; then
            echo "Copying directory: $source_path -> $target"
            cp -r "$source_path" "$target"
        elif [[ -f "$source_path" ]]; then
            echo "Copying file: $source_path -> $target"
            cp "$source_path" "$target"
        else
            echo "Warning: missing $source_path"
        fi


        chown -R "$user:$user" "$tgt"

        # Post-commands
        jq -r ".dotfiles[$i].post_copy[]" "$cfg" 2>/dev/null | while read cmd; do
            [[ -n "$cmd" ]] && eval "${cmd//USER/$user}"
        done
    done
}

copy_dotfiles "$USERNAME"

### ENABLE LY ###
systemctl enable ly.service

### FIX PERMS ###
chown -R "$USERNAME:$USERNAME" /home/"$USERNAME"

echo "== Installation complete =="
