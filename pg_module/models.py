from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class CharityCategory(Base):
    __tablename__ = 'charitycategory'

    category = Column(Text, nullable=False, index=True, primary_key=True)
    charityname = Column(Text, nullable=False)

class UserCategory(Base):
    __tablename__ = 'usercategory'

    category = Column(Text, nullable=False, index=True, primary_key=True)
    userid = Column(Text, nullable=False, primary_key=True)
