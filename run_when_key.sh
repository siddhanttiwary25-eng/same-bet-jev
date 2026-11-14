#!/bin/zsh
# Waits until TYPESAFE_API_KEY is filled in .env, then smoke-tests and runs the benchmark.
cd "${0:A:h}"
for i in {1..1440}; do
  len=$(awk -F= '/^TYPESAFE_API_KEY=/{v=$2; gsub(/[ "\x27]/,"",v); print length(v)}' .env)
  [[ "$len" -gt 0 ]] && break
  sleep 5
done
[[ "$len" -gt 0 ]] || { echo "no key after 2h"; exit 1; }
echo "key found, smoke test:"
.venv/bin/python src/jev_match.py || exit 1
echo "benchmark:"
.venv/bin/python src/benchmark.py
