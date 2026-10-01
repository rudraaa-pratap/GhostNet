import { useEffect, useState } from 'react'

/** Current unix time (seconds), refreshed on an interval — keeps render pure. */
export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now() / 1000)
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return now
}
