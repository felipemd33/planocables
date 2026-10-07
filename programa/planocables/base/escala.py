"""Escala del dibujo: mm por pt, normalizada a 1:N. Solo biblioteca estandar."""

RIEL_MM = 35.0                   # riel DIN TS35
PT_MM = 25.4 / 72                # 1 pt en mm a escala 1:1
ESCALAS = (0.2, 0.5, 1, 2, 2.5, 3, 4, 5, 6, 8, 10, 15, 20, 25, 50)   # 1:N normalizadas


def snap_escala(mm_pt, tol=0.05):
    """mm/pt -> la escala normalizada 1:N mas cercana, si esta a menos del 5 %"""
    n = mm_pt / PT_MM
    k = min(ESCALAS, key=lambda e: abs(e / n - 1))
    return round(k * PT_MM, 4) if abs(k / n - 1) < tol else round(mm_pt, 4)
