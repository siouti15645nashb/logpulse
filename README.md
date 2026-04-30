# logpulse

> Lightweight log aggregator that tails multiple files and filters output with regex patterns in real time.

---

## Installation

```bash
pip install logpulse
```

Or install from source:

```bash
git clone https://github.com/youruser/logpulse.git && cd logpulse && pip install .
```

---

## Usage

Tail a single file:

```bash
logpulse /var/log/syslog
```

Tail multiple files and filter output with a regex pattern:

```bash
logpulse /var/log/syslog /var/log/nginx/access.log --pattern "ERROR|WARN"
```

Use it programmatically:

```python
from logpulse import LogPulse

pulse = LogPulse(
    files=["/var/log/app.log", "/var/log/worker.log"],
    pattern=r"ERROR|CRITICAL"
)

for line in pulse.stream():
    print(line)
```

### CLI Options

| Flag | Description |
|------|-------------|
| `--pattern` | Regex pattern to filter log lines |
| `--no-color` | Disable colored output |
| `--timestamps` | Prepend local timestamps to each line |

---

## License

This project is licensed under the [MIT License](LICENSE).