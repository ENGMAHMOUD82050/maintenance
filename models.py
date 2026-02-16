from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from marshmallow import Schema, fields, ValidationError

def validate_non_empty(value):
    if not value:
        raise ValidationError('Field cannot be empty.')

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False, validation=validate_non_empty)
    email = Column(String(100), unique=True, nullable=False, validation=validate_non_empty)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    items = relationship('Item', back_populates='owner')

class Item(Base):
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, validation=validate_non_empty)
    owner_id = Column(Integer, ForeignKey('users.id'))
    
    # Relationships
    owner = relationship('User', back_populates='items')

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate_non_empty)
    email = fields.Email(required=True, validate=validate_non_empty)

class ItemSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate_non_empty)
    owner_id = fields.Int()