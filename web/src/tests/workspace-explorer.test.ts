import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'
import { useWorkspaceStore } from '@/stores/workspace'

import { api } from '@/api/client'
import WorkspaceDiff from '@/components/file-explorer/WorkspaceDiff.vue'
import { useFileTree } from '@/composables/useFileTree'

describe('workspace explorer', () => {
  beforeEach(() => { vi.restoreAllMocks() })

  it('loads directories lazily and previews a selected text file', async () => {
    vi.spyOn(api, 'listWorkspaceFiles').mockImplementation(async path => path
      ? [{ name: 'main.ts', path: 'src/main.ts', type: 'file', size: 12, modified_at: '2026-01-01T00:00:00Z' }]
      : [{ name: 'src', path: 'src', type: 'directory', modified_at: '2026-01-01T00:00:00Z' }])
    vi.spyOn(api, 'getWorkspaceFile').mockResolvedValue({
      path: 'src/main.ts', content: 'const ready = true', binary: false,
      truncated: false, size: 18, modified_at: '2026-01-01T00:00:00Z',
    })
    useWorkspaceStore().select('folder-a')
    const scope = effectScope()
    const explorer = scope.run(() => useFileTree())!

    await flushPromises()
    expect(api.listWorkspaceFiles).toHaveBeenCalledTimes(1)
    await explorer.toggleExpand(explorer.tree.value[0])
    await explorer.selectNode(explorer.tree.value[0].children![0])

    expect(api.listWorkspaceFiles).toHaveBeenNthCalledWith(1, '', 'folder-a')
    expect(api.listWorkspaceFiles).toHaveBeenNthCalledWith(2, 'src', 'folder-a')
    expect(api.getWorkspaceFile).toHaveBeenCalledWith('src/main.ts', 'folder-a')
    expect(explorer.selectedContent.value?.content).toContain('ready')
    await explorer.toggleExpand(explorer.tree.value[0])
    await explorer.toggleExpand(explorer.tree.value[0])
    expect(api.listWorkspaceFiles).toHaveBeenCalledTimes(2)
    scope.stop()
  })

  it('renders additions and deletions from the workspace diff endpoint', async () => {
    // Chromium supplies this observer; jsdom does not implement layout observers.
    vi.stubGlobal('ResizeObserver', class {
      observe() {}
      unobserve() {}
      disconnect() {}
    })
    vi.spyOn(api, 'listWorkspaceChanges').mockResolvedValue({
      git: true,
      truncated: false,
      changes: [{ path: 'src/main.ts', status: 'modified', additions: 0, deletions: 0, diff: '', diff_truncated: false }],
    })
    vi.spyOn(api, 'getWorkspaceDiff').mockResolvedValue({
      path: 'src/main.ts', status: 'modified', additions: 1, deletions: 1,
      diff: '@@ -1 +1 @@\n-old\n+new\n', diff_truncated: false,
    })
    const wrapper = mount(WorkspaceDiff)
    await flushPromises()

    expect(wrapper.text()).toContain('src/main.ts')
    expect(wrapper.find('code.addition').text()).toContain('+new')
    expect(wrapper.find('code.deletion').text()).toContain('-old')
  })
})
