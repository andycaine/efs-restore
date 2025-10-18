STACK_NAME ?= efs-restore-stack
VERSION := $(shell uv version --short)

.PHONY: publish clean lint deploy destroy

template.yaml: efs_restore/efs_restore.py efs_restore/efs_restore_lambda.py
	uv run python -m efs_restore.efs_restore > template.yaml

clean:
	rm -f template.yaml

lint: template.yaml efs_restore/efs_restore.py efs_restore/efs_restore_lambda.py
	cfn-lint template.yaml
	uv run ruff check efs_restore/
