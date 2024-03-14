format:
	black -l 120 -t py311 .
	terraform fmt -check -recursive .

test: init
	black -l 120 --check -t py311 .
	pylint main.py
	terraform validate

clean:
	rm -rf dist
	rm -f package.zip

init:
	terraform init

build: clean test
	mkdir dist
	pip install --target ./dist -r requirements.txt
	cd dist; zip -r ../package.zip .
	zip package.zip main.py

plan:
	terraform plan -out=rds-backup.tfplan

deploy:
	terraform apply rds-backup.tfplan
