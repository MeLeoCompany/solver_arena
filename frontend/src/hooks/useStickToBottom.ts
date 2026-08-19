import { useCallback, useRef } from 'react'

const STICK_THRESHOLD_PX = 40

export function useStickToBottom<T extends HTMLElement>() {
  const containerRef = useRef<T>(null)
  const stickingRef = useRef(true)

  const handleScroll = useCallback(() => {
    const el = containerRef.current
    if (!el) return
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    stickingRef.current = distanceFromBottom < STICK_THRESHOLD_PX
  }, [])

  const scrollToBottomIfSticking = useCallback(() => {
    if (stickingRef.current) {
      containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight })
    }
  }, [])

  const resetSticking = useCallback(() => {
    stickingRef.current = true
  }, [])

  return { containerRef, handleScroll, scrollToBottomIfSticking, resetSticking }
}
