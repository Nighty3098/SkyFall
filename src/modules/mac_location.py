import asyncio
import gzip
import struct
import xml.etree.ElementTree as ET
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

APPLE_SENTINEL = -18000000000


class MacLocation:
    def __init__(self):
        pass

    @staticmethod
    def _decode_varint(data, offset):
        val = 0
        shift = 0
        while True:
            byte = data[offset]
            val |= (byte & 0x7F) << shift
            shift += 7
            offset += 1
            if not (byte & 0x80):
                break
        return val, offset

    @staticmethod
    def _zigzag(v):
        return (v >> 1) ^ -(v & 1)

    def _mylnikov(self, mac: str, timeout: int = 10):
        try:
            import requests

            r = requests.get(
                "https://api.mylnikov.org/geolocation/wifi",
                params={"v": "1.1", "data": "open", "bssid": mac},
                timeout=timeout,
            )
            d = r.json()
            if d.get("result") == 200 and d.get("data", {}).get("lat") is not None:
                return d["data"]["lat"], d["data"]["lon"]
        except Exception:
            pass
        return None

    def _yandex(self, mac: str, timeout: int = 10):
        try:
            import requests

            r = requests.get(
                "https://api.lbs.yandex.net/cellid_location/",
                params={"wifinetworks": f"{mac.replace(':', '')}:-65"},
                timeout=timeout,
            )
            root = ET.fromstring(r.text)
            if root.get("source") == "FoundByWifi":
                coords = root.find("coordinates")
                if coords is not None:
                    lat = coords.get("latitude")
                    lon = coords.get("longitude")
                    if lat and lon:
                        return float(lat), float(lon)
        except Exception:
            pass
        return None

    def _microsoft(self, mac: str, timeout: int = 10):
        try:
            import requests

            xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<GetLocationUsingFingerprint xmlns="http://inference.location.live.com">
  <RequestHeader>
    <Timestamp>{datetime.now().strftime("%Y-%m-%dT%H:%M:%S")}</Timestamp>
    <ApplicationId>e1e71f6b-2149-45f3-a298-a20682ab5017</ApplicationId>
    <TrackingId>21BF9AD6-CFD3-46B3-B041-EE90BD34FDBC</TrackingId>
    <DeviceProfile>
      <ClientGuid>0fc571be-4624-4ce0-b04e-911bdeb1a222</ClientGuid>
      <Platform>Windows7</Platform>
      <DeviceType>PC</DeviceType>
      <OSVersion>7600.16695.amd64fre.win7_gdr.101026-1503</OSVersion>
      <LFVersion>9.0.8080.16413</LFVersion>
      <ExtendedDeviceInfo/>
    </DeviceProfile>
    <Authorization/>
  </RequestHeader>
  <BeaconFingerprint>
    <Detections>
      <Wifi7>
        <BssId>{mac}</BssId>
        <rssi>-1</rssi>
      </Wifi7>
    </Detections>
  </BeaconFingerprint>
</GetLocationUsingFingerprint>"""
            r = requests.post(
                "https://inference.location.live.net/inferenceservice/v21/Pox/GetLocationUsingFingerprint",
                data=xml,
                headers={"Content-Type": "application/xml"},
                timeout=timeout,
            )
            if r.status_code != 200:
                return None
            ns = {"ns": "http://inference.location.live.com"}
            result = ET.fromstring(r.text).find(
                ".//ns:GetLocationUsingFingerprintResult", ns
            )
            if (
                result is None
                or result.findtext("ns:ResponseStatus", None, ns) != "Success"
            ):
                return None
            lr = result.find("ns:LocationResult", ns)
            if lr is None:
                return None
            rs = lr.find("ns:ResolverStatus", ns)
            if (
                rs is None
                or rs.findtext("ns:Status", None, ns) != "Success"
                or rs.findtext("ns:Source", None, ns) != "Internal"
            ):
                return None
            ru = lr.findtext("ns:RadialUncertainty", None, ns)
            if ru is None or int(ru) >= 500:
                return None
            pos = lr.find("ns:ResolvedPosition", ns)
            if pos is None:
                return None
            lat = pos.findtext("ns:Latitude", None, ns)
            lon = pos.findtext("ns:Longitude", None, ns)
            return (float(lat), float(lon)) if lat and lon else None
        except Exception:
            pass
        return None

    def _apple(self, mac: str, timeout: int = 10):
        try:
            import requests

            mac_bytes = mac.encode()
            body = (
                bytes([0x18, 0x00])
                + bytes([0x20, 0x64])
                + bytes([0x12, 1 + len(mac_bytes), 0x0A, len(mac_bytes)])
                + mac_bytes
            )
            size = struct.pack(">H", len(body))
            hdr = (
                bytes([0x00, 0x01, 0x00, 0x05])
                + b"en_US"
                + bytes([0x00, 0x13])
                + b"com.apple.locationd"
                + bytes([0x00, 0x0C])
                + b"8.4.1.12H321"
                + bytes([0x00, 0x00, 0x00, 0x01, 0x00, 0x00])
            )
            r = requests.post(
                "https://gs-loc.apple.com/clls/wloc",
                data=hdr + size + body,
                timeout=timeout,
            )
            marker = bytes([0x00, 0x00, 0x00, 0x01, 0x00, 0x00])
            idx = r.content.find(marker)
            if idx == -1:
                return None
            proto = r.content[idx + 8 :]
            off = 0
            while off < len(proto):
                tag = proto[off]
                off += 1
                field = tag >> 3
                wire = tag & 0x07
                if wire != 2:
                    _, off = self._decode_varint(proto, off)
                    continue
                length, off = self._decode_varint(proto, off)
                sub = proto[off : off + length]
                off += length
                if field != 2:
                    continue
                so = 0
                while so < len(sub):
                    t = sub[so]
                    so += 1
                    f = t >> 3
                    w = t & 0x07
                    if w != 2:
                        _, so = self._decode_varint(sub, so)
                        continue
                    l2, so = self._decode_varint(sub, so)
                    sub2 = sub[so : so + l2]
                    so += l2
                    if f != 2:
                        continue
                    so2 = 0
                    rlat = rlon = None
                    while so2 < len(sub2):
                        tt = sub2[so2]
                        so2 += 1
                        ff = tt >> 3
                        ww = tt & 0x07
                        if ww == 2:
                            ln, so2 = self._decode_varint(sub2, so2)
                            so2 += ln
                            continue
                        if ww != 0:
                            _, so2 = self._decode_varint(sub2, so2)
                            continue
                        v, so2 = self._decode_varint(sub2, so2)
                        dv = self._zigzag(v)
                        if ff == 1:
                            rlat = dv
                        elif ff == 2:
                            rlon = dv
                        if (
                            rlat is not None
                            and rlon is not None
                            and rlat != APPLE_SENTINEL
                            and rlon != APPLE_SENTINEL
                        ):
                            return rlat * 1e-8, rlon * 1e-8
        except Exception:
            pass
        return None

    def _google(self, mac: str, timeout: int = 10):
        try:
            import requests

            mac_val = int(mac.replace(":", ""), 16)
            temp_val = 0x112233445566

            def vint(n):
                b = []
                while n > 0x7F:
                    b.append((n & 0x7F) | 0x80)
                    n >>= 7
                b.append(n & 0x7F)
                return bytes(b)

            w1 = bytes([0x0A, 0x00, 0x40]) + vint(mac_val)
            w2 = bytes([0x0A, 0x00, 0x40]) + vint(temp_val)
            w1e = bytes([0x12, len(w1)]) + w1
            w2e = bytes([0x12, len(w2)]) + w2
            fc = (
                bytes([0x08])
                + vint(162723)
                + bytes([0x12, len(w1e) + len(w2e)])
                + w1e
                + w2e
                + bytes([0x18, 0x02])
            )
            fd = bytes([0x12, len(fc)]) + fc
            fl = bytes([0x22, len(fd)]) + fd
            v = bytes([0x0A, 4]) + b"2021"
            pv = b"android/LEAGOO/full_wf562g_leagoo/wf562g_leagoo:6.0/MRA58K/1511161770:user/release-keys"
            p = bytes([0x12, len(pv)]) + pv
            le = b"en_US"
            lf = bytes([0x2A, len(le)]) + le
            fh = bytes([0x0A, len(v + p + lf)]) + v + p + lf
            proto = fh + fl
            gz = gzip.compress(proto)
            sz = struct.pack(">I", len(gz))
            hdr = (
                bytes([0x00, 0x02, 0x00, 0x00, 0x1F])
                + b"location,2021,android,gms,en_US"
                + bytes(10)
                + b"\x01"
                + b"g"
                + struct.pack(">I", 187)
                + bytes([0x00, 0x01, 0x01, 0x00, 0x01, 0x00, 0x08])
                + b"g:loc/ql"
                + bytes([0x00, 0x00, 0x00, 0x04])
                + b"POST"
                + bytes([0x6D, 0x72, 0x00, 0x00, 0x00, 0x04])
                + b"ROOT"
                + bytes([0x00])
                + sz
                + bytes([0x00, 0x01])
                + b"g"
            )
            r = requests.post(
                "https://www.google.com/loc/m/api",
                data=hdr + gz + bytes(2),
                timeout=timeout,
            )
            idx = r.content.find(b"\x1f\x8b")
            if idx < 0:
                return None
            u = gzip.decompress(r.content[idx:])

            def walk(d, depth=0):
                off = 0
                while off < len(d):
                    t = d[off]
                    off += 1
                    f = t >> 3
                    w = t & 7
                    if w == 0:
                        _, off = self._decode_varint(d, off)
                    elif w == 2:
                        ln, off = self._decode_varint(d, off)
                        sub = d[off : off + ln]
                        off += ln
                        if depth < 4:
                            res = walk(sub, depth + 1)
                            if res:
                                return res
                        if depth == 4:
                            lo = 0
                            lat = lon = None
                            while lo < len(sub):
                                tt = sub[lo]
                                lo += 1
                                ff = tt >> 3
                                ww = tt & 7
                                if ww == 5:
                                    v = struct.unpack("<i", sub[lo : lo + 4])[0]
                                    lo += 4
                                    if ff == 1:
                                        lat = v
                                    elif ff == 2:
                                        lon = v
                                elif ww == 2:
                                    ln2, lo = self._decode_varint(sub, lo)
                                    lo += ln2
                                else:
                                    _, lo = self._decode_varint(sub, lo)
                            if lat is not None and lon is not None:
                                return lat * 1e-7, lon * 1e-7
                    elif w == 5:
                        off += 4
                return None

            return walk(u)
        except Exception:
            pass
        return None

    def locate(
        self,
        mac: str,
        providers: list[str] | None = None,
        timeout: int = 10,
        on_result: Callable | None = None,
    ):
        all_providers = {
            "Yandex": self._yandex,
            "Apple": self._apple,
            "Google": self._google,
            "Microsoft": self._microsoft,
            "Mylnikov": self._mylnikov,
        }

        selected = {
            k: v
            for k, v in all_providers.items()
            if providers is None or k in providers
        }

        result = {"mac": mac, "location": {}}

        with ThreadPoolExecutor(max_workers=len(selected)) as ex:
            fs = {ex.submit(fn, mac, timeout): name for name, fn in selected.items()}
            for f in as_completed(fs):
                name = fs[f]
                try:
                    res = f.result()
                    if res:
                        lat, lon = res
                        result["location"][name] = {"latitude": lat, "longitude": lon}
                        if on_result:
                            on_result(f"{name}: {lat:.7f}, {lon:.7f}")
                    else:
                        result["location"][name] = None
                        if on_result:
                            on_result(f"{name}: no data")
                except Exception as e:
                    result["location"][name] = None
                    if on_result:
                        on_result(f"{name}: {e}")

        return result

    def locate_pretty(
        self, mac: str, providers: list[str] | None = None, timeout: int = 10
    ):
        data = self.locate(mac, providers, timeout)
        print(f"\nMAC: {data['mac']}")
        print(f"{'─' * 50}")
        for name, loc in data["location"].items():
            if loc:
                print(f"{name}: {loc['latitude']:.7f}, {loc['longitude']:.7f}")
            else:
                print(f"{name}: no data")

    async def locate_async(
        self, mac: str, providers: list[str] | None = None, timeout: int = 10
    ):
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(None, self.locate, mac, providers, timeout)
        return await asyncio.wrap_future(fut)

    def locate_multi(
        self,
        macs: list[str],
        providers: list[str] | None = None,
        timeout: int = 10,
        on_result: Callable | None = None,
    ):
        return [self.locate(mac, providers, timeout, on_result) for mac in macs]

    async def locate_multi_async(
        self,
        macs: list[str],
        providers: list[str] | None = None,
        timeout: int = 10,
    ):
        loop = asyncio.get_running_loop()
        futures = [
            loop.run_in_executor(None, self.locate, mac, providers, timeout)
            for mac in macs
        ]
        wrapped = [asyncio.wrap_future(f) for f in futures]
        return await asyncio.gather(*wrapped)

    def locate_json(
        self, mac: str, providers: list[str] | None = None, timeout: int = 10
    ) -> dict:
        return self.locate(mac, providers, timeout)
