PYTHON ?= python3

.PHONY: prepare golden train evaluate test all

prepare:
	$(PYTHON) -m src.prepare_data --input data/raw/twcs.csv --output data/apple_support_slice.csv

golden:
	$(PYTHON) -m src.make_golden --slice data/apple_support_slice.csv --output data/golden_eval.csv

train:
	$(PYTHON) -m src.evaluate --slice data/apple_support_slice.csv --golden data/golden_eval.csv --out reports/results.json

evaluate: train

test:
	$(PYTHON) -m unittest discover -s tests -v

all: test evaluate

