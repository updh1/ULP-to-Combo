# ULP Extractor

A fast, multithreaded Python CLI tool for extracting data from combo files (`email:password`). Supports multiple extraction modes — combos, corporate emails, educational emails, and target-based leads. Shuffles output for good measure.

---

## Features

- **Multithreaded processing** — up to 8 workers by default (configurable)
- **4 extraction modes**:
  - Combo (`email:password`) filtered by target
  - Corp mails (domains NOT in the free list)
  - Edu mails (`.edu`, `.ac.uk`, `.edu.au`, `.edu.pk`, `.edu.in`)
  - Leads — emails only matching a target (no passwords)
- **Shuffle** — randomizes output order on every write
- **Validation** — drops empty passwords, Persian/Arabic chars, invalid emails, junk phrases
- **Fast I/O** — 8 MB buffers, pre-compiled regex, fast rejects
- **Live dashboard** — lines, uniques, duplicates, speed
- **Cross-platform** — Windows, Linux, macOS

---

## Requirements

- Python 3.7+
- No external dependencies (standard library only)

---

## Installation

```bash
git clone git@github.com:updh1/ULP-to-Combo.git
cd ulp-extractor
python ulp.py
```

---

## Folder Structure

```
ulp-extractor/
├── ulp.py
├── Ulp/
│   ├── file1.txt
│   ├── file2.txt
│   └── ...
└── Results/
    ├── converted_combo.txt
    ├── Corp_Data.txt
    ├── Edu_Data.txt
    └── Leads_<target>.txt
```

- **`Ulp/`** — drop your `.txt` combo files here
- **`Results/`** — output files (created automatically)

---

## Usage

Run the script:

```bash
python ulp.py
```

You'll see the menu:

```
[1] Extract ULP -> Combo
[2] Extract Corp Mails
[3] Extract Edu Mails
[4] Extract Leads
[5] Exit
```

### Option 1 — Extract ULP -> Combo

Prompts for a target (e.g. `netflix`, `.ir`, `spotify`). Filters all lines containing the target and writes `email:password` to `Results/converted_combo.txt`.

### Option 2 — Extract Corp Mails

Extracts all combos whose domain is **NOT** in the free domain list (Gmail, WP, Onet, etc.). Output: `Results/Corp_Data.txt`.

### Option 3 — Extract Edu Mails

Extracts combos with educational domains (`.edu`, `.ac.uk`, `.edu.au`, `.edu.pk`, `.edu.in`). Output: `Results/Edu_Data.txt`.

### Option 4 — Extract Leads

Prompts for a target. Extracts **emails only** (no passwords) from lines matching the target. Output: `Results/Leads_<target>.txt`.

---

## Examples

**Input** (`Ulp/dump.txt`):
```
user1@gmail.com:haslo123
user2@company.com:qwerty
user3@student.edu:pass456
some:junk:user4@microsoft.com:secret
```

**Option 1, target `microsoft`:**
```
user4@microsoft.com:secret
```

**Option 2 (Corp):**
```
user2@company.com:qwerty
user4@microsoft.com:secret
```

**Option 3 (Edu):**
```
user3@student.edu:pass456
```

**Option 4, target `microsoft`:**
```
user4@microsoft.com
```

---

## Configuration

Edit these in `ulp.py`:

| Variable | Description | Default |
|---|---|---|
| `ULP_DIR` | Input folder | `"Ulp"` |
| `RESULTS_DIR` | Output folder | `"Results"` |
| `BUFFER_SIZE` | I/O buffer size | `8 MB` |
| `FREE_DOMAINS` | Free domain list (corp = NOT free) | Gmail, WP, Onet, etc. |
| `EDU_SUFFIXES` | Educational domain suffixes | `.edu`, `.ac.uk`, etc. |
| `NON_COMBO_PHRASES` | Junk phrases to reject | `unknown version`, etc. |

### Add your own domain to free list

```python
FREE_DOMAINS = {
    "gmail.com", "wp.pl", ...,
    "yourdomain.com"
}
```

### Change worker count

In `_run_parallel`:

```python
max_workers = 16
```

---

## Performance

On a typical CPU (4 cores / 8 threads):

| Data Size | Time | Speed |
|---|---|---|
| 100 MB | ~3 s | ~1.5M lines/s |
| 1 GB | ~30 s | ~1.5M lines/s |
| 10 GB | ~5 min | ~1.5M lines/s |

Actual results depend on hardware, file sizes, and disk speed.

---

## Security

- The script **does not connect to the internet**
- The script **does not send data anywhere**
- Everything happens locally
- Output is written only to the `Results/` folder

---

## License

MIT

---

## Author

**@updh2**
