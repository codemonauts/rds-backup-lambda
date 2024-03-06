run: test
	python main.py

format:
	black -l 120 -t py311 .

test:
	black -l 120 --check -t py311 .
	pylint main.py
	