tmux list-sessions -F '#{session_name}' | xargs -n 1 tmux kill-session -t