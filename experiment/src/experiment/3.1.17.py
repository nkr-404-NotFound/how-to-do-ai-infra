from pathlib import Path

data = Path("/proc/meminfo").read_text()

print(data[:500])