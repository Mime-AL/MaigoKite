// @vitest-environment node
import { describe, expect, it } from 'vitest'

import { createRuntimeEnvironment } from '@/electron/runtime-env'

describe('Electron runtime environment', () => {
  it('keeps keychain and proxy plumbing without forwarding arbitrary secrets', () => {
    const result = createRuntimeEnvironment({
      PATH: '/usr/bin',
      DBUS_SESSION_BUS_ADDRESS: 'unix:path=/run/user/1000/bus',
      XDG_RUNTIME_DIR: '/run/user/1000',
      HTTPS_PROXY: 'http://proxy.example.test:8080',
      NANAMI_WORKSPACE_ROOT: '/workspace/project',
      OPENAI_API_KEY: 'must-not-be-forwarded',
      UNRELATED_SECRET: 'must-not-be-forwarded',
    })

    expect(result).toMatchObject({
      PATH: '/usr/bin',
      DBUS_SESSION_BUS_ADDRESS: 'unix:path=/run/user/1000/bus',
      XDG_RUNTIME_DIR: '/run/user/1000',
      HTTPS_PROXY: 'http://proxy.example.test:8080',
      NANAMI_WORKSPACE_ROOT: '/workspace/project',
    })
    expect(result.OPENAI_API_KEY).toBeUndefined()
    expect(result.UNRELATED_SECRET).toBeUndefined()
  })
})
