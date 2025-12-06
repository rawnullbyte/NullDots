function update
    if test (count $argv) -gt 0
        pacman $argv
    else
        pacman -Syu
    end
end
