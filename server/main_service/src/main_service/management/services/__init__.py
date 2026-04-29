"""Management Service 내부 모듈 (V6 아키텍처).

5개 모듈이 gRPC servicer 뒤에서 비즈니스 로직을 담당한다.
모두 동일 DB(Interface Service 와 공유)를 SQLAlchemy 로 사용한다.
"""
