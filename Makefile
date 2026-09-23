.PHONY: dev test eval seed verify-offline contracts clean

dev:
	docker compose up --build

test:
	docker compose run --rm gateway pytest tests/ -v
	docker compose run --rm web npm run test

eval:
	docker compose run --rm gateway python -m eval.harness.run --dataset $(DATASET)

seed:
	docker compose run --rm gateway python -m scripts.seed_drug_data \
		--onc eval/datasets/drugs/onc_high_priority_mapped.csv \
		--crediblemeds eval/datasets/drugs/crediblemeds_qtdrugs.csv \
		--ddinter eval/datasets/drugs/ddinter2_interactions.csv \
		--brands eval/datasets/drugs/indian_medicine_brands.csv

verify-offline:
	@echo "Asserting zero outbound egress except the FHIR allowlist..."
	docker compose run --rm --network none asr pytest tests/security/test_no_egress.py -v
	docker compose run --rm --network none llm pytest tests/security/test_no_egress.py -v
	docker compose run --rm --network none safety pytest tests/security/test_no_egress.py -v
	docker compose run --rm gateway pytest tests/security/ -v
	@echo "verify-offline: PASSED"

contracts:
	python packages/contracts/generate.py \
		--schema packages/contracts/soap_note.schema.json \
		--out-py packages/contracts/python \
		--out-ts packages/contracts/ts

clean:
	docker compose down -v
	find . -name "__pycache__" -exec rm -rf {} +
