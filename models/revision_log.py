# modulo_diseno/models/revision_log.py

from odoo import models, fields

class RevisionLog(models.Model):
    _name = "design.revision_log"
    _description = "Historial de revisiones del diseño"
    _order = "create_date desc"

    design_id = fields.Many2one("design.design", string="Diseño relacionado", ondelete="cascade", required=True)
    usuario_id = fields.Many2one("res.users", string="Usuario", required=True)
    observaciones = fields.Text("Observaciones")
    tipo = fields.Selection([
        ('validacion_disenador', 'Validación Diseñador'),
        ('validacion_validador', 'Validación Validador'),
        ('rechazo', 'Rechazo'),
        ('aprobacion_cliente', 'Aprobación del Cliente')
    ], string="Tipo de acción", required=True)
