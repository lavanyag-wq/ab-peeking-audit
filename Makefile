.PHONY: lint test experiments receipts verify

lint:
	ruff check src tests tools experiments

test:
	pytest --junitxml=reports/junit.xml --cov=ab_peeking_audit --cov-report=json:reports/coverage.json --cov-report=term

experiments:
	python experiments/exp_inflation.py
	python experiments/exp_identical_pvalue.py
	python experiments/exp_correction_cost.py

receipts:
	python tools/collect_metrics.py --skip-tests
	python tools/check_numbers.py

verify: lint test experiments receipts
