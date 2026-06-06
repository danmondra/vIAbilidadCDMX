from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import relationship

from db.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    state = Column(String)
    data = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Session id={self.id} state={self.state}>"


class Giro(Base):
    __tablename__ = "giros"

    no = Column(Integer, primary_key=True, autoincrement=True)
    clave_scian = Column(Integer)
    clasificación = Column(String)
    descripción = Column(String)
    horario_de_operación = Column(String)
    tipo_de_impacto = Column(String)
    articulo_lem = Column(String, nullable=True)
    formato_siapem = Column(String, nullable=True)
    keywords = Column(Text, nullable=True)
    nombre_corto = Column(String, nullable=True)

    def __repr__(self):
        return f"<Giro no={self.no} nombre_corto={self.nombre_corto}>"


class TramitePaso(Base):
    __tablename__ = "tramites_pasos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    impacto = Column(String, nullable=False)
    fase = Column(String, nullable=False)
    paso = Column(Integer)
    nombre = Column(String)
    descripcion = Column(Text)
    link = Column(String)
    link_info = Column(String)
    costo = Column(String)
    plazo = Column(String)
    obligatorio = Column(String)
    condicion = Column(String)
    fundamento = Column(String)
    orden = Column(Integer)


class SiapemFormato(Base):
    __tablename__ = "siapem_formatos"

    formato = Column(String, primary_key=True)
    impacto = Column(String)
    tipo = Column(String)
    titulo = Column(String)
    costo = Column(String)
    plazo = Column(String)
    pasos_json = Column(Text)
    documentos_json = Column(Text)
    nota = Column(Text)
    advertencia = Column(Text)
    link = Column(String)


class ProgramaApoyo(Base):
    __tablename__ = "programas_apoyo"

    id = Column(Integer, primary_key=True)
    nombre = Column(String)
    organismo = Column(String)
    descripcion = Column(Text)
    monto_max = Column(Float)
    tipo = Column(String)
    modalidad = Column(String)
    tasa_interes = Column(String)
    plazo_max_meses = Column(Integer)
    requisitos_json = Column(Text)
    link = Column(String)
    aplica_giros_json = Column(Text)
    convocatoria = Column(String)
    direccion = Column(String)
    contacto = Column(String)
    beneficios_adicionales_json = Column(Text)
    descuento = Column(String)
    costo_renta = Column(String)
    proyectos_elegibles_json = Column(Text)
    duracion_programa = Column(String)


class LegalRule(Base):
    __tablename__ = "legal_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    regla = Column(String)
    fundamento = Column(String)
    descripcion = Column(Text)
    aplica_impacto = Column(String)
    aplica_giros_pattern = Column(String)
    nivel_db = Column(Integer)
    obligatorio = Column(Integer)
    mensaje_usuario = Column(Text)


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String)
    action = Column(String)
    giro = Column(String, nullable=True)
    zona = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Interaction user_id={self.user_id} action={self.action}>"
