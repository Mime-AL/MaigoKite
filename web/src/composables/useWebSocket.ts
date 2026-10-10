import { onUnmounted, ref } from 'vue'
import { api, type AgentEvent } from '@/api/client'
import { EventSocket } from '@/api/socket'
export function useWebSocket(sessionId: string, receive: (event: AgentEvent) => void = () => undefined) {
  const isConnected = ref(false)
  const stream = new EventSocket({
    connect: (callback) => api.connectEvents(sessionId, callback),
    history: (after, signal) => api.listTaskEvents(sessionId, after, signal),
    receive: (event) => receive(event),
    connection: (value) => {
      isConnected.value = value
    },
  })
  onUnmounted(() => stream.stop())
  return { isConnected, connect: () => stream.start(), disconnect: () => stream.stop() }
}
