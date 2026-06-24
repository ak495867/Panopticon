.PHONY: install test lint format clean

install:
	pip install -e .[dev]

test:
	pytest tests/ -v

lint:
	flake8 panopticon tests --count --max-line-length=120 --statistics
	black --check panopticon tests

format:
	black panopticon tests

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf panopticon/__pycache__
	rm -rf tests/__pycache__
	rm -rf *.egg-info
	rm -f panopticon_memory.db
	rm -f panopticon_telemetry.jsonl
