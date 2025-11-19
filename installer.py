import logging
import os
import sys
import json
import subprocess

class LogFormatter(logging.Formatter):
    RESET = '\033[0m'
    COLORS = {
        'DEBUG': '\033[1;34m',    # Bold blue
        'INFO': '\033[1;32m',     # Bold green
        'WARNING': '\033[1;33m',  # Bold yellow
        'ERROR': '\033[1;31m',    # Bold red
        'CRITICAL': '\033[1;35m'  # Bold magenta
    }
    def __init__(self, fmt='%(levelname)-8s %(name)s: %(message)s', use_color=None):
        super().__init__(fmt)
        self.use_color = (not os.getenv('NO_COLOR')) and (use_color if use_color is not None else sys.stderr.isatty())
    def format(self, record):
        msg = super().format(record)
        if not self.use_color:
            return msg
        return f"{self.COLORS.get(record.levelname,'')}{msg}{self.RESET}"

logger = logging.getLogger("installer")
logger.setLevel(logging.DEBUG)
h = logging.StreamHandler()
h.setLevel(logging.DEBUG)
h.setFormatter(LogFormatter(use_color=sys.stderr.isatty()))

def run(*args, **kwargs):
    return os.system(*args, **kwargs)

current_user = subprocess.check_output(["id", "-u", "-n"], text=True).strip()
logger.info(f"Running as user: {current_user}")

if os.geteuid() == 0:
    logger.error("Please make a new user and run this script as that user, not as root.")
    sys.exit(1)

run("""sudo pacman -Syu --noconfirm""")
run("""sudo pacman -S --needed git base-devel jq --noconfirm""")

# Chaotic AUR
run("""sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com""")
run("""sudo pacman-key --lsign-key 3056513887B78AEB""")
run("""sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' --noconfirm""")
run("""sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm""")
run("""sudo grep -q "\\[chaotic-aur\\]" /etc/pacman.conf || \\
    echo -e "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist" >> /etc/pacman.conf\"""")
run("""sudo pacman -Syu --noconfirm""")

# Install yay
run(f"""bash <<'EOF'
cd /tmp
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si --noconfirm
rm -rf /tmp/yay
EOF""")

# Main packages
run(f"""yay -S --noconfirm --needed \
    hyprland waybar alacritty fish \
    python-pywal wpgtk swww gradience kvantum kvantum-theme-materia \
    cliphist wl-clipboard mako grim slurp swappy \
    upower brightnessctl pavucontrol playerctl \
    networkmanager nm-applet bluez bluez-utils blueman \
    fastfetch git stow \
    noto-fonts noto-fonts-emoji ttf-font-awesome \
    polkit-kde-agent xdg-desktop-portal-hyprland \
    ly
""")

# Load JSON
with open('dotfiles.json', 'r') as file:
    dotfiles_data = json.load(file)

# Iterate through each entry
for dotfile in dotfiles_data:
    source = dotfile.get("source")
    target = dotfile.get("target")
    pre_copy = dotfile.get("pre_copy", [])
    post_copy = dotfile.get("post_copy", [])

    logger.info(f"Source: {source}")
    logger.info(f"Target: {target}")
    logger.info(f"Pre-copy commands: {pre_copy}")
    logger.info(f"Post-copy commands: {post_copy}")
    logger.info("----------")

    if pre_copy: run(pre_copy)
    run(f"""sudo cp -R ./dotfiles/{source} {target}""")
    if post_copy: run(post_copy)

# Enable ly
run("sudo systemctl enable ly.service")

# Set ownership
run(f"""sudo chown -R "{current_user}:{current_user}" /home/"{current_user}\"""")