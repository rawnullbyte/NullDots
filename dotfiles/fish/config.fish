if status is-interactive
    # Commands to run in interactive sessions can go here
end

# Custom uwu command

# safe-arg-escaper (returns quoted args)
function __escape_args
    set -l out
    for a in $argv
        # replace single quotes with '"'"' safe sequence then wrap in single quotes
        set a (string replace -a "'" "'\"'\"'" -- $a)
        set out $out "'$a'"
    end
    echo (string join ' ' $out)
end

# update: default behavior pacman -Syu, but forwards any args to pacman
function update
    if test (count $argv) -gt 0
        pacman $argv
    else
        pacman -Syu
    end
end

# uwu: sudo wrapper that supports:
# - no args -> interactive root shell
# - "uwu install <pkg...>" -> sudo pacman -S <pkg...> (or if first arg after install starts with '-', run pacman with those flags)
# - function invocation: serializes function and runs it under sudo fish -c "<def>\n<call>"
# - otherwise forwards to sudo normally
function uwu
    if test (count $argv) -eq 0
        # interactive root shell
        command sudo -s
        return
    end

    set -l first $argv[1]

    # special-case: uwu install <...>
    if test $first = 'install'
        if test (count $argv) -eq 1
            # no package -> do a full system upgrade
            command sudo pacman -Syu
            return
        end

        set -l rest $argv[2..-1]
        # if the first of rest looks like an option (starts with -), treat as full pacman args
        if string match -q -r '^-' $rest[1]
            command sudo pacman $rest
        else
            command sudo pacman -S $rest
        end
        return
    end

    # if first arg is a fish function, serialize it and run under root's fish
    if functions -q $first
        # capture function definition as text
        set -l fdef (functions $first)

        # prepare remaining args (2..end) safely quoted
        if test (count $argv) -gt 1
            set -l rest (__escape_args $argv[2..-1])
            set -l fullcmd "$fdef\n$first $rest"
        else
            set -l fullcmd "$fdef\n$first"
        end

        # run under sudo: root runs fish -c "<function-def + invocation>"
        command sudo fish -c "$fullcmd"
    else
        # normal external command: forward to sudo
        command sudo $argv
    end
end

# optional: persist to ~/.config/fish/functions (funcsave)


# -- Fastfetch -- #

# ~/.config/fish/config.fish

# Detect kitty as the terminal
if test "$TERM" = "xterm-kitty"
    # Run only if this is the first fish instance in this terminal session
    if not set -q __fastfetch_ran
        set -g __fastfetch_ran 1
        fastfetch
    end
end
