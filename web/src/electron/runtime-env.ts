const RUNTIME_ENV_ALLOWLIST = [
  'PATH',
  'LANG',
  'LC_ALL',
  'HOME',
  'USERPROFILE',
  'APPDATA',
  'LOCALAPPDATA',
  'SYSTEMROOT',
  'TEMP',
  'TMP',
  'TMPDIR',
  'XDG_RUNTIME_DIR',
  'DBUS_SESSION_BUS_ADDRESS',
  'HTTP_PROXY',
  'HTTPS_PROXY',
  'ALL_PROXY',
  'NO_PROXY',
  'SSL_CERT_FILE',
  'REQUESTS_CA_BUNDLE',
  'NANAMI_WORKSPACE_ROOT',
] as const

/** Build the minimal host environment needed by the local runtime and OS keychain. */
export function createRuntimeEnvironment(source: NodeJS.ProcessEnv = process.env): NodeJS.ProcessEnv {
  const target: NodeJS.ProcessEnv = {}
  for (const key of RUNTIME_ENV_ALLOWLIST) {
    const value = source[key]
    if (value) target[key] = value
  }
  if (!target.LANG) target.LANG = 'C.UTF-8'
  return target
}
