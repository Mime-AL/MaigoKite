export type { CapsuleRequest, DesktopNotification } from './preload'
// Derive the renderer contract from the actual whitelist, not a second list of
// promised methods that can compile while no matching preload implementation exists.
// The renderer Window declaration lives in types/electron.d.ts so TypeScript
// cannot shadow it with this directory's same-named preload.ts module.
export {}
