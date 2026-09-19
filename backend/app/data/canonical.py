from __future__ import annotations

from typing import Any


CANONICAL_FIELDS: dict[str, dict[str, Any]] = {
    "customer_id": {"label": "Cliente", "type": "identifier", "required": True, "description": "Identificador único del cliente."},
    "loan_id": {"label": "Crédito / cuenta", "type": "identifier", "required": True, "description": "Identificador único de la obligación o cuenta."},
    "product_id": {"label": "Producto", "type": "categorical", "required": False, "description": "Producto financiero asociado."},
    "origination_date": {"label": "Fecha de originación", "type": "date", "required": False, "description": "Fecha de desembolso, apertura u originación."},
    "due_date": {"label": "Fecha de vencimiento", "type": "date", "required": False, "description": "Próxima o última fecha contractual de vencimiento."},
    "snapshot_date": {"label": "Fecha de corte", "type": "date", "required": False, "description": "Fecha del snapshot utilizado para análisis histórico."},
    "scheduled_amount": {"label": "Monto programado", "type": "numeric", "required": False, "description": "Monto contractual esperado para pago."},
    "paid_amount": {"label": "Monto pagado", "type": "numeric", "required": False, "description": "Monto efectivamente pagado."},
    "outstanding_principal": {"label": "Saldo de capital", "type": "numeric", "required": True, "description": "Exposición o capital pendiente."},
    "status": {"label": "Estado", "type": "categorical", "required": False, "description": "Estado operativo o contractual."},
    "segment": {"label": "Segmento", "type": "categorical", "required": False, "description": "Segmentación de negocio, riesgo o cobranza."},
    "dpd": {"label": "Días de mora (DPD)", "type": "numeric", "required": False, "description": "Días desde el vencimiento contractual."},
    "pd": {"label": "Probabilidad de default (PD)", "type": "numeric", "required": False, "description": "Probabilidad estimada de incumplimiento."},
    "lgd": {"label": "Pérdida dado default (LGD)", "type": "numeric", "required": False, "description": "Porcentaje esperado de pérdida ante default."},
    "ead": {"label": "Exposición al default (EAD)", "type": "numeric", "required": False, "description": "Exposición utilizada por el modelo de pérdida."},
}


def registry() -> dict[str, Any]:
    return {
        "version": "canonical-financial-model-v1",
        "fields": [{"id": field_id, **metadata} for field_id, metadata in CANONICAL_FIELDS.items()],
        "required_for_ingestion": [field_id for field_id, metadata in CANONICAL_FIELDS.items() if metadata["required"]],
        "design_principle": "Source-specific names map into a stable financial vocabulary before analytics or decisioning.",
    }


def required_fields_for_models(model_catalog: list[dict[str, Any]]) -> set[str]:
    result: set[str] = set()
    for model in model_catalog:
        result.update(model.get("requires") or [])
    return result
