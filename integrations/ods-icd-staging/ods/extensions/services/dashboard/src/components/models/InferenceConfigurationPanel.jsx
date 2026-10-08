import './inference-configuration-panel.css'
import { useMemo, useState } from 'react'
import { useInferenceConfigurations } from '../../hooks/useInferenceConfigurations'

const LABELS = {
  runtime: 'Runtime', runtime_revision: 'Runtime revision', kernel: 'Kernel',
  quantization: 'Quantization', context: 'Context', gpu_layers: 'GPU layers',
  kv_cache: 'KV cache', flash_attention: 'Flash Attention', offload: 'Offload',
  speculation: 'Speculation', draft_tokens: 'Draft tokens', batch: 'Batch',
}
const EDITABLE_DIMENSIONS = [
  'kernel', 'context', 'gpu_layers', 'kv_cache', 'flash_attention',
  'offload', 'speculation', 'draft_tokens', 'batch',
]
function valueKey(value) { return JSON.stringify(value ?? null) }
function displayValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'On' : 'Off'
  return String(value)
}

/** Staged ODS component. Pass the existing Dashboard i18n translator as t. */
export default function InferenceConfigurationPanel({ modelId, t = (_key, fallback) => fallback }) {
  const {
    configurations, selected, selectedId, setSelectedId, loading, applying,
    error, applyResult, refresh, apply,
  } = useInferenceConfigurations(modelId)
  const [draft, setDraft] = useState(null)
  const current = draft || selected?.configuration || null

  const exactCandidate = useMemo(() => {
    if (!current) return null
    return configurations.find(item =>
      Object.keys(item.configuration).every(key =>
        valueKey(item.configuration[key]) === valueKey(current[key]),
      ),
    ) || null
  }, [configurations, current])

  const optionsFor = key => {
    const options = new Map()
    configurations.forEach(item => options.set(valueKey(item.configuration[key]), item.configuration[key]))
    return [...options.entries()]
  }

  const changeDimension = (key, serialized) => {
    const value = JSON.parse(serialized)
    const base = { ...(current || {}), [key]: value }
    const match = configurations.find(item =>
      Object.keys(item.configuration).every(field =>
        valueKey(item.configuration[field]) === valueKey(base[field]),
      ),
    )
    setDraft(base)
    if (match) {
      setSelectedId(match.configuration_id)
      setDraft(match.configuration)
    }
  }

  const chooseCandidate = event => {
    setSelectedId(event.target.value)
    const candidate = configurations.find(item => item.configuration_id === event.target.value)
    setDraft(candidate?.configuration || null)
  }

  const submit = async () => { if (exactCandidate) await apply(exactCandidate) }

  return (
    <section className="ods-inference-configuration" aria-labelledby="ods-icd-title">
      <header>
        <h3 id="ods-icd-title">{t('models.inferenceConfiguration.title', 'Inference configuration')}</h3>
        <p>{t('models.inferenceConfiguration.description', 'Explore supported runtime settings for this model. Applying settings does not activate or change the selected model.')}</p>
      </header>
      {loading && <p role="status">{t('models.inferenceConfiguration.loading', 'Discovering configurations…')}</p>}
      {!loading && !error && configurations.length === 0 && (
        <p>{t('models.inferenceConfiguration.empty', 'No compatible inference configurations were discovered for this model.')}</p>
      )}
      {configurations.length > 0 && (
        <>
          <label>
            {t('models.inferenceConfiguration.preset', 'Discovered configuration')}
            <select value={selectedId} onChange={chooseCandidate} disabled={loading || applying}>
              {configurations.map(item => (
                <option key={item.configuration_id} value={item.configuration_id}>
                  {item.configuration.runtime} · {item.configuration.kernel || 'default'} · {item.configuration.kv_cache || 'default'} · {item.configuration_id.slice(0, 10)}
                </option>
              ))}
            </select>
          </label>
          {current && (
            <div className="ods-inference-configuration__fields">
              {EDITABLE_DIMENSIONS.filter(key => Object.prototype.hasOwnProperty.call(current, key)).map(key => (
                <label key={key}>
                  {t('models.inferenceConfiguration.fields.' + key, LABELS[key] || key)}
                  <select value={valueKey(current[key])} onChange={event => changeDimension(key, event.target.value)} disabled={loading || applying}>
                    {optionsFor(key).map(([serialized, value]) => (
                      <option key={serialized} value={serialized}>{displayValue(value)}</option>
                    ))}
                  </select>
                </label>
              ))}
              <dl>
                {Object.entries(current).filter(([key]) => !EDITABLE_DIMENSIONS.includes(key) && key !== 'model_ref').map(([key, value]) => (
                  <div key={key}>
                    <dt>{t('models.inferenceConfiguration.fields.' + key, LABELS[key] || key)}</dt>
                    <dd>{displayValue(value)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
          {!exactCandidate && (
            <p role="status">{t('models.inferenceConfiguration.invalidCombination', 'This combination is not in the discovered candidate set. Choose a supported combination before applying.')}</p>
          )}
          <p>{t('models.inferenceConfiguration.measurementNotice', 'Discovered settings are unmeasured proposals. Run a benchmark after applying; performance is not guaranteed.')}</p>
          <div className="ods-inference-configuration__actions">
            <button type="button" onClick={refresh} disabled={loading || applying}>{t('models.inferenceConfiguration.refresh', 'Refresh')}</button>
            <button type="button" onClick={submit} disabled={!exactCandidate || applying || loading}>
              {applying ? t('models.inferenceConfiguration.applying', 'Applying…') : t('models.inferenceConfiguration.apply', 'Apply settings')}
            </button>
          </div>
        </>
      )}
      {error && <p role="alert">{error}</p>}
      {applyResult && (
        <p role="status">{t('models.inferenceConfiguration.applied', 'Settings applied. The model was not activated; benchmark this exact configuration before comparing performance.')}</p>
      )}
    </section>
  )
}
