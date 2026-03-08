# Alfred shell completions for fish
# Generated automatically - do not edit manually

# Disable file completions by default
complete -c alfred -f

# Global flags (available at top-level only, not in subcommands)
complete -c alfred -n "__fish_use_subcommand" -s t -l telegram -d "Run as Telegram bot"
complete -c alfred -n "__fish_use_subcommand" -s l -l log -d "Set log level" -a "info debug"
complete -c alfred -n "__fish_use_subcommand" -l install-completions -d "Install shell completions"
complete -c alfred -l help -d "Show help"

# Top-level commands with descriptions
complete -c alfred -n "__fish_use_subcommand" -a "daemon" -d "Manage the background daemon process"
complete -c alfred -n "__fish_use_subcommand" -a "cron" -d "Manage scheduled cron jobs"
complete -c alfred -n "__fish_use_subcommand" -a "memory" -d "Memory system management"
complete -c alfred -n "__fish_use_subcommand" -a "--telegram" -d "--telegram"
complete -c alfred -n "__fish_use_subcommand" -a "-t" -d "-t"
complete -c alfred -n "__fish_use_subcommand" -a "--log" -d "--log"
complete -c alfred -n "__fish_use_subcommand" -a "-l" -d "-l"
complete -c alfred -n "__fish_use_subcommand" -a "--install-completions" -d "--install-completions"
complete -c alfred -n "__fish_use_subcommand" -a "--help" -d "--help"

# Subcommand completions
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "list" -d "List all scheduled jobs"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "submit" -d "Submit a new job for review"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "review" -d "Review pending jobs"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "approve" -d "Approve a pending job"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "reject" -d "Reject a pending job"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "history" -d "Show job execution history"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "start" -d "Start a job immediately"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "stop" -d "Stop a running job"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "status" -d "Show job status"
complete -c alfred -n "__fish_seen_subcommand_from cron" -a "reload" -d "Reload cron configuration"
complete -c alfred -n "__fish_seen_subcommand_from daemon" -a "stop" -d "Stop the background daemon"
complete -c alfred -n "__fish_seen_subcommand_from daemon" -a "status" -d "Check daemon status"
complete -c alfred -n "__fish_seen_subcommand_from daemon" -a "reload" -d "Reload daemon configuration"
complete -c alfred -n "__fish_seen_subcommand_from daemon" -a "logs" -d "Open log file in $PAGER or $EDITOR"
complete -c alfred -n "__fish_seen_subcommand_from memory" -a "migrate" -d "Migrate memory storage"
complete -c alfred -n "__fish_seen_subcommand_from memory" -a "status" -d "Show memory status"
complete -c alfred -n "__fish_seen_subcommand_from memory" -a "prune" -d "Prune expired memories"

# Command-specific options
complete -c alfred -n "__fish_seen_subcommand_from daemon; and not __fish_seen_subcommand_from stop status reload logs" -l bg -d "Run in background (daemonize)"
