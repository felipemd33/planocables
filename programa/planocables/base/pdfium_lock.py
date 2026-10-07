"""Candado de PDFium: pdfium no admite uso simultaneo desde varios hilos. Es UNO solo para todo el programa:
ocr_raster lo reexporta, asi 'from ocr_raster import PDFIUM_LOCK' (web, eplan, topo, bornes.motor) da este mismo objeto.
No es reentrante: nunca tomarlo dos veces en el mismo hilo. Solo biblioteca estandar."""
import threading

PDFIUM_LOCK = threading.Lock()
