.PHONY: sync-schemas check-schemas test build

SCHEMA_SRC := spec/schema
SCHEMA_DST := src/cryowire/schemas

sync-schemas:
	cp $(SCHEMA_SRC)/*.schema.json $(SCHEMA_DST)/

check-schemas:
	@diff -q $(SCHEMA_SRC)/wiring.schema.json $(SCHEMA_DST)/wiring.schema.json && \
	diff -q $(SCHEMA_SRC)/metadata.schema.json $(SCHEMA_DST)/metadata.schema.json && \
	diff -q $(SCHEMA_SRC)/components.schema.json $(SCHEMA_DST)/components.schema.json && \
	diff -q $(SCHEMA_SRC)/chip.schema.json $(SCHEMA_DST)/chip.schema.json && \
	diff -q $(SCHEMA_SRC)/cooldown.schema.json $(SCHEMA_DST)/cooldown.schema.json && \
	echo "Schemas are in sync." || \
	(echo "ERROR: Schemas out of sync. Run 'make sync-schemas'." && exit 1)

test:
	uv run pytest tests/ -v

build:
	uv build
