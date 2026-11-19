"""
main.py — Punto de entrada del backend (FastAPI): arma los componentes, monta la API y el WebSocket.

Ejecutar (desde backend/, con el entorno virtual activo):
    $env:SIMULACION="1"; uvicorn app.main:app --reload --port 8000     # sin hardware
    uvicorn app.main:app --port 8000 --host 0.0.0.0                     # con Arduino y cámara

Documentación interactiva de la API: http://localhost:8000/docs
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .bins import GestorBotes
from .camera import CamaraReal, CamaraSimulada
from .config import Configuracion, cargar_ajustes
from .db import BaseDatos
from .game import Juego
from .model import cargar_modelo
from .orchestrator import Difusor, EstadoInvalido, Orquestador
from .routes import Contexto, router
from .serial_link import EnlaceReal, EnlaceSimulado, ErrorSerial
from .voice import Voz

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


def crear_app() -> FastAPI:
    ajustes = cargar_ajustes()

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):
        db = BaseDatos(ajustes.ruta_db)
        config = Configuracion(db)
        if ajustes.simulacion:
            camara = CamaraSimulada(ajustes)
            def crear_enlace(cb):
                return EnlaceSimulado(cb, ajustes.factor_tiempo)
        else:
            camara = CamaraReal(ajustes, config.get("indice_camara"))
            def crear_enlace(cb):
                return EnlaceReal(cb, config.get("puerto_serial"), ajustes.baudios)
        botes = GestorBotes(db, config.get("umbral_aviso_bote"))
        juego = Juego(db)
        orq = Orquestador(ajustes, config, db, camara, cargar_modelo(ajustes), botes, juego, Voz(), Difusor(),
                          crear_enlace)
        app.state.ctx = Contexto(ajustes=ajustes, config=config, db=db, orq=orq, botes=botes, juego=juego)
        await orq.iniciar()
        try:
            yield
        finally:
            await orq.detener()
            db.cerrar()

    app = FastAPI(
        title="Clasificador de residuos — Cyber Insanos",
        description="API del orquestador (contrato: docs/api_contrato.md)",
        version="1.0",
        lifespan=ciclo_de_vida,
    )
    # Red local del evento: el panel puede abrirse desde cualquier laptop o celular
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(router)
    app.mount("/captures", StaticFiles(directory=ajustes.dir_capturas), name="captures")

    @app.exception_handler(EstadoInvalido)
    async def _estado_invalido(_: Request, error: EstadoInvalido):
        return JSONResponse(status_code=409, content={"detail": str(error)})

    @app.exception_handler(ErrorSerial)
    async def _error_serial(_: Request, error: ErrorSerial):
        return JSONResponse(status_code=503, content={"detail": str(error)})

    @app.get("/")
    def raiz() -> dict:
        return {"servicio": "clasificador", "simulacion": ajustes.simulacion,
                "documentacion": "/docs", "estado": "/api/estado", "websocket": "/ws/eventos"}

    @app.websocket("/ws/eventos")
    async def ws_eventos(ws: WebSocket) -> None:
        await ws.accept()
        ctx: Contexto = ws.app.state.ctx
        await ws.send_text(Difusor.mensaje("hola", ctx.orq.estado_dict()))
        ctx.orq.difusor.agregar(ws)
        try:
            while True:
                texto = await ws.receive_text()
                try:
                    datos = json.loads(texto)
                except json.JSONDecodeError:
                    continue
                if isinstance(datos, dict) and datos.get("tipo") == "ping":
                    await ws.send_text(Difusor.mensaje("pong", {}))
        except WebSocketDisconnect:
            pass
        finally:
            ctx.orq.difusor.quitar(ws)

    return app


app = crear_app()
