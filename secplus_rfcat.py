#!/usr/bin/env python3
"""RFcat legacy Security+ OOK transmitter for authorized lab testing.

Requires RFcat hardware (typically CC1111/YARD Stick One) and the Security+
encoder from https://github.com/argilo/secplus/blob/master/secplus_tx_secplus.py.

Uses the radio's 2000-baud hardware clock, not Python sleeps, for the pulses.
"""

import argparse
import sys
from pathlib import Path


def _base3_digits(value: int, count: int = 20) -> list[int]:
    """Convert an integer to a fixed-width, most-significant-first ternary list."""
    digits = [0] * count
    for i in range(count - 1, -1, -1):
        digits[i] = value % 3
        value //= 3
    if value:
        raise ValueError("value exceeds ternary field width")
    return digits


def _reverse32(value: int) -> int:
    """Reverse the bit order of a 32-bit integer."""
    return int(f"{value:032b}"[::-1], 2)


def encode_ook(rolling: int, fixed: int, fast: bool = False) -> list[int]:
    """Encode a Security+ 1.0 rolling/fixed pair into 2000-baud OOK samples.

    Each ternary symbol occupies four 0.5 ms samples:
        0 -> 0001
        1 -> 0011
        2 -> 0111

    A complete message consists of two frames, each containing a sync
    symbol, 20 data symbols, and an inter-frame quiet period.
    """
    if not (0 <= rolling < 2**32):
        raise ValueError("rolling must be a 32-bit unsigned integer")
    if not (0 <= fixed < 3**20):
        raise ValueError("fixed must be in 0..3**20-1")

    rolling_digits = _base3_digits(_reverse32(rolling & 0xFFFFFFFE))
    fixed_digits = _base3_digits(fixed)

    symbol_bits = (
        (0, 0, 0, 1),
        (0, 0, 1, 1),
        (0, 1, 1, 1),
    )

    output = []

    for frame in range(2):
        # Frame 1 starts with ternary 0; frame 2 starts with ternary 2.
        symbols = [0 if frame == 0 else 2]
        accumulator = 0

        start = frame * 10
        for i in range(start, start + 10):
            rolling_digit = rolling_digits[i]
            fixed_digit = fixed_digits[i]

            accumulator += rolling_digit
            symbols.append(rolling_digit)

            accumulator += fixed_digit
            symbols.append(accumulator % 3)

        for symbol in symbols:
            output.extend(symbol_bits[symbol])

        # Original GNU Radio encoder's normal timing uses a 58 ms gap.
        if not fast:
            output.extend([0] * (29 * 4))

    return output


def build_waveform(rolling: int, fixed: int, repeats: int = 4) -> list[int]:
    """Return the Security+ 1.0 OOK waveform, including quiet gaps."""
    if not (0 <= rolling < 2**32):
        raise ValueError("rolling must be a 32-bit unsigned integer")
    if not (0 <= fixed < 3**20):
        raise ValueError("fixed must be in 0..3**20-1")
    if not (1 <= repeats <= 20):
        raise ValueError("repeats must be in 1..20")

    message = encode_ook(rolling, fixed, fast=False)
    return [0] * 100 + message * repeats + [0] * 100


def pack_msb(bits: list[int]) -> bytes:
    """RFcat transmits the most significant bit of each byte first."""
    if not all(bit in (0, 1) for bit in bits):
        raise ValueError("waveform must contain only 0/1 bits")
    if len(bits) % 8:
        bits = bits + [0] * (-len(bits) % 8)
    return bytes(sum(bit << (7 - index) for index, bit in enumerate(bits[offset:offset + 8]))
                 for offset in range(0, len(bits), 8))


def configure_radio(dongle, frequency: int, invert: bool = False) -> None:
    from rflib import MOD_ASK_OOK

    dongle.setModeIDLE()
    dongle.setFreq(frequency)
    dongle.setMdmModulation(MOD_ASK_OOK)
    # Explicitly populate the PA table: a default/blank PA table can
    # produce no RF carrier even though the transmit command succeeds.
    dongle.setMaxPower()
    dongle.setMdmDRate(2000)
    dongle.setMdmSyncMode(0)
    dongle.setEnableMdmManchester(False)
    dongle.setEnableMdmFEC(False)
    dongle.setEnablePktCRC(False)
    dongle.setEnablePktDataWhitening(False)
    dongle.setEnableCCA(0)
    # Avoid automatic byte-length or address checks; RFxmitLong selects
    # the appropriate radio packet mode for its supplied payload length.


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rolling", type=lambda s: int(s, 0), required=True)
    parser.add_argument("--fixed", type=lambda s: int(s, 0), required=True)
    parser.add_argument("--freq", type=lambda s: int(s, 0), default=315150000)
    parser.add_argument("--repeats", type=int, default=4)
    parser.add_argument("--invert", action="store_true",
                        help="invert the OOK power-table mapping for diagnostics")
    parser.add_argument("--device", type=int, default=0, help="RFcat dongle index")
    parser.add_argument("--output", type=Path, help="write packed OOK samples to file")
    parser.add_argument("--transmit", action="store_true", help="transmit over an attached RFcat dongle")
    args = parser.parse_args()

    bits = build_waveform(args.rolling, args.fixed, args.repeats)
    if args.invert:
        bits = [1 - bit for bit in bits]
    data = pack_msb(bits)
    print(f"OOK: {len(bits)} symbols at 2000 baud = {len(bits) / 2000:.3f} s")
    print(f"Packed bytes: {len(data)}; frequency: {args.freq} Hz")

    if args.output:
        args.output.write_bytes(data)
        print(f"Wrote {args.output}")

    if not args.transmit:
        print("Dry run complete. No RF transmitted; specify --transmit to send.")
        return

    from rflib import RfCat

    dongle = RfCat(idx=args.device)
    try:
        configure_radio(dongle, args.freq, invert=args.invert)
        print("Actual frequency:", dongle.getFreq()[0])
        print("Actual baud:", dongle.getMdmDRate())
        print("OOK PA table:", hex(dongle.radiocfg.pa_table0), hex(dongle.radiocfg.pa_table1))
        # The waveform is larger than the standard RFcat TX block. RFxmitLong
        # sends it through the extended transfer path in supported firmware.
        result = dongle.RFxmitLong(data)
        if result not in (None, 0):
            raise RuntimeError(f"RFcat returned non-success status: {result!r}")
        print("Transmission call completed")
    finally:
        dongle.setModeIDLE()


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, ImportError) as error:
        sys.exit(str(error))
