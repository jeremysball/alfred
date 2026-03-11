#!/bin/bash
# Static bash completion for alfred
# Generated automatically - do not edit manually

_alfred_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Build command path (e.g., "cron list")
    local cmd_path=""
    for ((i=1; i<COMP_CWORD; i++)); do
        if [[ -n "${COMP_WORDS[i]}" && ! "${COMP_WORDS[i]}" =~ ^- ]]; then
            cmd_path="${cmd_path}${COMP_WORDS[i]} "
        fi
    done
    cmd_path="${cmd_path% }"

    case "$cmd_path" in
        "")
            opts="--help --install-completions --log --telegram -l -t cron daemon memory"
            ;;
        cron)
            opts="approve history list reject review submit"
            ;;
        daemon)
            opts="logs reload start status stop"
            ;;
        memory)
            opts="migrate prune status"
            ;;
        *)
            opts=""
            ;;
    esac

    if [[ -n "$opts" ]]; then
        COMPREPLY=( $(compgen -W "$opts" -- "$cur") )
    fi

    return 0
}

complete -F _alfred_completion alfred
