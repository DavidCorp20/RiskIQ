import { useState } from 'react'
import {
  CheckCircle2,
  ChevronRight,
  Database,
  Eye,
  FileSpreadsheet,
  Info,
  Loader2,
  X,
} from 'lucide-react'
import { discoverFile, ingestFile, batchOverrideConflicts } from './api'
import DataExplorer from './DataExplorer'
import ReconciliationPanel from './ReconciliationPanel'

const activeDatasetId = () => {
  try {
    return (
      JSON.parse(localStorage.getItem('riskiq.activeDataset') || 'null')
        ?.dataset_id || ''
    )
  } catch {
    return ''
  }
}

export default function DataUpload() {
  const [open, setOpen] = useState(false)
  const [explorerOpen, setExplorerOpen] = useState(false)
  const [file, setFile] = useState(null)
  const [discovery, setDiscovery] = useState(null)
  const [mappings, setMappings] = useState([])
  const [loading, setLoading] = useState(false)
  const [bulkLoading, setBulkLoading] = useState(false)
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [snapshotDate, setSnapshotDate] = useState(
    new Date().toISOString().slice(0, 10),
  )
  const [reconciliation, setReconciliation] = useState(null)
  const [resolutions, setResolutions] = useState({})
  const [reason, setReason] = useState('')

  const appendMode = Boolean(activeDatasetId())

  const choose = (event) => {
    setFile(event.target.files?.[0] || null)
    setDiscovery(null)
    setMappings([])
    setError('')
    setDone(false)
    setReconciliation(null)
    setResolutions({})
    setReason('')
  }

  const openUpload = () => {
    setSnapshotDate(new Date().toISOString().slice(0, 10))
    setError('')
    setDone(false)
    setReconciliation(null)
    setResolutions({})
    setReason('')
    setOpen(true)
  }

  const discover = async () => {
    if (!file) return

    setLoading(true)
    setError('')

    try {
      const result = await discoverFile(file)
      setDiscovery(result)
      setMappings(
        (result.mapping_suggestions || []).map((item) => ({
          source: item.source,
          target: item.target,
          required: item.required,
        })),
      )
    } catch (error) {
      setError(error.message || 'No se pudo leer el archivo.')
    } finally {
      setLoading(false)
    }
  }

  const ingest = async (payload = {}) => {
    if (!file || !mappings.length) return

    if (appendMode && !snapshotDate) {
      setError('Indica la fecha de corte del snapshot.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const result = await ingestFile(
        file,
        mappings,
        appendMode ? activeDatasetId() : '',
        snapshotDate,
        payload,
      )

      if (result.status === 'reconciliation_required') {
        setReconciliation(result.reconciliation)
        setResolutions({})
        return
      }

      setDone(true)
      setReconciliation(null)
      setTimeout(() => window.location.reload(), 700)
    } catch (error) {
      const data = error?.data

      if (data?.reconciliation) {
        setReconciliation(data.reconciliation)
        return
      }

      setError(error.message || 'No se pudo procesar la cartera.')
    } finally {
      setLoading(false)
    }
  }

  const commit = () =>
    ingest({
      resolutions,
      actor: 'user',
      reason,
    })

  const bulkOverride = async (justification) => {
    const datasetId = activeDatasetId()
    const conflicts = (reconciliation?.items || []).filter(
      (item) => item.classification === 'conflict',
    )

    if (!datasetId || !conflicts.length) return

    setBulkLoading(true)
    setError('')

    try {
      const result = await batchOverrideConflicts(
        datasetId,
        conflicts.map((item) => item.key),
        Object.fromEntries(
          conflicts.map((item) => [item.key, item.incoming]),
        ),
        justification,
        'user',
        file?.name || 'batch-reconciliation',
        reconciliation?.items || [],
      )

      if (result.rejected) {
        throw new Error(
          `No se pudieron completar ${result.rejected} observaciones: ${
            result.rejections
              ?.map((item) => `${item.key}: ${item.reason}`)
              .join(' · ') || 'revisa la carga.'
          }`,
        )
      }

      setReason(justification)
      setDone(true)
      setReconciliation(null)
      setTimeout(() => window.location.reload(), 700)
    } catch (error) {
      setError(
        error.message || 'No se pudo aplicar la actualización masiva.',
      )
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div className="riskiq-upload-layer">
      <div className="fixed right-5 top-20 z-40 flex gap-2">
        {activeDatasetId() && (
          <button
            type="button"
            onClick={() => setExplorerOpen(true)}
            className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-50"
          >
            <Eye size={16} />
            Ver datos
          </button>
        )}

        <button
          type="button"
          onClick={openUpload}
          className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-300 bg-white px-3 text-sm font-semibold text-slate-800 shadow-sm hover:bg-slate-50"
        >
          {appendMode ? 'Actualizar cartera' : 'Cargar cartera'}
        </button>
      </div>

      {explorerOpen && (
        <div
          className="fixed inset-0 z-[55] overflow-auto bg-slate-950/30 p-4 pt-20"
          role="dialog"
          aria-modal="true"
          aria-label="Explorador de datos"
        >
          <div className="mx-auto max-w-[1500px] rounded-xl border border-slate-200 bg-slate-50 shadow-2xl">
            <div className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
              <div>
                <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  DATA FOUNDATION
                </div>
                <div className="text-sm font-semibold text-slate-900">
                  Explorador de datos · cartera activa
                </div>
              </div>

              <button
                type="button"
                onClick={() => setExplorerOpen(false)}
                className="rounded-md p-2 text-slate-400 hover:bg-slate-100"
                aria-label="Cerrar"
              >
                <X size={18} />
              </button>
            </div>

            <div className="p-4">
              <DataExplorer datasetId={activeDatasetId()} />
            </div>
          </div>
        </div>
      )}

      {open && (
        <div
          className="fixed inset-0 z-[60] flex items-start justify-center overflow-auto bg-slate-950/30 p-4 pt-24"
          role="dialog"
          aria-modal="true"
          aria-label="Cargar cartera"
        >
          <div className="w-full max-w-3xl overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl">
            <header className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
              <div>
                <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <Database size={14} />
                  Data ingestion
                </div>

                <h2 className="mt-1 text-lg font-semibold text-slate-900">
                  {appendMode
                    ? 'Agregar snapshot a la cartera'
                    : 'Cargar cartera de créditos'}
                </h2>

                <p className="mt-0.5 text-sm text-slate-500">
                  {appendMode
                    ? 'La carga usa identidad histórica y reconciliación; no crea duplicados.'
                    : 'CSV o Excel · descubrir campos · revisar mapeo · crear cartera.'}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setOpen(false)}
                className="rounded-md p-2 text-slate-400 hover:bg-slate-100"
                aria-label="Cerrar"
              >
                <X size={18} />
              </button>
            </header>

            <div className="space-y-5 p-5">
              {appendMode && (
                <div className="rounded-lg border border-blue-200 bg-blue-50/60 px-4 py-3 text-sm text-blue-800">
                  <strong>Modo histórico activo.</strong> Esta carga conserva
                  los snapshots anteriores y reconcilia las observaciones que
                  compartan <strong>loan_id + snapshot_date</strong>.
                </div>
              )}

              <div className="rounded-lg border border-slate-200 bg-white p-4">
                <label className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <Info size={14} />
                  Fecha de corte del archivo
                </label>

                <div className="mt-2 flex flex-col gap-2 sm:flex-row sm:items-center">
                  <input
                    type="date"
                    value={snapshotDate}
                    onChange={(event) => setSnapshotDate(event.target.value)}
                    className="h-9 rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-800"
                  />

                  <span className="text-xs text-slate-500">
                    Si el archivo trae snapshot_date, RiskIQ conserva ese valor
                    por fila.
                  </span>
                </div>
              </div>

              <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6">
                <label className="flex cursor-pointer flex-col items-center justify-center gap-2 text-center">
                  <FileSpreadsheet size={28} className="text-slate-500" />

                  <span className="text-sm font-semibold text-slate-800">
                    Selecciona CSV / XLSX
                  </span>

                  <span className="text-xs text-slate-500">
                    Corte mensual, snapshot o histórico completo
                  </span>

                  <input
                    type="file"
                    accept=".csv,.xlsx,.xls"
                    onChange={choose}
                    className="sr-only"
                  />
                </label>

                {file && (
                  <div className="mt-4 flex items-center justify-between rounded-md border border-slate-200 bg-white px-3 py-2">
                    <span className="truncate text-sm font-medium text-slate-700">
                      {file.name}
                    </span>

                    <button
                      type="button"
                      onClick={() => choose({ target: { files: [] } })}
                      className="text-xs text-slate-500 hover:text-slate-900"
                    >
                      Cambiar
                    </button>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={discover}
                  disabled={!file || loading}
                  className="inline-flex h-9 items-center gap-2 rounded-md bg-slate-900 px-3 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 size={15} className="animate-spin" />
                  ) : (
                    <ChevronRight size={15} />
                  )}
                  Detectar campos
                </button>

                {discovery && (
                  <span className="text-xs text-slate-500">
                    Campos detectados:{' '}
                    {discovery.columns?.length ||
                      discovery.headers?.length ||
                      mappings.length}
                  </span>
                )}
              </div>

              {discovery && (
                <div className="rounded-lg border border-slate-200">
                  <div className="border-b border-slate-200 px-4 py-3">
                    <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Mapeo universal
                    </div>
                    <div className="text-sm text-slate-600">
                      Las columnas adicionales se conservan para Data Explorer
                      y segmentación.
                    </div>
                  </div>

                  <div className="max-h-72 overflow-auto">
                    {mappings.map((mapping, index) => (
                      <div
                        className="grid grid-cols-[1fr_auto_1fr_auto] items-center gap-3 border-b border-slate-100 px-4 py-2.5 last:border-0"
                        key={`${mapping.source}-${index}`}
                      >
                        <span className="truncate text-sm text-slate-700">
                          {mapping.source || '—'}
                        </span>

                        <span className="text-slate-400">→</span>

                        <input
                          value={mapping.target || ''}
                          onChange={(event) =>
                            setMappings((items) =>
                              items.map((item, itemIndex) =>
                                itemIndex === index
                                  ? {
                                      ...item,
                                      target: event.target.value,
                                    }
                                  : item,
                              ),
                            )
                          }
                          className="h-8 rounded-md border border-slate-200 px-2 text-sm text-slate-800 outline-none focus:border-slate-400"
                        />

                        <span>
                          {mapping.required ? (
                            <span className="rounded-full bg-amber-50 px-2 py-1 text-[11px] font-medium text-amber-700">
                              requerido
                            </span>
                          ) : null}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {error && (
                <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {error}
                </div>
              )}

              {done && (
                <div className="flex items-center gap-2 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  <CheckCircle2 size={16} />
                  {appendMode ? 'Snapshot reconciliado.' : 'Cartera creada.'}{' '}
                  Actualizando RiskIQ…
                </div>
              )}

              <div className="flex justify-end gap-2 border-t border-slate-200 pt-4">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="h-9 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700"
                >
                  Cancelar
                </button>

                <button
                  type="button"
                  onClick={() => ingest()}
                  disabled={!file || !mappings.length || loading || done}
                  className="h-9 rounded-md bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
                >
                  {loading
                    ? 'Analizando…'
                    : appendMode
                      ? 'Revisar y reconciliar'
                      : 'Crear cartera y analizar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {reconciliation && (
        <ReconciliationPanel
          report={reconciliation}
          resolutions={resolutions}
          setResolutions={setResolutions}
          reason={reason}
          setReason={setReason}
          loading={loading}
          bulkLoading={bulkLoading}
          onBulkOverride={bulkOverride}
          onCancel={() => setReconciliation(null)}
          onCommit={commit}
        />
      )}
    </div>
  )
}
