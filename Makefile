.PHONY: install data run app test lint

install:
	pip install -r requirements-dev.txt
	pip install -e .

data:
	python scripts/generate_sample_data.py

run: data
	python -m rdcap.pipeline

app:
	streamlit run app/streamlit_app.py

test:
	pytest -q

lint:
	ruff check src scripts tests app
