# fixpm bash hook
# Enable with:  eval "$(fixpm --init bash)"   (add that line to ~/.bashrc)

__FIXPM_LAST_CMD=""
__FIXPM_RUNNING=1

# Terminal-integration helpers (systemd OSC-133, vte.sh, ...) also run inside
# the PROMPT_COMMAND chain / PS0; a call to an already-defined "__"-prefixed
# function can never be user-typed input, so never treat it as a command.
__fixpm_is_helper() {
  local first=${1%% *}
  [ "${first#__}" != "$first" ] && declare -f -- "$first" >/dev/null 2>&1
}

# DEBUG-trap based capture. Secondary channel only: other integrations may
# install their own DEBUG trap over ours (only one exists per shell), so this
# path can silently die at any time.
__fixpm_record() {
  [ -n "$COMP_LINE" ] && return 0        # don't record during tab-completion
  [ -n "$__FIXPM_RUNNING" ] && return 0
  __fixpm_is_helper "$BASH_COMMAND" && return 0
  __FIXPM_RUNNING=1                      # close the gate: one record per cycle
  __FIXPM_LAST_CMD=$BASH_COMMAND
  return 0
}

# Runs as the LAST entry of PROMPT_COMMAND: opens the capture gate only after
# every prompt-time integration function has finished, so none of them can
# leak into the captured command.
__fixpm_arm() {
  unset __FIXPM_RUNNING
  return 0
}

__fixpm_hook() {
  local ec=$?
  local cmd=""

  # PRIMARY channel: read the just-executed line from history. History is
  # written right after execution, in the same prompt cycle as $?, so cmd and
  # ec always describe the SAME command — immune to DEBUG-trap clobbering.
  # NOTE: `history 1` is deliberately used instead of `fc -ln -1`; empirically
  # fc's view lags one entry behind at PROMPT_COMMAND time on some builds.
  local hist
  hist=$(history 1 2>/dev/null | sed -E 's/^[[:space:]]*[0-9]+[[:space:]]+//;
                                         s/^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}(:[0-9]{2})?[[:space:]]+//')
  if [ -n "$hist" ]; then
    cmd=$hist
  else
    cmd=$__FIXPM_LAST_CMD                   # fallback: history unavailable
  fi

  __fixpm_is_helper "$cmd" && cmd=""
  # Self-heal: an integration may have installed its own DEBUG trap over ours.
  trap '__fixpm_record' DEBUG

  export FIXPM_LAST_COMMAND="$cmd"
  export FIXPM_LAST_EXIT_CODE="$ec"
  if [ -n "${FIXPM_DEBUG:-}" ]; then
    printf 'fixpm hook: cmd=%q ec=%s\n' "$cmd" "$ec" >&2
  fi
  [ "$ec" -eq 0 ] && return 0
  case "$cmd" in
    ""|fixpm*|"npm -v"*) return 0 ;;
    npm*|npx*|pnpx*|pnpm*|yarn*)
      # Set FIXPM_DEBUG=1 to see why the probe fails (e.g. fixpm not on PATH).
      if [ -n "${FIXPM_DEBUG:-}" ]; then
        command fixpm --dry-run "$cmd"
      else
        command fixpm --dry-run "$cmd" >/dev/null 2>&1
      fi && \
        printf '  \033[33mfix available -- run \033[1mfixpm\033[0m\033[33m\033[0m\n'
      ;;
  esac
  return 0
}

PROMPT_COMMAND="__fixpm_hook${PROMPT_COMMAND:+;$PROMPT_COMMAND};__fixpm_arm"
trap '__fixpm_record' DEBUG
