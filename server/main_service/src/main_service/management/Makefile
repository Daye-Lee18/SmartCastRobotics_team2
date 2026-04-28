PROTO_DIR := proto
OUT_DIR   := .

.PHONY: proto install run clean

install:
	pip install -r requirements.txt

proto:
	python -m grpc_tools.protoc \
		-I $(PROTO_DIR) \
		--python_out=$(OUT_DIR) \
		--grpc_python_out=$(OUT_DIR) \
		$(PROTO_DIR)/management.proto

run: proto
	python server.py

clean:
	rm -f management_pb2.py management_pb2_grpc.py
