# Alfred shell completions for fish
# Generated automatically - do not edit manually

# Disable file completions by default
complete -c alfred -f

# Options
complete -c alfred -s t -l telegram -d "Run as Telegram bot"
complete -c alfred -s l -l log -d "Set log level" -a "info debug"
complete -c alfred -l install-completions -d "Install shell completions"
complete -c alfred -n "__fish_use_subcommand" -a "--telegram"
complete -c alfred -n "__fish_use_subcommand" -a "-t"
complete -c alfred -n "__fish_use_subcommand" -a "--log"
complete -c alfred -n "__fish_use_subcommand" -a "-l"
complete -c alfred -n "__fish_use_subcommand" -a "--install-completions"
complete -c alfred -n "__fish_use_subcommand" -a "--help"
