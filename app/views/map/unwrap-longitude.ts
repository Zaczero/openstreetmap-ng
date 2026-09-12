const WORLD_WIDTH_DEGREES = 360

/**
 * Return the copy of `lon` closest to `referenceLon`.
 *
 * MapLibre accepts unwrapped longitudes. Neighboring vertices must stay in the
 * same world copy so globe mode draws the short antimeridian path instead of
 * wrapping the long way around the earth.
 */
export const unwrapLongitude = (lon: number, referenceLon: number) =>
  lon + Math.round((referenceLon - lon) / WORLD_WIDTH_DEGREES) * WORLD_WIDTH_DEGREES

/**
 * Order a longitude pair for a filter rectangle.
 *
 * Small inverted spans are handle inversions (swap). Wider jumps are dateline
 * crossings and keep their order, with `maxLon` unwrapped toward `minLon`.
 */
export const orderLongitudeBounds = (
  minLon: number,
  maxLon: number,
): [number, number] => {
  if (Math.abs(maxLon - minLon) < 180 && minLon > maxLon) {
    return [maxLon, minLon]
  }
  return [minLon, unwrapLongitude(maxLon, minLon)]
}
