// 64 chars to encode 6 bits
const _ARRAY = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_~"

export const shortLinkEncode = (lon, lat, zoom) => {
    const x = BigInt(Math.floor((lon + 180) * 11930464.711111112)) // (2 ** 32) / 360
    const y = BigInt(Math.floor((lat + 90) * 23860929.422222223)) // (2 ** 32) / 180
    let c = 0n

    for (let i = 31n; i >= 0; i--) {
        c = (c << 2n) | (((x >> i) & 1n) << 1n) | ((y >> i) & 1n)
    }

    const d = Math.ceil((zoom + 8) / 3)
    const r = (zoom + 8) % 3

    const strList = Array(d + r)
    if (r) strList.fill("-", d)

    for (let i = 0n; i < d; i++) {
        const digit = (c >> (58n - 6n * i)) & 0x3fn
        strList[i] = _ARRAY[digit]
    }

    return strList.join("")
}
