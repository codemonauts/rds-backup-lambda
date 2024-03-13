run: test
	python main.py

format:
	black -l 120 -t py311 .

test:
	black -l 120 --check -t py311 .
	pylint main.py

clean:
	rm -rf dist
	rm -f package.zip

build: clean test
	mkdir dist
	pip install --target ./dist -r requirements.txt
	cd dist; zip -r ../package.zip .
	zip package.zip main.py
