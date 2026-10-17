
# rfcat-secplus

Standalone Security+ 1.0 OOK waveform encoder and RF transmitter for RFcat-compatible hardware, including the YARD Stick One.

A lightweight Python implementation of the legacy Security+ 1.0 protocol that generates ASK/OOK waveforms and supports RF transmission using the RFcat framework.

Based on the Security+ encoding implementation from [argilo/secplus](https://github.com/argilo/secplus), this project incorporates the encoding logic directly, eliminating the runtime dependency on `secplus_tx_secplus.py`.

## Features

- Standalone Security+ 1.0 protocol encoder
- YARD Stick One / CC1111 support
- ASK/OOK modulation at 2,000 baud
- Configurable RF frequency (315.150 MHz default)
- Rolling and fixed code inputs in decimal or hexadecimal
- Configurable transmission repetitions
- Binary waveform generation and export
- Optional RF transmission via `--transmit`
- OOK waveform inversion for diagnostics
- RFcat frequency, baud rate, and PA-table diagnostics
- Hardware-timed RF output without Python-based pulse timing

## Hardware Requirements

- YARD Stick One or compatible RFcat-supported radio
- Appropriate antenna for the operating frequency
- USB-connected computer

## Software Requirements

- Python 3.9+
- [RFcat](https://github.com/atlas0fd00m/rfcat)
- Compatible RFcat firmware

The Security+ encoder uses only the Python standard library. RFcat is required when transmitting.

## Installation

Clone the repository:

```bash
git clone https://github.com/YOUR_USERNAME/rfcat-secplus.git
cd rfcat-secplus
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install RFcat:

```bash
pip install rfcat
```

RFcat installation and USB permissions may vary depending on your operating system.

## Usage

### Generate a Waveform

Generate a waveform without transmitting RF:

```bash
python secplus_rfcat.py \
  --freq 315150000 \
  --rolling 0x00000000 \
  --fixed 0x00000000 \
  --repeats 4 \
  --output waveform.bin
```

This generates a binary file containing the packed OOK waveform.

### Command-Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--rolling` | 32-bit rolling-code value | Required |
| `--fixed` | Fixed-code value | Required |
| `--freq` | Frequency in Hz | `315150000` |
| `--repeats` | Number of message repetitions | `4` |
| `--output` | Output binary waveform file | None |
| `--transmit` | Enable RF transmission | Disabled |
| `--device` | RFcat device index | `0` |
| `--invert` | Invert OOK waveform bits | Disabled |

Display the available options:

```bash
python secplus_rfcat.py --help
```

## How It Works

Security+ 1.0 uses a ternary encoding scheme combining rolling-code and fixed-code information.

The encoder converts the input values into two frames, each containing:

- One synchronization symbol
- Twenty ternary data symbols
- An inter-frame quiet period

Each ternary symbol is converted into four OOK samples:

| Symbol | OOK Representation |
|--------|--------------------|
| `0` | `0001` |
| `1` | `0011` |
| `2` | `0111` |
| Quiet | `0000` |

At 2,000 baud, each sample represents 500 microseconds.

The complete waveform includes synchronization, inter-frame gaps, repetitions, and leading/trailing quiet periods.

### RFcat Configuration

The transmitter configures the radio with:

- ASK/OOK modulation
- 2,000-baud data rate
- Hardware-controlled bit timing
- Synchronization word disabled
- Manchester encoding disabled
- Forward error correction disabled
- CRC disabled
- Data whitening disabled
- Clear-channel assessment disabled
- Explicit PA-table configuration

The implementation uses RFcat's extended transmission mechanism, `RFxmitLong()`, to handle waveform payloads larger than the standard transmission block.

## Validation

The standalone encoder was validated against the original `secplus_tx_secplus.encode_ook()` implementation.

Both implementations produced identical 400-bit message waveforms and identical packed binary output when supplied with the same input values.

### Test Parameters

| Parameter | Value |
|-----------|-------|
| Rolling code | `2731817118` |
| Fixed code | `876029924` |
| Frequency | `315150000 Hz` |
| Repetitions | `4` |
| Total waveform | `1800 bits` |
| Packed output | `225 bytes` |
| Duration | `0.900 seconds` |

### Verified SHA-256

```text
0dec6c120b998f09cde13c634479db394b8b337f04d0556fb948b8dba1ec3d26
```

The original encoder, standalone encoder, and newly generated waveform all produced this exact hash.

### Hardware Validation

The RFcat transmitter was tested with a YARD Stick One.

A Flipper Zero successfully detected and decoded the resulting signal as:

```text
Security+ 1.0
42-bit
```

The decoder also successfully extracted rolling-code and fixed-code information.

This validates the waveform format and protocol compatibility, but does not guarantee acceptance by every receiver.

## Project Structure

```text
rfcat-secplus/
├── secplus_rfcat.py
├── README.md
└── LICENSE
```

## Current Limitations

- Security+ 1.0 only
- No Security+ 2.0 support
- No built-in RF receiver or capture decoder
- No automatic rolling-code synchronization
- RF transmission requires compatible RFcat hardware

## Future Development

Potential improvements include:

- Automated waveform regression tests
- RF capture analysis and protocol decoding
- Additional hardware compatibility testing
- Integration with RFcat-web
- Improved RF diagnostics
- Security+ 2.0 research and protocol support

## Responsible Use

This project is intended for authorized RF research, education, interoperability testing, and protocol development.

Only transmit to equipment you own or have explicit authorization to test. Observe applicable radio-frequency regulations.

Security+ is used in physical access-control systems. Improper transmissions can affect device operation or rolling-code synchronization.

## Credits

Security+ protocol encoding is based on:

- [argilo/secplus](https://github.com/argilo/secplus) — Clayton Smith and contributors

RF communication uses:

- [RFcat](https://github.com/atlas0fd00m/rfcat)

## License

The Security+ encoding implementation is derived from GPL-licensed code in `argilo/secplus`, distributed under the GNU General Public License version 3 or later.

Retain applicable upstream copyright notices and include the appropriate GPL license text in the repository's `LICENSE` file.

