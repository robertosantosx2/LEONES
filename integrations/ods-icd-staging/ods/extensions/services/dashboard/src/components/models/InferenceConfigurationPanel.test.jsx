import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import InferenceConfigurationPanel from './InferenceConfigurationPanel'
import { useInferenceConfigurations } from '../../hooks/useInferenceConfigurations'

vi.mock('../../hooks/useInferenceConfigurations', () => ({
  useInferenceConfigurations: vi.fn(),
}))

const configuration = {
  runtime: 'cafe-llama.cpp',
  runtime_revision: 'test',
  kernel: 'baseline',
  model_ref: 'demo-model',
  quantization: 'Q4_K_M',
  context: 4096,
  gpu_layers: 12,
  kv_cache: 'f16',
  flash_attention: true,
  offload: 'none',
  speculation: 'none',
  draft_tokens: 0,
  batch: 1,
}
const candidate = {
  configuration_id: 'config-demo-1234567890',
  configuration,
  measurement_required: true,
  execution_authorized: false,
}

function hookState(overrides = {}) {
  return {
    configurations: [candidate],
    rankedMeasurements: [],
    selected: candidate,
    selectedId: candidate.configuration_id,
    setSelectedId: vi.fn(),
    loading: false,
    applying: false,
    error: '',
    applyResult: null,
    refresh: vi.fn().mockResolvedValue(undefined),
    apply: vi.fn().mockResolvedValue(true),
    ...overrides,
  }
}

describe('InferenceConfigurationPanel', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders discovered configuration fields and the unmeasured notice', () => {
    useInferenceConfigurations.mockReturnValue(hookState())
    render(<InferenceConfigurationPanel modelId="demo-model" />)

    expect(screen.getByRole('heading', { name: 'Inference configuration' })).toBeInTheDocument()
    expect(screen.getByLabelText('KV cache')).toHaveValue('"f16"')
    expect(screen.getByText(/unmeasured proposals/i)).toBeInTheDocument()
  })

  it('applies only a discovered candidate', async () => {
    const state = hookState()
    useInferenceConfigurations.mockReturnValue(state)
    render(<InferenceConfigurationPanel modelId="demo-model" />)

    fireEvent.click(screen.getByRole('button', { name: 'Apply settings' }))
    await waitFor(() => expect(state.apply).toHaveBeenCalledWith(candidate))
  })

  it('benchmarks the exact applied configuration and refreshes measurements', async () => {
    const refresh = vi.fn().mockResolvedValue(undefined)
    useInferenceConfigurations.mockReturnValue(hookState({
      applyResult: { configuration_id: candidate.configuration_id },
      refresh,
    }))
    const onBenchmark = vi.fn().mockResolvedValue(true)
    render(<InferenceConfigurationPanel modelId="demo-model" onBenchmark={onBenchmark} />)

    fireEvent.click(screen.getByRole('button', { name: 'Benchmark this configuration' }))
    await waitFor(() => expect(onBenchmark).toHaveBeenCalledWith(
      'demo-model',
      { configuration_id: candidate.configuration_id },
    ))
    await waitFor(() => expect(refresh).toHaveBeenCalled())
  })

  it('shows measured results only when exact-workload evidence exists', () => {
    useInferenceConfigurations.mockReturnValue(hookState({
      rankedMeasurements: [{
        configuration_id: candidate.configuration_id,
        measured_tps: 42.5,
        workload_id: 'dashboard-local-benchmark-v1:max_tokens=128',
      }],
    }))
    render(<InferenceConfigurationPanel modelId="demo-model" />)

    expect(screen.getByText(/42.5 tokens\/s/)).toBeInTheDocument()
    expect(screen.getByText(/dashboard-local-benchmark-v1:max_tokens=128/)).toBeInTheDocument()
  })
})
