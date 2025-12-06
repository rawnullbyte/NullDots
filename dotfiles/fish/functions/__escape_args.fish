function __escape_args
    set -l out
    for a in $argv
        # replace single quotes with '"'"' safe sequence then wrap in single quotes
        set a (string replace -a "'" "'\"'\"'" -- $a)
        set out $out "'$a'"
    end
    echo (string join ' ' $out)
end
