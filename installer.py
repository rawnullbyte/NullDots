import logging
import os
import sys
import json
import subprocess
import threading

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
logger.addHandler(h)

def run(cmd, shell=True):
    """
    Runs a command in a subprocess with real-time output and interactive input.
    Returns the subprocess return code.
    """
    
    logger.info(f"Running command: {cmd}")

    # Start the subprocess
    process = subprocess.Popen(
        cmd,
        shell=shell,
        stdin=sys.stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Function to read output line by line
    def stream_output(pipe):
        for line in iter(pipe.readline, ''):
            print(line, end='')  # already has newline
        pipe.close()

    # Start a thread to stream stdout
    t = threading.Thread(target=stream_output, args=(process.stdout,))
    t.start()

    # Wait for process to finish
    process.wait()
    t.join()

    logger.info(f"Command exited with code {process.returncode}")
    return process.returncode
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
    echo -e "\n[chaotic-aur]\nInclude = /etc/pacman.d/chaotic-mirrorlist" >> /etc/pacman.conf""")
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
packages = ""
# Hyprland + core apps
packages += "hyprland waybar alacritty fish "
# Themes / appearance
packages += "python-pywal wpgtk swww gradience kvantum kvantum-theme-materia "
# Wayland utilities / screenshot / clipboard / notification
packages += "cliphist wl-clipboard mako grim slurp swappy "
# Power / audio / media control
packages += "upower brightnessctl pavucontrol playerctl "
# Network / bluetooth
packages += "networkmanager bluez bluez-utils blueman "
# Utilities
packages += "fastfetch git stow "
# Fonts
packages += "noto-fonts noto-fonts-emoji ttf-font-awesome "
# Polkit / portal / display manager
packages += "polkit-kde-agent xdg-desktop-portal-hyprland ly"

# Install all packages at once
run(f"yay -S --noconfirm --needed {packages}")

logger.info("Loading dotfiles...")

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

    if pre_copy:
        for cmd in pre_copy:
            r = run(cmd)
            if r != 0:
                logger.error(f"Pre-copy command failed: {pre_copy}")

    r = run(f"cp -R \"{source}\" \"{target}\"")
    if r != 0:
        logger.error(f"Failed to copy {source} to {target}")

    if post_copy:
        for cmd in post_copy:
            r = run(cmd)
            if r != 0:
                logger.error(f"Post-copy command failed: {post_copy}")

# Enable ly
run("sudo systemctl enable ly.service")

# Set ownership
run(f"""sudo chown -R "{current_user}:{current_user}" /home/"{current_user}\"""")