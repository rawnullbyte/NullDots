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
