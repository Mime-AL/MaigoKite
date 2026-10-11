// Loaded only by the complete local suite, not by ordinary `npm run dev`.
// Vite has no persistent task state: close it when its launcher's pipe disappears.
if (process.env.MAIGOKITE_PARENT_PIPE === '1') {
  const stop = () => process.kill(process.pid, 'SIGTERM')
  process.stdin.once('end', stop)
  process.stdin.once('error', stop)
  process.stdin.resume()
}
