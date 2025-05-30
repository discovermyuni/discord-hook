from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


def create_tables(engine, *args):
    Base.metadata.create_all(bind=engine)
