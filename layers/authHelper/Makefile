.PHONY: build-AuthLayer

build-AuthLayer:
	mkdir -p "$(ARTIFACTS_DIR)/python"
	cp *.py "$(ARTIFACTS_DIR)/python"	
	/usr/local/bin/python3.13 -m pip install -r requirements.txt -t "$(ARTIFACTS_DIR)/python"