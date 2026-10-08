import { useCallback, useEffect, useMemo, useState } from 'react'

async function readJson(response) {
  try { return await response.json() } catch { return {} }
}

function messageFrom(body, fallback) {
  if (typeof body?.detail === 'string' && body.detail.trim()) return body.detail
  if (typeof body?.detail?.message === 'string' && body.detail.message.trim()) return body.detail.message
  return fallback
}

export function useInferenceConfigurations(modelId, { enabled = true } = {}) {
  const [configurations, setConfigurations] = useState([])
  const [selectedId, setSelectedId] = useState('')
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [error, setError] = useState('')
  const [applyResult, setApplyResult] = useState(null)

  const refresh = useCallback(async () => {
    if (!enabled || !modelId) {
      setConfigurations([])
      setSelectedId('')
      return
    }
    setLoading(true)
    setError('')
    try {
      const response = await fetch(
        '/api/models/' + encodeURIComponent(modelId) + '/inference-configurations',
        { headers: { Accept: 'application/json' }, cache: 'no-store' },
      )
      const body = await readJson(response)
      if (!response.ok) throw new Error(messageFrom(body, 'Could not load inference configurations'))
      const next = Array.isArray(body?.configurations) ? body.configurations : []
      setConfigurations(next)
      setSelectedId(current => next.some(item => item.configuration_id === current)
        ? current
        : (next[0]?.configuration_id || ''))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load inference configurations')
      setConfigurations([])
      setSelectedId('')
    } finally {
      setLoading(false)
    }
  }, [enabled, modelId])

  useEffect(() => { void refresh() }, [refresh])

  const selected = useMemo(
    () => configurations.find(item => item.configuration_id === selectedId) || null,
    [configurations, selectedId],
  )

  const apply = useCallback(async (candidate = selected) => {
    if (!modelId || !candidate || applying) return false
    setApplying(true)
    setError('')
    setApplyResult(null)
    try {
      const response = await fetch(
        '/api/models/' + encodeURIComponent(modelId) + '/inference-configuration',
        {
          method: 'POST',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify({
            configuration_id: candidate.configuration_id,
            configuration: candidate.configuration,
          }),
        },
      )
      const body = await readJson(response)
      if (!response.ok) throw new Error(messageFrom(body, 'Could not apply inference configuration'))
      setApplyResult(body)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not apply inference configuration')
      return false
    } finally {
      setApplying(false)
    }
  }, [applying, modelId, selected])

  return { configurations, selected, selectedId, setSelectedId, loading, applying, error, applyResult, refresh, apply }
}

export default useInferenceConfigurations
