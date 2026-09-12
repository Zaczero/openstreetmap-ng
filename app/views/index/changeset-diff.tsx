import { LoadingSpinner } from "@index/_action-sidebar"
import { clearChangesetDiff, setChangesetDiff } from "@map/layers/changeset-diff"
import { convertRenderElementsData } from "@map/render-objects"
import { useSignal } from "@preact/signals"
import type { Data_Element as ChangesetElement } from "@proto/changeset_pb"
import {
  Service as ElementService,
  type DataValid as ElementData,
} from "@proto/element_pb"
import { ElementType } from "@proto/shared_pb"
import { rpcUnary } from "@utils/rpc"
import type { OSMNode, OSMWay } from "@utils/osm-objects"
import type { Map as MaplibreMap } from "maplibre-gl"
import { useEffect } from "preact/hooks"
import { t } from "i18next"

type DiffObjects = (OSMNode | OSMWay)[]

type DiffElement = {
  element: ChangesetElement
  type: ElementType
}

type DiffState =
  | { tag: "loading" }
  | {
      tag: "ready"
      loaded: number
      failed: number
      truncated: number
      before: DiffObjects
      after: DiffObjects
    }
  | { tag: "error" }

const MAX_DIFF_ELEMENTS = 120
const DIFF_REQUEST_CONCURRENCY = 4

const getDiffElements = (data: {
  nodes: ChangesetElement[]
  ways: ChangesetElement[]
  relations: ChangesetElement[]
}): DiffElement[] => [
  ...data.nodes.map((element) => ({ element, type: ElementType.node })),
  ...data.ways.map((element) => ({ element, type: ElementType.way })),
  ...data.relations.map((element) => ({ element, type: ElementType.relation })),
]

const selectTargetGeometry = (
  response: ElementData,
  entry: DiffElement,
): DiffObjects => {
  const objects = convertRenderElementsData(response.context.render)
  if (entry.type === ElementType.relation) return objects

  return objects.filter(
    (object) =>
      object.type === ElementType[entry.type] && object.id === entry.element.id,
  )
}

const addUniqueObjects = (
  target: DiffObjects,
  seen: Set<string>,
  objects: DiffObjects,
) => {
  for (const object of objects) {
    const key = `${object.type}:${object.id}`
    if (seen.has(key)) continue
    seen.add(key)
    target.push(object)
  }
}

const loadSide = async (
  entry: DiffElement,
  version: bigint | null,
  signal: AbortSignal,
): Promise<{ objects: DiffObjects; attempted: boolean; failed: boolean }> => {
  if (version === null) return { objects: [], attempted: false, failed: false }

  try {
    const response = await rpcUnary(ElementService.method.get)(
      {
        ref: {
          case: "version",
          value: {
            type: entry.type,
            id: entry.element.id,
            version,
          },
        },
      },
      { signal },
    )
    return {
      objects: selectTargetGeometry(response.element, entry),
      attempted: true,
      failed: false,
    }
  } catch (error) {
    if (signal.aborted) throw error
    console.warn(
      "ChangesetDiff: Failed to load element version",
      entry.element.id,
      error,
    )
    return { objects: [], attempted: true, failed: true }
  }
}

const loadDiff = async (
  data: {
    nodes: ChangesetElement[]
    ways: ChangesetElement[]
    relations: ChangesetElement[]
  },
  signal: AbortSignal,
): Promise<Extract<DiffState, { tag: "ready" }>> => {
  const allEntries = getDiffElements(data)
  const entries = allEntries.slice(0, MAX_DIFF_ELEMENTS)
  const before: DiffObjects = []
  const after: DiffObjects = []
  const beforeSeen = new Set<string>()
  const afterSeen = new Set<string>()
  let nextIndex = 0
  let loaded = 0
  let failed = 0

  const loadEntry = async (entry: DiffElement) => {
    const version = entry.element.version
    const beforeVersion = version > 1n ? version - 1n : null
    const afterVersion = entry.element.visible ? version : null

    const [beforeResult, afterResult] = await Promise.all([
      loadSide(entry, beforeVersion, signal),
      loadSide(entry, afterVersion, signal),
    ])

    if (beforeResult.attempted || afterResult.attempted) loaded++
    if (beforeResult.failed || afterResult.failed) failed++
    addUniqueObjects(before, beforeSeen, beforeResult.objects)
    addUniqueObjects(after, afterSeen, afterResult.objects)
  }

  const worker = async () => {
    while (true) {
      if (signal.aborted)
        throw new DOMException("The diff request was aborted", "AbortError")
      const index = nextIndex++
      const entry = entries[index]
      if (!entry) return
      await loadEntry(entry)
    }
  }

  await Promise.all(
    Array.from({ length: Math.min(DIFF_REQUEST_CONCURRENCY, entries.length) }, () =>
      worker(),
    ),
  )

  return {
    tag: "ready",
    loaded,
    failed,
    truncated: allEntries.length - entries.length,
    before,
    after,
  }
}

const DiffLegend = () => (
  <div class="changeset-diff-legend small mb-2">
    <span>
      <i
        class="changeset-diff-swatch changeset-diff-swatch-before me-1"
        aria-hidden="true"
      />
      {t("changeset.diff.before")}
    </span>
    <span class="ms-3">
      <i
        class="changeset-diff-swatch changeset-diff-swatch-after me-1"
        aria-hidden="true"
      />
      {t("changeset.diff.after")}
    </span>
  </div>
)

export const ChangesetDiff = ({
  map,
  data,
}: {
  map: MaplibreMap
  data: {
    id: bigint
    nodes: ChangesetElement[]
    ways: ChangesetElement[]
    relations: ChangesetElement[]
  }
}) => {
  const state = useSignal<DiffState>({ tag: "loading" })

  useEffect(() => {
    const controller = new AbortController()
    clearChangesetDiff(map)
    state.value = { tag: "loading" }

    void loadDiff(data, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return
        setChangesetDiff(map, result.before, result.after)
        state.value = result
      })
      .catch((error) => {
        if (controller.signal.aborted) return
        console.error("ChangesetDiff: Failed to load", error)
        state.value = { tag: "error" }
      })

    return () => {
      controller.abort()
      clearChangesetDiff(map)
    }
  }, [map, data.id])

  const current = state.value
  return (
    <div
      class="section changeset-diff"
      aria-live="polite"
    >
      <h4>{t("changeset.diff.title")}</h4>
      {current.tag === "loading" ? (
        <div class="d-flex align-items-center gap-2 text-muted">
          <LoadingSpinner />
          <span>{t("changeset.diff.loading")}</span>
        </div>
      ) : current.tag === "error" ? (
        <p class="alert alert-warning mb-0">{t("changeset.diff.error")}</p>
      ) : (
        <>
          <DiffLegend />
          <p class="small text-muted mb-1">
            {t("changeset.diff.summary", { count: current.loaded })}
          </p>
          {!current.before.length && !current.after.length && (
            <p class="small text-muted mb-1">{t("changeset.diff.no_geometry")}</p>
          )}
          {current.failed > 0 && (
            <p class="small text-muted mb-1">
              {t("changeset.diff.partial", { count: current.failed })}
            </p>
          )}
          {current.truncated > 0 && (
            <p class="small text-muted mb-0">
              {t("changeset.diff.limit", { count: current.truncated })}
            </p>
          )}
        </>
      )}
    </div>
  )
}
