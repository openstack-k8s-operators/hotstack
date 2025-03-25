SPHINX_BUILD   ?= sphinx-build
BUILD_DIR      = build/html
SOURCE_DIR     = source
SCENARIO       ?=
SCENARIOS_DIR  ?=
VENV_DIR       ?= .venvs/scenario_doc

ifndef SCENARIO
$(error SCENARIO is not set)
endif
ifndef SCENARIOS_DIR
$(error SCENARIOS_DIR is not set)
endif

.PHONY: scenario_doc
scenario_doc: scenario_doc_venv
scenario_doc: export SCENARIO=$(SCENARIO)
scenario_doc: export SCENARIOS_DIR=$(SCENARIOS_DIR)
scenario_doc:
	source "$(VENV_DIR)/bin/activate" && $(SPHINX_BUILD) -a -E -W --keep-going -b dirhtml "$(SOURCE_DIR)" "$(BUILD_DIR)"/"$(SCENARIO)"
	cd $(BUILD_DIR) && tar cvzf $(SCENARIO).tar.gz $(SCENARIO)

.PHONY: scenario_doc_venv
scenario_doc_venv:
	mkdir -p "$(VENV_DIR)"
	python3 -m venv "$(VENV_DIR)"
	source "$(VENV_DIR)/bin/activate" && pip install -U -r ./requirements.txt

.PHONY: clean
clean:
	rm -rf "$(BUILD_DIR)/$(SCENARIO)"
	rm -f "$(BUILD_DIR)/$(SCENARIO).tar.gz"

.PHONY: clean_venv
clean_venv:
	rm -rf "$(VENV_DIR)"

.PHONY: clean_all
clean_all: clean clean_venv
clean_all:
	rm -rf "$(BUILD_DIR)"
