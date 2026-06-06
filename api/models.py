from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ViabilidadRequest(BaseModel):
    giro: str
    alcaldia: str
    colonia: Optional[str] = None
    m2: int = 100
    aforo: int = 50
    alcohol: str = "no"  # no / complemento / principal


class ViabilidadResponse(BaseModel):
    impacto: str
    formato_siapem: str
    proteccion_civil_requerida: bool
    uso_suelo: Dict[str, Any]
    competencia: Dict[str, Any]
    rentabilidad: Dict[str, Any]
    gastos_fijos: Dict[str, Any]
    tramites: Dict[str, Any]
    programas_apoyo: List[Any]
    links: Dict[str, Any]


class GiroBusquedaResponse(BaseModel):
    nombre: str
    scian: str
    impacto: str
    formato_siapem: str


class TramiteStep(BaseModel):
    paso: int
    nombre: str
    descripcion: str
    link: Optional[str] = None
    costo: str
    plazo: str
    obligatorio: bool
