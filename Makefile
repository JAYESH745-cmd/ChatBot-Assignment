PYTHON ?= python3

.PHONY: prepare golden train evaluate judge-packet test all

prepare:
	$(PYTHON) -m src.prepare_data --input data/raw/twcs.csv --output data/apple_support_slice.csv

golden:
	$(PYTHON) -m src.make_golden --slice data/apple_support_slice.csv --output data/golden_eval.csv

train:
	$(PYTHON) -m src.evaluate --slice data/apple_support_slice.csv --golden data/golden_eval.csv --out reports/results.json

evaluate: train

judge-packet:
	$(PYTHON) -m src.make_judge_packet --predictions reports/predictions.csv --output data/judge_calibration_template.csv

test:
	$(PYTHON) -m unittest discover -s tests -v

all: test evaluate
