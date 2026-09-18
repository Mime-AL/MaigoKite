import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'

describe('API client errors', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('explains an unstructured 404 from an outdated or missing Gateway route', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('404 page not found', { status: 404 })))

    await expect(api.updateUserPreferences({ assistantName: '小七' })).rejects.toThrow('请重启应用')
  })

  it('preserves a structured API error instead of replacing it with the restart hint', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ error: { code: 'NOT_FOUND', message: 'workspace not found' } }),
      { status: 404, headers: { 'Content-Type': 'application/json' } },
    )))

    await expect(api.getUserPreferences()).rejects.toThrow('workspace not found')
  })

  it('requests a model catalog from the configured provider endpoint', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ models: [{ id: 'model-a', context_window: 32768 }] }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.discoverChatModels({
      id: 'profile-a', provider: 'openai_compatible', baseUrl: 'https://models.example/v1',
    }, 'secret')).resolves.toEqual([{ id: 'model-a', context_window: 32768 }])

    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/models/actions/discover'), expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({
        id: 'profile-a', provider: 'openai_compatible',
        base_url: 'https://models.example/v1', api_key: 'secret',
      }),
    }))
  })

  it('maps workspace runtime status without deriving local values in the browser', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({
        workspace_id: 'personal',
        workspace_root: '/srv/workspace',
        workspace_source: 'environment',
        environment: 'production',
        gateway: { status: 'serving', version: '0.1.0' },
        agent_core: { status: 'serving', version: '0.1.0' },
        restart: {
          pending: false,
          required_for: ['Workspace 根目录'],
          hot_applied: ['权限模式'],
          note: '当前没有待重启更改。',
        },
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ))
    vi.stubGlobal('fetch', fetchMock)

    await expect(api.getWorkspaceRuntimeStatus()).resolves.toMatchObject({
      workspaceRoot: '/srv/workspace',
      workspaceSource: 'environment',
      agentCore: { status: 'serving', version: '0.1.0' },
      restart: { requiredFor: ['Workspace 根目录'], hotApplied: ['权限模式'] },
    })
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/workspaces/personal/runtime-status'),
      expect.any(Object),
    )
  })
})
