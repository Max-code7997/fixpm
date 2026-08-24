# fixpm zsh hook
# Enable with:  eval "$(fixpm --init zsh)"   (add that line to ~/.zshrc)

typeset -g __FIXPM_LAST_CMD=""

__fixpm_preexec() {
  __FIXPM_LAST_CMD="$1"                 # full command line about to run
}

__fixpm_precmd() {
  local ec=$?
  local cmd="$__FIXPM_LAST_CMD"
  export FIXPM_LAST_COMMAND="$cmd"
  export FIXPM_LAST_EXIT_CODE="$ec"
  [[ -n "${FIXPM_DEBUG:-}" ]] && print -r -- "fixpm hook: cmd=$cmd ec=$ec" >&2
  (( ec == 0 )) && return 0
  case "$cmd" in
    ""|fixpm*|"npm -v"*) return 0 ;;
    npm*|npx*|pnpx*|pnpm*|yarn*)
      # Set FIXPM_DEBUG=1 to see why the probe fails (e.g. fixpm not on PATH).
      if [[ -n "${FIXPM_DEBUG:-}" ]]; then
        command fixpm --dry-run "$cmd"
      else
        command fixpm --dry-run "$cmd" >/dev/null 2>&1
      fi && \
        print -P "  %F{yellow}fix available -- run %Bfixpm%b%f"
      ;;
  esac
  return 0
}

autoload -Uz add-zsh-hook
add-zsh-hook preexec __fixpm_preexec
add-zsh-hook precmd __fixpm_precmd
