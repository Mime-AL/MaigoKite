const RUNTIME_ENV_ALLOWLIST = [
  'PATH',
  'LANG',
  'LC_ALL',
  'HOME',
  'XDG_CACHE_HOME',
  'XDG_CONFIG_HOME',
  'XDG_DATA_HOME',
  'USERPROFILE',
  'APPDATA',
  'LOCALAPPDATA',
  'SYSTEMROOT',
  'COMSPEC',
  'PATHEXT',
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
  'VIRTUAL_ENV',
  'UV_PROJECT_ENVIRONMENT',
  'UV_PYTHON_INSTALL_DIR',
  'UV_CACHE_DIR',
  'http_proxy',
  'https_proxy',
  'all_proxy',
  'no_proxy',
  'MAIGOKITE_WORKSPACE_ROOT',
  'MAIGOKITE_INSTALL_DIR',
] as const

/** Build the minimal host environment needed by the local runtime and OS keychain. */
export function createRuntimeEnvironment(source: NodeJS.ProcessEnv = process.env): NodeJS.ProcessEnv {
  const target: NodeJS.ProcessEnv = {}
  for (const key of RUNTIME_ENV_ALLOWLIST) {
    // Windows commonly spells these Path/SystemRoot; Node's explicit env is case-sensitive.
    const sourceKey = process.platform === 'win32'
      ? Object.keys(source).find((entry) => entry.toUpperCase() === key.toUpperCase())
      : key
    const value = sourceKey ? source[sourceKey] : undefined
    if (value) target[key] = value
  }
  if (!target.LANG) target.LANG = 'C.UTF-8'
  // The backend writes UTF-8 into Node pipes on both Windows editions;
  // Python 3.14 otherwise uses the host locale for redirected text streams.
  target.PYTHONUTF8 = '1'
  target.PYTHONIOENCODING = 'utf-8'
  target.PYTHONUNBUFFERED = '1'
  return target
}
