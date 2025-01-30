from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Guild(Base):
    """Модель для зберігання інформації про сервери Discord."""
    __tablename__ = 'guilds'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_primary = Column(Boolean, default=False)
    
    # Відношення
    channels = relationship("Channel", back_populates="guild")
    roles = relationship("Role", back_populates="guild")
    
    def __repr__(self):
        return f"<Guild(name='{self.name}', discord_id='{self.discord_id}')>"

class Channel(Base):
    """Модель для зберігання інформації про канали."""
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    type = Column(String(20), nullable=False)  # text, voice, category
    position = Column(Integer, default=0)
    category_id = Column(String(20), nullable=True)
    
    # Зовнішні ключі
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    
    # Відношення
    guild = relationship("Guild", back_populates="channels")
    messages = relationship("Message", back_populates="channel")
    
    def __repr__(self):
        return f"<Channel(name='{self.name}', type='{self.type}')>"

class Role(Base):
    """Модель для зберігання інформації про ролі."""
    __tablename__ = 'roles'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    color = Column(Integer, nullable=True)
    position = Column(Integer, default=0)
    permissions = Column(String(20), nullable=False)  # Бітове поле прав
    
    # Зовнішні ключі
    guild_id = Column(Integer, ForeignKey('guilds.id'))
    
    # Відношення
    guild = relationship("Guild", back_populates="roles")
    
    def __repr__(self):
        return f"<Role(name='{self.name}', position={self.position})>"

class Message(Base):
    """Модель для зберігання повідомлень."""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), unique=True, nullable=False)
    content = Column(Text, nullable=True)
    author_id = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    edited_at = Column(DateTime, nullable=True)
    
    # Метадані повідомлення
    has_attachments = Column(Boolean, default=False)
    attachments_data = Column(Text, nullable=True)  # JSON з даними про вкладення
    embeds_data = Column(Text, nullable=True)  # JSON з даними про вбудовані елементи
    
    # Дані синхронізації
    sync_status = Column(String(20), default='pending')  # pending, synced, failed
    sync_error = Column(Text, nullable=True)
    synced_message_id = Column(String(20), nullable=True)  # ID синхронізованого повідомлення
    
    # Зовнішні ключі
    channel_id = Column(Integer, ForeignKey('channels.id'))
    
    # Відношення
    channel = relationship("Channel", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id='{self.discord_id}', author_id='{self.author_id}')>"

class SyncOperation(Base):
    """Модель для відстеження операцій синхронізації."""
    __tablename__ = 'sync_operations'
    
    id = Column(Integer, primary_key=True)
    operation_type = Column(String(50), nullable=False)  # clone, message_sync, etc.
    status = Column(String(20), default='in_progress')  # in_progress, completed, failed
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Деталі операції
    source_guild_id = Column(String(20), nullable=False)
    target_guild_id = Column(String(20), nullable=False)
    items_total = Column(Integer, default=0)
    items_processed = Column(Integer, default=0)
    error_log = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<SyncOperation(type='{self.operation_type}', status='{self.status}')>"