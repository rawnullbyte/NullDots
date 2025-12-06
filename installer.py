#!/usr/bin/env python3
"""
NullDots Installer - Enhanced Python Version
"""

import os
import sys
import json
import subprocess
import threading
import shutil
from pathlib import Path
from datetime import datetime

class LogFormatter:
    RESET = '\033[0m'
    COLORS = {
        'INFO': '\033[1;34m',    # Bold blue
        'SUCCESS': '\033[1;32m', # Bold green
        'WARNING': '\033[1;33m', # Bold yellow
        'ERROR': '\033[1;31m',   # Bold red
    }
    
    @classmethod
    def format(cls, level, message):
        if not sys.stderr.isatty() or os.getenv('NO_COLOR'):
            return f"[{level}] {message}"
        return f"{cls.COLORS.get(level, cls.RESET)}[{level}]{cls.RESET} {message}"

class NullDotsInstaller:
    def __init__(self):
        self.current_user = os.getenv('USER')
        self.home_dir = Path.home()
        self.config_dir = self.home_dir / '.config'
        self.backup_dir = self.home_dir / f'.dotfiles_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        self.dotfiles_source = Path('./dotfiles')
        
        # Package categories for better organization
        self.package_categories = {
            'hyprland': [
                "hyprland", "polkit-kde-agent", "xdg-desktop-portal-hyprland",
                "hyprpicker", "hyprlock", "hypridle", "wlogout"
            ],
            'essentials': [
                "waybar", "tofi", "dunst", "kitty", "fish", "fastfetch",
                "wl-clipboard", "cliphist", "flameshot", "swww", "python-pywal"
            ],
            'theming': [
                "nwg-look", "kvantum", "kvantum-theme-catppuccin-git",
                "qt5-wayland", "qt6-wayland", "qt5ct", "qt6ct"
            ],
            'system': [
                "upower", "brightnessctl", "pipewire", "wireplumber", "pamixer",
                "networkmanager", "bluez", "bluez-utils", "blueman", "ly"
            ],
            'fonts': [
                "ttf-cascadia-code-nerd", "ttf-cascadia-mono-nerd", "ttf-fira-code",
                "ttf-fira-mono", "ttf-fira-sans", "ttf-firacode-nerd", "ttf-iosevka-nerd",
                "ttf-iosevkaterm-nerd", "ttf-jetbrains-mono-nerd", "ttf-jetbrains-mono",
                "ttf-nerd-fonts-symbols", "ttf-nerd-fonts-symbols-mono"
            ]
        }

    def log(self, level, message):
        print(LogFormatter.format(level, message))

    def run(self, cmd, shell=True, desc=None):
        """Run command with real-time output and proper error handling"""
        if desc:
            self.log('INFO', f"Running: {desc}")
        else:
            self.log('INFO', f"Running: {cmd}")
        
        try:
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

            def stream_output(pipe):
                for line in iter(pipe.readline, ''):
                    print(line, end='')
                pipe.close()

            t = threading.Thread(target=stream_output, args=(process.stdout,))
            t.start()
            process.wait()
            t.join()
            
            if process.returncode == 0:
                self.log('SUCCESS', f"Completed: {desc or cmd}")
                return True
            else:
                self.log('ERROR', f"Failed: {desc or cmd} (exit code: {process.returncode})")
                return False
                
        except Exception as e:
            self.log('ERROR', f"Exception running command: {e}")
            return False

    def check_root(self):
        """Ensure not running as root"""
        if os.geteuid() == 0:
            self.log('ERROR', "Please run as regular user, not root. Create a new user if needed.")
            return False
        return True

    def install_yay(self):
        """Install yay AUR helper if not present"""
        if self.run("command -v yay", desc="Checking for yay"):
            self.log('INFO', "yay is already installed")
            return True
        
        self.log('INFO', "Installing yay...")
        commands = [
            "cd /tmp",
            "git clone https://aur.archlinux.org/yay.git",
            "cd yay && makepkg -si --noconfirm",
            "cd /tmp && rm -rf yay"
        ]
        
        return self.run(" && ".join(commands), desc="Building and installing yay")

    def setup_chaotic_aur(self):
        """Setup Chaotic AUR repository"""
        if self.run("grep -q '\\[chaotic-aur\\]' /etc/pacman.conf", desc="Checking for Chaotic AUR"):
            self.log('INFO', "Chaotic AUR already configured")
            return True
        
        self.log('INFO', "Setting up Chaotic AUR...")
        
        commands = [
            "sudo pacman-key --recv-key 3056513887B78AEB --keyserver keyserver.ubuntu.com",
            "sudo pacman-key --lsign-key 3056513887B78AEB",
            "sudo pacman -U 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst' 'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst' --noconfirm",
            "sudo sh -c 'echo -e \"\\n[chaotic-aur]\\nInclude = /etc/pacman.d/chaotic-mirrorlist\" >> /etc/pacman.conf'",
            "sudo pacman -Syu --noconfirm"
        ]
        
        for cmd in commands:
            if not self.run(cmd, desc=cmd):
                return False
        return True

    def install_package_category(self, category_name, packages):
        """Install a category of packages"""
        self.log('INFO', f"Installing {category_name} packages...")
        
        for pkg in packages:
            # Check if package is already installed
            check_cmd = f"yay -Qi {pkg} >/dev/null 2>&1"
            if self.run(check_cmd, desc=f"Checking if {pkg} is installed"):
                self.log('INFO', f"{pkg} is already installed")
                continue
            
            if not self.run(f"yay -S --noconfirm --needed {pkg}", desc=f"Installing {pkg}"):
                self.log('WARNING', f"Failed to install {pkg}, continuing...")

    def backup_config(self, config_name):
        """Backup existing configuration"""
        config_path = self.config_dir / config_name
        backup_path = self.backup_dir / config_name
        
        if config_path.exists():
            self.log('INFO', f"Backing up {config_name}...")
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            try:
                if config_path.is_dir():
                    shutil.copytree(config_path, backup_path, dirs_exist_ok=True)
                else:
                    shutil.copy2(config_path, backup_path)
                self.log('SUCCESS', f"Backed up {config_name}")
            except Exception as e:
                self.log('WARNING', f"Could not backup {config_name}: {e}")

    def install_dotfiles(self):
        """Install dotfiles based on dotfiles.json"""
        dotfiles_json_path = Path('./dotfiles.json')
        if not dotfiles_json_path.exists():
            self.log('ERROR', "dotfiles.json not found")
            return False
        
        try:
            with open(dotfiles_json_path, 'r') as f:
                dotfiles_data = json.load(f)
        except Exception as e:
            self.log('ERROR', f"Failed to parse dotfiles.json: {e}")
            return False
        
        self.log('INFO', "Installing dotfiles...")
        
        for dotfile_entry in dotfiles_data:
            source = dotfile_entry.get("source", "").replace("./", "")
            target = dotfile_entry.get("target", "").replace("$HOME", str(self.home_dir))
            pre_copy = dotfile_entry.get("pre_copy", [])
            post_copy = dotfile_entry.get("post_copy", [])
            
            source_path = Path(source)
            target_path = Path(target)
            
            if not source_path.exists():
                self.log('WARNING', f"Source not found: {source_path}")
                continue
            
            # Run pre-copy commands
            for cmd in pre_copy:
                self.run(cmd, desc=f"Pre-copy: {cmd}")
            
            # Backup existing config
            config_name = source_path.name
            self.backup_config(config_name)
            
            # Copy files
            self.log('INFO', f"Installing {source_path} to {target_path}")
            try:
                if source_path.is_dir():
                    shutil.copytree(source_path, target_path, dirs_exist_ok=True)
                else:
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                self.log('SUCCESS', f"Installed {config_name}")
            except Exception as e:
                self.log('ERROR', f"Failed to copy {source_path}: {e}")
                continue
            
            # Run post-copy commands
            for cmd in post_copy:
                self.run(cmd, desc=f"Post-copy: {cmd}")
        
        return True

    def setup_services(self):
        """Enable system services"""
        self.log('INFO', "Setting up services...")
        
        services = ["ly", "bluetooth", "NetworkManager"]
        for service in services:
            self.run(f"sudo systemctl enable {service}.service", desc=f"Enabling {service}")

    def setup_permissions(self):
        """Set proper file permissions"""
        self.log('INFO', "Setting up permissions...")
        self.run(f"sudo chown -R {self.current_user}:{self.current_user} {self.home_dir}/", 
                desc="Setting home directory ownership")

    def create_directories(self):
        """Create necessary directories"""
        self.log('INFO', "Creating necessary directories...")
        
        directories = [
            self.home_dir / "Pictures" / "Screenshots",
            self.config_dir / "assets",
            self.home_dir / ".local" / "bin"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def copy_assets(self):
        """Copy additional assets"""
        assets_path = Path("./assets")
        if assets_path.exists():
            self.log('INFO', "Copying assets...")
            target_assets = self.config_dir / "assets"
            if target_assets.exists():
                shutil.rmtree(target_assets)
            shutil.copytree(assets_path, target_assets)
            self.log('SUCCESS', "Assets copied")

    def display_post_install_info(self):
        """Display post-installation instructions"""
        self.log('SUCCESS', "Installation completed!")
        
        print("\n" + "="*50)
        self.log('INFO', "POST-INSTALLATION INSTRUCTIONS:")
        print("="*50)
        print("1. Set themes and appearance:")
        print("   - Run: nwg-look (set GTK and icon themes)")
        print("   - Run: kvantummanager (select Catppuccin theme)")
        print("   - Run: qt5ct and qt6ct (set Qt themes)")
        print()
        print("2. Configure Fish shell as default:")
        print("   - Run: chsh -s $(which fish)")
        print()
        print("3. Reboot your system:")
        print("   - Run: sudo reboot")
        print()
        print("4. After reboot:")
        print("   - Select Hyprland as your desktop session in ly")
        print("   - Enjoy your new setup!")
        print()
        print(f"Backup of existing configs saved to: {self.backup_dir}")
        print("="*50)

    def install(self):
        """Main installation method"""
        self.log('INFO', f"Starting NullDots installation for user: {self.current_user}")
        
        # Pre-flight checks
        if not self.check_root():
            return False
        
        # System setup
        if not all([
            self.run("sudo pacman -Syu --noconfirm", desc="System update"),
            self.run("sudo pacman -S --needed git base-devel jq --noconfirm", desc="Installing base tools"),
            self.setup_chaotic_aur(),
            self.install_yay()
        ]):
            return False
        
        # Install packages by category
        for category, packages in self.package_categories.items():
            self.install_package_category(category, packages)
        
        # Dotfiles and configuration
        if not all([
            self.install_dotfiles(),
            self.setup_services(),
            self.setup_permissions(),
            self.create_directories(),
            self.copy_assets()
        ]):
            self.log('WARNING', "Some installation steps had issues")
        
        # Final instructions
        self.display_post_install_info()
        return True

def main():
    """Main entry point"""
    try:
        installer = NullDotsInstaller()
        success = installer.install()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[INFO] Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()