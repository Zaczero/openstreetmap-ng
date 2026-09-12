import {
  orderLongitudeBounds,
  unwrapLongitude,
} from "../../app/views/map/unwrap-longitude.ts"

const assertClose = (actual: number, expected: number, label: string) => {
  if (Math.abs(actual - expected) > 1e-9) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`)
  }
}

const assertPair = (
  actual: [number, number],
  expected: [number, number],
  label: string,
) => {
  assertClose(actual[0], expected[0], `${label}[0]`)
  assertClose(actual[1], expected[1], `${label}[1]`)
}

// Short Fiji–Tonga hop must stay on one world copy, not wrap the long way.
assertClose(unwrapLongitude(-170, 170), 190, "dateline eastward")
assertClose(unwrapLongitude(170, -170), -190, "dateline westward")
assertClose(unwrapLongitude(10, 5), 10, "same-copy no-op")
assertClose(unwrapLongitude(5, 5), 5, "identical")
assertClose(unwrapLongitude(180, -180), -180, "180 vs -180 same meridian")

// Filter: small inversion is a swapped handle, not a dateline crossing.
assertPair(orderLongitudeBounds(10, 5), [5, 10], "small inversion")
assertPair(orderLongitudeBounds(5, 10), [5, 10], "already ordered")

// Filter: 170 → -170 is a 20° dateline span; keep order and unwrap.
assertPair(orderLongitudeBounds(170, -170), [170, 190], "dateline span")

console.log("ok")
